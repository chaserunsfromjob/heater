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

import jsonstore

# The real gate: how much room must be left on the volume the checkouts live on
# before another one is created. A checkout is a second copy of the project's
# working files plus whatever its build leaves behind, and the fleet halts if the
# disk fills, so the floor is several checkouts' worth rather than one.
MIN_FREE_BYTES = 5 * 1024 ** 3

# A backstop, not the working limit: nothing normal comes near it. It catches a
# loop opening checkouts faster than the disk check can notice, where each one is
# small enough that the room left never falls below the floor.
MAX_SLOTS = 100

GIB = 1024 ** 3

# A lease older than this whose worktree still exists is assumed abandoned.
# Reclaiming is refused while the branch holds unpushed commits, so the cost of
# guessing wrong is a slot held slightly too long, never lost work.
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


def free_bytes(path: Path | None = None) -> int:
    """Room left on the volume the checkouts live on.

    Walks up to the nearest directory that exists: the worktree root is created
    on demand, and a missing directory is not a reason to answer "no room".
    """
    probe = Path(path or worktree_root())
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        return shutil.disk_usage(probe).free
    except OSError:
        # Unmeasurable is not the same as full. Refusing here would jam the pool
        # over a failed stat call; the backstop count still holds.
        return MIN_FREE_BYTES


def record_refusal(project: str, reason: str, *, free: int, held: int) -> dict[str, Any]:
    """Write down a lease that was refused for lack of room.

    Without this, "is the floor too high" is a feeling. With it, it is a query.
    """
    record = {
        "id": jsonstore.new_id(), "created": jsonstore.now(),
        "project": project, "reason": reason, "free_bytes": free,
        "floor_bytes": MIN_FREE_BYTES, "held": held, "max_slots": MAX_SLOTS,
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

    named = project or repo.name
    room, held = free_bytes(), len(active(project))
    if room < MIN_FREE_BYTES or held >= MAX_SLOTS:
        reclaim(project)
        room, held = free_bytes(), len(active(project))
    if room < MIN_FREE_BYTES:
        record_refusal(named, "disk", free=room, held=held)
        raise NoSlotAvailable(
            f"{room / GIB:.1f} GiB free where the checkouts live, below the "
            f"{MIN_FREE_BYTES / GIB:.1f} GiB floor; wait for room or free some, "
            "rather than starting a checkout that could fill the disk")
    if held >= MAX_SLOTS:
        record_refusal(named, "runaway", free=room, held=held)
        raise NoSlotAvailable(
            f"{held} checkouts already open for {named}, at the runaway backstop "
            f"of {MAX_SLOTS}; something is opening them in a loop")

    # The commit this slot started from. Without it there is no way to tell a
    # fresh checkout from one carrying real work: both have commits in them.
    code, base_sha = git(repo, "rev-parse", base)
    branch_code, base_branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    record = {
        "id": jsonstore.new_id(), "created": jsonstore.now(),
        "project": project or repo.name, "repo": str(repo), "branch": branch,
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


def reclaim(project: str = "") -> list[dict[str, Any]]:
    """Take back slots nobody is using. Never takes one holding unpushed work."""
    taken = []
    for record in active(project):
        path = Path(record.get("path", ""))
        if not path.exists():
            taken.append(release(record["id"], "worktree gone", force=True))
            continue
        age = age_minutes(record)
        if age is not None and age > STALE_MINUTES and not work_at_risk(record):
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
    room = f"{free_bytes() / GIB:.1f} GiB free, floor {MIN_FREE_BYTES / GIB:.1f} GiB"
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
        taken = reclaim()
        print(f"reclaimed {len(taken)} slot(s)" if taken else "nothing to reclaim")
        for record in taken:
            print(f"  {record['id']}: {record['released_how']}")
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
