#!/usr/bin/env python3
"""Leased git worktrees, created on demand.

A project normally has one checkout, and one worker in it is fine. The moment a
second worker is needed on the same project, that worker needs its own checkout
or the two trample each other.

Nobody decides when that moment arrives. Dispatch asks for a slot, and a slot is
created if one is needed and none is free. The operator is never asked to
provision a pool, because provisioning is a decision the system can make from
what it already knows.

What limits the pool is the machine, not a headcount picked in advance. Leasing
is refused when the volume the checkouts live on is close to full, because one
bad night starting thirty checkouts fills the disk, and a full disk halts the
whole fleet. Every refusal is written to `store/refusals/`, so "how often does
this actually bite" is a query rather than a guess.

    bin/worktrees.py list
    bin/worktrees.py reclaim
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import heartbeats
import jsonstore

# The only gate: how much room must be left on the volume the checkouts live on
# before another one is created. Not a multiple of a checkout's size — it is
# headroom for the volume as a whole, since a filling disk halts the fleet and
# everything else on the machine long before the checkouts are what is left.
MIN_FREE_BYTES = 5 * 1024 ** 3

GIB = 1024 ** 3

# A lease older than this whose worktree still exists is assumed abandoned.
# Reclaiming is refused while the branch holds unpushed commits, so the cost of
# guessing wrong is a slot held slightly too long, never lost work.
# How long the slot has been held, which is not `heartbeats.STALE_MINUTES`: that
# one is how long a checkout has been silent. Two quantities, one name.
STALE_MINUTES = 240

SAFE = re.compile(r"[^A-Za-z0-9_-]")


class NoSlotAvailable(RuntimeError):
    """The machine has no room for another checkout. Wait for room, or free some."""


def leases_dir() -> Path:
    return jsonstore.resolve_dir("HEATER_LEASES_DIR", "store/leases")


def refusals_dir() -> Path:
    return jsonstore.resolve_dir("HEATER_REFUSALS_DIR", "store/refusals")


def worktree_root() -> Path:
    return Path(os.environ.get("HEATER_WORKTREE_ROOT") or Path.home() / ".heater" / "worktrees")


def git(repo: Path, *args: str, timeout: int = 60) -> tuple[int, str]:
    try:
        done = subprocess.run(["git", "-C", str(repo), *args],
                              capture_output=True, text=True, timeout=timeout)
    except (subprocess.SubprocessError, OSError) as error:
        return 1, str(error)
    return done.returncode, (done.stdout + done.stderr).strip()


def active(project: str = "") -> list[dict[str, Any]]:
    live = [l for l in jsonstore.load(leases_dir()) if not l.get("released_at")]
    if project:
        live = [l for l in live if l.get("project") == project]
    return sorted(live, key=lambda l: l.get("created", ""))


def age_minutes(record: dict[str, Any]) -> float | None:
    try:
        return (datetime.now(timezone.utc)
                - datetime.fromisoformat(record["created"])).total_seconds() / 60
    except (KeyError, ValueError):
        return None


def slug(text: str) -> str:
    return SAFE.sub("-", text).strip("-")[:40] or "project"


def free_bytes(path: Path | None = None) -> int | None:
    """Room left on the volume the checkouts live on, or None if it cannot be read.

    Walks up to the nearest directory that exists: the worktree root is created
    on demand, and a missing directory is not a reason to answer "no room".
    """
    probe = Path(path or worktree_root())
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        return shutil.disk_usage(probe).free
    except OSError:
        # Unmeasurable is not the same as full, and it is not a number either:
        # answering with the floor would put a figure nobody measured into the
        # refusals store, where every number is supposed to be a real reading.
        return None


def short_of_room(free: int | None) -> bool:
    """True only when the disk was measured and came back under the floor.

    A failed stat call does not jam the pool: refusing over one would stop every
    dispatch on the machine for something that is not a shortage.
    """
    return free is not None and free < MIN_FREE_BYTES


def record_refusal(project: str, reason: str, *, free: int | None, held: int) -> dict[str, Any]:
    """Write down a lease that was refused for lack of room.

    Without this, "is the floor too high" is a feeling. With it, it is a query.
    `measured` says whether `free_bytes` is a reading or a blank.
    """
    record = {
        "id": jsonstore.new_id(), "created": jsonstore.now(),
        "project": project, "reason": reason, "free_bytes": free,
        "measured": free is not None,
        "floor_bytes": MIN_FREE_BYTES, "held": held,
    }
    jsonstore.write(refusals_dir(), record)
    return record


def refusals(days: int | None = None) -> list[dict[str, Any]]:
    """Refusals, newest last, optionally only recent ones."""
    records = jsonstore.load(refusals_dir())
    if days is None:
        return records
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    return [r for r in records if r.get("created", "") >= cutoff]


def lease(repo: Path, project: str, branch: str, *, dispatch_id: str = "",
          base: str = "HEAD") -> dict[str, Any]:
    """Create a checkout for one worker and record who holds it.

    Reclaims what it can before refusing, so a dead worker's slot does not
    block a live one.
    """
    repo = Path(repo).resolve()
    if not (repo / ".git").exists():
        raise ValueError(f"{repo} is not a git repository")

    # One name for the project throughout: an empty `project` counts and reclaims
    # across every project at once, while the refusal record says it is this one.
    named = project or repo.name
    room, held = free_bytes(), len(active(named))
    if short_of_room(room):
        reclaim(named)
        room, held = free_bytes(), len(active(named))
    if short_of_room(room):
        record_refusal(named, "disk", free=room, held=held)
        raise NoSlotAvailable(
            f"{room / GIB:.1f} GiB free where the checkouts live, below the "
            f"{MIN_FREE_BYTES / GIB:.1f} GiB floor; free some room, or escalate "
            "with `bin/queue.py add --kind escalation` if there is none to free")

    # The commit this slot started from. Without it there is no way to tell a
    # fresh checkout from one carrying real work: both have commits in them.
    code, base_sha = git(repo, "rev-parse", base)
    branch_code, base_branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    record = {
        "id": jsonstore.new_id(), "created": jsonstore.now(),
        "project": named, "repo": str(repo), "branch": branch,
        "dispatch_id": dispatch_id, "base_sha": base_sha if code == 0 else "",
        # The branch this slot was cut from, and the one its work lands back into.
        "base_branch": base_branch if branch_code == 0 else "",
        "path": "", "released_at": None, "released_how": "",
    }
    path = worktree_root() / slug(record["project"]) / record["id"]
    path.parent.mkdir(parents=True, exist_ok=True)

    code, output = git(repo, "worktree", "add", "-b", branch, str(path), base)
    if code != 0:
        raise RuntimeError(f"could not create a worktree: {output}")

    record["path"] = str(path)
    jsonstore.write(leases_dir(), record)
    return record


def contained_by(path: Path, ref: str) -> bool:
    """True when this checkout's commits are already reachable from `ref`."""
    code, _ = git(path, "merge-base", "--is-ancestor", "HEAD", ref)
    return code == 0


