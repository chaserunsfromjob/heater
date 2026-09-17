#!/usr/bin/env python3
"""Tests for the three ways a change reached the trunk without the review it needs.

Each class is one recorded defect, reproduced before it was fixed:

* a pass from an old round counting after later rounds failed,
* one wording-only round counting as the end of a review that needs two,
* a branch with nothing on it read as work that has already landed.

All three end the same way — a merge nobody approved, or a live worker's
checkout deleted — so all three are tested against the real stores and, where
git is what decides, a real repository.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dispatch  # noqa: E402
import jsonstore  # noqa: E402
import store  # noqa: E402
import worktrees  # noqa: E402


def run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True, timeout=60)


def backdate(directory: Path, record_id: str, hours: float) -> None:
    """Move a stored record's clock back, in the file it already lives in.

    Rewritten in place rather than re-written through `jsonstore.write`: the
    filename carries the timestamp, so a rewrite would leave two files with one
    id and readers would see the older of the two.
    """
    when = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="microseconds")
    for path in directory.glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("id") == record_id:
            record["created"] = when
            path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            return
    raise AssertionError(f"no record {record_id} in {directory}")


class StoreCase(unittest.TestCase):
    """Every store this touches, in a directory that goes away afterwards."""

    ENV = ("HEATER_DISPATCHES_DIR", "HEATER_REVIEWS_DIR", "HEATER_SUITES_DIR",
           "HEATER_LEASES_DIR", "HEATER_WORKTREE_ROOT", "HEATER_REFUSALS_DIR",
           "HEATER_LOG_DIR")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.previous = {k: os.environ.get(k) for k in self.ENV}
        for key in self.ENV:
            os.environ[key] = str(self.root / key.lower())

    def tearDown(self):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def round_of(self, change: str, number: int, verdict: str, *,
                 findings: int = 0, wording_only: bool = False) -> dict:
        return store.record_review(change, number, "default", verdict,
                                   findings=findings, wording_only=wording_only)

    def wording_pass(self, change: str, number: int) -> dict:
        return self.round_of(change, number, "pass", findings=2, wording_only=True)

    def clean_pass(self, change: str, number: int) -> dict:
        return self.round_of(change, number, "pass")

    def approve(self, change: str) -> None:
        """The shortest honest way to the end of review: two consecutive passes."""
        self.wording_pass(change, 1)
        self.clean_pass(change, 2)


class TestTheLatestRoundDecides(StoreCase):
    """Task dc8e3ac0bd7f: a round-4 pass landed a change after rounds 5-7 failed."""

    def test_a_pass_does_not_survive_later_failures(self):
        self.wording_pass("auth", 3)
        self.clean_pass("auth", 4)
        for number in (5, 6, 7):
            self.round_of("auth", number, "fail", findings=3)
        self.assertFalse(dispatch.reviewed("auth"),
                         "the latest round failed; an older pass is not a review pass")

    def test_the_last_recorded_round_wins_when_numbers_tie(self):
        self.wording_pass("auth", 1)
        self.clean_pass("auth", 2)
        self.round_of("auth", 2, "fail", findings=1)
        self.assertFalse(dispatch.reviewed("auth"),
                         "two rounds numbered the same are settled by which was recorded last")

    def test_a_pass_hiding_substantive_findings_does_not_count(self):
        """Defensive: `bin/store.py review` refuses this, a handwritten file does not."""
        self.wording_pass("auth", 1)
        jsonstore.write(store.reviews_dir(), {
            "id": jsonstore.new_id(), "created": jsonstore.now(), "change": "auth",
            "project": "", "round": 2, "lens": "default", "verdict": "pass",
            "findings": 4, "wording_only": False, "files": 0, "insertions": 0,
            "deletions": 0, "cost_usd": None, "duration_s": None, "note": "",
        })
        self.assertFalse(dispatch.reviewed("auth"),
                         "a pass with substantive findings outstanding is not a pass")

    def test_a_later_pass_after_failures_ends_review(self):
        for number in (1, 2):
            self.round_of("auth", number, "fail", findings=3)
        self.wording_pass("auth", 3)
        self.clean_pass("auth", 4)
        self.assertTrue(dispatch.reviewed("auth"))

    def test_rounds_of_another_change_are_not_counted(self):
        self.approve("other")
        self.round_of("auth", 1, "fail", findings=1)
        self.assertFalse(dispatch.reviewed("auth"))


class TestReviewEndsOnTwoRounds(StoreCase):
    """Task f16c56933d8a: reconcile merged on the first wording-only pass.

    `skills/adversarial-review/SKILL.md` ends review on two consecutive rounds
    that find only wording, then one final round landed on.
    """

    def test_one_wording_only_pass_is_not_the_end_of_review(self):
        self.round_of("auth", 5, "fail", findings=6)
        self.wording_pass("auth", 6)
        self.assertFalse(dispatch.reviewed("auth"),
                         "review ends on two consecutive rounds, not one")

    def test_a_single_first_round_pass_is_not_the_end_of_review(self):
        self.clean_pass("auth", 1)
        self.assertFalse(dispatch.reviewed("auth"))

    def test_two_wording_only_passes_end_review(self):
        self.wording_pass("auth", 6)
        self.wording_pass("auth", 7)
        self.assertTrue(dispatch.reviewed("auth"))

    def test_a_clean_final_round_after_a_wording_pass_ends_review(self):
        self.wording_pass("auth", 6)
        self.clean_pass("auth", 7)
        self.assertTrue(dispatch.reviewed("auth"))

    def test_a_fail_between_two_passes_starts_the_count_again(self):
        self.wording_pass("auth", 1)
        self.round_of("auth", 2, "fail", findings=2)
        self.wording_pass("auth", 3)
        self.assertFalse(dispatch.reviewed("auth"),
                         "consecutive means consecutive; a fail resets the count")

    def test_the_rule_is_two_rounds_and_says_so(self):
        self.assertEqual(dispatch.ROUNDS_TO_END_REVIEW, 2)


class GitCase(StoreCase):
    """A real repository, because what is being tested is what git says."""

    def setUp(self):
        super().setUp()
        self.repo = self.root / "proj"
        self.repo.mkdir()
        run("git", "init", "-q", "-b", "main", cwd=self.repo)
        run("git", "config", "user.email", "t@t", cwd=self.repo)
        run("git", "config", "user.name", "t", cwd=self.repo)
        (self.repo / "a.txt").write_text("hello\n")
        run("git", "add", "-A", cwd=self.repo)
        run("git", "commit", "-qm", "init", cwd=self.repo)

    def tearDown(self):
        for record in worktrees.active():
            try:
                worktrees.release(record["id"], "teardown", force=True)
            except Exception:
                pass
        super().tearDown()

    def worker(self, task: str = "add a feature") -> dict:
        return dispatch.open_dispatch(task, project="api", repo=str(self.repo))

    def work(self, record: dict, name: str = "feature.txt", body: str = "new\n") -> None:
        path = Path(record["workdir"])
        (path / name).write_text(body)
        run("git", "add", "-A", cwd=path)
        run("git", "commit", "-qm", f"add {name}", cwd=path)

    def stored(self, dispatch_id: str) -> dict:
        return next(d for d in jsonstore.load(dispatch.dispatches_dir()) if d["id"] == dispatch_id)

    def beat(self, cwd: Path, *, minutes_ago: float = 0.0, session: str = "s1") -> None:
        # Where the PostToolUse hook writes: alongside the log directory.
        directory = self.root / "heartbeat"
        directory.mkdir(parents=True, exist_ok=True)
        when = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
        (directory / f"{session}.json").write_text(json.dumps({
            "at": when.isoformat(timespec="seconds"), "session": session,
            "role": "worker", "tool": "Bash", "cwd": str(cwd)}) + "\n", encoding="utf-8")


class TestLandingSaysWhichRound(GitCase):
    """Task dc8e3ac0bd7f, the half of it that is about the record it leaves."""

    def test_landing_is_refused_on_a_stale_pass(self):
        record = self.worker()
        self.work(record)
        self.approve(record["id"])
        self.round_of(record["id"], 3, "fail", findings=2)
        with self.assertRaises(dispatch.NotReadyToLand):
            dispatch.land(record["id"])
        self.assertTrue(Path(record["workdir"]).exists(), "a refusal must change nothing")

    def test_the_note_names_the_round_it_landed_on(self):
        record = self.worker()
        self.work(record)
        self.wording_pass(record["id"], 5)
        self.clean_pass(record["id"], 6)
        landed = dispatch.land(record["id"])
        self.assertIn("round 6", landed["note"],
                      "the note must say which round was landed on")

    def test_skipping_review_is_recorded_in_the_note(self):
        record = self.worker()
        self.work(record)
        landed = dispatch.land(record["id"], skip_review=True)
        self.assertIn("review skipped", landed["note"].lower(),
                      "an override that leaves no trace is indistinguishable from a review")

    def test_reconcile_notes_the_round_it_landed_on(self):
        record = self.worker()
        self.work(record)
        self.wording_pass(record["id"], 4)
        self.clean_pass(record["id"], 5)
        dispatch.reconcile()
        self.assertIn("round 5", self.stored(record["id"])["note"])

    def test_reconcile_holds_a_change_whose_latest_round_failed(self):
        record = self.worker()
        self.work(record)
        self.approve(record["id"])
        self.round_of(record["id"], 3, "fail", findings=2)
        report = dispatch.reconcile()
        self.assertIn(record["id"], report["awaiting_review"])
        self.assertFalse((self.repo / "feature.txt").is_file(),
                         "nothing may reach the trunk on a round that failed")


class TestAnEmptyBranchIsNotLanded(GitCase):
    """Task f0b91b86f69f: reconcile discarded three running research workers.

    A branch with no commits on it is work that has not started, not work that
    has already landed. The two are indistinguishable to `merge-base`, which is
    why the sweep asked the wrong question.
    """

    def test_a_live_worker_with_nothing_committed_is_held(self):
        record = self.worker("research the options")
        report = dispatch.reconcile()
        self.assertNotIn(record["id"], report["landed"])
        self.assertTrue(Path(record["workdir"]).exists(),
                        "a running worker's checkout must survive the sweep")
        self.assertEqual([d["id"] for d in dispatch.live()], [record["id"]],
                         "a worker still out is not a dispatch that landed")

    def test_the_hold_is_reported(self):
        record = self.worker("research the options")
        report = dispatch.reconcile()
        held = [h for h in report["held"] if h["dispatch"] == record["id"]]
        self.assertEqual(len(held), 1)
        self.assertIn("no commits", held[0]["why"])

    def test_its_slot_is_kept(self):
        record = self.worker("research the options")
        dispatch.reconcile()
        self.assertEqual([l["id"] for l in worktrees.active("api")], [record["lease_id"]])

    def test_an_old_empty_branch_with_no_heartbeat_is_cleaned_up(self):
        record = self.worker("research the options")
        backdate(dispatch.dispatches_dir(), record["id"],
                 dispatch.EMPTY_BRANCH_STALE_HOURS + 1)
        report = dispatch.reconcile()
        self.assertIn(record["id"], report["landed"])
        self.assertFalse(Path(record["workdir"]).exists())

    def test_an_old_empty_branch_with_a_live_heartbeat_is_held(self):
        record = self.worker("research the options")
        backdate(dispatch.dispatches_dir(), record["id"],
                 dispatch.EMPTY_BRANCH_STALE_HOURS + 1)
        self.beat(Path(record["workdir"]))
        report = dispatch.reconcile()
        self.assertTrue([h for h in report["held"] if h["dispatch"] == record["id"]])
        self.assertTrue(Path(record["workdir"]).exists(),
                        "a worker whose tool calls are still returning is alive")

    def test_an_old_heartbeat_does_not_keep_a_dead_worker_alive(self):
        record = self.worker("research the options")
        backdate(dispatch.dispatches_dir(), record["id"],
                 dispatch.EMPTY_BRANCH_STALE_HOURS + 1)
        self.beat(Path(record["workdir"]), minutes_ago=dispatch.STALE_MINUTES + 1)
        report = dispatch.reconcile()
        self.assertIn(record["id"], report["landed"])

    def test_a_heartbeat_from_another_checkout_does_not_count(self):
        record = self.worker("research the options")
        backdate(dispatch.dispatches_dir(), record["id"],
                 dispatch.EMPTY_BRANCH_STALE_HOURS + 1)
        self.beat(self.repo)
        report = dispatch.reconcile()
        self.assertIn(record["id"], report["landed"])

    def test_uncommitted_work_is_saved_and_lands_rather_than_holding(self):
        record = self.worker()
        (Path(record["workdir"]) / "loose.py").write_text("never committed\n")
        self.approve(record["id"])
        dispatch.reconcile()
        self.assertTrue((self.repo / "loose.py").is_file(),
                        "autosave runs first, so this branch is not empty")

    def test_work_already_merged_is_still_cleaned_up(self):
        record = self.worker()
        self.work(record)
        self.approve(record["id"])
        dispatch.reconcile()
        again = dispatch.reconcile()
        self.assertEqual(again["landed"], [])
        self.assertFalse(Path(record["workdir"]).exists())


if __name__ == "__main__":
    unittest.main()
