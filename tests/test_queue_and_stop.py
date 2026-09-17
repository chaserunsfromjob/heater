#!/usr/bin/env python3
"""Tests for the fleet queue and the Stop hook that reads it.

The Stop hook is the only channel to the stoker, so the two failure modes that
matter are pinned here: waking nobody when something waits, and waking forever
for something already delivered.
"""

from __future__ import annotations

import contextlib
import io
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

import queue  # noqa: E402
import stop as stop_hook  # noqa: E402


class QueueCase(unittest.TestCase):
    """A queue of its own and no context reading at all.

    The queue directory is redirected so the suite never touches the operator's
    real queue. The state directory is redirected at an empty directory for the
    same reason: with no reading recorded there, the context is QUIET, and the
    Stop hook's handover branch stays out of the way. Reading the live snapshot
    instead made identical code pass in a clean worktree and fail in a checkout
    that happened to be further through its session.
    """

    MANAGED = ("HEATER_QUEUE_DIR", "HEATER_STATE_DIR",
               "HEATER_HANDOVER_AT", "HEATER_HANDOVER_CEILING")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous = {key: os.environ.get(key) for key in self.MANAGED}
        os.environ["HEATER_QUEUE_DIR"] = self.tmp.name
        os.environ["HEATER_STATE_DIR"] = str(Path(self.tmp.name) / "state")
        for key in ("HEATER_HANDOVER_AT", "HEATER_HANDOVER_CEILING"):
            os.environ.pop(key, None)

    def tearDown(self):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def set_role(self, role: str | None):
        self.addCleanup(lambda p=os.environ.get("HEATER_ROLE"): (
            os.environ.pop("HEATER_ROLE", None) if p is None else os.environ.update({"HEATER_ROLE": p})
        ))
        if role is None:
            os.environ.pop("HEATER_ROLE", None)
        else:
            os.environ["HEATER_ROLE"] = role


class TestQueue(QueueCase):
    def test_add_then_pending(self):
        queue.add("finding", "stale TODO", project="api", path="src/p.py")
        waiting = queue.pending()
        self.assertEqual(len(waiting), 1)
        self.assertEqual(waiting[0]["summary"], "stale TODO")
        self.assertIsNone(waiting[0]["delivered_at"])

    def test_ids_are_unique(self):
        ids = {queue.add("finding", f"item {n}")["id"] for n in range(25)}
        self.assertEqual(len(ids), 25)

    def test_most_urgent_first(self):
        queue.add("finding", "low one", urgency="low")
        queue.add("report", "normal one")
        queue.add("escalation", "high one", urgency="high")
        self.assertEqual([i["urgency"] for i in queue.pending()], ["high", "normal", "low"])

    def test_same_urgency_keeps_arrival_order(self):
        first = queue.add("finding", "first")
        second = queue.add("finding", "second")
        order = [i["id"] for i in queue.pending()]
        self.assertEqual(order.index(first["id"]) < order.index(second["id"]), True)

    def test_delivered_items_drop_out_of_pending(self):
        queue.add("finding", "seen it")
        queue.mark_delivered(queue.pending())
        self.assertEqual(queue.pending(), [])
        self.assertEqual(len(queue.load_all()), 1, "delivery must not delete the item")

    def test_rejects_unknown_kind(self):
        with self.assertRaises(ValueError):
            queue.add("nonsense", "x")

    def test_rejects_unknown_urgency(self):
        with self.assertRaises(ValueError):
            queue.add("finding", "x", urgency="catastrophic")

    def test_rejects_empty_summary(self):
        with self.assertRaises(ValueError):
            queue.add("finding", "   ")

    def test_corrupt_file_is_skipped_not_fatal(self):
        queue.add("finding", "good one")
        (Path(self.tmp.name) / "broken.json").write_text("{ not json", encoding="utf-8")
        self.assertEqual(len(queue.load_all()), 1)

    def test_summary_names_every_item(self):
        queue.add("escalation", "token expiry call", project="api", urgency="high")
        queue.add("finding", "stale TODO", project="api")
        text = queue.summarise(queue.pending())
        self.assertIn("token expiry call", text)
        self.assertIn("stale TODO", text)
        self.assertIn("2 item(s)", text)

    def test_a_page_long_item_is_listed_as_its_first_line_and_where_to_read_it(self):
        """The debrief files a whole page; a list that prints it is not a list."""
        item = queue.add("report", "What the agents did in the last 5 hours\n\n"
                                   "18 jobs went out.\nOne is still running.")
        text = queue.summarise(queue.pending())
        self.assertIn("What the agents did in the last 5 hours", text)
        self.assertNotIn("18 jobs went out", text)
        self.assertIn("3 more lines", text)
        self.assertIn(f"bin/queue.py show {item['id']}", text)

    def test_a_one_line_item_is_listed_whole_with_no_pointer(self):
        queue.add("finding", "stale TODO in the parser")
        text = queue.summarise(queue.pending())
        self.assertIn("stale TODO in the parser", text)
        self.assertNotIn("more lines", text)

    def test_show_prints_the_whole_item(self):
        item = queue.add("report", "first line\nsecond line\nthird line")
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = queue.main(["queue.py", "show", item["id"]])
        self.assertEqual(code, 0)
        self.assertIn("third line", printed.getvalue())

    def test_show_of_an_unknown_id_says_so_rather_than_printing_nothing(self):
        complaint = io.StringIO()
        with contextlib.redirect_stderr(complaint):
            self.assertEqual(queue.main(["queue.py", "show", "nosuchitem"]), 1)
        self.assertIn("nosuchitem", complaint.getvalue())