def work_at_risk(record: dict[str, Any]) -> bool:
    """True when this slot holds work that exists nowhere else.

    Three ways work is safe, and all three must be checked or the pool jams:
    merged into the branch it was cut from, pushed to a remote, or simply never
    started. Asking only "was it pushed" refuses to release a slot whose work
    has already landed, which is the normal end of a dispatch.

    Measured against the commit the slot started from, never against "has any
    commits at all". A fresh checkout inherits the whole history of its base, so
    counting commits marks every empty slot as holding work.
    """
    path = Path(record.get("path", ""))
    if not path.exists():
        return False

    code, output = git(path, "status", "--porcelain")
    if code == 0 and output.strip():
        return True

    # Landed: its commits are already in the branch it will merge back into.
    if (trunk := record.get("base_branch")) and contained_by(path, trunk):
        return False

    # Pushed: its commits are on the remote.
    if contained_by(path, f"origin/{record['branch']}"):
        return False

    base = record.get("base_sha")
    if not base:
        # An old lease with no recorded base: refuse to guess, and hold the slot.
        return True
    code, output = git(path, "log", "--oneline", f"{base}..HEAD")
    return code == 0 and bool(output.strip())


# Kept as the old name so nothing that imports it breaks silently.
unpushed = work_at_risk


def release(lease_id: str, how: str = "released", *, force: bool = False) -> dict[str, Any]:
    """Give a slot back. Refuses while the branch holds work nobody else has."""
    record = next((l for l in jsonstore.load(leases_dir()) if l["id"] == lease_id), None)
    if record is None:
        raise ValueError(f"no lease with id {lease_id!r}")
    if record.get("released_at"):
        return record
    if not force and work_at_risk(record):
        raise RuntimeError(
            f"{lease_id} still holds work on {record['branch']} that exists nowhere else; "
            "land it or push it before releasing the slot")

    path = Path(record.get("path", ""))
    if path.exists():
        code, _ = git(Path(record["repo"]), "worktree", "remove", "--force", str(path))
        if code != 0:
            shutil.rmtree(path, ignore_errors=True)
    git(Path(record["repo"]), "worktree", "prune")

    record.update(released_at=jsonstore.now(), released_how=how)
    jsonstore.write(leases_dir(), record)
    return record


