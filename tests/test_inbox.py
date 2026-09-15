#!/usr/bin/env python3
"""Tests for the findings inbox and the capped task list.

Two opinions are enforced here and both are easy to erode by accident: a
dismissal must carry a reason, because the reason is what stops the next worker
refiling; and the task list must actually delete what falls past the cap, rather
than quietly keeping it somewhere.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import inbox  # noqa: E402
import jsonstore  # noqa: E402
import queue  # noqa: E402


class InboxCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous = {k: os.environ.get(k) for k in ("HEATER_QUEUE_DIR", "HEATER_TASKS_DIR")}
        os.environ["HEATER_QUEUE_DIR"] = str(Path(self.tmp.name) / "queue")
        os.environ["HEATER_TASKS_DIR"] = str(Path(self.tmp.name) / "tasks")

    def tearDown(self):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def file_finding(self, summary: str, **kwargs) -> str:
        return queue.add("finding", summary, **kwargs)["id"]


class TestJudging(InboxCase):
    def test_a_new_finding_is_open(self):
        self.file_finding("stale TODO")
        self.assertEqual(len(inbox.open_findings()), 1)

    def test_dismissal_closes_it_and_records_the_reason(self):
        found = self.file_finding("stale TODO")
        inbox.dismiss(found, "deliberate")
        self.assertEqual(inbox.open_findings(), [])
        self.assertEqual(inbox.dismissed()[0]["resolution"]["reason"], "deliberate")

    def test_dismissal_without_a_reason_is_refused(self):
        found = self.file_finding("stale TODO")
        with self.assertRaises(ValueError):
            inbox.dismiss(found, "   ")

    def test_promotion_closes_it(self):
        found = self.file_finding("no backoff")
        inbox.promote(found, 70)
        self.assertEqual(inbox.open_findings(), [])

    def test_cannot_judge_the_same_finding_twice(self):
        found = self.file_finding("stale TODO")
        inbox.dismiss(found, "deliberate")
        with self.assertRaises(ValueError):
            inbox.promote(found, 50)

    def test_unknown_id_is_refused(self):
        with self.assertRaises(ValueError):
            inbox.dismiss("deadbeefcafe", "nope")

    def test_only_findings_can_be_judged(self):
        escalation = queue.add("escalation", "needs a product call")["id"]
        with self.assertRaises(ValueError):
            inbox.dismiss(escalation, "not mine")

    def test_score_must_be_in_range(self):
        found = self.file_finding("x")
        with self.assertRaises(ValueError):
            inbox.promote(found, 101)

    def test_other_queue_kinds_are_not_findings(self):
        queue.add("report", "done")
        queue.add("failure", "red")
        self.assertEqual(inbox.open_findings(), [])


class TestRefiling(InboxCase):
    """The recorded reason is what stops the next worker filing the same thing."""

    def dismissed_example(self):
        found = self.file_finding("Stale TODO in the parser")
        inbox.dismiss(found, "deliberate; the parser owns that TODO")
        return found

    def test_catches_an_exact_refile(self):
        self.dismissed_example()
        self.assertIsNotNone(inbox.would_refile("Stale TODO in the parser"))

    def test_catches_a_reworded_refile(self):
        self.dismissed_example()
        self.assertIsNotNone(inbox.would_refile("there is a stale TODO in the parser"))

    def test_catches_punctuation_and_case_differences(self):
        self.dismissed_example()
        self.assertIsNotNone(inbox.would_refile("stale todo in the parser!"))

    def test_lets_a_genuinely_new_finding_through(self):
        self.dismissed_example()
        self.assertIsNone(inbox.would_refile("config loader ignores the timeout setting"))

    def test_does_not_match_against_open_findings(self):
        self.file_finding("Stale TODO in the parser")
        self.assertIsNone(inbox.would_refile("Stale TODO in the parser"),
                          "only a judged dismissal answers the question")

    def test_does_not_match_against_promoted_findings(self):
        found = self.file_finding("Auth retry has no backoff")
        inbox.promote(found, 60)
        self.assertIsNone(inbox.would_refile("Auth retry has no backoff"))

    def test_returns_the_reason_so_the_worker_learns_why(self):
        self.dismissed_example()
        prior = inbox.would_refile("stale TODO in the parser")
        self.assertIn("deliberate", prior["resolution"]["reason"])


class TestTaskList(InboxCase):
    def promote_many(self, count: int, base_score: int = 1):
        for n in range(count):
            found = self.file_finding(f"finding {n}")
            inbox.promote(found, min(100, base_score + n))

    def test_ranked_best_first(self):
        for summary, score in (("low", 10), ("high", 90), ("mid", 50)):
            inbox.promote(self.file_finding(summary), score)
        self.assertEqual([t["title"] for t in inbox.ranked()], ["high", "mid", "low"])

    def test_ties_go_to_whichever_was_raised_first(self):
        first = inbox.promote(self.file_finding("first"), 50)[0]
        second = inbox.promote(self.file_finding("second"), 50)[0]
        self.assertEqual([t["id"] for t in inbox.ranked()], [first["id"], second["id"]])

    def test_cap_is_enforced(self):
        self.promote_many(inbox.TASK_CAP + 5)
        self.assertEqual(len(inbox.ranked()), inbox.TASK_CAP)

    def test_what_falls_past_the_cap_is_deleted_not_archived(self):
        self.promote_many(inbox.TASK_CAP + 3)
        on_disk = jsonstore.load(inbox.tasks_dir())
        self.assertEqual(len(on_disk), inbox.TASK_CAP,
                         "a dropped task must leave no file behind; opinion 5 says deleted")

    def test_the_lowest_scoring_are_the_ones_dropped(self):
        self.promote_many(inbox.TASK_CAP + 3)
        scores = [t["score"] for t in inbox.ranked()]
        self.assertEqual(min(scores), max(scores) - inbox.TASK_CAP + 1)

    def test_promote_reports_what_it_dropped(self):
        self.promote_many(inbox.TASK_CAP)
        found = self.file_finding("a better one")
        _, dropped = inbox.promote(found, 100)
        self.assertEqual(len(dropped), 1)

    def test_a_high_score_displaces_a_low_one(self):
        self.promote_many(inbox.TASK_CAP, base_score=10)
        inbox.promote(self.file_finding("urgent"), 100)
        self.assertEqual(inbox.ranked()[0]["title"], "urgent")

    def test_completed_tasks_leave_the_list(self):
        task, _ = inbox.promote(self.file_finding("x"), 50)
        inbox.complete(task["id"])
        self.assertEqual(inbox.ranked(), [])

    def test_completing_an_unknown_task_is_refused(self):
        with self.assertRaises(ValueError):
            inbox.complete("deadbeefcafe")

    def test_a_completed_task_frees_a_slot(self):
        self.promote_many(inbox.TASK_CAP)
        inbox.complete(inbox.ranked()[0]["id"])
        self.assertEqual(len(inbox.ranked()), inbox.TASK_CAP - 1)

    def test_task_carries_its_source_finding(self):
        found = self.file_finding("trace me", project="api", path="src/x.py")
        task, _ = inbox.promote(found, 50)
        self.assertEqual(task["source_finding"], found)
        self.assertEqual(task["path"], "src/x.py")

    def test_title_defaults_to_the_finding_summary(self):
        task, _ = inbox.promote(self.file_finding("the summary"), 50)
        self.assertEqual(task["title"], "the summary")

    def test_title_can_be_overridden(self):
        task, _ = inbox.promote(self.file_finding("the summary"), 50, "a better title")
        self.assertEqual(task["title"], "a better title")


class TestRendering(InboxCase):
    def test_empty_inbox_says_so(self):
        self.assertIn("no findings", inbox.render_findings(inbox.open_findings()))

    def test_empty_task_list_says_so(self):
        self.assertIn("none", inbox.render_tasks(inbox.ranked()))

    def test_findings_render_with_their_ids(self):
        found = self.file_finding("stale TODO", path="src/p.py")
        text = inbox.render_findings(inbox.open_findings())
        self.assertIn(found, text)
        self.assertIn("src/p.py", text)


if __name__ == "__main__":
    unittest.main()
