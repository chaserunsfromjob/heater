#!/usr/bin/env python3
"""Tests for step 6: dispatch records, the role loader, the heartbeat, and bearings.

The stoker runs unattended, so the failures that matter are the quiet ones: a
dispatch left open, a role file that silently fails to load, a heartbeat that
never says anything, and a hook that wedges a session it cannot help.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "hooks"))

import bearings  # noqa: E402
import deploy  # noqa: E402
import dispatch  # noqa: E402
import session_start  # noqa: E402
import stoker  # noqa: E402


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

    def test_a_refused_lease_has_a_route_other_than_waiting(self):
        """Below the disk floor with nothing left to reclaim, waiting is stalling:
        the stoker asks instead, and the queue is how it asks."""
        text = (ROOT / "roles" / "stoker.md").read_text(encoding="utf-8")
        self.assertIn("--kind escalation", text)

    def test_every_role_file_has_a_loader_path(self):
        for role_file in (ROOT / "roles").glob("*.md"):
            self.assertTrue(session_start.role_rules(role_file.stem).strip(),
                            f"roles/{role_file.name} would never load")


class TestMachineDriftNote(unittest.TestCase):
    """A session whose own repo registers these hooks must not be told the
    machine's registration is stale: the hooks are running — this is one of them
    — so the line is false here, and a false warning teaches the reader to
    ignore the true one later."""

    HOOKS_STALE = "hook registration out of date"
    NO_LINE = "no status line, so nothing can see context usage and handover cannot fire"

    def note(self, *, covered: bool, settings: str | None,
             cwd: str | None = None, links: dict | None = None) -> str:
        with mock.patch.object(deploy, "project_settings_current", return_value=covered), \
             mock.patch.object(deploy, "settings_drift", return_value=settings), \
             mock.patch.object(deploy, "links", return_value=links or {}):
            return session_start.drift_note({"cwd": cwd or str(ROOT)})

    def stale_link(self) -> dict:
        return {Path(self.tmp.name) / "CLAUDE.md": ROOT / "rules" / "global.md"}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_committed_project_file_silences_the_registration_line(self):
        self.assertEqual(self.note(covered=True, settings=self.HOOKS_STALE), "")

    def test_it_silences_the_status_line_warning_too(self):
        self.assertEqual(self.note(covered=True, settings=self.NO_LINE), "")

    def test_a_missing_or_stale_project_file_still_warns(self):
        self.assertIn(self.HOOKS_STALE, self.note(covered=False, settings=self.HOOKS_STALE))

    def test_a_missing_status_line_still_warns_without_the_project_file(self):
        self.assertIn("handover cannot fire", self.note(covered=False, settings=self.NO_LINE))

    def test_a_session_outside_this_repo_still_hears_about_the_machine(self):
        """Elsewhere the machine's registration is the only thing switching hooks
        on, so this repo's committed file says nothing about that session."""
        self.assertIn(self.HOOKS_STALE,
                      self.note(covered=True, settings=self.HOOKS_STALE, cwd=self.tmp.name))

    def test_link_drift_is_reported_whether_or_not_the_project_file_covers_hooks(self):
        """CLAUDE.md, agents and skills reach a session only as machine links,
        which no project settings file can stand in for."""
        for covered in (True, False):
            note = self.note(covered=covered, settings=self.HOOKS_STALE, links=self.stale_link())
            self.assertIn("CLAUDE.md: not deployed", note)

    def test_a_covered_machine_with_no_link_drift_says_nothing_at_all(self):
        self.assertEqual(self.note(covered=True, settings=None), "")


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

    def test_no_session_id_writes_no_heartbeat(self):
        """Nothing can ever clear a beat with no session id, so never write one."""
        with tempfile.TemporaryDirectory() as tmp:
            for payload in ({"tool_name": "Bash"}, {"session_id": "", "tool_name": "Bash"},
                            {"session_id": "   ", "tool_name": "Bash"}):
                result = self.run_hook("post_tool_use.py", json.dumps(payload),
                                       {"HEATER_LOG_DIR": str(Path(tmp) / "logs")})
                self.assertEqual(result.returncode, 0)
                self.assertEqual(list((Path(tmp) / "heartbeat").glob("*.json")), [],
                                 f"{payload} left a heartbeat nothing will ever retire")

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
        self.assertTrue(self.script.is_file(), f"{self.script} is missing")
        self.assertTrue(os.access(self.script, os.X_OK), f"{self.script} is not executable")

    def test_it_is_only_an_entry_point(self):
        """bin/ holds entry points; a module there shadows one in tools/."""
        self.assertIn("exec python3 tools/stoker.py", self.script.read_text(encoding="utf-8"))

    def test_it_sets_the_role_the_session_start_hook_reads(self):
        self.assertEqual(stoker.child_env()["HEATER_ROLE"], "stoker")

    def test_it_gives_the_session_an_identity_the_hook_can_read(self):
        """The hook reads it from its own environment and writes it into the
        marker, which is how the supervisor knows the marker is its child's."""
        with mock.patch.dict(os.environ, {stoker.CHILD_ENV: "abc123"}):
            self.assertEqual(stoker.child_env("abc123")[stoker.CHILD_ENV], "abc123")
            self.assertEqual(stoker.child_token(), "abc123")

    def test_the_role_it_sets_has_a_rules_file(self):
        self.assertTrue((ROOT / "roles" / "stoker.md").is_file())

    def test_it_starts_under_remote_control(self):
        """Remote Control is what lets the operator talk to the stoker from the
        app without the stoker giving up the machine it governs."""
        self.assertIn("--remote-control", stoker.command())

    def test_it_names_the_session_so_it_can_be_found_in_the_app(self):
        """An unnamed session lands in the list as a generated hostname phrase,
        which is not a thing the operator can pick out."""
        self.assertIn("heater stoker", stoker.command())

    def test_the_session_name_can_be_overridden(self):
        with mock.patch.dict(os.environ, {"HEATER_SESSION_NAME": "other"}):
            self.assertIn("other", stoker.command())
            self.assertNotIn("heater stoker", stoker.command())

    def test_every_launch_carries_an_opening_instruction(self):
        """A fresh interactive session sits idle forever with nobody to type."""
        self.assertIn(stoker.INITIAL_PROMPT, stoker.command())
        self.assertIn("bearings", stoker.INITIAL_PROMPT)
        self.assertIn("HANDOVER.md", stoker.INITIAL_PROMPT)

    def test_it_enters_the_repo_so_the_session_starts_in_the_right_folder(self):
        self.assertIn('cd "$(dirname "$0")/.."', self.script.read_text(encoding="utf-8"))

    def test_it_is_syntactically_valid_shell(self):
        done = subprocess.run(["bash", "-n", str(self.script)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)


STUB_CLAUDE = '''#!/usr/bin/env python3
"""Stands in for `claude`. Records how it was launched, then waits to be ended.

Ctrl-C is ignored here on purpose, because `claude` ignores it too: one press
cancels the turn, and the session decides that for itself. A stub that died of
it would hide a supervisor that leaves its session running.
"""
import json, os, signal, sys, time
from pathlib import Path

signal.signal(signal.SIGINT, signal.SIG_IGN)

log = Path(os.environ["STUB_LOG"])
state = Path(os.environ["HEATER_STATE_DIR"])
token = os.environ.get("HEATER_STOKER_CHILD")


def written():
    if not log.exists():
        return []
    return [json.loads(l) for l in log.read_text().splitlines() if l.strip()]


def record(entry):
    with log.open("a") as handle:
        handle.write(json.dumps(entry) + "\\n")


seen = sum(1 for r in written() if "launch" in r)
record({
    "launch": seen + 1,
    "argv": sys.argv[1:],
    "role": os.environ.get("HEATER_ROLE"),
    "token": token,
    "owner": os.environ.get("HEATER_STOKER_OWNER"),
    "pid": os.getpid(),
    "cwd": os.getcwd(),
    "marker_present": (state / "handover-complete").exists(),
})

mode = os.environ.get("STUB_MODE", "sleep")
if mode == "exit" or (mode == "handoff" and seen >= 1):
    sys.exit(int(os.environ.get("STUB_EXIT", "0")))
if mode in ("mark", "mark_then_exit", "hook"):
    # What the Stop hook does once the handover is written, current and pushed,
    # by the same call the hook makes. A hook that loses the one marker path to
    # another supervisor's session runs again at the next turn boundary, which
    # is what the retry stands in for.
    sys.path.insert(0, os.environ["STUB_REPO"] + "/tools")
    import stoker as marking
    while True:
        wrote = marking.mark_complete("now", token, f"s{seen + 1}")
        record({"mark": seen + 1, "token": token, "wrote": wrote,
                "marked": marking.marker_token()})
        if wrote or mode != "hook":
            break
        time.sleep(0.1)
    if mode == "mark_then_exit":
        # Handed over, and then ended by itself inside one poll interval.
        sys.exit(0)
if mode == "crash":
    # Shut down by something outside the supervisor, after a real session's worth
    # of life: what an out-of-memory kill looks like from here.
    time.sleep(float(os.environ.get("STUB_LIVE", "0.2")))
    os.kill(os.getpid(), signal.SIGKILL)
time.sleep(60)
'''


class TestStokerSupervisor(unittest.TestCase):
    """The handoff has to cost the operator nothing, so the supervisor is the
    thing that must not need watching. Every test here runs it for real against
    a stub `claude`, because what matters is process behaviour, not intent."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.state = root / "state"
        self.state.mkdir()
        self.log = root / "launches.jsonl"
        self.binaries = root / "bin"
        self.binaries.mkdir()
        stub = self.binaries / "claude"
        stub.write_text(STUB_CLAUDE, encoding="utf-8")
        stub.chmod(0o755)

    def marker(self) -> Path:
        return self.state / "handover-complete"

    def environment(self, **extra: str) -> dict[str, str]:
        return {**os.environ,
                "PATH": f"{self.binaries}{os.pathsep}{os.environ.get('PATH', '')}",
                "HEATER_STATE_DIR": str(self.state),
                "HEATER_LOG_DIR": str(Path(self.tmp.name) / "logs"),
                "STUB_LOG": str(self.log),
                "STUB_REPO": str(ROOT),
                "HEATER_STOKER_POLL": "0.05",
                "HEATER_STOKER_PAUSE": "0.05",
                "HEATER_STOKER_GRACE": "0.05",
                "HEATER_STOKER_KILL_AFTER": "5",
                **extra}

    def records(self, path: Path | None = None) -> list[dict]:
        path = path or self.log
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    def launches(self, path: Path | None = None) -> list[dict]:
        """Only the records a launch wrote; a session can write others too."""
        return [r for r in self.records(path) if "launch" in r]

    def supervisor(self, **extra: str) -> subprocess.Popen:
        return subprocess.Popen([sys.executable, str(ROOT / "tools" / "stoker.py")],
                                env=self.environment(**extra), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)

    def run_supervisor(self, timeout: int = 60, **extra: str):
        done = self.supervisor(**extra)
        try:
            out, err = done.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            done.kill()
            out, err = done.communicate()
            self.fail(f"the supervisor never exited\nstdout: {out}\nstderr: {err}")
        return done.returncode, out, err

    def hook_events(self) -> list[dict]:
        path = Path(self.tmp.name) / "logs" / "hooks.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    def live_owner(self) -> dict:
        """A supervisor that is still running: this test process stands in for one."""
        return {"owner_pid": os.getpid(), "owner_start": stoker.process_start(os.getpid())}

    def dead_owner(self) -> dict:
        """A supervisor that is gone. The start time is what makes it certain:
        the number can be handed out again, but not with that moment attached."""
        spent = subprocess.Popen([sys.executable, "-c", "pass"])
        spent.wait()
        return {"owner_pid": spent.pid, "owner_start": "Thu Jan  1 00:00:00 1970"}

    def hand_over(self, token: str | None, owner: dict | None = None) -> None:
        """Write the marker exactly as the Stop hook in that session would."""
        self.marker().write_text(
            json.dumps({"at": "2026-01-01T00:00:00+00:00", "token": token, "session": "s",
                        **(owner if owner is not None else self.live_owner())}) + "\n",
            encoding="utf-8")

    def wait_until(self, condition, timeout: float = 30.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if condition():
                return True
            time.sleep(0.02)
        return False

    def wait_for_launches(self, count: int, process: subprocess.Popen, timeout: float = 30.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if len(self.launches()) >= count:
                return self.launches()
            if process.poll() is not None and len(self.launches()) < count:
                break
            time.sleep(0.05)
        process.kill()
        self.fail(f"only {len(self.launches())} launch(es) after waiting for {count}")

    def test_the_launch_carries_the_role_the_name_and_a_prompt(self):
        code, _, err = self.run_supervisor(STUB_MODE="exit", HEATER_STOKER_MIN_LIFETIME="0")
        self.assertEqual(code, 0, err)
        record = self.launches()[0]
        self.assertEqual(record["role"], "stoker")
        self.assertIn("--remote-control", record["argv"])
        self.assertIn("heater stoker", record["argv"])
        self.assertIn(stoker.INITIAL_PROMPT, record["argv"])
        self.assertEqual(Path(record["cwd"]).resolve(), ROOT.resolve())

    def test_the_marker_ends_the_session_and_a_fresh_one_follows(self):
        """This is the handoff. Nobody types anything for it to happen."""
        running = self.supervisor(STUB_MODE="handoff", HEATER_STOKER_MIN_LIFETIME="0")
        first = self.wait_for_launches(1, running)
        self.hand_over(first[0]["token"])
        records = self.wait_for_launches(2, running)
        running.communicate(timeout=30)
        self.assertEqual(len(records), 2)
        self.assertFalse(records[1]["marker_present"],
                         "the marker must be gone, or the new session dies on its first poll")
        self.assertFalse(self.marker().exists())

    def test_a_marker_it_did_not_write_survives_the_launch(self):
        """Deleting it would answer for the supervisor still waiting on it.
        It cannot end this supervisor's session either way: no other identity
        ever matches the one this launch was given."""
        self.hand_over("some-other-session")
        code, _, err = self.run_supervisor(STUB_MODE="exit", HEATER_STOKER_MIN_LIFETIME="0")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.launches()), 1, "it refused to open a session at all")
        self.assertTrue(self.marker().exists(), "another session's mark is not ours to delete")
        self.assertTrue(any(e["event"] == "stoker_foreign_marker" for e in self.hook_events()),
                        "it must say it saw a mark it was leaving alone")

    def test_a_marker_left_by_a_supervisor_that_is_gone_is_reclaimed(self):
        """The machine restarted mid-session and the marker outlived the
        supervisor that was waiting on it. Left where it is, it takes the one
        marker path forever and no session here can ever hand over again."""
        self.hand_over("a-session-of-the-supervisor-that-died", owner=self.dead_owner())
        running = self.supervisor(STUB_MODE="handoff", HEATER_STOKER_MIN_LIFETIME="0")
        first = self.wait_for_launches(1, running)
        self.assertTrue(self.wait_until(lambda: not self.marker().exists(), 15),
                        "a marker nobody is waiting on was left to block every handoff")
        self.assertTrue(any(e["event"] == "stoker_stale_marker" for e in self.hook_events()),
                        "it must say what it reclaimed and whose it said it was")
        self.hand_over(first[0]["token"])
        records = self.wait_for_launches(2, running)
        running.communicate(timeout=30)
        self.assertEqual(len(records), 2, "the handoff never came back after the reclaim")

    def test_a_session_that_ends_as_it_hands_over_is_still_a_handover(self):
        """The session wrote its marker and then ended inside one poll interval.
        Reading the exit first called that the operator closing the session and
        stopped the supervisor, so the handoff quietly needed a person again."""
        running = self.supervisor(STUB_MODE="mark_then_exit", HEATER_STOKER_MIN_LIFETIME="0",
                                  HEATER_STOKER_MAX_HANDOFFS="2")
        try:
            _, err = running.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            running.kill()
            self.fail("it never stopped")
        self.assertEqual(len(self.launches()), 3,
                         "a session that ended as it handed over was taken for an ending")
        self.assertIn("3 times", err, "the sessions it opened were handoffs, not stops")

    def test_two_supervisors_in_one_folder_each_end_only_their_own_session(self):
        """One marker path, two supervisors. Each session's mark has to reach
        the supervisor that launched it, and neither session may be left
        running with nobody watching it."""
        second = Path(self.tmp.name) / "launches-b.jsonl"
        shared = {"STUB_MODE": "hook", "HEATER_STOKER_MIN_LIFETIME": "0",
                  "HEATER_STOKER_POLL": "0.1", "HEATER_STOKER_MAX_HANDOFFS": "500"}
        first = self.supervisor(**shared)
        other = self.supervisor(**shared, STUB_LOG=str(second))
        try:
            handed_over = self.wait_until(
                lambda: len(self.launches()) >= 2 and len(self.launches(second)) >= 2, 40)
            self.assertTrue(handed_over,
                            f"a session's mark never reached its own supervisor: "
                            f"{len(self.launches())} and {len(self.launches(second))} launch(es)")
            self.assertIsNone(first.poll(), "one supervisor stopped on the other's mark")
            self.assertIsNone(other.poll(), "one supervisor stopped on the other's mark")
            for log in (self.log, second):
                tokens = {r["token"] for r in self.launches(log)}
                marks = [r for r in self.records(log) if "mark" in r]
                self.assertTrue(marks, "no session ever asked to be ended")
                for mark in marks:
                    if mark["wrote"]:
                        self.assertEqual(mark["marked"], mark["token"],
                                         "a session's mark was overwritten by another's")
                self.assertTrue(tokens.isdisjoint(
                    {r["token"] for r in self.launches(second if log is self.log else self.log)}),
                    "two supervisors handed out the same identity")
        finally:
            for process in (first, other):
                process.terminate()
                try:
                    process.communicate(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()

    def test_a_session_shut_down_by_the_machine_is_opened_again(self):
        """Running out of memory is not the operator stopping the stoker."""
        running = self.supervisor(STUB_MODE="sleep", HEATER_STOKER_MIN_LIFETIME="0.5")
        first = self.wait_for_launches(1, running)
        time.sleep(1.0)
        os.kill(first[0]["pid"], signal.SIGKILL)
        records = self.wait_for_launches(2, running)
        running.terminate()
        running.communicate(timeout=30)
        self.assertEqual(len(records), 2, "a session the machine killed was taken for a stop")

    def test_a_session_ended_from_outside_by_hand_stops_the_supervisor(self):
        """The plain terminate is what a closing terminal sends to everything in
        it, and what `kill` sends by default. That is a person, not a machine."""
        running = self.supervisor(STUB_MODE="sleep", HEATER_STOKER_MIN_LIFETIME="0.5")
        first = self.wait_for_launches(1, running)
        time.sleep(1.0)
        os.kill(first[0]["pid"], signal.SIGTERM)
        try:
            running.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            running.kill()
            self.fail("the supervisor kept going after the session was ended by hand")
        self.assertEqual(len(self.launches()), 1, "it reopened a session the operator ended")
        self.assertEqual(running.returncode, 128 + int(signal.SIGTERM))

    def test_endless_shutdowns_stop_it(self):
        """Whatever is killing the session can keep killing it, and a session
        that lived a while never trips the never-started rule."""
        running = self.supervisor(STUB_MODE="crash", HEATER_STOKER_MIN_LIFETIME="0",
                                  HEATER_STOKER_MAX_CRASHES="2", STUB_LIVE="0.2")
        try:
            _, err = running.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            running.kill()
            self.fail("it kept reopening a session that was being killed")
        self.assertNotEqual(running.returncode, 0)
        self.assertEqual(len(self.launches()), 3, "it stopped at the wrong count")
        self.assertIn("3 times", err, "the message must name how many it saw")
        self.assertIn("more than the 2", err, "and how many it expects")
        self.assertNotIn("Traceback", err)
        for jargon in ("SIGKILL", "SIGTERM", "exit code", "subprocess", "marker", "token"):
            self.assertNotIn(jargon, err, "the operator reads this; keep it in plain words")

    def test_an_unreadable_marker_does_not_kill_the_next_session(self):
        self.marker().write_text("left behind\n", encoding="utf-8")
        code, _, err = self.run_supervisor(STUB_MODE="exit", HEATER_STOKER_MIN_LIFETIME="0")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.launches()), 1)

    def test_the_session_ending_by_itself_ends_the_supervisor(self):
        """/exit and Ctrl-C have to still stop the stoker."""
        code, _, _ = self.run_supervisor(STUB_MODE="exit", STUB_EXIT="7",
                                         HEATER_STOKER_MIN_LIFETIME="0")
        self.assertEqual(code, 7, "the supervisor exits with the session's own code")
        self.assertEqual(len(self.launches()), 1, "it must not reopen a session the operator ended")

    def test_three_instant_deaths_stop_it(self):
        """A claude that cannot start at all must not spin forever."""
        code, _, err = self.run_supervisor(STUB_MODE="exit", STUB_EXIT="9",
                                           HEATER_STOKER_MIN_LIFETIME="30")
        self.assertEqual(len(self.launches()), 3)
        self.assertEqual(code, 9)
        self.assertIn("3 times in a row", err)
        for jargon in ("SIGTERM", "exit code", "subprocess", "marker"):
            self.assertNotIn(jargon, err, "the operator reads this; keep it in plain words")

    def test_stopping_the_supervisor_takes_the_session_with_it(self):
        """Closing the terminal must not leave a session running with nobody watching."""
        running = self.supervisor(STUB_MODE="sleep", HEATER_STOKER_MIN_LIFETIME="30")
        self.wait_for_launches(1, running)
        os.kill(running.pid, signal.SIGTERM)
        try:
            running.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            running.kill()
            self.fail("the supervisor ignored SIGTERM")
        self.assertEqual(len(self.launches()), 1, "it must not reopen after being stopped")

    def test_every_launch_gets_an_identity_of_its_own(self):
        """The marker is one shared path, so the token in it is the only thing
        that says which session asked to be ended."""
        running = self.supervisor(STUB_MODE="handoff", HEATER_STOKER_MIN_LIFETIME="0")
        first = self.wait_for_launches(1, running)
        self.hand_over(first[0]["token"])
        records = self.wait_for_launches(2, running)
        running.communicate(timeout=30)
        tokens = [r["token"] for r in records]
        self.assertTrue(all(tokens), "a launch with no identity cannot be told apart")
        self.assertEqual(len(set(tokens)), 2, "a reused identity makes a stale marker fatal")

    def test_a_marker_from_a_session_it_did_not_start_is_left_alone(self):
        """Opening a plain `claude` in this folder makes another stoker. Its
        handover must not end the supervised session in its place."""
        running = self.supervisor(STUB_MODE="sleep", HEATER_STOKER_MIN_LIFETIME="30")
        self.wait_for_launches(1, running)
        self.hand_over("some-other-session")
        noticed = self.wait_until(
            lambda: any(e["event"] == "stoker_foreign_marker" for e in self.hook_events()), 15)
        self.assertTrue(noticed, "it must say that it saw a marker and whose it was")
        self.assertIsNone(running.poll(), "the supervised session was ended by somebody else's marker")
        self.assertEqual(len(self.launches()), 1)
        self.assertTrue(self.marker().exists(), "another session's marker is not ours to delete")
        os.kill(running.pid, signal.SIGTERM)
        running.communicate(timeout=30)

    def test_stopping_during_the_pause_between_sessions_opens_no_new_one(self):
        """A `kill` that lands in the gap after a handoff has to stop the
        supervisor too, not be slept through and a fresh session opened over it."""
        running = self.supervisor(STUB_MODE="sleep", HEATER_STOKER_MIN_LIFETIME="0",
                                  HEATER_STOKER_PAUSE="10")
        first = self.wait_for_launches(1, running)
        self.hand_over(first[0]["token"])
        paused = self.wait_until(
            lambda: any(e["event"] == "stoker_restart" for e in self.hook_events()), 20)
        self.assertTrue(paused, "the handoff never finished, so the pause was never reached")
        os.kill(running.pid, signal.SIGTERM)
        try:
            # Well inside the ten-second pause: a supervisor that only notices
            # once the pause is over has already sat through being stopped.
            running.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            running.kill()
            self.fail("the supervisor slept through being stopped")
        self.assertEqual(len(self.launches()), 1, "it opened a session after being stopped")

    def test_fast_handoffs_are_never_mistaken_for_launches_that_will_not_start(self):
        """A session that hands over did its job, however quickly it got there."""
        running = self.supervisor(STUB_MODE="mark", HEATER_STOKER_MIN_LIFETIME="30")
        self.wait_for_launches(4, running)
        self.assertIsNone(running.poll(), "handoffs counted as failed launches")
        os.kill(running.pid, signal.SIGTERM)
        _, err = running.communicate(timeout=30)
        self.assertNotIn("times in a row", err)

    def test_endless_fast_handoffs_stop_it(self):
        """Handing over costs a session nothing, so one that opens with nothing
        to do can hand over again forever. Something has to bound that."""
        running = self.supervisor(STUB_MODE="mark", HEATER_STOKER_MIN_LIFETIME="0",
                                  HEATER_STOKER_MAX_HANDOFFS="2")
        try:
            _, err = running.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            running.kill()
            self.fail("it kept replacing a session that finished instantly")
        self.assertNotEqual(running.returncode, 0)
        self.assertEqual(len(self.launches()), 3, "it stopped at the wrong count")
        self.assertIn("3 times", err, "the message must name how many it saw")
        self.assertIn("more than the 2", err, "and how many it expects")
        self.assertNotIn("Traceback", err)
        for jargon in ("SIGTERM", "exit code", "subprocess", "marker", "token"):
            self.assertNotIn(jargon, err, "the operator reads this; keep it in plain words")

    def test_the_handoff_bound_is_a_rate_not_a_total(self):
        """A stoker that hands over normally runs for weeks. Only handoffs
        packed into one window are evidence of anything being wrong."""
        self.assertEqual(stoker.DEFAULT_MAX_HANDOFFS, 5)
        self.assertEqual(stoker.DEFAULT_HANDOFF_WINDOW, 3600.0)
        with mock.patch.dict(os.environ, {"HEATER_STOKER_MAX_HANDOFFS": "9",
                                          "HEATER_STOKER_HANDOFF_WINDOW": "60"}):
            self.assertEqual(stoker.limits().max_handoffs, 9)
            self.assertEqual(stoker.limits().handoff_window, 60)

    def alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, PermissionError):
            return False
        return True

    def assert_stopped_cleanly(self, running: subprocess.Popen, pid: int):
        try:
            _, err = running.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            running.kill()
            self.fail("Ctrl-C did not stop the supervisor")
        self.assertNotIn("Traceback", err, "the operator pressed a key and got a page of Python")
        self.assertTrue(self.wait_until(lambda: not self.alive(pid), 10),
                        "the session outlived the supervisor that was watching it")
        self.assertEqual(len(self.launches()), 1, "it opened a session after being stopped")

    def test_ctrl_c_while_a_finished_session_is_being_given_its_last_breath(self):
        """Ctrl-C is the documented way to stop this, and the gap between a
        session finishing and being closed is no exception to that."""
        running = self.supervisor(STUB_MODE="sleep", HEATER_STOKER_MIN_LIFETIME="0",
                                  HEATER_STOKER_GRACE="10")
        first = self.wait_for_launches(1, running)
        self.hand_over(first[0]["token"])
        self.assertTrue(self.wait_until(
            lambda: any(e["event"] == "handover_marker_seen" for e in self.hook_events()), 20),
            "the handoff was never noticed, so that gap was never reached")
        os.kill(running.pid, signal.SIGINT)
        self.assert_stopped_cleanly(running, first[0]["pid"])

    def test_ctrl_c_during_the_pause_between_sessions(self):
        running = self.supervisor(STUB_MODE="sleep", HEATER_STOKER_MIN_LIFETIME="0",
                                  HEATER_STOKER_PAUSE="10")
        first = self.wait_for_launches(1, running)
        self.hand_over(first[0]["token"])
        self.assertTrue(self.wait_until(
            lambda: any(e["event"] == "stoker_restart" for e in self.hook_events()), 20),
            "the handoff never finished, so the pause was never reached")
        os.kill(running.pid, signal.SIGINT)
        self.assert_stopped_cleanly(running, first[0]["pid"])

    def test_a_missing_claude_says_so_rather_than_tracebacking(self):
        done = subprocess.run([sys.executable, str(ROOT / "tools" / "stoker.py")],
                              env={**self.environment(), "PATH": str(Path(self.tmp.name) / "empty")},
                              capture_output=True, text=True, timeout=60)
        self.assertNotEqual(done.returncode, 0)
        self.assertNotIn("Traceback", done.stderr)
        self.assertIn("Claude", done.stderr)


class FakeChild:
    """A session that ignores everything, so the timing under test is the
    supervisor's own and not a real process's scheduling."""

    pid = 4321

    def __init__(self, lifetime: float | None = None):
        self.started = time.monotonic()
        self.lifetime = lifetime
        self.terminated_at: float | None = None

    def poll(self):
        if self.terminated_at is not None:
            return 0
        if self.lifetime is not None and time.monotonic() - self.started >= self.lifetime:
            return 0
        return None

    def terminate(self):
        self.terminated_at = time.monotonic()

    def wait(self, timeout=None):
        return 0


class TestWatchingForTheMarker(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # Marks written here name this process as the supervisor waiting on
        # them, which is a supervisor that is very much still running.
        patch = mock.patch.dict(os.environ, {"HEATER_STATE_DIR": self.tmp.name,
                                             stoker.OWNER_ENV: stoker.own_owner()})
        patch.start()
        self.addCleanup(patch.stop)

    def test_the_session_gets_a_breath_before_it_is_ended(self):
        """The Stop hook that wrote the marker has to return and its closing
        message has to reach the screen, and neither is instant."""
        stoker.mark_complete("now", "mine", "s1")
        child = FakeChild()
        started = time.monotonic()
        _, handed_over, _ = stoker.watch(child, 0.01, "mine", grace=0.4, kill_after=1.0)
        self.assertTrue(handed_over)
        self.assertGreaterEqual(child.terminated_at - started, 0.35,
                                "it ended the session before the hook could finish")

    def test_the_grace_is_short_and_separate_from_the_bound_on_a_hang(self):
        self.assertEqual(stoker.DEFAULT_GRACE, 2.0)
        self.assertLess(stoker.DEFAULT_GRACE, stoker.DEFAULT_KILL_AFTER)

    def test_the_grace_is_configurable(self):
        with mock.patch.dict(os.environ, {"HEATER_STOKER_GRACE": "0.25"}):
            self.assertEqual(stoker._number("HEATER_STOKER_GRACE", stoker.DEFAULT_GRACE), 0.25)

    def test_a_marker_naming_another_session_is_not_a_handover(self):
        stoker.mark_complete("now", "somebody-else", "s2")
        _, handed_over, _ = stoker.watch(FakeChild(lifetime=0.2), 0.01, "mine",
                                         grace=0.01, kill_after=1.0)
        self.assertFalse(handed_over, "it ended its session on another session's marker")
        self.assertTrue(stoker.marker_path().exists())

    def test_an_unreadable_marker_is_not_a_handover_either(self):
        stoker.marker_path().write_text("left behind by an older version\n", encoding="utf-8")
        _, handed_over, _ = stoker.watch(FakeChild(lifetime=0.2), 0.01, "mine",
                                         grace=0.01, kill_after=1.0)
        self.assertFalse(handed_over)

    def test_a_session_already_gone_when_its_marker_is_read_still_handed_over(self):
        """It wrote the mark and ended inside one poll interval. Calling that an
        ending stops the supervisor, and the successor never opens."""
        stoker.mark_complete("now", "mine", "s1")
        _, handed_over, _ = stoker.watch(FakeChild(lifetime=0), 0.01, "mine",
                                         grace=0.01, kill_after=1.0)
        self.assertTrue(handed_over, "the handoff was read as the operator closing the session")

    def test_a_marker_nobody_is_waiting_on_is_cleared_out_of_the_way(self):
        """Left there it takes the one path forever, and every later session in
        this folder loses its way of saying it has finished."""
        stoker.marker_path().write_text(
            json.dumps({"at": "earlier", "token": "gone", "session": "s0",
                        "owner_pid": 999999, "owner_start": "Thu Jan  1 00:00:00 1970"}) + "\n",
            encoding="utf-8")
        _, handed_over, _ = stoker.watch(FakeChild(lifetime=0.2), 0.01, "mine",
                                         grace=0.01, kill_after=1.0)
        self.assertFalse(handed_over, "it ended its session on a marker that was not its own")
        self.assertFalse(stoker.marker_path().exists())


class TestWhoEndedTheSession(unittest.TestCase):
    """Stopping the stoker is the operator's to do. A session killed from
    underneath it is not that, and treating it as that is the stoker silently
    not running any more."""

    def test_a_session_that_ends_on_its_own_is_the_operator(self):
        for code in (0, 1, 7):
            self.assertFalse(stoker.is_crash(code), f"exit {code} was read as a shutdown")

    def test_ctrl_c_and_a_plain_terminate_are_the_operator(self):
        for name in ("SIGINT", "SIGTERM"):
            self.assertFalse(stoker.is_crash(-int(getattr(signal, name))), name)

    def test_anything_else_killed_a_session_that_was_still_working(self):
        for name in ("SIGKILL", "SIGSEGV", "SIGABRT", "SIGBUS"):
            self.assertTrue(stoker.is_crash(-int(getattr(signal, name))), name)

    def test_how_many_shutdowns_it_will_reopen_before_it_stops(self):
        self.assertEqual(stoker.DEFAULT_MAX_CRASHES, 3)
        with mock.patch.dict(os.environ, {"HEATER_STOKER_MAX_CRASHES": "7"}):
            self.assertEqual(stoker.limits().max_crashes, 7)


class TestHandoverMarker(unittest.TestCase):
    """The marker is the whole signal between the hook and the supervisor."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # A supervised session: it was told which session it is, and which
        # supervisor is waiting on it. Both go into the mark it leaves.
        patch = mock.patch.dict(os.environ, {"HEATER_STATE_DIR": self.tmp.name,
                                             stoker.CHILD_ENV: "tok",
                                             stoker.OWNER_ENV: stoker.own_owner()})
        patch.start()
        self.addCleanup(patch.stop)

    def test_it_lives_beside_the_other_session_state(self):
        self.assertEqual(stoker.marker_path().parent, Path(self.tmp.name))

    def test_marking_writes_it_once(self):
        self.assertTrue(stoker.mark_complete("first"))
        self.assertFalse(stoker.mark_complete("second"), "the marker's existence is the guard")
        self.assertIn("first", stoker.marker_path().read_text(encoding="utf-8"))

    def test_it_names_the_session_that_asked_to_be_ended(self):
        stoker.mark_complete("first", "tok", "session-9")
        self.assertEqual(stoker.marker_token(), "tok")
        self.assertEqual(json.loads(stoker.marker_path().read_text())["session"], "session-9")

    def test_a_session_nobody_supervises_writes_nothing(self):
        """Its marker would end whichever session a supervisor is running,
        which is never the one that wrote it."""
        with mock.patch.dict(os.environ, {stoker.CHILD_ENV: ""}):
            self.assertFalse(stoker.mark_complete("first"))
        self.assertFalse(stoker.marker_path().exists())

    def test_no_marker_reads_as_no_token_at_all(self):
        self.assertIsNone(stoker.marker_token())

    def test_clearing_a_marker_that_is_not_there_is_not_an_error(self):
        stoker.clear_marker()
        stoker.clear_marker()
        self.assertFalse(stoker.marker_path().exists())

    def test_an_unwritable_state_directory_never_raises(self):
        with mock.patch.dict(os.environ, {"HEATER_STATE_DIR": "/proc/nope"}):
            self.assertFalse(stoker.mark_complete("x"))
            stoker.clear_marker()

    def live_owner(self) -> dict:
        return {"owner_pid": os.getpid(), "owner_start": stoker.process_start(os.getpid())}

    def dead_owner(self) -> dict:
        spent = subprocess.Popen([sys.executable, "-c", "pass"])
        spent.wait()
        return {"owner_pid": spent.pid, "owner_start": "Thu Jan  1 00:00:00 1970"}

    def existing(self, token: str, owner: dict) -> None:
        stoker.marker_path().write_text(
            json.dumps({"at": "earlier", "token": token, "session": "s0", **owner}) + "\n",
            encoding="utf-8")

    def test_the_mark_names_the_supervisor_waiting_on_it(self):
        """A supervisor remembers what it handed out only while it is running,
        so after a restart the owner in the mark is all there is to go on."""
        with mock.patch.dict(os.environ, {stoker.OWNER_ENV: f"{os.getpid()} Tue Sep 15 17:00:00 2026"}):
            stoker.mark_complete("now", "tok", "s1")
        written = json.loads(stoker.marker_path().read_text(encoding="utf-8"))
        self.assertEqual(written["owner_pid"], os.getpid())
        self.assertEqual(written["owner_start"], "Tue Sep 15 17:00:00 2026")

    def test_a_mark_a_running_supervisor_is_waiting_on_is_refused(self):
        """That supervisor is about to end the session named in it. Taking the
        path would end the wrong conversation and lose this session's request."""
        self.existing("another-session", self.live_owner())
        self.assertFalse(stoker.mark_complete("now", "tok", "s1"))
        self.assertEqual(stoker.marker_token(), "another-session")

    def test_a_mark_nobody_is_waiting_on_is_taken_over(self):
        """Nothing will ever act on it, and leaving it there means no session in
        this folder can hand over again."""
        self.existing("a-session-that-is-gone", self.dead_owner())
        self.assertTrue(stoker.mark_complete("now", "tok", "s1"))
        self.assertEqual(stoker.marker_token(), "tok")

    def test_a_pid_handed_out_again_is_not_the_supervisor_that_is_gone(self):
        """This process is alive and wearing that number, but it started at a
        different moment, so the mark still belongs to nobody."""
        self.existing("a-session-that-is-gone",
                      {"owner_pid": os.getpid(), "owner_start": "Thu Jan  1 00:00:00 1970"})
        self.assertTrue(stoker.mark_complete("now", "tok", "s1"))

    def test_only_one_of_many_sessions_marking_at_once_is_told_it_marked(self):
        """Looking first and writing afterwards leaves a gap both sessions walk
        through, and the loser overwrites the winner's request with its own."""
        ready = threading.Barrier(8)
        results: list[tuple[bool, str]] = []
        lock = threading.Lock()

        def ask(number: int) -> None:
            ready.wait()
            wrote = stoker.mark_complete("now", f"tok{number}", f"s{number}")
            with lock:
                results.append((wrote, f"tok{number}"))

        threads = [threading.Thread(target=ask, args=(n,)) for n in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(30)
        winners = [token for wrote, token in results if wrote]
        self.assertEqual(len(winners), 1, "two sessions were both told they had marked")
        self.assertEqual(stoker.marker_token(), winners[0],
                         "the mark on disk is not the one that was acknowledged")


if __name__ == "__main__":
    unittest.main()
