#!/usr/bin/env python3
"""Tests for the ways the sweep and its records said something that was not so.

Each class is one recorded defect, reproduced before it was fixed:

* a pass from an old round counting after later rounds failed,
* one wording-only round counting as the end of a review that needs two,
* a branch with nothing on it read as work that has already landed,
* a sweep that printed what it could not finish and then exited 0,
* a dispatch closed as landed without a word about the review it rested on,
* a worker that abandoned an empty branch recorded as one that landed work.

They end the same way — a merge nobody approved, a live worker's checkout
deleted, or a green wake over work nobody finished — so all of them are tested
against the real stores and, where git is what decides, a real repository.
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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

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
        """Two rounds both called "round 2": the one recorded last decides.

        Built so that the two orderings disagree. The fail is stored first, so
        its filename sorts earliest and the store hands it over first; the pass
        is then backdated an hour, so `created` says the opposite of the
        filename. Reading the rounds in file order ends on two passes and calls
        the review over; reading them by `created` ends on the fail.
        """
        self.round_of("auth", 2, "fail", findings=1)
        later_pass = self.clean_pass("auth", 2)
        backdate(store.reviews_dir(), later_pass["id"], 1)
        self.clean_pass("auth", 3)
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
        """One change's rounds never end another change's review.

        "other" is reviewed to the end while "auth" has a single pass of its
        own. Counting every round in the store would read auth's pass and
        other's last pass as two consecutive passes for auth.
        """
        self.approve("other")
        self.wording_pass("auth", 1)
        self.assertFalse(dispatch.reviewed("auth"),
                         "auth has had one round; another change's rounds are not auth's")
        self.assertTrue(dispatch.reviewed("other"))


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

    def test_skipping_review_records_the_reason_given(self):
        """OPINIONS.md 13 lets the stoker skip review "recording why in the store note".

        The override phrase alone says a human decided; it does not say what
        they decided on, which is the half somebody reading the note a week
        later needs.
        """
        record = self.worker()
        self.work(record)
        landed = dispatch.land(record["id"], skip_review=True,
                               reason="research doc, stoker read it end to end")
        self.assertIn("review skipped by the stoker's explicit override: "
                      "research doc, stoker read it end to end", landed["note"])

    def test_skipping_review_without_a_reason_says_no_reason_was_given(self):
        """Refused would strand the override; silence would read as a reason."""
        record = self.worker()
        self.work(record)
        landed = dispatch.land(record["id"], skip_review=True)
        self.assertIn("review skipped by the stoker's explicit override "
                      "(no reason given)", landed["note"])

    def test_reconcile_records_that_review_was_skipped(self):
        record = self.worker()
        self.work(record)
        dispatch.reconcile(require_review=False)
        note = self.stored(record["id"])["note"]
        self.assertIn("review skipped by the stoker's explicit override "
                      "(no reason given)", note)

    def test_reconcile_records_the_reason_review_was_skipped(self):
        record = self.worker()
        self.work(record)
        dispatch.reconcile(require_review=False, reason="one-line typo fix")
        self.assertIn("review skipped by the stoker's explicit override: "
                      "one-line typo fix", self.stored(record["id"])["note"])

    def test_the_reason_reaches_the_note_from_the_command_line(self):
        """The flag is only worth having if it is wired to the note."""
        landing = self.worker()
        self.work(landing)
        with contextlib.redirect_stdout(io.StringIO()):
            dispatch.main(["dispatch.py", "land", landing["id"], "--skip-review",
                           "--reason", "operator read it"])
        self.assertIn("override: operator read it", self.stored(landing["id"])["note"])

        swept = self.worker()
        self.work(swept, name="second.txt")
        with contextlib.redirect_stdout(io.StringIO()):
            dispatch.main(["dispatch.py", "reconcile", "--skip-review",
                           "--reason", "operator read this one too"])
        self.assertIn("override: operator read this one too",
                      self.stored(swept["id"])["note"])

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
        self.assertIn(record["id"], report["abandoned"])
        self.assertFalse(Path(record["workdir"]).exists())

    def test_an_old_empty_branch_with_a_live_heartbeat_is_kept(self):
        record = self.worker("research the options")
        backdate(dispatch.dispatches_dir(), record["id"],
                 dispatch.EMPTY_BRANCH_STALE_HOURS + 1)
        self.beat(Path(record["workdir"]))
        report = dispatch.reconcile()
        self.assertIn(record["id"], report["awaiting_review"])
        self.assertNotIn(record["id"], report["landed"])
        self.assertTrue(Path(record["workdir"]).exists(),
                        "a worker whose tool calls are still returning is alive")

    def test_an_old_heartbeat_does_not_keep_a_dead_worker_alive(self):
        record = self.worker("research the options")
        backdate(dispatch.dispatches_dir(), record["id"],
                 dispatch.EMPTY_BRANCH_STALE_HOURS + 1)
        self.beat(Path(record["workdir"]), minutes_ago=dispatch.STALE_MINUTES + 1)
        report = dispatch.reconcile()
        self.assertIn(record["id"], report["abandoned"])

    def test_a_heartbeat_from_another_checkout_does_not_count(self):
        record = self.worker("research the options")
        backdate(dispatch.dispatches_dir(), record["id"],
                 dispatch.EMPTY_BRANCH_STALE_HOURS + 1)
        self.beat(self.repo)
        report = dispatch.reconcile()
        self.assertIn(record["id"], report["abandoned"])

    def test_uncommitted_work_is_saved_and_lands_rather_than_holding(self):
        record = self.worker()
        (Path(record["workdir"]) / "loose.py").write_text("never committed\n")
        self.approve(record["id"])
        dispatch.reconcile()
        self.assertTrue((self.repo / "loose.py").is_file(),
                        "autosave runs first, so this branch is not empty")

    def test_work_already_merged_is_still_cleaned_up(self):
        """A sweep that merged and then stopped leaves the rest to the next one.

        This is the state reconcile finds after a crash between the merge and
        the cleanup: the dispatch still open, its slot still held, and the
        commits already reachable from the trunk. The checkout is gone because
        removing it is the step that sweep got through before it stopped. The
        same state with the checkout still in place is the test below.
        """
        record = self.worker()
        self.work(record)
        self.approve(record["id"])
        lease = next(l for l in jsonstore.load(worktrees.leases_dir())
                     if l["id"] == record["lease_id"])
        run("git", "merge", "--no-ff", lease["branch"], "-m", "landed by hand", cwd=self.repo)
        run("git", "worktree", "remove", "--force", lease["path"], cwd=self.repo)

        report = dispatch.reconcile()

        self.assertEqual(report["landed"], [record["id"]])
        self.assertIn("already in the trunk", self.stored(record["id"])["note"],
                      "work the trunk already has is cleaned up, not merged again")
        self.assertFalse(Path(record["workdir"]).exists())

    def test_work_merged_with_its_checkout_still_there_lands_rather_than_holding(self):
        """Finding 113737ab1cf3: merged work was held as work that never started.

        Counting the commits the trunk does not have answers 0 for two opposite
        branches: one nobody has committed on, and one whose commits the trunk
        already has. Asked only that way, a branch merged by hand — or by a
        sweep that stopped before removing the checkout — is held on "no commits
        yet; the worker is still out", and a day later closed as work nobody
        ever did. What separates them is the commit the slot was cut from: this
        branch has moved past it, so it has been merged, not skipped.
        """
        record = self.worker()
        self.work(record)
        self.approve(record["id"])
        lease = next(l for l in jsonstore.load(worktrees.leases_dir())
                     if l["id"] == record["lease_id"])
        run("git", "merge", "--no-ff", lease["branch"], "-m", "landed by hand", cwd=self.repo)
        self.assertTrue(Path(record["workdir"]).exists(), "the checkout is still there")

        report = dispatch.reconcile()

        self.assertEqual(report["held"], [], "merged work is not a worker still out")
        self.assertEqual(report["landed"], [record["id"]])
        self.assertIn("already in the trunk", self.stored(record["id"])["note"])
        self.assertFalse(Path(record["workdir"]).exists(),
                         "its slot goes back once the trunk provably has the work")

    def test_a_live_worker_that_caught_up_with_a_moved_trunk_is_kept(self):
        """A branch reaches the trunk two ways, and only one of them is finished.

        A worker that runs `git merge main` before its first commit leaves a
        branch whose commits the trunk has, standing past the commit the slot
        was cut from — the same two answers a merged branch gives. Read as
        merged, the sweep deletes the checkout of a worker whose last tool call
        was seconds ago. The heartbeat is what separates them.
        """
        record = self.worker("research the options")
        (self.repo / "b.txt").write_text("trunk moved on\n")
        run("git", "add", "-A", cwd=self.repo)
        run("git", "commit", "-qm", "trunk moves", cwd=self.repo)
        run("git", "merge", "--no-edit", "-q", "main", cwd=Path(record["workdir"]))
        self.beat(Path(record["workdir"]))

        report = dispatch.reconcile()

        self.assertIn(record["id"], report["awaiting_review"],
                      "a worker still making tool calls is not finished")
        self.assertNotIn(record["id"], report["landed"])
        self.assertTrue(Path(record["workdir"]).exists(),
                        "a running worker's checkout must survive the sweep")
        self.assertEqual([d["id"] for d in dispatch.live()], [record["id"]],
                         "a worker still out is not a dispatch that landed")

    def test_a_silent_checkout_whose_work_is_in_the_trunk_still_lands(self):
        """The guard is the heartbeat, not the state of the branch.

        Same branch as the test above with nothing heard from the checkout, so
        the sweep that finds it must still clean it up; otherwise the guard
        would strand every merged slot instead of the running ones.
        """
        record = self.worker()
        self.work(record)
        self.approve(record["id"])
        lease = next(l for l in jsonstore.load(worktrees.leases_dir())
                     if l["id"] == record["lease_id"])
        run("git", "merge", "--no-ff", lease["branch"], "-m", "landed by hand", cwd=self.repo)
        self.beat(Path(record["workdir"]), minutes_ago=dispatch.STALE_MINUTES + 1)

        report = dispatch.reconcile()

        self.assertEqual(report["landed"], [record["id"]])
        self.assertFalse(Path(record["workdir"]).exists())

    def test_an_old_silent_merged_checkout_is_not_closed_as_never_started(self):
        """The same branch left a day, which is when the false note gets written."""
        record = self.worker()
        self.work(record)
        self.approve(record["id"])
        backdate(dispatch.dispatches_dir(), record["id"],
                 dispatch.EMPTY_BRANCH_STALE_HOURS + 1)
        lease = next(l for l in jsonstore.load(worktrees.leases_dir())
                     if l["id"] == record["lease_id"])
        run("git", "merge", "--no-ff", lease["branch"], "-m", "landed by hand", cwd=self.repo)

        dispatch.reconcile()

        note = self.stored(record["id"])["note"]
        self.assertIn("already in the trunk", note)
        self.assertNotIn("nothing committed", note,
                         "the work is in the trunk; the record may not say there was none")

    def test_a_lease_with_no_recorded_base_is_held_rather_than_guessed_at(self):
        """Older leases never recorded where they were cut from, so nothing is assumed.

        Without that commit the two empty-looking branches cannot be told
        apart, and the safe half is holding the slot: the same refusal
        `worktrees.work_at_risk` makes for the same missing record.
        """
        record = self.worker("research the options")
        lease = next(l for l in jsonstore.load(worktrees.leases_dir())
                     if l["id"] == record["lease_id"])
        lease["base_sha"] = ""
        jsonstore.write(worktrees.leases_dir(), lease)

        report = dispatch.reconcile()

        held = [h for h in report["held"] if h["dispatch"] == record["id"]]
        self.assertEqual(len(held), 1)
        self.assertIn("no record of the commit it was cut from", held[0]["why"])
        self.assertTrue(Path(record["workdir"]).exists())



class TestTheSweepDoesNotCommitALiveWorkersFiles(GitCase):
    """Task d80c47c137ae: the autosave that ran before any heartbeat guard.

    Every guard in reconcile asks the heartbeat before deleting a checkout, but
    autosave ran above all of them, so a sweep passing a worker mid-edit staged
    and committed a half-written file on that worker's branch. Nothing is lost,
    which is why it went unnoticed; what it costs is a commit the worker did not
    make, in the middle of the change it was making.
    """

    def dirty(self, record: dict) -> str:
        done = subprocess.run(["git", "status", "--porcelain"], cwd=record["workdir"],
                              capture_output=True, text=True, check=True, timeout=60)
        return done.stdout

    def test_loose_files_are_left_alone_while_the_worker_is_still_in_the_checkout(self):
        record = self.worker()
        self.work(record)
        (Path(record["workdir"]) / "half_written.py").write_text("def half(\n")
        self.beat(Path(record["workdir"]))

        report = dispatch.reconcile()

        self.assertIn("half_written.py", self.dirty(record),
                      "the sweep may not commit a file the worker is still writing")
        self.assertIn(record["id"], report["awaiting_review"],
                      "a worker nobody has reviewed yet is awaiting review, not held")
        self.assertEqual([d["id"] for d in dispatch.live()], [record["id"]])

    def test_a_live_unreviewed_worker_does_not_hold_the_sweep(self):
        """Holding back autosave may not turn a normal wake into a failed one.

        Every worker still out is unreviewed for most of its life. Reporting one
        as held makes `reconcile` exit non-zero on every wake with anybody
        working, which is the ordinary state of the fleet, and hides the real
        holds among them.
        """
        record = self.worker()
        self.work(record)
        (Path(record["workdir"]) / "half_written.py").write_text("def half(\n")
        self.beat(Path(record["workdir"]))

        report = dispatch.reconcile()

        self.assertEqual(report["held"], [],
                         "a live unreviewed worker is not something to hold the sweep on")
        self.assertEqual(report["needs_fix"], [])

    def test_a_reviewed_checkouts_loose_files_are_saved_even_with_a_worker_in_it(self):
        """The one route that takes a live checkout still commits its loose work.

        A dispatch whose review has ended is cleaned up on the next sweep even
        with a session still working in it — `README` says so, and says not to
        keep one open expecting it to survive. Since that route removes the
        checkout, skipping autosave there would delete the loose files with it,
        which is the opposite of what holding back autosave is for.
        """
        record = self.worker()
        self.work(record)
        (Path(record["workdir"]) / "loose.py").write_text("never committed\n")
        self.approve(record["id"])
        self.beat(Path(record["workdir"]))

        report = dispatch.reconcile()

        self.assertEqual(report["landed"], [record["id"]])
        self.assertTrue((self.repo / "loose.py").is_file(),
                        "the route that takes the checkout must save what is loose in it")

    def test_a_silent_checkouts_loose_files_are_still_saved(self):
        """The guard is the heartbeat, so silence is still autosaved: otherwise
        the sweep would stop protecting the work it exists to protect."""
        record = self.worker()
        (Path(record["workdir"]) / "loose.py").write_text("never committed\n")
        self.approve(record["id"])
        self.beat(Path(record["workdir"]), minutes_ago=dispatch.STALE_MINUTES + 1)

        dispatch.reconcile()

        self.assertTrue((self.repo / "loose.py").is_file(),
                        "a checkout nobody is in is autosaved and lands as before")


class TestSkipReviewDoesNotTakeALiveWorkersSlot(GitCase):
    """The third route out of reconcile that removes a checkout: the merge.

    The two before it — an empty branch, and a branch the trunk already
    contains — each ask the heartbeat before deleting anything. The merge route
    asked only whether a review was recorded, so `--skip-review` walked a
    running worker's first commit into the trunk and took the checkout with it.
    """

    def test_skip_review_holds_a_worker_whose_tool_calls_still_return(self):
        record = self.worker()
        self.work(record)
        self.beat(Path(record["workdir"]))

        report = dispatch.reconcile(require_review=False, reason="stoker override")

        held = [h for h in report["held"] if h["dispatch"] == record["id"]]
        self.assertEqual(len(held), 1, "a worker still making tool calls is not finished")
        self.assertIn("tool call", held[0]["why"])
        self.assertEqual(report["landed"], [])
        self.assertTrue(Path(record["workdir"]).exists(),
                        "a running worker's checkout must survive the sweep")
        self.assertEqual([d["id"] for d in dispatch.live()], [record["id"]],
                         "a worker still out is not a dispatch that landed")

    def test_skip_review_lands_the_same_branch_once_the_checkout_goes_silent(self):
        """The guard is the heartbeat, so silence still lands: otherwise the
        override would never land anything at all."""
        record = self.worker()
        self.work(record)
        self.beat(Path(record["workdir"]), minutes_ago=dispatch.STALE_MINUTES + 1)

        report = dispatch.reconcile(require_review=False, reason="stoker override")

        self.assertEqual(report["landed"], [record["id"]])
        self.assertEqual(report["held"], [])
        self.assertFalse(Path(record["workdir"]).exists())
        self.assertIn("review skipped", self.stored(record["id"])["note"])


class TestTheSweepsExitCodeSaysWhatItFound(GitCase):
    """Task 68b249e08219: a sweep printed work it could not finish and exited 0.

    The stoker reads the exit code at every wake. A sweep that prints a hold and
    then says green leaves the hold for whoever happens to read the text, which
    on a wake at four in the morning is nobody.
    """

    def sweep(self, *args: str) -> tuple[int, str]:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = dispatch.main(["dispatch.py", "reconcile", *args])
        return code, printed.getvalue()

    def clean_report(self, **extra) -> dict:
        report = {"at": jsonstore.now(), "landed": [], "abandoned": [], "held": [],
                  "awaiting_review": [], "needs_fix": [], "runs_finished": []}
        report.update(extra)
        return report

    def test_a_held_dispatch_exits_non_zero(self):
        record = self.worker()
        self.work(record)
        (self.repo / "operator.txt").write_text("uncommitted work of the operator's\n")

        code, printed = self.sweep()

        self.assertEqual(code, 1, f"a sweep that held everything is not green:\n{printed}")
        self.assertTrue(Path(record["workdir"]).exists())

    def test_a_branch_needing_a_fixer_exits_non_zero(self):
        record = self.worker()
        self.work(record)
        self.approve(record["id"])

        code, printed = self.sweep("--gate", "exit 1")

        self.assertEqual(code, 1, f"a branch needing a fixer is not green:\n{printed}")

    def test_a_worker_still_awaiting_review_is_green(self):
        """Settled in ced8b534b39b: every worker is unreviewed for most of its life."""
        record = self.worker()
        self.work(record)

        code, printed = self.sweep()

        self.assertIn("awaiting review  1", printed)
        self.assertEqual(code, 0, "a live worker nobody has reviewed yet is the normal state")

    def test_a_sweep_that_landed_everything_is_green(self):
        record = self.worker()
        self.work(record)
        self.approve(record["id"])

        code, printed = self.sweep()

        self.assertEqual(code, 0, printed)
        self.assertEqual(self.stored(record["id"])["outcome"], "landed")

    def test_an_entry_the_exit_code_never_heard_of_is_not_green(self):
        """The exit code is read off the report, not off a list of two keys.

        Every way the sweep learns to say "this is not finished" — commits left
        on a branch, commits it could not check — has to reach the wake on the
        day it is added, not on the day somebody remembers to extend the exit.
        """
        report = self.clean_report(left_on_the_branch=[{"dispatch": "d1",
                                                        "why": "never reached the trunk"}])
        with mock.patch.object(dispatch, "reconcile", return_value=report):
            code, printed = self.sweep()

        self.assertEqual(code, 1, "work the sweep could not finish may not read as green")
        self.assertIn("left_on_the_branch", printed,
                      "an exit of 1 has to say on screen what it is about")

    def test_the_clean_keys_are_named_and_only_those(self):
        self.assertEqual(dispatch.reconcile_unclean(
            self.clean_report(landed=["a"], awaiting_review=["b"], runs_finished=["r"])), [])
        self.assertEqual(dispatch.reconcile_unclean(self.clean_report(held=[{"why": "x"}])),
                         ["held"])
        self.assertEqual(dispatch.reconcile_unclean(self.clean_report(needs_fix=[{"why": "x"}])),
                         ["needs_fix"])


class TestClosingSaysWhatItRestedOn(GitCase):
    """Task 3259f1e2808e: two routes closed a dispatch as landed saying nothing.

    Both are cleanup rather than merges — the commits are in the trunk already,
    or there is no checkout left to consolidate — so neither reads the review
    store before closing. That is right; saying nothing about it is not, because
    the note is the only place a landing can be checked from afterwards.
    """

    def test_a_dispatch_with_no_checkout_records_the_review_state_it_closed_on(self):
        record = self.worker()
        self.work(record)
        worktrees.release(record["lease_id"], "taken back by hand", force=True)

        dispatch.reconcile()

        note = self.stored(record["id"])["note"]
        self.assertIn("no checkout to consolidate", note)
        self.assertIn("no round recorded", note,
                      "a close that consulted no review must say so in the note")

    def test_a_dispatch_with_no_checkout_names_a_failed_round(self):
        record = self.worker()
        self.work(record)
        self.round_of(record["id"], 3, "fail", findings=2)
        worktrees.release(record["lease_id"], "taken back by hand", force=True)

        dispatch.reconcile()

        self.assertIn("round 3: fail", self.stored(record["id"])["note"])

    def test_already_in_the_trunk_records_the_review_state_it_closed_on(self):
        record = self.worker()
        self.work(record)
        lease = next(l for l in jsonstore.load(worktrees.leases_dir())
                     if l["id"] == record["lease_id"])
        run("git", "merge", "--no-ff", lease["branch"], "-m", "landed by hand", cwd=self.repo)

        dispatch.reconcile()

        note = self.stored(record["id"])["note"]
        self.assertIn("already in the trunk", note)
        self.assertIn("no round recorded", note,
                      "the trunk has the commits; the note still has to say what that rested on")

    def test_already_in_the_trunk_names_a_failed_round(self):
        record = self.worker()
        self.work(record)
        self.round_of(record["id"], 2, "fail", findings=5)
        lease = next(l for l in jsonstore.load(worktrees.leases_dir())
                     if l["id"] == record["lease_id"])
        run("git", "merge", "--no-ff", lease["branch"], "-m", "landed by hand", cwd=self.repo)

        dispatch.reconcile()

        self.assertIn("round 2: fail", self.stored(record["id"])["note"])


class TestAnAbandonedWorkerIsNotALanding(GitCase):
    """Task 3259f1e2808e, the half about a worker that produced nothing.

    An empty branch left past `EMPTY_BRANCH_STALE_HOURS` with a silent checkout
    is a worker that went away. Closing it as `landed` puts it in every count of
    what the fleet delivered, and `abandoned` has been an outcome all along.
    """

    def stale_empty_worker(self) -> dict:
        record = self.worker("research the options")
        backdate(dispatch.dispatches_dir(), record["id"],
                 dispatch.EMPTY_BRANCH_STALE_HOURS + 1)
        return record

    def test_an_abandoned_empty_branch_closes_as_abandoned(self):
        record = self.stale_empty_worker()

        dispatch.reconcile()

        self.assertEqual(self.stored(record["id"])["outcome"], "abandoned",
                         "nothing landed; the record may not say it did")
        self.assertFalse(Path(record["workdir"]).exists(), "the slot still goes back")

    def test_the_sweep_reports_it_as_abandoned_rather_than_landed(self):
        record = self.stale_empty_worker()

        report = dispatch.reconcile()

        self.assertEqual(report["abandoned"], [record["id"]])
        self.assertEqual(report["landed"], [], "the report says what the record says")

    def test_an_abandoned_worker_is_not_a_sweep_that_needs_answering(self):
        """The slot is back and nothing is left on the branch, so the wake is green."""
        self.stale_empty_worker()
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = dispatch.main(["dispatch.py", "reconcile"])
        self.assertEqual(code, 0, printed.getvalue())

    def test_a_run_whose_last_member_abandoned_is_finished(self):
        """Nothing of the run is left anywhere, which is what the list means."""
        first = dispatch.open_dispatch("part one", run_id="r1")
        second = dispatch.open_dispatch("part two", run_id="r1")
        dispatch.close_dispatch(first["id"], "landed", "merged")
        self.assertEqual(dispatch.finished_runs(), [],
                         "one member is still out; the run is not finished")
        dispatch.close_dispatch(second["id"], "abandoned", "the worker went away")
        self.assertEqual(dispatch.finished_runs(), ["r1"])

    def test_a_run_with_a_failed_member_is_not_finished(self):
        first = dispatch.open_dispatch("part one", run_id="r2")
        second = dispatch.open_dispatch("part two", run_id="r2")
        dispatch.close_dispatch(first["id"], "landed", "merged")
        dispatch.close_dispatch(second["id"], "failed", "the gate never passed")
        self.assertEqual(dispatch.finished_runs(), [],
                         "a failed member leaves work to account for")


if __name__ == "__main__":
    unittest.main()
