#!/usr/bin/env python3
"""Push work that exists on one machine only, without anybody being asked.

Work that is committed but not pushed lives on exactly one disk. If that machine
is the operator's PC and the session that made the commits has ended, the only
thing standing between the work and losing it is the operator typing a git
command. That is work the system can do for itself, so it does.

Every session runs the bearings read first, which is why this hangs off it: the
one moment every session reliably passes through is the moment it takes its
bearings. Every checkout the fleet knows about is swept, not just the one the
session happens to be sitting in, because the machine that holds the stranded
branch is usually not the machine that notices.

What it will never do: force, delete, reset, or move a branch. The only command
it runs against a remote is `git push -u origin <branch>`, which git itself
refuses when it would discard anything. A push that would not fast-forward is
reported and left alone, never forced.

Set `HEATER_AUTOPUSH=0` to turn the sweep off, which the test suite does: a
suite that pushed the branches of whatever machine it ran on would be a side
effect nobody asked for.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jsonstore
import worktrees

# Reaching the remote is one round trip; the push itself can be a slow one over
# a domestic connection. Both are bounded, because a bearings read that hangs is
# a bearings read nobody runs.
PROBE_TIMEOUT = 20
PUSH_TIMEOUT = 180

OFF = {"0", "no", "off", "false"}

REMOTE = "origin"


def enabled() -> bool:
    return (os.environ.get("HEATER_AUTOPUSH") or "").strip().lower() not in OFF


def git(path: Path, *args: str, timeout: int = 30) -> tuple[int, str]:
    try:
        done = subprocess.run(["git", "-C", str(path), *args],
                              capture_output=True, text=True, timeout=timeout)
    except (subprocess.SubprocessError, OSError) as error:
        return 1, str(error)
    return done.returncode, (done.stdout + done.stderr).strip()


def git_common_dir(path: Path) -> Path | None:
    """Where this checkout keeps its refs, or None if it is not a checkout.

    Worktrees share one set of refs with the checkout they were cut from, so two
    paths can hold the same branches. Sweeping by this instead of by path means
    a branch is considered once however many worktrees are open on it.
    """
    code, output = git(path, "rev-parse", "--git-common-dir", timeout=PROBE_TIMEOUT)
    if code != 0 or not output:
        return None
    common = Path(output)
    if not common.is_absolute():
        common = Path(path) / common
    try:
        return common.resolve()
    except OSError:
        return common


def recorded_paths() -> list[Path]:
    """Every checkout the stores name: project checkouts and leased worktrees.

    Paths are taken as recorded, which includes paths written on another machine
    with another operating system's spelling. One that does not exist here is
    simply not here, and is dropped by the existence check.
    """
    found: list[Path] = []
    for record in jsonstore.load(worktrees.leases_dir()):
        found += [record.get("repo", ""), record.get("path", "")]
    for record in jsonstore.load(jsonstore.resolve_dir("HEATER_DISPATCHES_DIR", "store/dispatches")):
        found += [record.get("repo", ""), record.get("workdir", "")]
    return [Path(p) for p in found if p]


def worktree_paths() -> list[Path]:
    """Checkouts under the worktree root, whether or not a lease still names them.

    A lease released after a crash, or one written by a machine whose store has
    not been pulled here yet, leaves a directory with commits in it and nothing
    pointing at it. The directory is the evidence, so the directory is swept.
    """
    root = worktrees.worktree_root()
    if not root.is_dir():
        return []
    found = []
    for project in sorted(root.iterdir()):
        if not project.is_dir():
            continue
        found.append(project)
        found += [tree for tree in sorted(project.iterdir()) if tree.is_dir()]
    return found


def checkouts() -> list[Path]:
    """Every distinct repository to sweep, the fleet repository first."""
    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in [jsonstore.REPO, *recorded_paths(), *worktree_paths()]:
        try:
            if not path.is_dir():
                continue
        except OSError:
            continue
        common = git_common_dir(path)
        if common is None or common in seen:
            continue
        seen.add(common)
        ordered.append(path)
    return ordered


def off_origin(path: Path, branch: str) -> bool:
    """True when this branch holds commits no origin ref can reach."""
    code, output = git(path, "rev-list", "--count", f"refs/heads/{branch}",
                       "--not", f"--remotes={REMOTE}")
    return code == 0 and output.strip() not in ("", "0")


def unpushed_branches(path: Path) -> list[str]:
    """Local branches carrying commits origin does not have.

    A branch tracking origin answers this from its own tracking count, which
    costs nothing. A branch with no upstream at all, or one whose upstream has
    been deleted on the remote, is asked the expensive question instead: it is
    exactly the branch a finished session forgot about.
    """
    code, output = git(path, "for-each-ref",
                       "--format=%(refname:short)%09%(upstream)%09%(upstream:track)",
                       "refs/heads")
    if code != 0:
        return []

    branches = []
    for line in output.splitlines():
        # Padded, never length-checked: a branch with no upstream ends the line
        # in empty fields, and trailing whitespace does not survive the trip.
        branch, upstream, track = (line.split("\t") + ["", ""])[:3]
        if not branch:
            continue
        tracks_origin = upstream.startswith(f"refs/remotes/{REMOTE}/") and "gone" not in track
        if tracks_origin:
            if "ahead" in track:
                branches.append(branch)
            continue
        if off_origin(path, branch):
            branches.append(branch)
    return branches


def remote_reachable(path: Path) -> tuple[bool, str]:
    """Whether origin answers. A machine that is merely offline is not a failure."""
    code, output = git(path, "remote", timeout=PROBE_TIMEOUT)
    if code != 0 or REMOTE not in output.split():
        return False, f"no {REMOTE} remote"
    code, output = git(path, "ls-remote", "--heads", REMOTE, timeout=PROBE_TIMEOUT)
    if code != 0:
        return False, "remote unreachable"
    return True, ""


def push(path: Path, branch: str) -> tuple[bool, str]:
    """Plain push, upstream set. Never forced: git refuses what would discard work."""
    code, output = git(path, "push", "-u", REMOTE, branch, timeout=PUSH_TIMEOUT)
    return code == 0, output.strip().splitlines()[-1] if output.strip() else ""


def sweep(paths: list[Path] | None = None) -> list[dict[str, Any]]:
    """Push what is only here, and say what happened for each checkout.

    Records, not printed lines, so the caller decides how to say it and a test
    can read the outcome rather than parse prose.
    """
    results: list[dict[str, Any]] = []
    for path in (checkouts() if paths is None else [Path(p) for p in paths]):
        branches = unpushed_branches(path)
        if not branches:
            continue
        reachable, why = remote_reachable(path)
        if not reachable:
            results.append({"path": str(path), "branch": "", "status": "skipped",
                            "detail": f"{why}; {len(branches)} branch(es) still local"})
            continue
        for branch in branches:
            done, detail = push(path, branch)
            results.append({"path": str(path), "branch": branch,
                            "status": "pushed" if done else "refused", "detail": detail})
    return results


def render(results: list[dict[str, Any]]) -> tuple[list[str], bool]:
    """One line per branch pushed, and whether anything still needs a person.

    A push that went through is news, not a problem, so it does not raise the
    flag. A branch still sitting on one disk does.
    """
    lines, attention = [], False
    for result in results:
        where = Path(result["path"]).name or result["path"]
        if result["status"] == "pushed":
            lines.append(f"  {result['branch']} pushed to {REMOTE} from {where}")
        elif result["status"] == "refused":
            attention = True
            lines.append(f"  {result['branch']} in {where} was refused by {REMOTE}: "
                         f"{result['detail'] or 'no reason given'}")
        else:
            attention = True
            lines.append(f"  {where} skipped: {result['detail']}")
    return lines, attention


def report() -> tuple[list[str], bool]:
    """The bearings section: sweep every known checkout, then say what happened."""
    if not enabled():
        return ["  off (HEATER_AUTOPUSH)"], False
    return render(sweep())
