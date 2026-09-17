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
import time
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

    def env(self, key: str, value: str | None) -> None:
        """Set or clear an environment variable for one test, then put it back."""
        previous = os.environ.get(key)

        def restore() -> None:
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous

        self.addCleanup(restore)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    def clone(self) -> Path:
        """A second clone of the same origin, so origin can move underneath us."""
        other = self.root / "other"
        run("git", "clone", "-q", str(self.origin), str(other), cwd=self.root)
        run("git", "config", "user.email", "t@t", cwd=other)
        run("git", "config", "user.name", "t", cwd=other)
        return other


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
        other = self.clone()
        theirs = self.commit("theirs.txt", "someone else", repo=other)
        run("git", "push", "-q", "origin", "main", cwd=other)

        self.commit("mine.txt", "diverged")
        results = unpushed.sweep([self.repo])

        self.assertEqual(self.statuses(results), {("main", "refused")})
        self.assertEqual(self.on_origin("main"), theirs, "origin must not be overwritten")

    def test_a_branch_named_like_a_forced_refspec_moves_nothing_else(self):
        """`+main` is a legal branch name and, passed bare, a forced refspec.

        Reproduced by hand before this test was written: `git push -u origin +main`
        reports a forced update and overwrites origin/main with the local branch,
        destroying a commit another clone had already pushed. Naming the ref on
        both sides of a colon is what makes git read it as a branch and nothing
        else.
        """
        other = self.clone()
        theirs = self.commit("theirs.txt", "someone else", repo=other)
        run("git", "push", "-q", "origin", "main", cwd=other)

        run("git", "checkout", "-q", "-b", "+main", cwd=self.repo)
        head = self.commit("mine.txt", "carried on a hostile branch name")

        results = unpushed.sweep([self.repo])

        self.assertEqual(self.on_origin("main"), theirs, "origin/main must not move")
        self.assertEqual(self.statuses(results), {("+main", "pushed")})
        self.assertEqual(self.on_origin("+main"), head)

    def test_a_branch_a_tag_also_names_is_pushed_under_its_own_name(self):
        """A tag of the same name makes the branch's short name ambiguous.

        Reproduced by hand first: with `refs/tags/worker/amb` present, git
        renders `%(refname:short)` for `refs/heads/worker/amb` as
        `heads/worker/amb`, and a push of `refs/heads/heads/worker/amb` names a
        ref that does not exist. The branch is then either dropped from the
        sweep or reported refused for ever.
        """
        self.branch("worker/amb")
        head = self.commit("m.txt", "work under a name a tag also claims")
        run("git", "tag", "worker/amb", "main", cwd=self.repo)

        self.assertEqual(unpushed.unpushed_branches(self.repo), ["worker/amb"])

        results = unpushed.sweep([self.repo])

        self.assertEqual(self.statuses(results), {("worker/amb", "pushed")})
        self.assertEqual(self.on_origin("worker/amb"), head)

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

    def test_an_unreachable_remote_is_reported_without_raising_the_flag(self):
        """Offline is news. Attention is what bearings turns into exit 1, and a
        laptop on a train would otherwise hold that flag up for ever."""
        run("git", "remote", "set-url", "origin", str(self.root / "gone.git"), cwd=self.repo)
        self.branch("worker/stranded")
        self.commit("g.txt", "stuck here")

        results = unpushed.sweep([self.repo])
        lines, attention = unpushed.render(results)

        self.assertEqual(len(lines), 1)
        self.assertIn("skipped", lines[0])
        self.assertIn("offline", lines[0])
        self.assertFalse(attention, "a machine that is merely offline is not a failure")

    def test_a_checkout_with_no_origin_is_reported_without_raising_the_flag(self):
        """A checkout that was never given a remote has nowhere to push to. That
        is a fact about the checkout, not a job waiting for a person."""
        run("git", "remote", "remove", "origin", cwd=self.repo)
        self.branch("worker/never-shared")
        self.commit("g.txt", "no remote to send it to")

        lines, attention = unpushed.render(unpushed.sweep([self.repo]))

        self.assertEqual(len(lines), 1)
        self.assertIn("no origin remote", lines[0])
        self.assertFalse(attention)

    def test_a_refused_push_still_raises_the_flag(self):
        """The one case a person must settle: origin answered and said no."""
        other = self.clone()
        self.commit("theirs.txt", "someone else", repo=other)
        run("git", "push", "-q", "origin", "main", cwd=other)
        self.commit("mine.txt", "diverged")

        lines, attention = unpushed.render(unpushed.sweep([self.repo]))

        self.assertTrue(attention, "a divergence nobody has resolved is waiting")
        self.assertTrue(any("refused" in line for line in lines))
        said = "\n".join(lines)
        self.assertIn("origin already has commits this branch does not", said)
        self.assertIn("the two histories need combining", said)
        self.assertNotIn("hint:", said, "git's last line is a hint, not the reason")
        self.assertIn("[rejected]", said, "git's own words are kept, in brackets")

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

    def test_a_reviewer_session_pushes_nothing(self):
        """A reviewer judges and never writes, and a push is a write.

        The write ban is enforced by hooks/pre_tool_use.py on the tools the
        session calls. A sweep that ran inside the bearings read would push real
        branches through a Python subprocess no hook ever sees, so the sweep has
        to know the role itself.
        """
        self.env("HEATER_AUTOPUSH", None)
        self.env("HEATER_ROLE", "reviewer")
        self.branch("worker/unreviewed")
        self.commit("k.txt", "a reviewer must not send this anywhere")
        original = unpushed.checkouts
        unpushed.checkouts = lambda: [self.repo]
        self.addCleanup(setattr, unpushed, "checkouts", original)

        self.assertFalse(unpushed.enabled())
        lines, attention = unpushed.report()

        self.assertFalse(attention)
        self.assertEqual(lines, ["  off (reviewer sessions never write)"])
        with self.assertRaises(subprocess.CalledProcessError):
            self.on_origin("worker/unreviewed")

    def test_an_unmarked_session_still_sweeps(self):
        """Turning the sweep off for a reviewer must not turn it off for everyone."""
        self.env("HEATER_AUTOPUSH", None)
        self.env("HEATER_ROLE", "worker")

        self.assertTrue(unpushed.enabled())

    def test_bearings_carries_a_pushed_section(self):
        previous = os.environ.get("HEATER_AUTOPUSH")
        os.environ["HEATER_AUTOPUSH"] = "0"
        self.addCleanup(lambda: os.environ.pop("HEATER_AUTOPUSH", None)
                        if previous is None else os.environ.update(HEATER_AUTOPUSH=previous))

        self.assertIn("## Pushed", bearings.report()[0])


