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
from unittest import mock

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

class TestStokerRouting(unittest.TestCase):
    """Opinion 2 wants a denial. Until step 6 there is no stoker to route through,
    so the warning is switched off rather than fired at something nobody can act on."""

    def test_silent_while_routing_is_unenforced(self):
        with mock.patch.object(pre_tool_use, "ENFORCE_STOKER_ROUTING", False):
            decision, _ = verdict("git commit -m 'hand written'", None)
        self.assertIsNone(decision, "an unactionable warning on every commit is noise")

    def test_warns_once_enforcement_is_switched_on(self):
        with mock.patch.object(pre_tool_use, "ENFORCE_STOKER_ROUTING", True):
            decision, message = verdict("git commit -m 'hand written'", None)
        self.assertEqual(decision, "allow", "step 6 makes this a warning, not a block")
        self.assertIn("stoker", message)

    def test_a_dispatched_session_is_silent_either_way(self):
        with mock.patch.object(pre_tool_use, "ENFORCE_STOKER_ROUTING", True):
            decision, _ = verdict("git commit -m 'dispatched'", "worker")
        self.assertIsNone(decision)


class TestReviewerIsJudgeOnly(unittest.TestCase):
    """Bash is a write tool, so the tool allowlist cannot make a reviewer judge-only.
    The guard does it instead."""

    def assertReviewerDenied(self, command: str):
        decision, message = verdict(command, "reviewer")
        self.assertEqual(decision, "deny", f"a reviewer must not be able to run {command!r}")
        self.assertIn("judges only", message)

    def assertReviewerAllowed(self, command: str):
        decision, _ = verdict(command, "reviewer")
        self.assertIsNone(decision, f"a reviewer must be able to run {command!r} to prove the change works")

    def test_cannot_commit(self):
        self.assertReviewerDenied("git commit -m 'sneaky'")

    def test_cannot_stage(self):
        self.assertReviewerDenied("git add src/x.py")

    def test_cannot_delete_files(self):
        self.assertReviewerDenied("rm -f src/x.py")

    def test_cannot_edit_in_place(self):
        self.assertReviewerDenied("sed -i 's/a/b/' src/x.py")

    def test_cannot_redirect_into_a_file(self):
        self.assertReviewerDenied("cat a.py > b.py")

    def test_can_run_the_suite(self):
        self.assertReviewerAllowed("python3 -m unittest discover -s tests")

    def test_can_run_the_gate(self):
        self.assertReviewerAllowed("bash bin/gate.sh")

    def test_can_discard_stderr(self):
        self.assertReviewerAllowed("pytest 2>&1 | tail -20")

    def test_can_silence_output(self):
        self.assertReviewerAllowed("ls >/dev/null")

    def test_can_search(self):
        self.assertReviewerAllowed("grep -rn 'def handle' hooks/")

    def test_write_tool_is_denied(self):
        decision = pre_tool_use.handle({"tool_name": "Write", "tool_input": {"file_path": "/tmp/x.py"}})
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_edit_tool_is_denied(self):
        decision = pre_tool_use.handle({"tool_name": "Edit", "tool_input": {"file_path": "/tmp/x.py"}})
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_read_tool_is_allowed(self):
        self.assertEqual(pre_tool_use.handle({"tool_name": "Read", "tool_input": {"file_path": "/tmp/x.py"}}), {})

    def setUp(self):
        self.previous = os.environ.get("HEATER_ROLE")
        os.environ["HEATER_ROLE"] = "reviewer"

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("HEATER_ROLE", None)
        else:
            os.environ["HEATER_ROLE"] = self.previous

    def test_a_fixer_may_still_write(self):
        os.environ["HEATER_ROLE"] = "fixer"
        decision = pre_tool_use.handle({"tool_name": "Write", "tool_input": {"file_path": "/tmp/x.py"}})
        self.assertEqual(decision, {}, "the lockdown must apply to reviewers only")


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