class TestStopHook(QueueCase):
    def setUp(self):
        super().setUp()
        # These two ask git and bin/handover.py about the checkout the suite is
        # running in, so what they answer is a property of the machine rather
        # than of the code under test. Pinned to "nothing outstanding" here;
        # what the hook does when they say otherwise is test_handover_trigger.py.
        for name in ("in_flight", "problems"):
            patch = mock.patch.object(stop_hook.handover, name, return_value=[])
            patch.start()
            self.addCleanup(patch.stop)

    def test_the_fixture_reads_no_live_session_state(self):
        """What the hook decides here must be a property of the code, not of the
        machine. Without this isolation the module passed in a clean worktree and
        failed in a checkout with uncommitted files, on byte-identical code, which
        made the gate useless as a landing signal."""
        self.assertIsNone(stop_hook.context.used(None), "a live reading leaked in")
        self.assertIsNone(stop_hook.handover_decision(), "handover must stay out of the way")

    def test_wakes_the_stoker_when_something_waits(self):
        queue.add("escalation", "needs a product call", urgency="high")
        self.set_role("stoker")
        decision = stop_hook.handle({})
        self.assertEqual(decision["hookSpecificOutput"]["decision"], "continue")
        self.assertIn("needs a product call", decision["hookSpecificOutput"]["reason"])

    def test_stays_quiet_when_the_queue_is_empty(self):
        self.set_role("stoker")
        self.assertEqual(stop_hook.handle({}), {})

    def test_never_wakes_a_worker(self):
        queue.add("escalation", "needs a product call", urgency="high")
        self.set_role("worker")
        self.assertEqual(stop_hook.handle({}), {})

    def test_never_wakes_an_unmarked_session_outside_the_fleet_repo(self):
        queue.add("escalation", "needs a product call")
        self.set_role(None)
        with tempfile.TemporaryDirectory() as elsewhere:
            self.assertEqual(stop_hook.handle({"cwd": elsewhere}), {})

    def test_wakes_an_unmarked_session_inside_the_fleet_repo(self):
        """The operator's own session in the fleet repo is the stoker, marker or
        not. Requiring the marker failed silently: the session opened, looked
        ordinary, and never received the queue."""
        queue.add("escalation", "needs a product call")
        self.set_role(None)
        decision = stop_hook.handle({"cwd": str(ROOT)})
        self.assertEqual(decision["hookSpecificOutput"]["decision"], "continue")

    def test_does_not_wake_twice_for_the_same_item(self):
        queue.add("finding", "only once")
        self.set_role("stoker")
        self.assertNotEqual(stop_hook.handle({}), {})
        self.assertEqual(stop_hook.handle({}), {}, "a delivered item must not wake the stoker again")

    def test_respects_stop_hook_active(self):
        queue.add("finding", "would loop")
        self.set_role("stoker")
        self.assertEqual(stop_hook.handle({"stop_hook_active": True}), {},
                         "continuing while a Stop hook is already active is an infinite loop")

    def test_a_new_item_wakes_again(self):
        queue.add("finding", "first")
        self.set_role("stoker")
        stop_hook.handle({})
        queue.add("finding", "second")
        decision = stop_hook.handle({})
        self.assertIn("second", decision["hookSpecificOutput"]["reason"])
        self.assertNotIn("first", decision["hookSpecificOutput"]["reason"])


class TestStopFailsOpen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_hook(self, stdin: str, role: str = "stoker") -> subprocess.CompletedProcess:
        # A subprocess cannot be patched, so the isolation is all environment:
        # an empty state directory means no context reading, which means QUIET,
        # which means the hook never consults the live checkout for a handover.
        env = {key: value for key, value in os.environ.items()
               if key not in ("HEATER_HANDOVER_AT", "HEATER_HANDOVER_CEILING")}
        env.update({"HEATER_ROLE": role,
                    "HEATER_QUEUE_DIR": "/nonexistent/path/for/queue",
                    "HEATER_STATE_DIR": self.tmp.name})
        return subprocess.run(
            [sys.executable, str(ROOT / "hooks" / "stop.py")],
            input=stdin, capture_output=True, text=True, timeout=20, env=env,
        )

    def test_missing_queue_directory_does_not_wedge_the_turn(self):
        result = self.run_hook(json.dumps({}))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_malformed_json_exits_zero(self):
        self.assertEqual(self.run_hook("not json").returncode, 0)


if __name__ == "__main__":
    unittest.main()
