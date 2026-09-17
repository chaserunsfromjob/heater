#!/usr/bin/env python3
"""Where a queue item or a store record lands when the code runs in a worktree.

Task d67cffad749a. Every store path was resolved from the file the code was
imported from, so a worker in a leased checkout of the fleet repository wrote
its findings into that checkout's own `queue/` and its records into its own
`store/`. The checkout is deleted when the slot goes back, so a finding filed
that way was gone before anyone read it, and a worker could never see the lease
it was itself holding.

Run against a real repository with a real secondary worktree, because what is
being asked here is what git says about the checkout the code runs from.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import fleetrepo  # noqa: E402


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   capture_output=True, text=True, timeout=60)


class WorktreeCase(unittest.TestCase):
    """A scratch fleet repository, and a second checkout of it beside it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.main = self.root / "fleet"
        self.main.mkdir()
        git("init", "-q", "-b", "main", cwd=self.main)
        git("config", "user.email", "t@t", cwd=self.main)
        git("config", "user.name", "t", cwd=self.main)
        for directory in ("tools", "bin"):
            shutil.copytree(ROOT / directory, self.main / directory,
                            ignore=shutil.ignore_patterns("__pycache__"))
        git("add", "-A", cwd=self.main)
        git("commit", "-qm", "the fleet repository", cwd=self.main)

        self.worker = self.root / "checkout"
        git("worktree", "add", "-q", "-b", "worker/x", str(self.worker), cwd=self.main)

    def tearDown(self):
        self.tmp.cleanup()

    def env(self, **extra: str) -> dict[str, str]:
        """The environment with every HEATER_ setting dropped, plus what is asked.

        Dropped rather than kept: the suite itself runs with the store pointed
        at a temporary directory, and inheriting that would answer the question
        before the code under test is reached.
        """
        clean = {k: v for k, v in os.environ.items() if not k.startswith("HEATER_")}
        clean.update(extra)
        return clean

    def queue_cli(self, checkout: Path, *args: str, **extra: str) -> str:
        done = subprocess.run([sys.executable, str(checkout / "bin" / "queue.py"), *args],
                              cwd=str(checkout), env=self.env(**extra),
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout

    def items_in(self, directory: Path) -> list[dict]:
        if not directory.is_dir():
            return []
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("*.json"))]


class TestAWorkerFilesIntoTheFleetQueue(WorktreeCase):
    """The finding has to survive the checkout it was filed from."""

    def test_an_item_filed_from_a_worktree_lands_in_the_main_checkout(self):
        self.queue_cli(self.worker, "add", "--kind", "finding",
                       "--summary", "the sweep prints a count nobody reads")

        filed = self.items_in(self.main / "queue")
        self.assertEqual([i["summary"] for i in filed],
                         ["the sweep prints a count nobody reads"],
                         "a finding filed from a leased checkout has to reach the fleet queue")
        self.assertEqual(self.items_in(self.worker / "queue"), [],
                         "nothing may be written into a checkout that is about to be deleted")

    def test_a_worktree_reads_what_the_main_checkout_holds(self):
        self.queue_cli(self.main, "add", "--kind", "escalation",
                       "--summary", "which trunk does the api project use")

        printed = self.queue_cli(self.worker, "list", "--all")

        self.assertIn("which trunk does the api project use", printed,
                      "a worker reading the queue has to see the fleet's queue")

    def test_a_worktree_reads_the_store_the_stoker_writes(self):
        """`jsonstore.load` is the read every store query goes through."""
        dispatches = self.main / "store" / "dispatches"
        dispatches.mkdir(parents=True)
        (dispatches / "20260101T000000.000000+0000-abcdef123456.json").write_text(
            json.dumps({"id": "abcdef123456", "created": "2026-01-01T00:00:00.000000+00:00"}) + "\n",
            encoding="utf-8")

        read = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, 'tools'); import jsonstore;"
             "where = jsonstore.resolve_dir('HEATER_DISPATCHES_DIR', 'store/dispatches');"
             "print([d['id'] for d in jsonstore.load(where)])"],
            cwd=str(self.worker), env=self.env(), capture_output=True, text=True, timeout=60)

        self.assertEqual(read.returncode, 0, read.stdout + read.stderr)
        self.assertIn("abcdef123456", read.stdout,
                      "a worker asking the store has to be shown the fleet's store")

    def test_the_directory_override_still_wins(self):
        elsewhere = self.root / "elsewhere"

        self.queue_cli(self.worker, "add", "--kind", "finding",
                       "--summary", "filed into a directory named by hand",
                       HEATER_QUEUE_DIR=str(elsewhere))

        self.assertEqual([i["summary"] for i in self.items_in(elsewhere)],
                         ["filed into a directory named by hand"])
        self.assertEqual(self.items_in(self.main / "queue"), [],
                         "the explicit override has to win over the resolved repository")

    def test_the_repository_override_wins_from_the_main_checkout(self):
        other = self.root / "other-fleet"

        self.queue_cli(self.main, "add", "--kind", "finding",
                       "--summary", "filed into another fleet repository",
                       HEATER_REPO=str(other))

        self.assertEqual([i["summary"] for i in self.items_in(other / "queue")],
                         ["filed into another fleet repository"])

    def test_the_main_checkout_is_its_own_fleet_repository(self):
        self.queue_cli(self.main, "add", "--kind", "finding",
                       "--summary", "filed from the main checkout")

        self.assertEqual([i["summary"] for i in self.items_in(self.main / "queue")],
                         ["filed from the main checkout"])


class TestResolvingTheFleetRepository(WorktreeCase):
    """The lookup itself, asked of each kind of directory it can be given."""

    def test_a_secondary_worktree_resolves_to_the_main_one(self):
        self.assertEqual(fleetrepo.canonical(self.worker), self.main)

    def test_a_main_checkout_resolves_to_itself(self):
        self.assertEqual(fleetrepo.canonical(self.main), self.main)

    def test_a_directory_that_is_no_repository_resolves_to_itself(self):
        loose = self.root / "loose"
        loose.mkdir()
        self.assertEqual(fleetrepo.canonical(loose), loose)

    def test_the_environment_override_wins_over_git(self):
        other = self.root / "named-by-hand"
        previous = os.environ.get("HEATER_REPO")
        os.environ["HEATER_REPO"] = str(other)
        try:
            self.assertEqual(fleetrepo.repo(), other)
        finally:
            if previous is None:
                os.environ.pop("HEATER_REPO", None)
            else:
                os.environ["HEATER_REPO"] = previous


if __name__ == "__main__":
    unittest.main()
