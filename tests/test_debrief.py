#!/usr/bin/env python3
"""Tests for the five-hour debrief.

The debrief is the one thing in the fleet written to be read by someone who does
not program, so the tests check the two things that would fail that reader: an
account that leaves out what an agent was sent to do or how its check went, and
an empty window that says nothing at all rather than saying it was empty.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import debrief  # noqa: E402
import dispatch  # noqa: E402
import jsonstore  # noqa: E402
import queue  # noqa: E402
import store  # noqa: E402
import worktrees  # noqa: E402


class DebriefCase(unittest.TestCase):
    ENV = ("HEATER_DISPATCHES_DIR", "HEATER_REVIEWS_DIR", "HEATER_SUITES_DIR",
           "HEATER_LEASES_DIR", "HEATER_QUEUE_DIR", "HEATER_ROLE")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous = {k: os.environ.get(k) for k in self.ENV}
        for key in self.ENV[:-1]:
            os.environ[key] = str(Path(self.tmp.name) / key.lower())
        os.environ.pop("HEATER_ROLE", None)

    def tearDown(self):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def stamp(self, minutes_ago: float) -> str:
        return (datetime.now(timezone.utc)
                - timedelta(minutes=minutes_ago)).isoformat(timespec="microseconds")

    def job(self, task: str, *, minutes_ago: float = 60, agent: str = "worker",
            outcome: str | None = None, closed_minutes_ago: float | None = None,
            note: str = "") -> dict:
        record = {
            "id": jsonstore.new_id(), "created": self.stamp(minutes_ago), "task": task,
            "project": "heater", "done_when": "", "task_id": "", "agent": agent,
            "repo": "", "workdir": "", "lease_id": "", "branch": "", "run_id": "",
            "part": "",
            "closed_at": self.stamp(closed_minutes_ago) if outcome else None,
            "outcome": outcome, "note": note,
        }
        jsonstore.write(dispatch.dispatches_dir(), record)
        return record

    def check(self, change: str, *, round_number: int = 1, verdict: str = "fail",
              findings: int = 0, cost: float | None = None,
              minutes_ago: float = 30) -> dict:
        record = {
            "id": jsonstore.new_id(), "created": self.stamp(minutes_ago),
            "change": change, "project": "heater", "round": round_number,
            "lens": "default", "verdict": verdict, "findings": findings,
            "wording_only": False, "files": 1, "insertions": 1, "deletions": 0,
            "cost_usd": cost, "duration_s": None, "note": "",
        }
        jsonstore.write(store.reviews_dir(), record)
        return record

    def workspace(self, *, released: bool = False, minutes_ago: float = 60) -> dict:
        record = {"id": jsonstore.new_id(), "created": self.stamp(minutes_ago),
                  "project": "heater", "repo": "", "branch": "b", "dispatch_id": "",
                  "base_sha": "", "base_branch": "main", "path": "",
                  "released_at": self.stamp(1) if released else None,
                  "released_how": "landed" if released else ""}
        jsonstore.write(worktrees.leases_dir(), record)
        return record


class TestAFullWindow(DebriefCase):
    def test_it_names_both_jobs_and_how_the_check_went(self):
        """The fixture the finding asked for: two jobs, one round of checking."""
        first = self.job("Vendor the poker solver so it builds without the network",
                         minutes_ago=200, outcome="landed", closed_minutes_ago=90,
                         note="merged into main")
        self.job("Build the usage taper against the plan's two windows", minutes_ago=90)
        self.check(first["id"], round_number=1, verdict="fail", findings=3, cost=0.42)

        text = debrief.write(hours=5)

        self.assertIn("Vendor the poker solver", text)
        self.assertIn("Build the usage taper", text)
        self.assertIn("Checked over once", text)
        self.assertIn("3 things to put right", text)
        self.assertIn("the work is now part of the project", text)
        self.assertIn("Still running", text)
        self.assertIn("$0.42", text)

    def test_a_passing_check_is_said_as_passing(self):
        record = self.job("Write the handover")
        self.check(record["id"], round_number=1, verdict="fail", findings=2)
        self.check(record["id"], round_number=2, verdict="pass")
        text = debrief.write(hours=5)
        self.assertIn("Checked over 2 times", text)
        self.assertIn("the last check passed it", text)

    def test_a_job_still_out_from_before_the_window_is_still_named(self):
        """It is about to be stopped, so leaving it out would hide the stop."""
        self.job("Long-running research sweep", minutes_ago=600)
        self.assertIn("Long-running research sweep", debrief.write(hours=5))

    def test_work_finished_before_the_window_is_left_out(self):
        self.job("Something from yesterday", minutes_ago=2000,
                 outcome="landed", closed_minutes_ago=1900)
        self.assertNotIn("Something from yesterday", debrief.write(hours=5))

    def test_notes_and_workspaces_are_counted(self):
        self.job("Anything at all")
        queue.add("escalation", "a decision is needed")
        self.workspace()
        self.workspace(released=True)
        text = debrief.write(hours=5)
        self.assertIn("1 note(s) were left for you", text)
        self.assertIn("a decision an agent needs from you", text)
        self.assertIn("1 separate working copy(ies)", text)

    def test_it_says_when_no_cost_was_recorded(self):
        record = self.job("Anything at all")
        self.check(record["id"])
        self.assertIn("No check recorded what it cost", debrief.write(hours=5))

    def test_it_leaves_out_identifiers_and_paths(self):
        record = self.job("Vendor the poker solver")
        self.check(record["id"])
        text = debrief.write(hours=5)
        self.assertNotIn(record["id"], text, "an id means nothing to the reader")
        self.assertNotIn("/", text.replace("\n", " ").replace("://", " "))


class TestAnEmptyWindow(DebriefCase):
    def test_it_says_so_plainly(self):
        text = debrief.write(hours=5)
        self.assertIn("Nothing happened in the last 5 hours", text)
        self.assertIn("no agent was sent out", text)

    def test_older_work_does_not_make_the_window_look_busy(self):
        self.job("Yesterday's job", minutes_ago=3000, outcome="landed",
                 closed_minutes_ago=2900)
        self.assertIn("Nothing happened", debrief.write(hours=5))


class TestFilingIt(DebriefCase):
    def test_the_queue_flag_files_it_as_a_report(self):
        self.job("Anything at all")
        item = debrief.file_it(debrief.write(hours=5))
        waiting = queue.pending()
        self.assertEqual([i["id"] for i in waiting], [item["id"]])
        self.assertEqual(waiting[0]["kind"], "report")
        self.assertIn("Anything at all", waiting[0]["summary"])


class TestTheEntryPoint(DebriefCase):
    def run_it(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(ROOT / "bin" / "debrief.py"), *args],
                              capture_output=True, text=True, timeout=60,
                              env={**os.environ})

    def test_it_runs_and_prints_the_account(self):
        self.job("Anything at all")
        done = self.run_it("--hours", "5")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("What the agents did in the last 5 hours", done.stdout)

    def test_it_does_not_file_anything_without_the_flag(self):
        self.job("Anything at all")
        self.run_it("--hours", "5")
        self.assertEqual(queue.pending(), [])

    def test_the_flag_files_it(self):
        self.job("Anything at all")
        done = self.run_it("--hours", "5", "--queue")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(queue.pending()), 1)

    def test_a_window_of_no_hours_is_refused(self):
        self.assertEqual(self.run_it("--hours", "0").returncode, 2)


if __name__ == "__main__":
    unittest.main()