def reclaim(project: str = "", *, held: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Take back slots nobody is using. Never takes one holding unpushed work.

    Age alone does not say a slot is abandoned. A four-hour dispatch is a long
    one, not a dead one, and a worker that has pushed everything and left
    nothing loose is indistinguishable by git from a slot nobody is in. The
    heartbeat is what separates them, so it is asked last, after the cheap
    answers, and before anything is removed.

    Pass `held` a list to be told which slots were kept and why; the slots
    actually taken are the return value either way.
    """
    taken = []
    for record in active(project):
        path = Path(record.get("path", ""))
        if not path.exists():
            taken.append(release(record["id"], "worktree gone", force=True))
            continue
        age = age_minutes(record)
        if age is None or age <= STALE_MINUTES:
            continue
        if work_at_risk(record):
            # Kept, and said out loud: this slot is out of the pool until
            # somebody pushes that branch, which is not "nothing to reclaim".
            if held is not None:
                held.append({"lease": record["id"], "project": record.get("project", ""),
                             "path": str(path),
                             "why": (f"held {age:.0f}m, but {record['branch']} holds "
                                     f"work that exists nowhere else")})
            continue
        if heartbeats.someone_working_in(path):
            if held is not None:
                held.append({"lease": record["id"], "project": record.get("project", ""),
                             "path": str(path),
                             "why": (f"held {age:.0f}m, but its checkout made a tool call "
                                     f"within {heartbeats.STALE_MINUTES}m")})
            continue
        taken.append(release(record["id"], f"abandoned after {age:.0f}m"))
    return taken


def landed(record: dict[str, Any], trunk: str = "") -> bool:
    """True when this slot's commits are already reachable from the trunk.

    Derived from git, never from a flag we wrote. A flag can be wrong after a
    crash halfway through consolidation; git cannot.
    """
    path = Path(record.get("path", ""))
    if not path.exists():
        return True
    return contained_by(path, trunk or record.get("base_branch") or "main")


def autosave(record: dict[str, Any]) -> bool:
    """Commit whatever the worker left loose, on its own branch.

    Uncommitted work is the easiest work to lose and the least valuable to
    protect by refusing. Committing it keeps it, keeps it isolated on a branch
    nobody else uses, and lets the sweep carry on without anybody being asked.
    """
    path = Path(record.get("path", ""))
    if not path.exists():
        return False
    code, dirty = git(path, "status", "--porcelain")
    if code != 0 or not dirty.strip():
        return False
    git(path, "add", "-A")
    code, _ = git(path, "commit", "-m",
                  f"Autosave uncommitted work on {record.get('branch', 'this branch')}")
    return code == 0


def render(records: list[dict[str, Any]]) -> str:
    free = free_bytes()
    reading = f"{free / GIB:.1f} GiB free" if free is not None else "free space unreadable"
    room = f"{reading}, floor {MIN_FREE_BYTES / GIB:.1f} GiB"
    if not records:
        return f"worktrees: no slots leased ({room})"
    lines = [f"{len(records)} slot(s) leased ({room}):"]
    for record in records:
        age = age_minutes(record)
        stamp = f"{age:.0f}m" if age is not None else "?"
        lines.append(f"  {record['id']}  {stamp:>6} ago  {record['project']}  "
                     f"{record['branch']}  {record['path']}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("list", help="slots currently leased")
    sub.add_parser("reclaim", help="take back slots nobody is using")
    done = sub.add_parser("release", help="give one slot back")
    done.add_argument("lease_id")
    done.add_argument("--force", action="store_true", help="release even with unpushed work")

    args = parser.parse_args(argv[1:])
    if args.action == "list":
        print(render(active()))
    elif args.action == "reclaim":
        kept: list[dict[str, Any]] = []
        taken = reclaim(held=kept)
        print(f"reclaimed {len(taken)} slot(s)" if taken else "nothing to reclaim")
        for record in taken:
            print(f"  {record['id']}: {record['released_how']}")
        for hold in kept:
            print(f"  kept {hold['lease']}: {hold['why']}")
    else:
        # Refusing to destroy unpushed work is an expected answer, not a crash.
        try:
            print(f"released {release(args.lease_id, force=args.force)['id']}")
        except (RuntimeError, ValueError) as error:
            print(f"worktrees: {error}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
