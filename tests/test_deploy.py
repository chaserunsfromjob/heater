#!/usr/bin/env python3
"""Tests for the fleet deploy script.

Deploy runs on every machine, so a broken link table is a fleet-wide failure —
one of the four things the opinions file allows hardening before it happens.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

import deploy  # noqa: E402


class TestLinkTable(unittest.TestCase):
    def test_every_source_exists(self):
        missing = [str(src) for src in deploy.LINKS.values() if not src.exists()]
        self.assertEqual(missing, [], "deploy would link to a file that is not in the repo")

    def test_every_source_is_inside_the_repo(self):
        for source in deploy.LINKS.values():
            self.assertTrue(source.resolve().is_relative_to(deploy.REPO), f"{source} escapes the repo")

    def test_no_two_targets_share_a_source_path(self):
        self.assertEqual(len(set(deploy.LINKS)), len(deploy.LINKS))


class TestDeployBehaviour(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "global.md"
        self.source.write_text("- Never force-push.\n", encoding="utf-8")
        self.target = self.root / "home" / "CLAUDE.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_creates_the_link_and_parent_directory(self):
        self.assertEqual(deploy.deploy(self.target, self.source), "linked")
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(self.target.read_text(encoding="utf-8"), "- Never force-push.\n")

    def test_is_idempotent(self):
        deploy.deploy(self.target, self.source)
        self.assertEqual(deploy.deploy(self.target, self.source), "already correct")

    def test_preserves_an_existing_real_file(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text("hand written rules\n", encoding="utf-8")
        result = deploy.deploy(self.target, self.source)
        self.assertIn("moved existing file", result)
        aside = self.target.with_name(self.target.name + ".pre-heater")
        self.assertEqual(aside.read_text(encoding="utf-8"), "hand written rules\n")

    def test_repoints_a_stale_link(self):
        stale = self.root / "old.md"
        stale.write_text("stale\n", encoding="utf-8")
        self.target.parent.mkdir(parents=True)
        self.target.symlink_to(stale)
        self.assertEqual(deploy.deploy(self.target, self.source), "relinked")
        self.assertEqual(self.target.resolve(), self.source.resolve())


class TestDescribe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "global.md"
        self.source.write_text("- Never force-push.\n", encoding="utf-8")
        self.target = self.root / "CLAUDE.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_reports_not_deployed(self):
        self.assertEqual(deploy.describe(self.target, self.source), "not deployed")

    def test_reports_missing_source(self):
        self.assertIn("source missing", deploy.describe(self.target, self.root / "gone.md"))

    def test_reports_occupied_by_real_file(self):
        self.target.write_text("x\n", encoding="utf-8")
        self.assertEqual(deploy.describe(self.target, self.source), "occupied by a real file")

    def test_silent_when_correct(self):
        deploy.deploy(self.target, self.source)
        self.assertIsNone(deploy.describe(self.target, self.source))


if __name__ == "__main__":
    unittest.main()
