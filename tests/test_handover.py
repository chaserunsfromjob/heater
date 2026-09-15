#!/usr/bin/env python3
"""Tests for the handover check.

Its whole value is refusing to say "safe" when it isn't, so the tests are mostly
about the ways a session can look finished and not be.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

import handover  # noqa: E402


class TestStamp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.note = Path(self.tmp.name) / "HANDOVER.md"
        self.patch = mock.patch.object(handover, "HANDOVER", self.note)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_missing_file_is_reported(self):
        self.assertIn("does not exist", handover.check_handover_exists())

    def test_unstamped_file_is_reported(self):
        self.note.write_text("# Handover\n\nno stamp here\n", encoding="utf-8")
        self.assertIn("no <!-- handover-commit", handover.check_handover_exists())

    def test_stamped_file_passes(self):
        self.note.write_text("<!-- handover-commit: 7a4aae9 -->\n", encoding="utf-8")
        self.assertIsNone(handover.check_handover_exists())

    def test_stamp_is_extracted(self):
        self.note.write_text("# Handover\n<!-- handover-commit: abc1234 -->\ntext\n", encoding="utf-8")
        self.assertEqual(handover.stamped_commit(), "abc1234")

    def test_stamp_tolerates_spacing(self):
        self.note.write_text("<!--handover-commit:deadbeef-->\n", encoding="utf-8")
        self.assertEqual(handover.stamped_commit(), "deadbeef")

    def test_full_length_sha_is_accepted(self):
        self.note.write_text("<!-- handover-commit: " + "a" * 40 + " -->\n", encoding="utf-8")
        self.assertEqual(handover.stamped_commit(), "a" * 40)


class TestStaleness(unittest.TestCase):
    """A handover that predates real work is worse than none: it reads current."""

    def stub_git(self, changed_files: str, code: int = 0):
        return mock.patch.object(handover, "git", return_value=(code, changed_files))

    def setUp(self):
        self.patch = mock.patch.object(handover, "stamped_commit", return_value="abc1234")
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_nothing_changed_is_current(self):
        with self.stub_git(""):
            self.assertIsNone(handover.check_handover_current())

    def test_only_the_note_changed_is_current(self):
        with self.stub_git("HANDOVER.md"):
            self.assertIsNone(handover.check_handover_current())

    def test_real_work_since_the_stamp_is_stale(self):
        with self.stub_git("HANDOVER.md\nrules/global.md"):
            problem = handover.check_handover_current()
            self.assertIn("work has landed since", problem)
            self.assertIn("rules/global.md", problem)

    def test_unknown_commit_is_reported(self):
        with self.stub_git("bad object", code=128):
            self.assertIn("not in this repository", handover.check_handover_current())

    def test_a_long_list_is_truncated(self):
        with self.stub_git("\n".join(f"f{n}.py" for n in range(9))):
            self.assertIn("and more", handover.check_handover_current())


class TestWorktree(unittest.TestCase):
    def test_dirty_tree_is_reported(self):
        with mock.patch.object(handover, "git", return_value=(0, " M a.py\n?? b.py")):
            self.assertIn("2 file(s)", handover.check_worktree_clean())

    def test_clean_tree_passes(self):
        with mock.patch.object(handover, "git", return_value=(0, "")):
            self.assertIsNone(handover.check_worktree_clean())


class TestPushed(unittest.TestCase):
    def test_unpushed_commits_are_reported(self):
        with mock.patch.object(handover, "git", side_effect=[(0, "main"), (0, "ref"), (0, "3")]):
            self.assertIn("3 commit(s) not pushed", handover.check_pushed())

    def test_everything_pushed_passes(self):
        with mock.patch.object(handover, "git", side_effect=[(0, "main"), (0, "ref"), (0, "0")]):
            self.assertIsNone(handover.check_pushed())

    def test_missing_remote_branch_is_reported(self):
        with mock.patch.object(handover, "git", side_effect=[(0, "feature"), (1, "not found")]):
            self.assertIn("no counterpart on origin", handover.check_pushed())


class TestSkillDocument(unittest.TestCase):
    """The procedure has to exist and name the script, or nobody runs it."""

    def test_skill_exists(self):
        self.assertTrue((ROOT / "skills" / "handover" / "SKILL.md").exists())

    def test_skill_names_the_check_script(self):
        text = (ROOT / "skills" / "handover" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("bin/handover.py", text)

    def test_skill_has_frontmatter_with_a_description(self):
        text = (ROOT / "skills" / "handover" / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("description:", text.split("---")[1])


class TestRunsEndToEnd(unittest.TestCase):
    def test_quick_mode_exits_cleanly_and_prints_every_check(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "bin" / "handover.py"), "--quick"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertIn("handover note", result.stdout)
        self.assertIn("working tree clean", result.stdout)
        self.assertIn(result.returncode, (0, 1))


if __name__ == "__main__":
    unittest.main()
