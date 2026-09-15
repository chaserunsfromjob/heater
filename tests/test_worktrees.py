#!/usr/bin/env python3
"""Tests for on-demand worktree leases.

These run against a real git repository in a temporary directory, because the
failures that matter here are git's, not Python's. The rule the tests exist to
protect: a slot holding work that exists nowhere else is never destroyed, by any
route — closing a dispatch, an explicit release, or reclaiming.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dispatch  # noqa: E402
import store  # noqa: E402
import worktrees  # noqa: E402


def run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True, timeout=60)


class WorktreeCase(unittest.TestCase):
    ENV = ("HEATER_LEASES_DIR", "HEATER_WORKTREE_ROOT", "HEATER_DISPATCHES_DIR",
           "HEATER_REVIEWS_DIR", "HEATER_SUITES_DIR")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.previous = {k: os.environ.get(k) for k in self.ENV}
        os.environ["HEATER_LEASES_DIR"] = str(self.root / "leases")
        os.environ["HEATER_WORKTREE_ROOT"] = str(self.root / "trees")
        os.environ["HEATER_DISPATCHES_DIR"] = str(self.root / "dispatches")
        os.environ["HEATER_REVIEWS_DIR"] = str(self.root / "reviews")
        os.environ["HEATER_SUITES_DIR"] = str(self.root / "suites")

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
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()


class TestLeasing(WorktreeCase):
    def test_lease_creates_a_real_checkout(self):
        held = worktrees.lease(self.repo, "api", "worker/one")
        path = Path(held["path"])
        self.assertTrue((path / "a.txt").is_file(), "the worker has no files to work on")

    def test_lease_puts_it_on_its_own_branch(self):
        held = worktrees.lease(self.repo, "api", "worker/one")
        done = subprocess.run(["git", "-C", held["path"], "branch", "--show-current"],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.stdout.strip(), "worker/one")

    def test_two_leases_do_not_share_a_directory(self):
        first = worktrees.lease(self.repo, "api", "worker/one")
        second = worktrees.lease(self.repo, "api", "worker/two")
        self.assertNotEqual(first["path"], second["path"])

    def test_lease_shows_up_as_active(self):
        held = worktrees.lease(self.repo, "api", "worker/one")
        self.assertEqual([l["id"] for l in worktrees.active("api")], [held["id"]])

    def test_a_non_repository_is_refused(self):
        with self.assertRaises(ValueError):
            worktrees.lease(self.root / "not-a-repo", "api", "worker/one")

    def test_the_cap_is_enforced(self):
        for n in range(worktrees.MAX_SLOTS):
            worktrees.lease(self.repo, "api", f"worker/{n}")
        with self.assertRaises(worktrees.NoSlotAvailable):
            worktrees.lease(self.repo, "api", "worker/overflow")

    def test_the_cap_is_per_project(self):
        for n in range(worktrees.MAX_SLOTS):
            worktrees.lease(self.repo, "api", f"worker/{n}")
        other = worktrees.lease(self.repo, "web", "worker/web")
        self.assertTrue(Path(other["path"]).exists(), "one busy project must not block another")


class TestReleasing(WorktreeCase):
    def test_release_removes_the_checkout(self):
        held = worktrees.lease(self.repo, "api", "worker/one")
        path = Path(held["path"])
        worktrees.release(held["id"])
        self.assertFalse(path.exists())

    def test_release_frees_the_slot(self):
        held = worktrees.lease(self.repo, "api", "worker/one")
        worktrees.release(held["id"])
        self.assertEqual(worktrees.active("api"), [])

    def test_release_is_idempotent(self):
        held = worktrees.lease(self.repo, "api", "worker/one")
        worktrees.release(held["id"])
        worktrees.release(held["id"])

    def test_unknown_lease_is_refused(self):
        with self.assertRaises(ValueError):
            worktrees.release("deadbeefcafe")

    def test_uncommitted_work_blocks_release(self):
        held = worktrees.lease(self.repo, "api", "worker/one")
        (Path(held["path"]) / "wip.txt").write_text("half finished\n")
        with self.assertRaises(RuntimeError):
            worktrees.release(held["id"])
        self.assertTrue(Path(held["path"]).exists(), "the work must still be there")

    def test_unpushed_commits_block_release(self):
        held = worktrees.lease(self.repo, "api", "worker/one")
        path = Path(held["path"])
        (path / "done.txt").write_text("real work\n")
        run("git", "add", "-A", cwd=path)
        run("git", "commit", "-qm", "work", cwd=path)
        with self.assertRaises(RuntimeError):
            worktrees.release(held["id"])

    def test_force_releases_anyway(self):
        held = worktrees.lease(self.repo, "api", "worker/one")
        (Path(held["path"]) / "wip.txt").write_text("half finished\n")
        worktrees.release(held["id"], force=True)
        self.assertEqual(worktrees.active("api"), [])


class TestReclaim(WorktreeCase):
    def test_reclaims_a_slot_whose_checkout_vanished(self):
        held = worktrees.lease(self.repo, "api", "worker/one")
        subprocess.run(["rm", "-rf", held["path"]], check=True, timeout=30)
        self.assertEqual(len(worktrees.reclaim("api")), 1)
        self.assertEqual(worktrees.active("api"), [])

    def test_never_reclaims_a_slot_holding_work(self):
        held = worktrees.lease(self.repo, "api", "worker/one")
        (Path(held["path"]) / "wip.txt").write_text("half finished\n")
        worktrees.reclaim("api")
        self.assertEqual(len(worktrees.active("api")), 1, "reclaim must never destroy work")

    def test_leaves_a_fresh_slot_alone(self):
        worktrees.lease(self.repo, "api", "worker/one")
        self.assertEqual(worktrees.reclaim("api"), [])

    def test_lease_reclaims_before_refusing(self):
        held = [worktrees.lease(self.repo, "api", f"worker/{n}") for n in range(worktrees.MAX_SLOTS)]
        subprocess.run(["rm", "-rf", held[0]["path"]], check=True, timeout=30)
        fresh = worktrees.lease(self.repo, "api", "worker/next")
        self.assertTrue(Path(fresh["path"]).exists(),
                        "a dead worker's slot must not block a live one")


class TestEveryWorkerGetsItsOwn(WorktreeCase):
    """The project's checkout is the consolidation target, never a workspace."""

    def test_even_the_first_worker_leases(self):
        record = dispatch.open_dispatch("fix auth", project="api", repo=str(self.repo))
        self.assertTrue(record["lease_id"])
        self.assertNotEqual(record["workdir"], str(self.repo))

    def test_the_main_checkout_is_never_handed_to_a_worker(self):
        for n in range(3):
            record = dispatch.open_dispatch(f"task {n}", project="api", repo=str(self.repo))
            self.assertNotEqual(record["workdir"], str(self.repo))

    def test_two_workers_do_not_share_a_checkout(self):
        first = dispatch.open_dispatch("one", project="api", repo=str(self.repo))
        second = dispatch.open_dispatch("two", project="api", repo=str(self.repo))
        self.assertNotEqual(first["workdir"], second["workdir"])
        self.assertNotEqual(first["branch"], second["branch"])

    def test_no_repo_means_no_lease(self):
        record = dispatch.open_dispatch("no repo given", project="api")
        self.assertEqual(record["lease_id"], "")

    def test_the_brief_tells_the_worker_where_to_work(self):
        record = dispatch.open_dispatch("fix parser", project="api", repo=str(self.repo))
        brief = dispatch.compose_brief(record)
        self.assertIn(record["workdir"], brief)
        self.assertIn(record["branch"], brief)


