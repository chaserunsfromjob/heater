#!/usr/bin/env python3
"""Tests for the review and suite stores.

Opinion 4 says a number in a decision comes from a live query. These tests pin
the query, because every downstream claim about cost and review load rests on it.
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dispatch  # noqa: E402
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

    def test_a_change_still_in_review_has_not_landed(self):
        """Neither seeded change has reached the end of its review loop.

        auth has one pass behind a fail and parser has a single pass, and review
        ends on two consecutive rounds that pass. Counting either as landed is
        the stale-pass reading `dispatch.reviewed` dropped.
        """
        self.seed()
        self.assertEqual(store.query()["reviews"]["changes_landed"], 0)

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


class TestChangesLandedAgreesWithDispatch(StoreCase):
    """Task 917775c34006: the query counted a change landed if any round passed.

    The same reading of a stale pass that `dispatch.reviewed` dropped, left in
    the figure every report of what the fleet delivered is drawn from. Two
    readers of one store have to give one answer, so both ask `reviewloop`.
    """

    def landed(self, days: int | None = None) -> int:
        return store.query(days=days)["reviews"]["changes_landed"]

    def end_review_of(self, change: str, first: int = 1) -> None:
        store.record_review(change, first, "default", "pass", findings=2, wording_only=True)
        store.record_review(change, first + 1, "default", "pass")

    def test_a_pass_that_later_rounds_failed_is_not_landed(self):
        self.end_review_of("auth")
        store.record_review("auth", 3, "default", "fail", findings=4)
        self.assertEqual(self.landed(), 0,
                         "the latest round failed; an older pass did not land it")

    def test_a_single_pass_is_not_landed(self):
        store.record_review("auth", 1, "default", "pass")
        self.assertEqual(self.landed(), 0, "review ends on two consecutive rounds")

    def test_a_review_that_ended_is_landed(self):
        self.end_review_of("auth")
        self.assertEqual(self.landed(), 1)

    def test_the_figure_agrees_with_the_dispatch_store(self):
        """One store, two readers, one answer: the point of the shared judgement."""
        self.end_review_of("landed-change")
        self.end_review_of("reopened")
        store.record_review("reopened", 3, "default", "fail", findings=1)
        store.record_review("fresh", 1, "default", "pass")
        store.record_review("failing", 1, "default", "fail", findings=9)

        names = ("landed-change", "reopened", "fresh", "failing")
        by_dispatch = [c for c in names if dispatch.reviewed(c)]

        self.assertEqual(by_dispatch, ["landed-change"])
        self.assertEqual(self.landed(), len(by_dispatch))
        self.assertEqual(self.landed(days=7), len(by_dispatch))

    def backdate(self, record: dict, days: float) -> None:
        """Move one recorded round's clock back, in the file it already lives in.

        Rewritten in place rather than re-recorded: the filename carries the
        timestamp, so a second write would leave two files with one id.
        """
        when = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="microseconds")
        path = next(Path(os.environ["HEATER_REVIEWS_DIR"]).glob(f"*{record['id']}.json"))
        path.write_text(path.read_text().replace(record["created"], when), encoding="utf-8")

    def test_a_review_that_began_before_the_window_and_ended_inside_it_counts(self):
        """The change landed this week; only its opening round is a month old.

        Windowing the rounds before asking whether the loop ended cuts that
        first round off, leaves one pass behind, and reports nothing landed —
        while the sweep, which reads the whole history, lands it.
        """
        first = store.record_review("auth", 1, "default", "pass", findings=2, wording_only=True)
        store.record_review("auth", 2, "default", "pass")
        self.backdate(first, 30)

        self.assertTrue(dispatch.reviewed("auth"))
        self.assertEqual(self.landed(days=7), 1,
                         "a change is landed by its whole history, not by the window")

    def test_a_review_that_ended_before_the_window_is_not_counted_in_it(self):
        """Attributed to the window by the round that ended it, which is old."""
        first = store.record_review("auth", 1, "default", "pass", findings=2, wording_only=True)
        second = store.record_review("auth", 2, "default", "pass")
        self.backdate(first, 40)
        self.backdate(second, 30)

        self.assertEqual(self.landed(days=7), 0, "it landed last month, not this week")
        self.assertEqual(self.landed(), 1, "all time still has it")

    def test_the_query_command_still_runs_over_a_window(self):
        self.end_review_of("auth")
        store.record_suite("bin/gate.sh", True, duration_s=1.0)
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = store.main(["store.py", "query", "--days", "7"])
        self.assertEqual(code, 0)
        self.assertIn("(1 landed)", printed.getvalue())


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
