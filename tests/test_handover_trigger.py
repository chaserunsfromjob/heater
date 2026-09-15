#!/usr/bin/env python3
"""Tests for automatic handover.

Hooks are never told how full the context window is; only the status line is.
The whole mechanism is that bridge, so the tests pin both halves: that the
status line records the number, and that the Stop hook acts on it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "hooks"))

import context  # noqa: E402
import deploy  # noqa: E402
import statusline  # noqa: E402
import stoker  # noqa: E402
import stop as stop_hook  # noqa: E402


class StateCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        managed = ("HEATER_STATE_DIR", "HEATER_HANDOVER_AT", "HEATER_HANDOVER_CEILING",
                   stoker.CHILD_ENV)
        self.previous = {k: os.environ.get(k) for k in managed}
        os.environ["HEATER_STATE_DIR"] = self.tmp.name
        for key in managed[1:]:
            os.environ.pop(key, None)

    def tearDown(self):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def at(self, percentage: float, session: str = "s1"):
        statusline.main_payload = None
        context.record({"context_window": {"used_percentage": percentage,
                                           "context_window_size": 1000000},
                        "session_id": session})


class TestThreshold(StateCase):
    def test_default_is_well_below_compaction(self):
        self.assertLess(context.DEFAULT_HANDOVER_AT, 70)

    # A session is already near this before the operator has said anything:
    # system prompt, tool definitions and CLAUDE.md all arrive first.
    STARTUP_FLOOR = 10.0

    def test_the_mark_leaves_real_room_above_the_startup_floor(self):
        """The mark is measured against total usage, so the floor is a toll paid
        before any working room is counted. 25% left fifteen points, not
        twenty-five, which is what moved it."""
        self.assertGreaterEqual(context.DEFAULT_HANDOVER_AT - self.STARTUP_FLOOR, 20.0)

    def test_the_ceiling_is_above_the_arming_mark(self):
        self.assertGreater(context.DEFAULT_CEILING, context.DEFAULT_HANDOVER_AT)

    def test_a_ceiling_below_the_arming_mark_is_clamped(self):
        os.environ["HEATER_HANDOVER_AT"] = "40"
        os.environ["HEATER_HANDOVER_CEILING"] = "10"
        self.assertEqual(context.ceiling(), 40.0, "a ceiling under the arm would force instantly")

    def test_states_in_order(self):
        for percentage, expected in ((10, context.QUIET), (30, context.ARMED), (90, context.FORCED)):
            self.at(percentage)
            self.assertEqual(context.state(), expected, f"at {percentage}%")

    def test_no_reading_is_quiet(self):
        self.assertEqual(context.state(), context.QUIET, "no reading must not force a handover")

    def test_env_overrides_it(self):
        os.environ["HEATER_HANDOVER_AT"] = "42"
        self.assertEqual(context.threshold(), 42.0)

    def test_a_nonsense_override_falls_back(self):
        os.environ["HEATER_HANDOVER_AT"] = "soon"
        self.assertEqual(context.threshold(), context.DEFAULT_HANDOVER_AT)

    def test_below_threshold_is_not_due(self):
        self.at(context.DEFAULT_HANDOVER_AT - 10)
        self.assertFalse(context.due())

    def test_at_threshold_is_due(self):
        self.at(context.DEFAULT_HANDOVER_AT)
        self.assertTrue(context.due())

    def test_unknown_usage_is_never_due(self):
        self.assertFalse(context.due(), "no reading must not mean handover")

    def test_a_missing_percentage_is_ignored(self):
        self.assertIsNone(context.record({"context_window": {}}))

    def test_a_new_session_resets_the_announcement(self):
        self.at(60, "s1")
        context.mark_announced("now")
        self.at(60, "s2")
        self.assertFalse(context.announced())


class TestTranscriptSource(StateCase):
    """The primary source: every hook gets a transcript_path, and the last usage
    record in it is what the API actually reported. Works where no status line runs."""

    def transcript(self, *records) -> str:
        path = Path(self.tmp.name) / "t.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
        return str(path)

    def usage(self, read: int, write: int = 0, fresh: int = 0) -> dict:
        return {"message": {"usage": {"input_tokens": fresh,
                                      "cache_creation_input_tokens": write,
                                      "cache_read_input_tokens": read}}}

    def test_it_reads_the_window_in_use(self):
        path = self.transcript(self.usage(250_000, 1_000, 2))
        self.assertAlmostEqual(context.from_transcript(path), 25.1002, places=3)

    def test_it_takes_the_last_record_not_the_first(self):
        path = self.transcript(self.usage(100_000), self.usage(400_000))
        self.assertAlmostEqual(context.from_transcript(path), 40.0)

    def test_it_ignores_lines_without_usage(self):
        path = self.transcript({"type": "user", "text": "hello"}, self.usage(300_000))
        self.assertAlmostEqual(context.from_transcript(path), 30.0)

    def test_it_survives_a_corrupt_line(self):
        path = Path(self.tmp.name) / "t.jsonl"
        path.write_text('{"usage": broken\n' + json.dumps(self.usage(200_000)) + "\n", encoding="utf-8")
        self.assertAlmostEqual(context.from_transcript(str(path)), 20.0)

    def test_a_missing_file_reads_as_unknown(self):
        self.assertIsNone(context.from_transcript(str(Path(self.tmp.name) / "gone.jsonl")))

    def test_no_path_reads_as_unknown(self):
        self.assertIsNone(context.from_transcript(None))

    def test_a_transcript_with_no_usage_reads_as_unknown(self):
        self.assertIsNone(context.from_transcript(self.transcript({"type": "user"})))

    def test_it_reads_a_record_beyond_the_tail_window(self):
        """A long session's transcript is far bigger than the tail that gets read."""
        filler = [{"type": "user", "text": "x" * 2000} for _ in range(400)]
        path = self.transcript(*filler, self.usage(350_000))
        self.assertGreater(Path(path).stat().st_size, context.TAIL_BYTES)
        self.assertAlmostEqual(context.from_transcript(path), 35.0)

    def test_the_window_size_can_be_overridden(self):
        os.environ["HEATER_CONTEXT_WINDOW"] = "200000"
        self.addCleanup(os.environ.pop, "HEATER_CONTEXT_WINDOW", None)
        self.assertAlmostEqual(context.from_transcript(self.transcript(self.usage(100_000))), 50.0)

    def test_it_cannot_exceed_one_hundred_percent(self):
        self.assertLessEqual(context.from_transcript(self.transcript(self.usage(9_000_000))), 100.0)

    def test_the_transcript_beats_a_stale_snapshot(self):
        self.at(5)
        path = self.transcript(self.usage(600_000))
        self.assertAlmostEqual(context.used(path), 60.0, msg="a stale snapshot must not win")

    def test_the_snapshot_is_used_when_there_is_no_transcript(self):
        self.at(33)
        self.assertAlmostEqual(context.used(None), 33.0)

    def test_state_is_driven_by_the_transcript(self):
        self.assertEqual(context.state(self.transcript(self.usage(100_000))), context.QUIET)
        self.assertEqual(context.state(self.transcript(self.usage(300_000))), context.ARMED)
        self.assertEqual(context.state(self.transcript(self.usage(800_000))), context.FORCED)