class TestRuns(WorktreeCase):
    """Several workers, one task."""

    def test_a_run_starts_every_worker(self):
        records = dispatch.start_run("split the parser", repo=str(self.repo),
                                     project="api", workers=3)
        self.assertEqual(len(records), 3)

    def test_workers_in_a_run_share_a_run_id(self):
        records = dispatch.start_run("one task", repo=str(self.repo), project="api", workers=2)
        self.assertEqual(len({r["run_id"] for r in records}), 1)

    def test_each_worker_gets_its_own_checkout(self):
        records = dispatch.start_run("one task", repo=str(self.repo), project="api", workers=3)
        self.assertEqual(len({r["workdir"] for r in records}), 3)

    def test_parts_are_labelled(self):
        records = dispatch.start_run("one task", repo=str(self.repo), project="api",
                                     workers=2, parts=["the lexer", "the parser"])
        self.assertEqual([r["part"] for r in records], ["the lexer", "the parser"])

    def test_part_count_must_match_worker_count(self):
        with self.assertRaises(ValueError):
            dispatch.start_run("x", repo=str(self.repo), workers=3, parts=["only one"])

    def test_a_run_needs_at_least_one_worker(self):
        with self.assertRaises(ValueError):
            dispatch.start_run("x", repo=str(self.repo), workers=0)

    def test_a_run_cannot_exceed_the_slot_cap(self):
        with self.assertRaises(worktrees.NoSlotAvailable):
            dispatch.start_run("too many", repo=str(self.repo), project="api",
                               workers=worktrees.MAX_SLOTS + 1)