class TestDeadline(SweepCase):
    """One bound on the whole sweep, not one per checkout.

    Six recorded checkouts against a network that swallows packets is six probe
    timeouts in a row, and the sweep hangs off the one command every session is
    required to run first.
    """

    def crawl(self, seconds: float) -> None:
        """Make each checkout take longer than the deadline allows."""
        original = unpushed.unpushed_branches

        def slow(path):
            time.sleep(seconds)
            return original(path)

        unpushed.unpushed_branches = slow
        self.addCleanup(setattr, unpushed, "unpushed_branches", original)

    def test_checkouts_past_the_deadline_are_skipped_with_the_reason(self):
        # The slow step is the push, so the deadline falls between the first
        # checkout's only branch and the second checkout: the branch reached in
        # time goes, and the checkout after it is reported, not attempted.
        second = self.root / "second"
        second.mkdir()
        self.env("HEATER_AUTOPUSH_DEADLINE", "0.3")
        self.branch("worker/first")
        self.commit("l.txt", "reached in time")
        self.crawl_push(0.5)

        results = unpushed.sweep([self.repo, second])

        skipped = [r for r in results if r["status"] == "skipped"]
        self.assertEqual([r["path"] for r in skipped], [str(second)])
        self.assertIn("deadline", skipped[0]["detail"])
        self.assertEqual(self.statuses([r for r in results if r["status"] == "pushed"]),
                         {("worker/first", "pushed")})

    def test_one_slow_checkout_does_not_multiply_by_the_rest(self):
        self.env("HEATER_AUTOPUSH_DEADLINE", "0.2")
        self.crawl(0.3)

        started = time.monotonic()
        unpushed.sweep([self.repo, self.repo, self.repo, self.repo, self.repo])
        spent = time.monotonic() - started

        self.assertLess(spent, 1.5, "one slow checkout must not multiply by the rest")

    def crawl_push(self, seconds: float) -> None:
        """Make each push take longer than the deadline allows."""
        original = unpushed.push

        def slow(path, branch, timeout=None):
            time.sleep(seconds)
            return original(path, branch)

        unpushed.push = slow
        self.addCleanup(setattr, unpushed, "push", original)

    def test_branches_past_the_deadline_inside_one_checkout_are_skipped(self):
        """The bound is on the sweep, so it has to hold inside a checkout too.

        Four stalled pushes in one checkout cost four full push timeouts when
        the deadline was only consulted between checkouts, which is the first
        command every session runs sitting there for minutes.
        """
        for name in ("one", "two", "three", "four"):
            run("git", "checkout", "-q", "main", cwd=self.repo)
            self.branch(f"worker/{name}")
            self.commit(f"{name}.txt", name)
        self.env("HEATER_AUTOPUSH_DEADLINE", "0.5")
        self.crawl_push(0.5)

        started = time.monotonic()
        results = unpushed.sweep([self.repo])
        spent = time.monotonic() - started

        self.assertLess(spent, 2.0, "the deadline bounds the branches within a checkout")
        self.assertEqual(len(results), 4, "every branch is accounted for, reached or not")
        skipped = [r for r in results if r["status"] == "skipped"]
        self.assertTrue(skipped, "the branches not reached must be reported, not dropped")
        self.assertTrue(all("deadline" in r["detail"] for r in skipped))
        self.assertTrue(all(r["branch"] for r in skipped), "a skipped branch is named")

    def test_a_nonsense_deadline_falls_back_to_the_default(self):
        """`nan` compares false against everything, so it is no bound at all."""
        for value in ("nan", "inf", "-inf", "banana"):
            with self.subTest(value=value):
                self.env(unpushed.DEADLINE_ENV, value)
                self.assertEqual(unpushed.deadline_seconds(),
                                 float(unpushed.SWEEP_DEADLINE))

    def test_a_deadline_skip_is_news_not_a_failure(self):
        second = self.root / "second"
        second.mkdir()
        self.env("HEATER_AUTOPUSH_DEADLINE", "0.2")
        self.crawl(0.4)

        lines, attention = unpushed.render(unpushed.sweep([self.repo, second]))

        self.assertTrue(any("deadline" in line for line in lines))
        self.assertFalse(attention, "a slow network is not a person's job")


class TestTheSuiteNeverPushes(unittest.TestCase):
    def test_importing_the_test_package_turns_the_sweep_off(self):
        """Every test file, including ones written later that never think about it."""
        done = subprocess.run(
            [sys.executable, "-c", "import os, tests; print(os.environ.get('HEATER_AUTOPUSH'))"],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
            env={**os.environ, "HEATER_AUTOPUSH": "1"})

        self.assertEqual(done.stdout.strip(), "0", done.stderr)


class TestTheDocsSayItPushes(unittest.TestCase):
    """The sweep runs on every machine, by default, including on `main`. A
    behaviour nobody documented is one the operator meets by surprise."""

    def test_the_skill_table_carries_the_pushed_section(self):
        text = (ROOT / "skills" / "bearings" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("| Pushed |", text)
        self.assertIn("HEATER_AUTOPUSH", text)

    def test_the_readme_names_the_switch(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("HEATER_AUTOPUSH", text)

    def test_the_module_names_the_command_it_runs(self):
        self.assertIn("refs/heads/", unpushed.__doc__)


if __name__ == "__main__":
    unittest.main()
