#!/usr/bin/env python3
"""Tests for the fleet queue and the Stop hook that reads it.

The Stop hook is the only channel to the stoker, so the two failure modes that
matter are pinned here: waking nobody when something waits, and waking forever
for something already delivered.
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

import queue  # noqa: E402
import stop as stop_hook  # noqa: E402


class QueueCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous = os.environ.get("HEATER_QUEUE_DIR")
        os.environ["HEATER_QUEUE_DIR"] = self.tmp.name

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("HEATER_QUEUE_DIR", None)
        else:
            os.environ["HEATER_QUEUE_DIR"] = self.previous
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


class TestStopHook(QueueCase):
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

    def test_never_wakes_an_undispatched_session(self):
        queue.add("escalation", "needs a product call")
        self.set_role(None)
        self.assertEqual(stop_hook.handle({}), {})

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
    def run_hook(self, stdin: str, role: str = "stoker") -> subprocess.CompletedProcess:
        env = {**os.environ, "HEATER_ROLE": role, "HEATER_QUEUE_DIR": "/nonexistent/path/for/queue"}
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
