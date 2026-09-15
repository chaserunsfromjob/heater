#!/usr/bin/env python3
"""Tests for the review and suite stores.

Opinion 4 says a number in a decision comes from a live query. These tests pin
the query, because every downstream claim about cost and review load rests on it.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import store  # noqa: E402


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous = {k: os.environ.get(k) for k in ("HEATER_REVIEWS_DIR", "HEATER_SUITES_DIR")}
        os.environ["HEATER_REVIEWS_DIR"] = str(Path(self.tmp.name) / "reviews")
        os.environ["HEATER_SUITES_DIR"] = str(Path(self.tmp.name) / "suites")

    def tearDown(self):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()


class TestRecording(StoreCase):
    def test_round_is_written_and_read_back(self):
        store.record_review("auth", 1, "default", "fail", findings=2)
        result = store.query()
        self.assertEqual(result["reviews"]["rounds"], 1)
        self.assertEqual(result["reviews"]["failed_rounds"], 1)

    def test_rejects_unknown_lens(self):
        with self.assertRaises(ValueError):
            store.record_review("auth", 1, "vibes", "pass")

    def test_rejects_unknown_verdict(self):
        with self.assertRaises(ValueError):
            store.record_review("auth", 1, "default", "maybe")

    def test_rejects_round_zero(self):
        with self.assertRaises(ValueError):
            store.record_review("auth", 0, "default", "pass")

    def test_rejects_unnamed_change(self):
        with self.assertRaises(ValueError):
            store.record_review("   ", 1, "default", "pass")

    def test_cannot_pass_with_substantive_findings(self):
        """The loop lands on a pass; a pass carrying real findings would land them too."""
        with self.assertRaises(ValueError):
            store.record_review("auth", 2, "default", "pass", findings=3)

    def test_can_pass_with_wording_findings(self):
        store.record_review("auth", 3, "default", "pass", findings=2, wording_only=True)
        self.assertEqual(store.query()["reviews"]["wording_only_rounds"], 1)

    def test_suite_run_is_recorded(self):
        store.record_suite("bin/gate.sh", True, duration_s=1.0)
        store.record_suite("bin/gate.sh", False)
        result = store.query()["suites"]
        self.assertEqual((result["runs"], result["passed"], result["failed"]), (2, 1, 1))

    def test_suite_requires_a_command(self):
        with self.assertRaises(ValueError):
            store.record_suite("  ", True)


class TestAggregates(StoreCase):
    def seed(self):
        store.record_review("auth", 1, "default", "fail", findings=3, cost_usd=0.40,
                            insertions=30, deletions=5)
        store.record_review("auth", 2, "default", "pass", cost_usd=0.30)
        store.record_review("parser", 1, "default", "pass", cost_usd=0.20)

    def test_counts_changes_not_rounds(self):
        self.seed()
        reviews = store.query()["reviews"]
        self.assertEqual(reviews["rounds"], 3)
        self.assertEqual(reviews["changes"], 2)

    def test_rounds_per_change(self):
        self.seed()
        reviews = store.query()["reviews"]
        self.assertEqual(reviews["rounds_per_change_mean"], 1.5)
        self.assertEqual(reviews["rounds_per_change_max"], 2)

    def test_first_round_passes_counted(self):
        self.seed()
        self.assertEqual(store.query()["reviews"]["passed_first_round"], 1)

    def test_change_needing_a_fix_is_not_a_first_round_pass(self):
        self.seed()
        self.assertEqual(store.query()["reviews"]["changes_landed"], 2)

    def test_cost_totals(self):
        self.seed()
        reviews = store.query()["reviews"]
        self.assertAlmostEqual(reviews["cost_usd_total"], 0.90)
        self.assertAlmostEqual(reviews["cost_usd_per_change"], 0.45)

    def test_lines_changed_totalled(self):
        self.seed()
        self.assertEqual(store.query()["reviews"]["lines_changed"], 35)

    def test_missing_cost_is_surfaced_as_a_hole(self):
        store.record_review("auth", 1, "default", "pass")
        self.assertEqual(store.query()["reviews"]["rounds_missing_cost"], 1)
        self.assertIn("hole in collection", store.render(store.query()))

    def test_project_filter(self):
        store.record_review("a", 1, "default", "pass", project="api")
        store.record_review("b", 1, "default", "pass", project="web")
        self.assertEqual(store.query(project="api")["reviews"]["rounds"], 1)

    def test_window_excludes_older_rounds(self):
        self.seed()
        old = store.record_review("ancient", 1, "default", "pass")
        path = next(Path(os.environ["HEATER_REVIEWS_DIR"]).glob(f"*{old['id']}.json"))
        path.write_text(path.read_text().replace(old["created"], "2020-01-01T00:00:00.000000+00:00"))
        self.assertEqual(store.query(days=7)["reviews"]["changes"], 2)

    def test_query_is_always_stamped(self):
        """A number without a time is a claim, not evidence."""
        self.assertIn("as_of", store.query())
        self.assertIn("as of", store.render(store.query()))

    def test_empty_store_does_not_divide_by_zero(self):
        result = store.query()
        self.assertEqual(result["reviews"]["rounds"], 0)
        self.assertIsNone(result["reviews"]["rounds_per_change_mean"])
        store.render(result)


class TestAgentsAndSkills(unittest.TestCase):
    """A misfiled agent or skill fails silently: Claude Code simply never loads it."""

    def frontmatter(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"), f"{path} has no frontmatter")
        return text.split("---")[1]

    def test_reviewer_and_fixer_exist(self):
        for name in ("reviewer", "fixer"):
            self.assertTrue((ROOT / "agents" / f"{name}.md").exists())

    def test_agents_declare_name_and_description(self):
        for agent in (ROOT / "agents").glob("*.md"):
            front = self.frontmatter(agent)
            self.assertIn("name:", front)
            self.assertIn("description:", front)

    def test_agent_name_matches_its_filename(self):
        for agent in (ROOT / "agents").glob("*.md"):
            front = self.frontmatter(agent)
            declared = [l.split("name:", 1)[1].strip() for l in front.splitlines() if l.startswith("name:")][0]
            self.assertEqual(declared, agent.stem)

    def test_reviewer_has_no_write_tools(self):
        front = self.frontmatter(ROOT / "agents" / "reviewer.md")
        tools = [l for l in front.splitlines() if l.startswith("tools:")][0]
        for forbidden in ("Write", "Edit", "NotebookEdit"):
            self.assertNotIn(forbidden, tools, "a reviewer that can write is not judge-only")

    def test_fixer_can_write(self):
        front = self.frontmatter(ROOT / "agents" / "fixer.md")
        tools = [l for l in front.splitlines() if l.startswith("tools:")][0]
        self.assertIn("Edit", tools)

    def test_every_skill_directory_has_a_skill_file(self):
        for skill in (ROOT / "skills").iterdir():
            if skill.is_dir():
                self.assertTrue((skill / "SKILL.md").is_file(), f"{skill} has no SKILL.md")

    def test_review_skill_names_the_store_command(self):
        text = (ROOT / "skills" / "adversarial-review" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("bin/store.py", text)


if __name__ == "__main__":
    unittest.main()
