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
import worktrees  # noqa: E402


def run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True, timeout=60)


class WorktreeCase(unittest.TestCase):
    ENV = ("HEATER_LEASES_DIR", "HEATER_WORKTREE_ROOT", "HEATER_DISPATCHES_DIR")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.previous = {k: os.environ.get(k) for k in self.ENV}
        os.environ["HEATER_LEASES_DIR"] = str(self.root / "leases")
        os.environ["HEATER_WORKTREE_ROOT"] = str(self.root / "trees")
        os.environ["HEATER_DISPATCHES_DIR"] = str(self.root / "dispatches")

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


class TestDispatchLeasesAutomatically(WorktreeCase):
    """Nobody decides when a pool is needed. Dispatch works it out."""

    def test_the_first_worker_uses_the_project_checkout(self):
        record = dispatch.open_dispatch("fix auth", project="api", repo=str(self.repo))
        self.assertEqual(record["workdir"], str(self.repo))
        self.assertEqual(record["lease_id"], "")

    def test_the_second_worker_gets_its_own(self):
        dispatch.open_dispatch("fix auth", project="api", repo=str(self.repo))
        second = dispatch.open_dispatch("fix parser", project="api", repo=str(self.repo))
        self.assertNotEqual(second["workdir"], str(self.repo))
        self.assertTrue(second["lease_id"])
        self.assertTrue(Path(second["workdir"]).exists())

    def test_a_different_project_does_not_trigger_a_lease(self):
        dispatch.open_dispatch("fix auth", project="api", repo=str(self.repo))
        other = dispatch.open_dispatch("fix docs", project="web", repo=str(self.repo))
        self.assertEqual(other["lease_id"], "", "separate projects already have separate checkouts")

    def test_no_repo_means_no_lease(self):
        dispatch.open_dispatch("one", project="api")
        second = dispatch.open_dispatch("two", project="api")
        self.assertEqual(second["lease_id"], "")

    def test_the_brief_tells_the_worker_where_to_work(self):
        dispatch.open_dispatch("fix auth", project="api", repo=str(self.repo))
        second = dispatch.open_dispatch("fix parser", project="api", repo=str(self.repo))
        brief = dispatch.compose_brief(second)
        self.assertIn(second["workdir"], brief)
        self.assertIn(second["branch"], brief)

    def test_closing_gives_the_slot_back(self):
        dispatch.open_dispatch("fix auth", project="api", repo=str(self.repo))
        second = dispatch.open_dispatch("fix parser", project="api", repo=str(self.repo))
        dispatch.close_dispatch(second["id"], "pushed")
        self.assertEqual(worktrees.active("api"), [])

    def test_closing_holds_the_slot_when_work_is_unpushed(self):
        dispatch.open_dispatch("fix auth", project="api", repo=str(self.repo))
        second = dispatch.open_dispatch("fix parser", project="api", repo=str(self.repo))
        (Path(second["workdir"]) / "wip.txt").write_text("half finished\n")
        closed = dispatch.close_dispatch(second["id"], "pushed")
        self.assertEqual(len(worktrees.active("api")), 1)
        self.assertIn("slot held", closed["note"], "the reason must be recorded, not swallowed")

    def test_a_freed_slot_is_reused_by_the_next_worker(self):
        dispatch.open_dispatch("one", project="api", repo=str(self.repo))
        second = dispatch.open_dispatch("two", project="api", repo=str(self.repo))
        dispatch.close_dispatch(second["id"], "pushed")
        third = dispatch.open_dispatch("three", project="api", repo=str(self.repo))
        self.assertTrue(third["lease_id"])
        self.assertEqual(len(worktrees.active("api")), 1)


if __name__ == "__main__":
    unittest.main()