class TestReconcile(WorktreeCase):
    """The sweep: consolidate everything finished, clean up after it, lose nothing."""

    def start(self, workers: int = 2):
        return dispatch.start_run("one task", repo=str(self.repo), project="api", workers=workers)

    def work(self, record: dict, name: str, body: str, commit: bool = True):
        path = Path(record["workdir"])
        (path / name).write_text(body)
        if commit:
            run("git", "add", "-A", cwd=path)
            run("git", "commit", "-qm", f"work on {name}", cwd=path)

    def approve(self, *records: dict):
        for record in records:
            store.record_review(record["id"], 1, "default", "pass")

    def test_committed_work_reaches_the_trunk(self):
        first, second = self.start()
        self.work(first, "a.py", "from a\n")
        self.work(second, "b.py", "from b\n")
        self.approve(first, second)
        dispatch.reconcile()
        self.assertTrue((self.repo / "a.py").is_file())
        self.assertTrue((self.repo / "b.py").is_file())

    def test_uncommitted_work_is_saved_not_lost(self):
        first, second = self.start()
        self.work(first, "a.py", "from a\n")
        self.work(second, "loose.py", "never committed\n", commit=False)
        self.approve(first, second)
        dispatch.reconcile()
        self.assertTrue((self.repo / "loose.py").is_file(),
                        "uncommitted work is the easiest to lose and must survive")

    def test_everything_is_cleaned_up_afterwards(self):
        records = self.start()
        for n, record in enumerate(records):
            self.work(record, f"f{n}.py", f"{n}\n")
        self.approve(*records)
        dispatch.reconcile()
        self.assertEqual(worktrees.active("api"), [], "no slots left")
        for record in records:
            self.assertFalse(Path(record["workdir"]).exists(), "no folders left")
        done = subprocess.run(["git", "-C", str(self.repo), "branch", "--list", "worker/*"],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.stdout.strip(), "", "no branches left")

    def test_the_run_is_reported_finished(self):
        records = self.start()
        for n, record in enumerate(records):
            self.work(record, f"f{n}.py", f"{n}\n")
        self.approve(*records)
        report = dispatch.reconcile()
        self.assertIn(records[0]["run_id"], report["runs_finished"])

    def test_unreviewed_work_waits_and_is_kept(self):
        first, _ = self.start()
        self.work(first, "a.py", "from a\n")
        report = dispatch.reconcile()
        self.assertIn(first["id"], report["awaiting_review"])
        self.assertTrue(Path(first["workdir"]).exists(), "waiting must never mean discarding")

    def test_skipping_review_lands_it(self):
        first, second = self.start()
        self.work(first, "a.py", "from a\n")
        dispatch.reconcile(require_review=False)
        self.assertTrue((self.repo / "a.py").is_file())

    def test_a_worker_that_did_nothing_is_cleaned_up(self):
        records = self.start()
        self.approve(*records)
        dispatch.reconcile()
        self.assertEqual(worktrees.active("api"), [])

    def test_a_conflict_is_flagged_and_nothing_is_lost(self):
        first, second = self.start()
        self.work(first, "a.txt", "first version\n")
        self.work(second, "a.txt", "second version\n")
        self.approve(first, second)
        report = dispatch.reconcile()
        self.assertEqual(len(report["landed"]), 1)
        self.assertEqual(len(report["needs_fix"]), 1)
        loser = report["needs_fix"][0]["dispatch"]
        losing = first if first["id"] == loser else second
        self.assertTrue(Path(losing["workdir"]).exists(), "the losing worker keeps its work")

    def test_a_conflict_leaves_the_trunk_untouched(self):
        first, second = self.start()
        self.work(first, "a.txt", "first version\n")
        self.work(second, "a.txt", "second version\n")
        self.approve(first, second)
        dispatch.reconcile()
        done = subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain"],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.stdout.strip(), "", "no half-applied merge may be left behind")

    def test_a_moved_trunk_is_merged_in_rather_than_refused(self):
        """The usual conflict cause is the trunk moving while a worker was out."""
        first, second = self.start()
        self.work(first, "a.py", "from a\n")
        self.work(second, "b.py", "from b\n")
        self.approve(first, second)
        dispatch.reconcile()
        self.assertTrue((self.repo / "a.py").is_file() and (self.repo / "b.py").is_file())

    def test_running_it_again_changes_nothing(self):
        records = self.start()
        for n, record in enumerate(records):
            self.work(record, f"f{n}.py", f"{n}\n")
        self.approve(*records)
        dispatch.reconcile()
        before = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "HEAD"],
                                capture_output=True, text=True, timeout=30).stdout
        report = dispatch.reconcile()
        after = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "HEAD"],
                               capture_output=True, text=True, timeout=30).stdout
        self.assertEqual(before, after)
        self.assertEqual(report["landed"], [])

    def test_a_dirty_trunk_holds_everything_rather_than_mixing_it_in(self):
        first, _ = self.start()
        self.work(first, "a.py", "from a\n")
        self.approve(first)
        (self.repo / "operator-wip.txt").write_text("mine\n")
        report = dispatch.reconcile()
        self.assertTrue(report["held"])
        self.assertTrue(Path(first["workdir"]).exists())
        self.assertEqual((self.repo / "operator-wip.txt").read_text(), "mine\n")

    def test_a_failing_gate_flags_rather_than_lands(self):
        first, _ = self.start()
        self.work(first, "a.py", "from a\n")
        self.approve(first)
        report = dispatch.reconcile(gate="exit 1")
        self.assertTrue(report["needs_fix"])
        self.assertFalse((self.repo / "a.py").is_file())

    def test_cleanup_is_refused_when_work_is_not_in_the_trunk(self):
        """The invariant the whole sweep rests on."""
        first, _ = self.start()
        lease = worktrees.active("api")[0]
        self.work(first, "a.py", "from a\n")
        with self.assertRaises(RuntimeError):
            dispatch.finish(first, lease, lease["branch"], self.repo,
                            lease.get("base_branch") or "main", "pretending")