class TestStatusLine(StateCase):
    def render(self, payload: dict) -> str:
        done = subprocess.run([sys.executable, str(ROOT / "hooks" / "statusline.py")],
                              input=json.dumps(payload), capture_output=True, text=True,
                              timeout=30, env={**os.environ})
        return done.stdout.strip()

    def test_it_records_what_it_was_told(self):
        self.render({"context_window": {"used_percentage": 61.4}, "session_id": "s"})
        self.assertAlmostEqual(context.used(), 61.4)

    def test_it_shows_the_percentage(self):
        self.assertIn("61%", self.render({"context_window": {"used_percentage": 61.4}}))

    def test_it_flags_when_handover_is_due(self):
        self.assertIn("HANDOVER DUE", self.render({"context_window": {"used_percentage": 80}}))

    def test_it_flags_the_armed_zone_differently_from_the_ceiling(self):
        armed = self.render({"context_window": {"used_percentage": 30}})
        forced = self.render({"context_window": {"used_percentage": 90}})
        self.assertNotEqual(armed, forced)

    def test_it_stays_quiet_below_the_threshold(self):
        self.assertNotIn("HANDOVER", self.render({"context_window": {"used_percentage": 20}}))

    def test_it_survives_garbage(self):
        done = subprocess.run([sys.executable, str(ROOT / "hooks" / "statusline.py")],
                              input="not json", capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0)
        self.assertTrue(done.stdout.strip(), "a broken status line must still render something")

    def test_it_survives_an_unwritable_state_directory(self):
        done = subprocess.run([sys.executable, str(ROOT / "hooks" / "statusline.py")],
                              input=json.dumps({"context_window": {"used_percentage": 50}}),
                              capture_output=True, text=True, timeout=30,
                              env={**os.environ, "HEATER_STATE_DIR": "/proc/nope"})
        self.assertEqual(done.returncode, 0)


