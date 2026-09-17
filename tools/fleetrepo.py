#!/usr/bin/env python3
"""Which checkout is the fleet repository: the one place that question is asked.

Every store the fleet keeps -- the queue, the task list, the dispatch, review,
suite and lease records -- lives in a directory inside the fleet repository, and
each one used to be resolved from the file that happened to import it. A worker
runs from a leased checkout, so that answered "this checkout": findings went
into a `queue/` nobody reads and were deleted with the checkout when the slot
went back, and a worker asking which lease it held was shown an empty store.

A leased checkout is a git worktree of the fleet repository, and git knows it:
a secondary worktree has its own git directory while sharing the common one, so
the two differ there and match in the main checkout. The main worktree is the
fleet repository. `HEATER_REPO` overrides the lot, for a machine that keeps the
repository somewhere this cannot work out.

The `HEATER_*_DIR` settings still win over this: they name a directory outright,
and this only decides which repository a relative default hangs off.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]

# Asked of git once per checkout: the answer cannot change while the process
# runs, and the store is read often enough that a subprocess per read shows.
_ANSWERED: dict[Path, Path] = {}


def ask_git(cwd: Path, *args: str) -> str:
    """What git says, or "" if it could not be asked or refused to answer."""
    try:
        done = subprocess.run(["git", "-C", str(cwd), *args],
                              capture_output=True, text=True, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def main_worktree(checkout: Path) -> Path | None:
    """The checkout this worktree hangs off, or None if this is not a worktree.

    None covers both "this is the main checkout" and "this is no repository at
    all", because the caller does the same thing with either: the directory it
    was given is the answer.
    """
    own = ask_git(checkout, "rev-parse", "--absolute-git-dir")
    shared = ask_git(checkout, "rev-parse", "--git-common-dir")
    if not own or not shared:
        return None
    common = Path(shared)
    if not common.is_absolute():
        common = checkout / common
    if Path(own).resolve() == common.resolve():
        # One git directory doing both jobs: this is the main checkout.
        return None
    listing = ask_git(checkout, "worktree", "list", "--porcelain")
    first = listing.splitlines()[0] if listing else ""
    if first.startswith("worktree "):
        # git lists the main worktree first, whichever one it is asked from.
        return Path(first[len("worktree "):]).resolve()
    # The common git directory is the main checkout's `.git`, so its parent is
    # the main checkout. Kept as the fallback for a git too old to list.
    return common.resolve().parent


def canonical(start: Path | None = None) -> Path:
    """The fleet repository, worked out from the checkout `start` sits in."""
    checkout = Path(start or HERE).resolve()
    if checkout not in _ANSWERED:
        _ANSWERED[checkout] = main_worktree(checkout) or checkout
    return _ANSWERED[checkout]


def repo() -> Path:
    """The fleet repository this process reads and writes, override included.

    Read from the environment on every call rather than at import: a test and a
    wake both point this somewhere else after the modules are already loaded.
    """
    named = os.environ.get("HEATER_REPO")
    return Path(named).expanduser() if named else canonical(HERE)