class TestLanding(WorktreeCase):
    """The end of a dispatch: the work merges back and the extra checkout goes."""

    def second_worker(self, task: str = "add a feature"):
        return dispatch.open_dispatch(task, project="api", repo=str(self.repo))

    def do_work(self, record: dict, name: str = "feature.txt", body: str = "new\n"):
        path = Path(record["workdir"])
        (path / name).write_text(body)
        run("git", "add", "-A", cwd=path)
        run("git", "commit", "-qm", f"add {name}", cwd=path)

    def pass_review(self, record: dict):
        store.record_review(record["id"], 1, "default", "pass", cost_usd=0.1)

    def test_work_reaches_the_main_checkout(self):
        record = self.second_worker()
        self.do_work(record)
        self.pass_review(record)
        dispatch.land(record["id"])
        self.assertTrue((self.repo / "feature.txt").is_file(),
                        "the whole point is that the work comes back")

    def test_the_extra_checkout_is_removed(self):
        record = self.second_worker()
        self.do_work(record)
        self.pass_review(record)
        workdir = Path(record["workdir"])
        dispatch.land(record["id"])
        self.assertFalse(workdir.exists())

    def test_the_slot_is_freed(self):
        record = self.second_worker()
        self.do_work(record)
        self.pass_review(record)
        dispatch.land(record["id"])
        self.assertEqual(worktrees.active("api"), [])

    def test_the_dispatch_closes_as_landed(self):
        record = self.second_worker()
        self.do_work(record)
        self.pass_review(record)
        self.assertEqual(dispatch.land(record["id"])["outcome"], "landed")

    def test_the_branch_is_deleted_after_landing(self):
        record = self.second_worker()
        self.do_work(record)
        self.pass_review(record)
        branch = record["branch"]
        dispatch.land(record["id"])
        done = subprocess.run(["git", "-C", str(self.repo), "branch", "--list", branch],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.stdout.strip(), "", "a spent branch is deleted without asking")

    def test_landing_without_a_review_pass_is_refused(self):
        record = self.second_worker()
        self.do_work(record)
        with self.assertRaises(dispatch.NotReadyToLand):
            dispatch.land(record["id"])
        self.assertTrue(Path(record["workdir"]).exists(), "a refusal must change nothing")

    def test_a_failed_review_does_not_count_as_a_pass(self):
        record = self.second_worker()
        self.do_work(record)
        store.record_review(record["id"], 1, "default", "fail", findings=2)
        with self.assertRaises(dispatch.NotReadyToLand):
            dispatch.land(record["id"])

    def test_uncommitted_work_blocks_landing(self):
        record = self.second_worker()
        self.do_work(record)
        self.pass_review(record)
        (Path(record["workdir"]) / "half.txt").write_text("unfinished\n")
        with self.assertRaises(dispatch.NotReadyToLand):
            dispatch.land(record["id"])

    def test_a_failing_gate_blocks_landing(self):
        record = self.second_worker()
        self.do_work(record)
        self.pass_review(record)
        with self.assertRaises(dispatch.NotReadyToLand):
            dispatch.land(record["id"], gate="exit 3")
        self.assertTrue(Path(record["workdir"]).exists())

    def test_a_passing_gate_allows_landing(self):
        record = self.second_worker()
        self.do_work(record)
        self.pass_review(record)
        dispatch.land(record["id"], gate="true")
        self.assertTrue((self.repo / "feature.txt").is_file())

    def test_a_dirty_main_checkout_blocks_landing(self):
        record = self.second_worker()
        self.do_work(record)
        self.pass_review(record)
        (self.repo / "operator-wip.txt").write_text("mine\n")
        with self.assertRaises(dispatch.NotReadyToLand):
            dispatch.land(record["id"])
        self.assertTrue((self.repo / "operator-wip.txt").is_file(),
                        "the operator's own work must be untouched")

    def test_a_conflict_is_aborted_and_leaves_nothing_behind(self):
        record = self.second_worker()
        self.do_work(record, "a.txt", "worker version\n")
        self.pass_review(record)
        (self.repo / "a.txt").write_text("operator version\n")
        run("git", "add", "-A", cwd=self.repo)
        run("git", "commit", "-qm", "operator edit", cwd=self.repo)

        with self.assertRaises(dispatch.NotReadyToLand):
            dispatch.land(record["id"])
        done = subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain"],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.stdout.strip(), "",
                         "a failed merge must be aborted, not left half-applied")
        self.assertEqual((self.repo / "a.txt").read_text(), "operator version\n")
        self.assertTrue(Path(record["workdir"]).exists(), "the worker's slot survives a refusal")

    def test_landing_twice_is_refused(self):
        record = self.second_worker()
        self.do_work(record)
        self.pass_review(record)
        dispatch.land(record["id"])
        with self.assertRaises(dispatch.NotReadyToLand):
            dispatch.land(record["id"])

    def test_a_worker_with_no_checkout_lands_without_merging(self):
        record = dispatch.open_dispatch("no repo", project="api")
        self.pass_review(record)
        self.assertEqual(dispatch.land(record["id"])["outcome"], "landed")

    def test_skip_review_is_available_for_a_human_who_has_looked(self):
        record = self.second_worker()
        self.do_work(record)
        dispatch.land(record["id"], skip_review=True)
        self.assertTrue((self.repo / "feature.txt").is_file())

    def test_a_landed_slot_can_be_reused(self):
        record = self.second_worker()
        self.do_work(record)
        self.pass_review(record)
        dispatch.land(record["id"])
        again = dispatch.open_dispatch("next task", project="api", repo=str(self.repo))
        self.assertTrue(again["lease_id"])


if __name__ == "__main__":
    unittest.main()