class TestStopTrigger(StateCase):
    """Armed is not due. Cutting a session off mid-task costs the work twice."""

    def busy(self, *reasons):
        return mock.patch.object(stop_hook.handover, "in_flight", return_value=list(reasons))

    def outstanding(self, *reasons):
        return mock.patch.object(stop_hook.handover, "problems", return_value=list(reasons))

    def supervised(self, token: str = "child-token"):
        """A session a supervisor launched, which is the only kind it can end."""
        return mock.patch.dict(os.environ, {stoker.CHILD_ENV: token})

    def test_quiet_below_the_arming_mark(self):
        self.at(10)
        self.assertIsNone(stop_hook.handover_decision())

    def test_armed_and_mid_task_waits(self):
        self.at(30)
        with self.busy("uncommitted changes in 3 file(s)"), self.outstanding("x"):
            decision = stop_hook.handover_decision()
        self.assertNotIn("hookSpecificOutput", decision, "it must not cut the task off")
        self.assertIn("Do not start anything new", decision["systemMessage"])

    def test_armed_and_mid_task_says_what_is_in_flight(self):
        self.at(30)
        with self.busy("2 worker(s) still out"), self.outstanding("x"):
            self.assertIn("2 worker(s) still out", stop_hook.handover_decision()["systemMessage"])

    def test_armed_and_mid_task_only_says_it_once(self):
        self.at(30)
        with self.busy("uncommitted changes"), self.outstanding("x"):
            stop_hook.handover_decision()
            self.assertIsNone(stop_hook.handover_decision(), "nagging every turn trains it out")

    def test_armed_at_a_boundary_hands_over(self):
        self.at(30)
        with self.busy(), self.outstanding("handover note: does not exist"):
            decision = stop_hook.handover_decision()
        self.assertEqual(decision["hookSpecificOutput"]["decision"], "continue")
        self.assertIn("clean boundary", decision["hookSpecificOutput"]["reason"])

    def test_the_armed_handover_is_not_described_as_forced(self):
        self.at(30)
        with self.busy(), self.outstanding("x"):
            self.assertNotIn("ceiling", stop_hook.handover_decision()["hookSpecificOutput"]["reason"])

    def test_the_ceiling_overrides_being_mid_task(self):
        self.at(90)
        with self.busy("uncommitted changes in 9 file(s)"), self.outstanding("x"):
            decision = stop_hook.handover_decision()
        self.assertEqual(decision["hookSpecificOutput"]["decision"], "continue")
        self.assertIn("ceiling", decision["hookSpecificOutput"]["reason"])
        self.assertIn("park", decision["hookSpecificOutput"]["reason"])

    def test_the_instruction_names_what_is_outstanding(self):
        self.at(90)
        with self.busy(), self.outstanding("pushed to origin: 2 commits"):
            self.assertIn("2 commits", stop_hook.handover_decision()["hookSpecificOutput"]["reason"])

    def test_it_lets_the_turn_end_once_the_handover_is_ready(self):
        self.at(30)
        with self.supervised(), self.busy(), self.outstanding():
            decision = stop_hook.handover_decision()
        self.assertNotIn("hookSpecificOutput", decision)
        self.assertIn("bin/stoker.sh", decision["systemMessage"])

    def test_the_ready_message_asks_the_operator_for_nothing(self):
        """Opinion 12: the handoff needs nothing from the operator."""
        self.at(30)
        with self.supervised(), self.busy(), self.outstanding():
            decision = stop_hook.handover_decision()
        self.assertNotIn("/clear", decision["systemMessage"])

    def test_a_ready_handover_marks_the_session_done(self):
        """The marker is the signal the supervisor is watching for."""
        self.at(30)
        with self.supervised(), self.busy(), self.outstanding():
            stop_hook.handover_decision(None, "stoker")
        self.assertTrue(stoker.marker_path().exists())

    def test_the_marker_names_the_session_that_wrote_it(self):
        """One shared path with no identity in it would end whichever session
        the supervisor is running, which need not be this one."""
        self.at(30)
        with self.supervised("child-9"), self.busy(), self.outstanding():
            stop_hook.handover_decision(None, "stoker", "session-42")
        written = json.loads(stoker.marker_path().read_text(encoding="utf-8"))
        self.assertEqual(written["token"], "child-9")
        self.assertEqual(written["session"], "session-42")

    def test_a_session_nobody_supervises_leaves_no_marker(self):
        """A plain `claude` opened in the fleet repository is the stoker too.
        Its clean handover must not end the supervised session."""
        self.at(30)
        with self.busy(), self.outstanding():
            decision = stop_hook.handover_decision(None, "stoker", "session-42")
        self.assertFalse(stoker.marker_path().exists())
        self.assertIn("handover is written, current and pushed", decision["systemMessage"])
        self.assertNotIn("ending now", decision["systemMessage"])

    def test_it_does_not_promise_an_ending_it_cannot_deliver(self):
        """Another session's mark already holds the one path, so this session's
        was never written and no supervisor will act on it. Saying it is ending
        now would leave the operator waiting on something that never comes."""
        self.at(30)
        stoker.marker_path().write_text(
            json.dumps({"at": "earlier", "token": "somebody-else", "session": "s0"}) + "\n",
            encoding="utf-8")
        with self.supervised("child-9"), self.busy(), self.outstanding():
            decision = stop_hook.handover_decision(None, "stoker", "session-42")
        self.assertNotIn("ending now", decision["systemMessage"])
        self.assertIn("handover is written, current and pushed", decision["systemMessage"])
        self.assertIn("bin/stoker.sh", decision["systemMessage"])
        self.assertEqual(json.loads(stoker.marker_path().read_text())["token"], "somebody-else",
                         "another session's mark is not ours to overwrite")

    def test_a_mark_that_could_not_be_written_is_not_reported_as_written(self):
        """A full or read-only disk swallows the write. Nothing is on disk for
        any supervisor to act on, so nothing is promised."""
        self.at(30)
        with self.supervised("child-9"), self.busy(), self.outstanding(), \
                mock.patch.object(stoker, "mark_complete", return_value=False):
            decision = stop_hook.handover_decision(None, "stoker", "session-42")
        self.assertFalse(stoker.marker_path().exists())
        self.assertNotIn("ending now", decision["systemMessage"])
        self.assertIn("close it when you like", decision["systemMessage"])

    def test_the_session_id_reaches_the_marker_from_the_payload(self):
        self.at(30)
        os.environ["HEATER_ROLE"] = "stoker"
        self.addCleanup(os.environ.pop, "HEATER_ROLE", None)
        with self.supervised(), self.busy(), self.outstanding():
            stop_hook.handle({"session_id": "from-payload"})
        self.assertEqual(json.loads(stoker.marker_path().read_text())["session"], "from-payload")

    def test_it_marks_the_session_done_only_once(self):
        self.at(30)
        with self.supervised(), self.busy(), self.outstanding():
            stop_hook.handover_decision(None, "stoker")
            first = stoker.marker_path().read_text(encoding="utf-8")
            stop_hook.handover_decision(None, "stoker")
        self.assertEqual(stoker.marker_path().read_text(encoding="utf-8"), first)

    def test_it_never_ends_a_session_that_is_not_the_stoker(self):
        """A worker's session is a dispatch, not something to replace."""
        self.at(30)
        with self.supervised(), self.busy(), self.outstanding():
            decision = stop_hook.handover_decision(None, "worker")
        self.assertFalse(stoker.marker_path().exists())
        self.assertNotIn("bin/stoker.sh", decision["systemMessage"])

    def test_an_unfinished_handover_is_never_marked_done(self):
        self.at(90)
        with self.supervised(), self.busy(), self.outstanding("working tree clean: uncommitted"):
            stop_hook.handover_decision(None, "stoker")
        self.assertFalse(stoker.marker_path().exists())

    def test_handover_outranks_the_queue(self):
        """Picking up new work past the ceiling only makes the note harder to write."""
        self.at(90)
        os.environ["HEATER_ROLE"] = "stoker"
        self.addCleanup(os.environ.pop, "HEATER_ROLE", None)
        with mock.patch.object(stop_hook.handover, "problems", return_value=["something"]), \
             mock.patch.object(stop_hook.handover, "in_flight", return_value=[]), \
             mock.patch.object(stop_hook.queue, "pending", return_value=[{"id": "x"}]) as pending:
            stop_hook.handle({})
        pending.assert_not_called()

    def test_being_armed_does_not_block_the_queue_while_mid_task(self):
        """Armed means finish what you are doing, not stop working."""
        self.at(30)
        os.environ["HEATER_ROLE"] = "stoker"
        self.addCleanup(os.environ.pop, "HEATER_ROLE", None)
        with mock.patch.object(stop_hook.handover, "in_flight", return_value=["uncommitted"]), \
             mock.patch.object(stop_hook.handover, "problems", return_value=["x"]):
            stop_hook.handover_decision()          # burns the one announcement
            with mock.patch.object(stop_hook.queue, "pending", return_value=[]) as pending:
                stop_hook.handle({})
            pending.assert_called_once()

    def test_it_respects_stop_hook_active(self):
        self.at(90)
        self.assertEqual(stop_hook.handle({"stop_hook_active": True}), {},
                         "continuing while a Stop hook is active is an infinite loop")

    def test_it_applies_to_any_role_not_just_the_stoker(self):
        self.at(90)
        with mock.patch.object(stop_hook.handover, "problems", return_value=["something"]), \
             mock.patch.object(stop_hook.handover, "in_flight", return_value=[]):
            decision = stop_hook.handle({})
        self.assertEqual(decision["hookSpecificOutput"]["decision"], "continue")


