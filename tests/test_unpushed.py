#!/usr/bin/env python3
"""Tests for the sweep that pushes work living on one disk only.

Run against real git repositories with a real bare origin, because what is being
protected is git's behaviour and not Python's: a branch that never reached the
remote must go, a branch already there must be left alone, and nothing may ever
be forced, however convenient that would be.
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
sys.path.insert(0, str(ROOT / "hooks"))

import bearings  # noqa: E402
import unpushed  # noqa: E402


def run(*args: str, cwd: Path) -> str:
    done = subprocess.run(args, cwd=cwd, check=True, capture_output=True,
                          text=True, timeout=60)
    return done.stdout.strip()


class SweepCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

        self.origin = self.root / "origin.git"
        run("git", "init", "-q", "--bare", "-b", "main", str(self.origin), cwd=self.root)

        self.repo = self.root / "work"
        self.repo.mkdir()
        run("git", "init", "-q", "-b", "main", cwd=self.repo)
        run("git", "config", "user.email", "t@t", cwd=self.repo)
        run("git", "config", "user.name", "t", cwd=self.repo)
        run("git", "remote", "add", "origin", str(self.origin), cwd=self.repo)
        self.commit("a.txt", "hello")
        run("git", "push", "-q", "-u", "origin", "main", cwd=self.repo)

    def commit(self, name: str, text: str, *, repo: Path | None = None) -> str:
        where = repo or self.repo
        (where / name).write_text(text + "\n", encoding="utf-8")
        run("git", "add", "-A", cwd=where)
        run("git", "commit", "-qm", f"add {name}", cwd=where)
        return run("git", "rev-parse", "HEAD", cwd=where)

    def branch(self, name: str) -> None:
        run("git", "checkout", "-q", "-b", name, cwd=self.repo)

    def on_origin(self, branch: str) -> str:
        out = run("git", "rev-parse", f"refs/heads/{branch}", cwd=self.origin)
        return out

    def statuses(self, results: list[dict]) -> set[tuple[str, str]]:
        return {(r["branch"], r["status"]) for r in results}


class TestSweep(SweepCase):
    def test_a_branch_that_never_reached_origin_is_pushed(self):
        """The trigger case: a worker's branch left behind on one machine."""
        self.branch("worker/7eead182560d")
        head = self.commit("b.txt", "work nobody else has")

        results = unpushed.sweep([self.repo])

        self.assertEqual(self.statuses(results), {("worker/7eead182560d", "pushed")})
        self.assertEqual(self.on_origin("worker/7eead182560d"), head)

    def test_a_branch_already_on_origin_is_left_alone(self):
        self.branch("done")
        self.commit("c.txt", "already shared")
        run("git", "push", "-q", "-u", "origin", "done", cwd=self.repo)
        before = self.on_origin("done")

        results = unpushed.sweep([self.repo])

        self.assertEqual(results, [], "nothing was unpushed, so nothing should be touched")
        self.assertEqual(self.on_origin("done"), before)

    def test_new_commits_on_a_tracked_branch_are_pushed(self):
        self.branch("feature")
        self.commit("d.txt", "first")
        run("git", "push", "-q", "-u", "origin", "feature", cwd=self.repo)
        head = self.commit("e.txt", "second, never pushed")

        unpushed.sweep([self.repo])

        self.assertEqual(self.on_origin("feature"), head)

    def test_an_untracked_branch_identical_to_origin_is_left_alone(self):
        """No upstream is not the same as unpushed; origin already has these commits."""
        run("git", "branch", "copy", "main", cwd=self.repo)

        self.assertEqual(unpushed.unpushed_branches(self.repo), [])

    def test_main_is_pushed_but_never_forced(self):
        """Origin moved on. A plain push is refused, and nothing is overwritten."""
        other = self.root / "other"
        run("git", "clone", "-q", str(self.origin), str(other), cwd=self.root)
        run("git", "config", "user.email", "t@t", cwd=other)
        run("git", "config", "user.name", "t", cwd=other)
        theirs = self.commit("theirs.txt", "someone else", repo=other)
        run("git", "push", "-q", "origin", "main", cwd=other)

        self.commit("mine.txt", "diverged")
        results = unpushed.sweep([self.repo])

        self.assertEqual(self.statuses(results), {("main", "refused")})
        self.assertEqual(self.on_origin("main"), theirs, "origin must not be overwritten")

    def test_a_leased_worktree_counts_as_the_repository_it_was_cut_from(self):
        """Worktrees share refs, so sweeping both would ask the same question twice."""
        tree = self.root / "tree"
        run("git", "worktree", "add", "-q", "--detach", str(tree), "main", cwd=self.repo)

        self.assertEqual(unpushed.git_common_dir(tree), unpushed.git_common_dir(self.repo))

    def test_sweeping_twice_pushes_once(self):
        self.branch("worker/shared")
        head = self.commit("f.txt", "work in a leased checkout")

        first, second = unpushed.sweep([self.repo]), unpushed.sweep([self.repo])

        self.assertEqual(self.statuses(first), {("worker/shared", "pushed")})
        self.assertEqual(second, [], "a branch already sent must not be sent again")
        self.assertEqual(self.on_origin("worker/shared"), head)

    def test_an_unreachable_remote_is_skipped_with_a_reason(self):
        run("git", "remote", "set-url", "origin", str(self.root / "gone.git"), cwd=self.repo)
        self.branch("worker/stranded")
        self.commit("g.txt", "stuck here")

        lines, attention = unpushed.render(unpushed.sweep([self.repo]))

        self.assertEqual(len(lines), 1)
        self.assertIn("skipped", lines[0])
        self.assertTrue(attention, "work still on one disk is something waiting")

    def test_a_checkout_that_is_not_a_repository_is_ignored(self):
        plain = self.root / "plain"
        plain.mkdir()
        self.assertEqual(unpushed.sweep([plain]), [])


class TestReporting(SweepCase):
    def test_one_line_per_branch_pushed(self):
        self.branch("worker/one")
        self.commit("h.txt", "one")
        run("git", "checkout", "-q", "main", cwd=self.repo)
        self.branch("worker/two")
        self.commit("i.txt", "two")

        lines, attention = unpushed.render(unpushed.sweep([self.repo]))

        self.assertEqual(len(lines), 2)
        self.assertTrue(all("pushed to origin" in line for line in lines))
        self.assertFalse(attention, "a push that worked is news, not a problem")

    def test_the_switch_turns_the_sweep_off(self):
        previous = os.environ.get("HEATER_AUTOPUSH")
        os.environ["HEATER_AUTOPUSH"] = "0"
        self.addCleanup(lambda: os.environ.pop("HEATER_AUTOPUSH", None)
                        if previous is None else os.environ.update(HEATER_AUTOPUSH=previous))
        self.branch("worker/quiet")
        self.commit("j.txt", "not pushed by a test")

        self.assertFalse(unpushed.enabled())
        self.assertEqual(unpushed.report(), (["  off (HEATER_AUTOPUSH)"], False))

    def test_bearings_carries_a_pushed_section(self):
        previous = os.environ.get("HEATER_AUTOPUSH")
        os.environ["HEATER_AUTOPUSH"] = "0"
        self.addCleanup(lambda: os.environ.pop("HEATER_AUTOPUSH", None)
                        if previous is None else os.environ.update(HEATER_AUTOPUSH=previous))

        self.assertIn("## Pushed", bearings.report()[0])


if __name__ == "__main__":
    unittest.main()
