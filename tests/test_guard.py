#!/usr/bin/env python3
"""Tests for the PreToolUse guard.

The guard is the thing standing between a dispatched worker and an unrecoverable
mistake at 3am, so both halves are pinned: what it must deny, and what it must
never block.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

import pre_tool_use  # noqa: E402


def verdict(command: str, env_role: str | None = None) -> tuple[str | None, str]:
    """Return (permissionDecision, message) for a Bash command."""
    previous = os.environ.get("HEATER_ROLE")
    if env_role is None:
        os.environ.pop("HEATER_ROLE", None)
    else:
        os.environ["HEATER_ROLE"] = env_role
    try:
        decision = pre_tool_use.handle({"tool_name": "Bash", "tool_input": {"command": command}})
    finally:
        if previous is None:
            os.environ.pop("HEATER_ROLE", None)
        else:
            os.environ["HEATER_ROLE"] = previous
    specific = decision.get("hookSpecificOutput", {})
    message = specific.get("permissionDecisionReason") or decision.get("systemMessage") or ""
    return specific.get("permissionDecision"), message


class TestDenies(unittest.TestCase):
    def assertDenied(self, command: str):
        decision, message = verdict(command, "worker")
        self.assertEqual(decision, "deny", f"{command!r} was not denied")
        self.assertIn("rules/global.md", message, "a denial must name the rule it enforces")

    def test_force_push_long_flag(self):
        self.assertDenied("git push --force origin main")

    def test_force_push_short_flag(self):
        self.assertDenied("git push -f origin main")

    def test_force_with_lease_is_still_a_force_push(self):
        self.assertDenied("git push --force-with-lease origin main")

    def test_force_push_via_refspec(self):
        self.assertDenied("git push origin +main:main")

    def test_filter_branch(self):
        self.assertDenied("git filter-branch --tree-filter 'rm -f x' HEAD")

    def test_reflog_expire(self):
        self.assertDenied("git reflog expire --expire=now --all")

    def test_rm_rf_root(self):
        self.assertDenied("rm -rf /")

    def test_rm_rf_home(self):
        self.assertDenied("rm -rf ~")

    def test_rm_rf_wildcard(self):
        self.assertDenied("rm -rf *")

    def test_reading_dotenv(self):
        self.assertDenied("cat .env")

    def test_reading_a_scoped_dotenv(self):
        self.assertDenied("head -5 .env.production")

    def test_reading_a_private_key(self):
        self.assertDenied("cat ~/.ssh/id_ed25519")

    def test_reading_aws_credentials(self):
        self.assertDenied("cat ~/.aws/credentials")

    def test_env_dump(self):
        self.assertDenied("printenv | sort")

    def test_echoing_a_secret_variable(self):
        self.assertDenied("echo $ANTHROPIC_API_KEY")


class TestWarnsWithoutBlocking(unittest.TestCase):
    def assertWarned(self, command: str, role: str = "worker"):
        decision, message = verdict(command, role)
        self.assertEqual(decision, "allow", f"{command!r} must not be blocked")
        self.assertIn("rules/global.md", message, "a warning must name the rule")

    def test_git_add_all(self):
        self.assertWarned("git add -A")

    def test_git_add_dot(self):
        self.assertWarned("git add .")

    def test_hard_reset(self):
        self.assertWarned("git reset --hard HEAD~1")

    def test_git_clean(self):
        self.assertWarned("git clean -fd")

    def test_amend(self):
        self.assertWarned("git commit --amend -m 'fix'")

    def test_undispatched_git_write_warns(self):
        decision, message = verdict("git commit -m 'hand written'", None)
        self.assertEqual(decision, "allow", "the guard must not lock the operator out before step 6")
        self.assertIn("stoker", message)


class TestAllowsOrdinaryWork(unittest.TestCase):
    def assertAllowed(self, command: str, role: str = "worker"):
        decision, _ = verdict(command, role)
        self.assertIsNone(decision, f"{command!r} should have passed silently, got {decision}")

    def test_plain_listing(self):
        self.assertAllowed("ls -la")

    def test_ordinary_push(self):
        self.assertAllowed("git push origin feature-branch")

    def test_dispatched_commit_is_silent(self):
        self.assertAllowed("git commit -m 'real work'", "stoker")

    def test_staging_explicit_paths(self):
        self.assertAllowed("git add src/parse.py tests/test_parse.py")

    def test_deleting_a_spent_branch(self):
        self.assertAllowed("git branch -D spent-feature")

    def test_removing_a_named_directory(self):
        self.assertAllowed("rm -rf build/")

    def test_reading_ordinary_source(self):
        self.assertAllowed("cat src/environment.py")

    def test_a_file_merely_named_like_a_secret_word(self):
        self.assertAllowed("cat docs/credentials-policy.md")


class TestFileTools(unittest.TestCase):
    def test_reading_a_secret_file_is_denied(self):
        decision = pre_tool_use.handle({"tool_name": "Read", "tool_input": {"file_path": "/srv/app/.env"}})
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_reading_ordinary_source_is_silent(self):
        decision = pre_tool_use.handle({"tool_name": "Read", "tool_input": {"file_path": "/srv/app/main.py"}})
        self.assertEqual(decision, {})


class TestFailsOpen(unittest.TestCase):
    """A broken guard is an annoyance. A guard that blocks everything is a fleet halt."""

    def run_hook(self, stdin: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(ROOT / "hooks" / "pre_tool_use.py")],
            input=stdin, capture_output=True, text=True, timeout=20,
        )

    def test_malformed_json_exits_zero_and_allows(self):
        result = self.run_hook("this is not json")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_empty_stdin_exits_zero(self):
        result = self.run_hook("")
        self.assertEqual(result.returncode, 0)

    def test_unexpected_shape_exits_zero(self):
        result = self.run_hook(json.dumps({"tool_name": "Bash", "tool_input": "not a dict"}))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_json_array_exits_zero(self):
        result = self.run_hook("[1, 2, 3]")
        self.assertEqual(result.returncode, 0)

    def test_denial_output_is_valid_json(self):
        result = self.run_hook(json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push -f"}}))
        self.assertEqual(result.returncode, 0)
        parsed = json.loads(result.stdout)
        self.assertEqual(parsed["hookSpecificOutput"]["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