class TestCompactionBackstop(StateCase):
    def run_hook(self, name: str, payload: dict) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(ROOT / "hooks" / name)],
                              input=json.dumps(payload), capture_output=True, text=True,
                              timeout=30, env={**os.environ})

    def test_pre_compact_leaves_a_mark(self):
        self.run_hook("pre_compact.py", {"trigger": "auto"})
        self.assertTrue(context.read().get("compacted_at"))

    def test_pre_compact_warns(self):
        result = self.run_hook("pre_compact.py", {"trigger": "auto"})
        self.assertIn("HANDOVER.md", json.loads(result.stdout)["systemMessage"])

    def test_pre_compact_fails_open(self):
        result = subprocess.run([sys.executable, str(ROOT / "hooks" / "pre_compact.py")],
                                input="not json", capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0)

    def test_the_next_session_is_told_its_memory_was_edited(self):
        self.run_hook("pre_compact.py", {"trigger": "auto"})
        result = self.run_hook("session_start.py", {"source": "compact"})
        self.assertIn("compacted", json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"])

    def test_the_mark_is_cleared_after_it_is_read(self):
        self.run_hook("pre_compact.py", {"trigger": "auto"})
        self.run_hook("session_start.py", {"source": "compact"})
        self.assertFalse(context.read().get("compacted_at"), "a stale warning is worse than none")


class TestDeployment(unittest.TestCase):
    def test_the_status_line_is_deployed(self):
        self.assertIn("statusline.py", deploy.status_line()["command"])

    def test_pre_compact_is_registered(self):
        self.assertIn("PreCompact", deploy.hook_groups())

    def test_a_missing_status_line_is_reported_as_drift(self):
        with mock.patch.object(deploy, "read_settings", return_value={"hooks": deploy.merge_hooks({})}), \
             mock.patch.object(Path, "exists", return_value=True):
            self.assertIn("handover cannot fire", deploy.settings_drift() or "")

    def test_a_foreign_status_line_is_reported_rather_than_replaced(self):
        settings = {"hooks": deploy.merge_hooks({}), "statusLine": {"command": "/mine/bar.sh"}}
        with mock.patch.object(deploy, "read_settings", return_value=settings), \
             mock.patch.object(Path, "exists", return_value=True):
            drift = deploy.settings_drift() or ""
        self.assertIn("not this repository's", drift)


if __name__ == "__main__":
    unittest.main()
