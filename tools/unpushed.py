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
it runs against a remote is
`git push -u origin refs/heads/<branch>:refs/heads/<branch>`, spelled out on both
sides because a branch may legally be called `+main` and a bare `+main` is how a
forced refspec is written: git would read it as an order to overwrite `main`.
Named in full it is a branch and nothing else, and a push that would not
fast-forward is reported and left alone, never forced.

Set `HEATER_AUTOPUSH=0` to turn the sweep off, which the test suite does: a
suite that pushed the branches of whatever machine it ran on would be a side
effect nobody asked for. A reviewer session turns it off for itself, because a
reviewer never writes. `HEATER_AUTOPUSH_DEADLINE` bounds how long the whole
sweep may take; whatever it has not reached by then, checkout or branch, is
reported as skipped rather than tried.
"""

from __future__ import annotations

import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Hooks last, so a module here always wins the name. The sweep needs the hooks'
# own answer to "what is this session", not a second copy of it: two answers
# would drift, and the drift would surface as a reviewer pushing branches.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import heater_hook
import jsonstore
import worktrees

# Reaching the remote is one round trip; the push itself can be a slow one over
# a domestic connection. Both are bounded, because a bearings read that hangs is
# a bearings read nobody runs.
PROBE_TIMEOUT = 20
PUSH_TIMEOUT = 180

# Per-checkout timeouts still let six recorded checkouts on a network that
# swallows packets cost six probes end to end, and this hangs off the one
# command every session is required to run first. So the sweep as a whole gets
# one bound as well. Zero, or any negative number, means no bound at all; text
# that is not a number, and a number with no finite value, falls back to this.
SWEEP_DEADLINE = 60
DEADLINE_ENV = "HEATER_AUTOPUSH_DEADLINE"

OFF = {"0", "no", "off", "false"}

# A reviewer judges and never writes. That ban is enforced on the tools the
# session calls, which cannot see a push made inside a Python subprocess, so the
# sweep has to refuse for itself.
READ_ONLY_ROLES = {"reviewer"}

REMOTE = "origin"

# What `git` reports when the timeout killed the command instead of git
# answering. git's own exit codes run 0-255 and a command killed by a signal
# shows as a small negative number, so nothing real can land on this value. It
# has to be told apart from a plain failure: a command cut short was never
# answered, and reporting no answer as a no puts a decision in front of a person
# that nobody has actually been asked to take.
TIMED_OUT = 1000


def why_off() -> str:
    """Empty when the sweep should run, otherwise what stopped it.

    A reason rather than a bare no, because the bearings line says it out loud:
    a sweep that quietly does nothing reads exactly like a sweep that found
    nothing to do.
    """
    if (os.environ.get("HEATER_AUTOPUSH") or "").strip().lower() in OFF:
        return "HEATER_AUTOPUSH"
    role = heater_hook.role()
    if role in READ_ONLY_ROLES:
        return f"{role} sessions never write"
    return ""


def enabled() -> bool:
    return not why_off()


def deadline_seconds() -> float:
    """How long the whole sweep may take. Unset or unreadable means the default.

    `nan` is rejected along with unreadable text, because every comparison
    against it is false: a deadline that is never past is no deadline at all,
    which is the one thing this value exists to prevent. `inf` says the same
    thing in plainer words and goes the same way.
    """
    raw = (os.environ.get(DEADLINE_ENV) or "").strip()
    try:
        value = float(raw)
    except ValueError:
        return float(SWEEP_DEADLINE)
    return value if math.isfinite(value) else float(SWEEP_DEADLINE)


def git(path: Path, *args: str, timeout: float = 30) -> tuple[int, str]:
    """Run one git command here, and report how it went.

    A command the timeout killed comes back as `TIMED_OUT` and never as a plain
    failure, because the two mean opposite things and only one of them is a
    person's job. Python's own account of the killing is dropped rather than
    passed on: it is the command line and a fraction of a second, printed as
    code, and it ends up read by somebody who has never seen git.
    """
    try:
        done = subprocess.run(["git", "-C", str(path), *args],
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return TIMED_OUT, f"no answer within {timeout:g}s"
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
    # The full refname, lstripped of `refs/heads/`, never `%(refname:short)`:
    # git shortens a branch to `heads/<name>` when a tag of the same name makes
    # the short form ambiguous, and `refs/heads/heads/<name>` names nothing.
    code, output = git(path, "for-each-ref",
                       "--format=%(refname:lstrip=2)%09%(upstream)%09%(upstream:track)",
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


def remote_reachable(path: Path, timeout: float = PROBE_TIMEOUT) -> tuple[bool, str]:
    """Whether origin answers. A machine that is merely offline is not a failure.

    The timeout is passed in rather than fixed, so what is left of the sweep
    deadline can cut a probe short instead of the probe outliving the deadline.
    """
    cut_short = f"checking {REMOTE} did not finish in time"
    code, output = git(path, "remote", timeout=timeout)
    if code == TIMED_OUT:
        return False, cut_short
    if code != 0 or REMOTE not in output.split():
        return False, f"no {REMOTE} remote"
    code, output = git(path, "ls-remote", "--heads", REMOTE, timeout=timeout)
    if code == TIMED_OUT:
        return False, cut_short
    if code != 0:
        return False, "offline"
    return True, ""


DIVERGED = ("origin already has commits this branch does not; "
            "the two histories need combining")

# git's own names for the same situation: the remote ref is not an ancestor of
# what is being pushed, so accepting it would drop commits.
DIVERGENCE_WORDS = ("non-fast-forward", "fetch first", "stale info")


def refusal_detail(output: str) -> str:
    """The one line of a refused push worth showing, said in plain words.

    git ends a rejected push with a hint line pointing at `git push --help`,
    and the last line is the line that gets read. It tells an operator with no
    git background nothing at all, so the line that actually carries the
    refusal is picked out instead and prefixed with what it means. git's own
    text is kept in brackets after it, because that is what a search, or a
    person who does know git, will want.
    """
    lines = [line.strip() for line in output.strip().splitlines() if line.strip()]
    if not lines:
        return ""
    salient = next((line for line in lines
                    if ("[rejected]" in line and line.startswith("!"))
                    or line.startswith("error:")), lines[-1])
    # git pads its columns; a run of spaces inside one sentence reads as a gap.
    salient = " ".join(salient.split())
    if any(word in salient for word in DIVERGENCE_WORDS):
        return f"{DIVERGED} ({salient})"
    return salient


def push(path: Path, branch: str, timeout: float = PUSH_TIMEOUT) -> tuple[str, str]:
    """Plain push, upstream set, the ref named in full on both sides.

    `git push origin <branch>` takes a refspec, not a name, so a branch legally
    called `+main` asks for a forced overwrite of `main` on the remote. Spelling
    both ends as `refs/heads/...` leaves no leading `+` to be read that way, and
    a push that would discard work is then refused by git as it should be.

    Answers with one of `pushed`, `refused` or `timeout`, and why. `timeout` is
    kept apart from `refused` because a push cut short before the remote could
    answer has decided nothing: the branch is still here and the next sweep will
    try it again, while a refusal is two histories waiting for a person.
    """
    refspec = f"refs/heads/{branch}:refs/heads/{branch}"
    code, output = git(path, "push", "-u", REMOTE, refspec, timeout=timeout)
    if code == TIMED_OUT:
        return "timeout", output
    if code != 0:
        return "refused", refusal_detail(output)
    return "pushed", output.strip().splitlines()[-1] if output.strip() else ""


def budget(expires: float | None, cap: float) -> float:
    """How long one git command may take: its own cap, or what is left of the sweep.

    Never less than a second, because a command given no time at all cannot
    even fail usefully; the sweep may therefore overrun its deadline by about
    one command, which is the price of ever finishing a command at all.
    """
    if expires is None:
        return cap
    return max(1.0, min(cap, expires - time.monotonic()))


def sweep(paths: list[Path] | None = None) -> list[dict[str, Any]]:
    """Push what is only here, and say what happened for each checkout.

    Records, not printed lines, so the caller decides how to say it and a test
    can read the outcome rather than parse prose.

    The deadline is consulted before every branch, not only before every
    checkout: one checkout holding four branches origin will not answer for
    costs four push timeouts otherwise, all of them inside the first command
    every session runs. What the deadline cuts short is reported as skipped,
    branch by branch, so no local work goes unmentioned.
    """
    results: list[dict[str, Any]] = []
    limit = deadline_seconds()
    # Started before the checkouts are even enumerated: finding them asks each
    # candidate directory a git question, and that stalls on the same network.
    expires = time.monotonic() + limit if limit > 0 else None
    missed_reason = (f"not reached inside the {limit:g}s sweep "
                     f"deadline ({DEADLINE_ENV})")
    # Which bound actually stopped the push: the sweep's, or the one on a single
    # push. A push is handed the smaller of the two, so the sweep's deadline is
    # what cut it short only when what was left of the sweep was the smaller
    # number, whatever the deadline was set to. Naming the wrong one sends
    # whoever reads it to change a setting that was not in play.
    def cut_short_reason(allowed: float) -> str:
        bound = (f"the {limit:g}s sweep deadline ({DEADLINE_ENV})"
                 if allowed < PUSH_TIMEOUT else f"{PUSH_TIMEOUT:g}s")
        return (f"the push did not finish inside {bound}; it will be tried "
                "again on the next bearings read")

    def out_of_time() -> bool:
        return expires is not None and time.monotonic() >= expires

    targets = checkouts() if paths is None else [Path(p) for p in paths]
    for index, path in enumerate(targets):
        if out_of_time():
            results += [{"path": str(missed), "branch": "", "status": "skipped",
                         "detail": missed_reason}
                        for missed in targets[index:]]
            break
        branches = unpushed_branches(path)
        if not branches:
            continue
        reachable, why = remote_reachable(path, timeout=budget(expires, PROBE_TIMEOUT))
        if not reachable:
            results.append({"path": str(path), "branch": "", "status": "skipped",
                            "detail": f"{why}; {len(branches)} branch(es) still local"})
            continue
        for position, branch in enumerate(branches):
            if out_of_time():
                results += [{"path": str(path), "branch": missed, "status": "skipped",
                             "detail": missed_reason} for missed in branches[position:]]
                break
            allowed = budget(expires, PUSH_TIMEOUT)
            outcome, detail = push(path, branch, timeout=allowed)
            if outcome == "timeout":
                outcome, detail = "skipped", cut_short_reason(allowed)
            results.append({"path": str(path), "branch": branch,
                            "status": outcome, "detail": detail})
    return results


def render(results: list[dict[str, Any]]) -> tuple[list[str], bool]:
    """One line per branch pushed, and whether anything still needs a person.

    Only a refusal raises the flag, because only a refusal is a decision waiting
    to be taken: origin answered and said no, and somebody has to reconcile the
    two histories. A push that worked is news. So is a checkout with no remote,
    or one whose remote could not be reached, or one the sweep ran out of time
    to try: bearings turns this flag into exit 1, and a laptop on a train would
    otherwise hold that exit code up until somebody found a network.
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
        elif result["branch"]:
            lines.append(f"  {result['branch']} in {where} skipped: {result['detail']}")
        else:
            lines.append(f"  {where} skipped: {result['detail']}")
    return lines, attention


def report() -> tuple[list[str], bool]:
    """The bearings section: sweep every known checkout, then say what happened."""
    off = why_off()
    if off:
        return [f"  off ({off})"], False
    return render(sweep())
