#!/usr/bin/env python3
"""Tests for step 6: dispatch records, the role loader, the heartbeat, and bearings.

The stoker runs unattended, so the failures that matter are the quiet ones: a
dispatch left open, a role file that silently fails to load, a heartbeat that
never says anything, and a hook that wedges a session it cannot help.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "hooks"))

import bearings  # noqa: E402
import dispatch  # noqa: E402
import session_start  # noqa: E402


class StoreCase(unittest.TestCase):
    ENV = ("HEATER_DISPATCHES_DIR", "HEATER_QUEUE_DIR", "HEATER_TASKS_DIR",
           "HEATER_REVIEWS_DIR", "HEATER_SUITES_DIR", "HEATER_LOG_DIR", "HEATER_ROLE")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous = {k: os.environ.get(k) for k in self.ENV}
        root = Path(self.tmp.name)
        for key in self.ENV[:-1]:
            os.environ[key] = str(root / key.lower())
        os.environ.pop("HEATER_ROLE", None)

    def tearDown(self):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()


class TestDispatchRecords(StoreCase):
    def test_open_then_live(self):
        record = dispatch.open_dispatch("fix auth", project="api")
        self.assertEqual([d["id"] for d in dispatch.live()], [record["id"]])

    def test_closing_removes_it_from_live(self):
        record = dispatch.open_dispatch("fix auth")
        dispatch.close_dispatch(record["id"], "pushed")
        self.assertEqual(dispatch.live(), [])

    def test_a_closed_dispatch_is_kept_not_deleted(self):
        record = dispatch.open_dispatch("fix auth")
        dispatch.close_dispatch(record["id"], "failed", "could not reproduce")
        import jsonstore
        stored = jsonstore.load(dispatch.dispatches_dir())
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["note"], "could not reproduce")

    def test_cannot_close_twice(self):
        record = dispatch.open_dispatch("fix auth")
        dispatch.close_dispatch(record["id"], "pushed")
        with self.assertRaises(ValueError):
            dispatch.close_dispatch(record["id"], "failed")

    def test_unknown_outcome_is_refused(self):
        record = dispatch.open_dispatch("fix auth")
        with self.assertRaises(ValueError):
            dispatch.close_dispatch(record["id"], "finished-ish")

    def test_unknown_dispatch_is_refused(self):
        with self.assertRaises(ValueError):
            dispatch.close_dispatch("deadbeefcafe", "pushed")

    def test_empty_task_is_refused(self):
        with self.assertRaises(ValueError):
            dispatch.open_dispatch("   ")

    def test_oldest_first_so_the_stuck_one_surfaces(self):
        first = dispatch.open_dispatch("one")
        second = dispatch.open_dispatch("two")
        self.assertEqual([d["id"] for d in dispatch.live()], [first["id"], second["id"]])


class TestBriefComposition(StoreCase):
    def test_brief_carries_the_task_and_done_condition(self):
        record = dispatch.open_dispatch("add backoff", done_when="a test proves it")
        brief = dispatch.compose_brief(record)
        self.assertIn("add backoff", brief)
        self.assertIn("a test proves it", brief)

    def test_brief_wraps_the_worker_standing_instructions(self):
        brief = dispatch.compose_brief(dispatch.open_dispatch("x"))
        self.assertIn("Work the task in your brief", brief,
                      "a brief without the wrapper is a worker with no standing instructions")

    def test_brief_names_its_own_dispatch_id(self):
        record = dispatch.open_dispatch("x")
        self.assertIn(record["id"], dispatch.compose_brief(record))

    def test_worker_wrapper_exists_on_disk(self):
        self.assertTrue(dispatch.worker_wrapper().strip(), "roles/worker.md is missing or empty")


class TestRoleLoader(StoreCase):
    def test_stoker_gets_the_stoker_rules(self):
        os.environ["HEATER_ROLE"] = "stoker"
        text = session_start.handle({"source": "startup"})["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Dispatch a worker for every code change", text)

    def test_worker_gets_the_worker_rules(self):
        os.environ["HEATER_ROLE"] = "worker"
        text = session_start.handle({"source": "startup"})["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Work the task in your brief", text)

    def test_an_unknown_role_loads_no_rules(self):
        os.environ["HEATER_ROLE"] = "gardener"
        decision = session_start.handle({"source": "startup"})
        text = decision.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertNotIn("# Stoker", text)

    def test_stoker_is_told_what_is_waiting(self):
        os.environ["HEATER_ROLE"] = "stoker"
        text = session_start.handle({"source": "startup"})["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Fleet state:", text)

    def test_a_worker_is_not_given_the_stoker_rules(self):
        os.environ["HEATER_ROLE"] = "worker"
        text = session_start.handle({"source": "startup"})["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("# Stoker", text)

    def test_every_role_file_has_a_loader_path(self):
        for role_file in (ROOT / "roles").glob("*.md"):
            self.assertTrue(session_start.role_rules(role_file.stem).strip(),
                            f"roles/{role_file.name} would never load")


class TestHooksFailOpen(unittest.TestCase):
    """A hook that wedges a session is worse than no hook at all."""

    def run_hook(self, name: str, stdin: str, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(ROOT / "hooks" / name)],
                              input=stdin, capture_output=True, text=True, timeout=30,
                              env={**os.environ, **(env or {})})

    def test_session_start_survives_garbage(self):
        self.assertEqual(self.run_hook("session_start.py", "not json").returncode, 0)

    def test_post_tool_use_survives_garbage(self):
        self.assertEqual(self.run_hook("post_tool_use.py", "not json").returncode, 0)

    def test_session_end_survives_garbage(self):
        self.assertEqual(self.run_hook("session_end.py", "not json").returncode, 0)

    def test_post_tool_use_survives_an_unwritable_heartbeat_directory(self):
        result = self.run_hook("post_tool_use.py", json.dumps({"session_id": "s", "tool_name": "Bash"}),
                               {"HEATER_LOG_DIR": "/proc/nonexistent/logs"})
        self.assertEqual(result.returncode, 0)

    def test_post_tool_use_emits_nothing_into_the_transcript(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_hook("post_tool_use.py",
                                   json.dumps({"session_id": "abc", "tool_name": "Bash"}),
                                   {"HEATER_LOG_DIR": str(Path(tmp) / "logs")})
            self.assertEqual(result.stdout.strip(), "", "a heartbeat must be silent")

    def test_heartbeat_is_written_and_names_the_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_hook("post_tool_use.py",
                          json.dumps({"session_id": "abc123", "tool_name": "Bash"}),
                          {"HEATER_LOG_DIR": str(Path(tmp) / "logs"), "HEATER_ROLE": "worker"})
            beat = json.loads((Path(tmp) / "heartbeat" / "abc123.json").read_text())
            self.assertEqual((beat["tool"], beat["role"]), ("Bash", "worker"))

    def test_heartbeat_filename_cannot_escape_its_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_hook("post_tool_use.py",
                          json.dumps({"session_id": "../../escaped", "tool_name": "Bash"}),
                          {"HEATER_LOG_DIR": str(Path(tmp) / "logs")})
            written = list((Path(tmp) / "heartbeat").glob("*.json"))
            self.assertEqual(len(written), 1)
            self.assertNotIn("..", written[0].name)

    def test_session_end_clears_the_heartbeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"HEATER_LOG_DIR": str(Path(tmp) / "logs")}
            self.run_hook("post_tool_use.py", json.dumps({"session_id": "s1", "tool_name": "Bash"}), env)
            self.assertTrue((Path(tmp) / "heartbeat" / "s1.json").exists())
            self.run_hook("session_end.py", json.dumps({"session_id": "s1", "reason": "clear"}), env)
            self.assertFalse((Path(tmp) / "heartbeat" / "s1.json").exists(),
                             "a finished session must stop looking alive")


class TestBearings(StoreCase):
    def test_reports_every_section(self):
        text, _ = bearings.report()
        for heading in ("Fleet", "Dispatches out", "Heartbeats", "This machine",
                        "Fleet repository", "Review load"):
            self.assertIn(f"## {heading}", text)

    def test_is_stamped_with_when_it_ran(self):
        self.assertIn("bearings as of", bearings.report()[0])

    def test_an_open_dispatch_needs_attention(self):
        dispatch.open_dispatch("still out")
        self.assertTrue(bearings.report()[1])

    def test_an_unjudged_finding_needs_attention(self):
        import queue
        queue.add("finding", "something odd")
        self.assertTrue(bearings.report()[1])

    def test_a_closed_dispatch_does_not_linger(self):
        record = dispatch.open_dispatch("done")
        dispatch.close_dispatch(record["id"], "pushed")
        self.assertNotIn(record["id"], bearings.report()[0])

    def test_survives_empty_stores(self):
        text, _ = bearings.report()
        self.assertIn("0 queue item(s) undelivered", text)


class TestRoutingIsNowEnforced(unittest.TestCase):
    def test_the_constant_is_on(self):
        """Step 6 is the step that flips it. If this fails, the README build order lies."""
        import pre_tool_use
        self.assertTrue(pre_tool_use.ENFORCE_STOKER_ROUTING)


class TestOpeningTheRepoIsTheStoker(unittest.TestCase):
    """The operator talks to one session, and opening the fleet repository is
    what makes it the stoker. The marker stays authoritative where it is set."""

    def setUp(self):
        import heater_hook
        self.hook = heater_hook
        self.saved = os.environ.get("HEATER_ROLE")
        os.environ.pop("HEATER_ROLE", None)
        self.project_dir = os.environ.pop("CLAUDE_PROJECT_DIR", None)

    def tearDown(self):
        for name, value in (("HEATER_ROLE", self.saved), ("CLAUDE_PROJECT_DIR", self.project_dir)):
            os.environ.pop(name, None)
            if value is not None:
                os.environ[name] = value

    def test_unmarked_in_the_repo_is_the_stoker(self):
        self.assertEqual(self.hook.role({"cwd": str(ROOT)}), "stoker")

    def test_unmarked_in_a_subdirectory_is_the_stoker(self):
        self.assertEqual(self.hook.role({"cwd": str(ROOT / "tools")}), "stoker")

    def test_unmarked_elsewhere_has_no_role(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            self.assertEqual(self.hook.role({"cwd": elsewhere}), "")

    def test_the_marker_still_wins(self):
        os.environ["HEATER_ROLE"] = "worker"
        self.assertEqual(self.hook.role({"cwd": str(ROOT)}), "worker")

    def test_a_reviewer_in_the_repo_is_still_a_reviewer(self):
        """The reviewer's write ban hangs off this. Defaulting over it would
        hand a judge the power to edit what it is judging."""
        os.environ["HEATER_ROLE"] = "reviewer"
        self.assertEqual(self.hook.role({"cwd": str(ROOT)}), "reviewer")

    def test_payload_outranks_the_process_working_directory(self):
        """The suite runs inside the repo, so a payload naming somewhere else
        must not be overruled by where the hook process happens to sit."""
        with tempfile.TemporaryDirectory() as elsewhere:
            self.assertFalse(self.hook.in_fleet_repo({"cwd": elsewhere}))

    def test_routing_enforcement_still_reads_the_marker_only(self):
        """Otherwise the fleet-repo default would silently retire the
        unrouted-write warning."""
        self.assertFalse(self.hook.is_dispatched())

    def test_the_session_start_hook_loads_the_stoker_rules(self):
        done = subprocess.run([sys.executable, str(ROOT / "hooks" / "session_start.py")],
                              input=json.dumps({"cwd": str(ROOT), "source": "startup"}),
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("stoker", done.stdout.lower())


class TestProjectMemory(unittest.TestCase):
    def test_claude_md_exists_and_names_the_role(self):
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("stoker", text.lower())

    def test_it_points_at_the_rules_rather_than_restating_them(self):
        """Opinion 8: a rule lives in exactly one place."""
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("rules/global.md", text)
        self.assertLess(len(text.splitlines()), 40, "CLAUDE.md rides in every session; keep it small")


class TestHandoverArchivesTheSession(unittest.TestCase):
    skill = ROOT / "skills" / "handover" / "SKILL.md"

    def test_the_procedure_ends_by_archiving(self):
        self.assertIn("Archive the session", self.skill.read_text(encoding="utf-8"))

    def test_it_forbids_seeding_the_next_session_from_this_one(self):
        """A seeded successor arrives with no checkout, so it is never filed
        under the project and the operator cannot find it."""
        self.assertIn("Do not open the next session from this one",
                      self.skill.read_text(encoding="utf-8"))

    def test_it_archives_only_after_the_push(self):
        text = self.skill.read_text(encoding="utf-8")
        self.assertLess(text.index("Commit the handover and push it"), text.index("Archive the session"))


class TestStokerLauncher(unittest.TestCase):
    """The operator is not a programmer. The launcher is the whole interface,
    so a broken one is a broken system, not a broken convenience."""

    script = ROOT / "bin" / "stoker.sh"

    def test_it_exists_and_runs(self):
        import os
        self.assertTrue(self.script.is_file(), f"{self.script} is missing")
        self.assertTrue(os.access(self.script, os.X_OK), f"{self.script} is not executable")

    def test_it_sets_the_role_the_session_start_hook_reads(self):
        self.assertIn("HEATER_ROLE=stoker", self.script.read_text(encoding="utf-8"))

    def test_the_role_it_sets_has_a_rules_file(self):
        self.assertTrue((ROOT / "roles" / "stoker.md").is_file())

    def test_it_starts_under_remote_control(self):
        """Remote Control is what lets the operator talk to the stoker from the
        app without the stoker giving up the machine it governs."""
        self.assertIn("--remote-control", self.script.read_text(encoding="utf-8"))

    def test_it_names_the_session_so_it_can_be_found_in_the_app(self):
        """An unnamed session lands in the list as a generated hostname phrase,
        which is not a thing the operator can pick out."""
        self.assertIn("heater stoker", self.script.read_text(encoding="utf-8"))

    def test_it_enters_the_repo_so_the_session_starts_in_the_right_folder(self):
        self.assertIn('cd "$(dirname "$0")/.."', self.script.read_text(encoding="utf-8"))

    def test_it_is_syntactically_valid_shell(self):
        done = subprocess.run(["bash", "-n", str(self.script)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)


if __name__ == "__main__":
    unittest.main()
