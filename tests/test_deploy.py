#!/usr/bin/env python3
"""Tests for the fleet deploy script.

Deploy runs on every machine, so a broken link table is a fleet-wide failure —
one of the four things the opinions file allows hardening before it happens.
"""

from __future__ import annotations

import json
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


class TestHookRegistration(unittest.TestCase):
    """Settings must be merged, never replaced: the operator has other settings."""

    def test_adds_both_hook_events(self):
        merged = deploy.merge_hooks({})
        self.assertIn("PreToolUse", merged)
        self.assertIn("Stop", merged)

    def test_hook_commands_point_into_this_repo(self):
        for groups in deploy.merge_hooks({}).values():
            for group in groups:
                for handler in group["hooks"]:
                    self.assertTrue(Path(handler["command"]).is_relative_to(deploy.REPO))

    def test_registered_hook_scripts_exist_and_are_executable(self):
        import os
        for groups in deploy.hook_groups().values():
            for group in groups:
                for handler in group["hooks"]:
                    script = Path(handler["command"])
                    self.assertTrue(script.exists(), f"{script} is registered but missing")
                    self.assertTrue(os.access(script, os.X_OK), f"{script} is not executable")

    def test_preserves_a_foreign_hook(self):
        foreign = {"matcher": "Bash", "hooks": [{"type": "command", "command": "/elsewhere/hook.sh"}]}
        merged = deploy.merge_hooks({"PreToolUse": [foreign]})
        self.assertIn(foreign, merged["PreToolUse"])

    def test_preserves_a_foreign_event(self):
        foreign = {"hooks": [{"type": "command", "command": "/elsewhere/start.sh"}]}
        merged = deploy.merge_hooks({"SessionStart": [foreign]})
        self.assertEqual(merged["SessionStart"], [foreign])

    def test_is_idempotent(self):
        once = deploy.merge_hooks({})
        self.assertEqual(deploy.merge_hooks(once), once)

    def test_replaces_a_stale_registration_rather_than_duplicating_it(self):
        stale = {"matcher": "Bash", "hooks": [{"type": "command", "command": str(deploy.HOOK_DIR / "pre_tool_use.py"), "timeout": 999}]}
        merged = deploy.merge_hooks({"PreToolUse": [stale]})
        self.assertEqual(len(merged["PreToolUse"]), 1)
        self.assertEqual(merged["PreToolUse"][0]["hooks"][0]["timeout"], 10)

    def test_output_is_serialisable(self):
        json.dumps(deploy.merge_hooks({}))


if __name__ == "__main__":
    unittest.main()
