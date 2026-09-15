#!/usr/bin/env python3
"""Where everything stands, in one read.

The first thing the stoker runs after a night away, and the thing to run before
deciding anything. Every number comes from a live query rather than from a file
somebody updated by hand.

Exit 0 when nothing needs attention, 1 when something does.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))

import deploy
import dispatch
import inbox
import jsonstore
import queue
import store
import usage
import worktrees
from heater_hook import heartbeat_dir

REPO = jsonstore.REPO

# A worker whose last tool call is older than this is quiet enough to look at.
STALE_MINUTES = 30
TOP_TASKS = 3


def git(*args: str) -> str:
    try:
        done = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def plan_usage() -> tuple[list[str], bool]:
    """How much of the plan is spent, and what that leaves room to start.

    First, because it bounds everything below it: there is no point ranking
    tasks before knowing how many may be started at all.
    """
    reading = usage.read()
    needs = (usage.band(reading) == usage.NOTHING_NEW
             or usage.missing(reading)
             or usage.stale(reading))
    return usage.lines(reading), needs


def fleet() -> tuple[list[str], bool]:
    undelivered, unjudged, tasks = queue.pending(), inbox.open_findings(), inbox.ranked()
    lines = [
        f"  {len(undelivered)} queue item(s) undelivered",
        f"  {len(unjudged)} finding(s) waiting to be judged",
        f"  {len(tasks)} task(s) on the list (cap {inbox.TASK_CAP})",
    ]
    lines += [f"    {n}. [{t['score']:>3}] {t['title']}" for n, t in enumerate(tasks[:TOP_TASKS], 1)]
    return lines, bool(undelivered or unjudged)


def out() -> tuple[list[str], bool]:
    lines = []
    for record in dispatch.live():
        age = dispatch.age_minutes(record)
        stamp = f"{age:.0f}m ago" if age is not None else "age unknown"
        quiet = "  <- quiet" if age is not None and age > STALE_MINUTES else ""
        lines.append(f"  {record['id']}  {stamp}  {record['task'][:60]}{quiet}")
    return lines, bool(lines)


def heartbeats() -> tuple[list[str], bool]:
    """A heartbeat says a worker's tool call returned. Silence says nothing, which
    is exactly why it is worth surfacing: quiet and dead look identical otherwise."""
    directory = heartbeat_dir()
    lines, attention = [], False
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        try:
            beat = json.loads(path.read_text(encoding="utf-8"))
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(beat["at"])).total_seconds() / 60
        except (json.JSONDecodeError, OSError, KeyError, ValueError):
            continue
        stale = age > STALE_MINUTES
        attention = attention or stale
        lines.append(f"  {beat.get('role') or 'unmarked'} {str(beat.get('session'))[:12]} "
                     f"last tool {age:.0f}m ago{'  <- may be dead' if stale else ''}")
    return lines, attention


def slots() -> tuple[list[str], bool]:
    """Leases are created on demand, so a slot showing here means real concurrency.

    The room left is what limits how many there can be, so it is reported beside
    them, along with how often a lease was actually refused for lack of it.
    """
    lines = []
    for record in worktrees.active():
        age = worktrees.age_minutes(record)
        stamp = f"{age:.0f}m ago" if age is not None else "age unknown"
        stale = "  <- abandoned?" if age is not None and age > worktrees.STALE_MINUTES else ""
        lines.append(f"  {record['project']}  {record['branch']}  {stamp}{stale}")

    free = worktrees.free_bytes()
    floor = worktrees.MIN_FREE_BYTES
    reading = (f"{free / worktrees.GIB:.1f} GiB free" if free is not None
               else "free space could not be read")
    lines.append(f"  {reading} where checkouts live "
                 f"(floor {floor / worktrees.GIB:.1f} GiB)")
    refused = worktrees.refusals(days=7)
    lines.append(f"  {len(refused)} lease(s) refused for lack of room in 7 days")
    return lines, any("abandoned" in l for l in lines) or worktrees.short_of_room(free)


def review_load() -> list[str]:
    result = store.query(days=7)["reviews"]
    return [
        f"  {result['rounds']} round(s) over {result['changes']} change(s) in 7 days",
        f"  rounds per change: median {result['rounds_per_change_median']}, worst {result['rounds_per_change_max']}",
        f"  cost: {result['cost_usd_total']} total",
    ]


def machine() -> tuple[list[str], bool]:
    drifted = [f"  {target}: {reason}" for target, source in deploy.links().items()
               if (reason := deploy.describe(target, source))]
    if (settings := deploy.settings_drift()):
        drifted.append(f"  {deploy.SETTINGS}: {settings}")
    return (drifted or ["  in sync"]), bool(drifted)


def repository() -> tuple[list[str], bool]:
    branch = git("rev-parse", "--abbrev-ref", "HEAD") or "?"
    dirty = [l for l in git("status", "--porcelain").splitlines() if l.strip()]
    ahead = git("rev-list", "--count", f"origin/{branch}..HEAD") or "0"
    lines = [f"  on {branch}", f"  {len(dirty)} uncommitted file(s)", f"  {ahead} commit(s) not pushed"]
    return lines, bool(dirty) or ahead not in ("", "0")


def section(title: str, lines: list[str]) -> str:
    return "\n".join([f"## {title}"] + (lines or ["  nothing"]))


def report() -> tuple[str, bool]:
    blocks, attention = [], False
    for title, (lines, needs) in (
        ("Plan usage", plan_usage()),
        ("Fleet", fleet()),
        ("Dispatches out", out()),
        ("Heartbeats", heartbeats()),
        ("Worktree slots", slots()),
        ("This machine", machine()),
        ("Fleet repository", repository()),
    ):
        blocks.append(section(title, lines))
        attention = attention or needs
    blocks.append(section("Review load", review_load()))
    tail = "something needs attention" if attention else "nothing waiting"
    return f"bearings as of {jsonstore.now()}\n\n" + "\n\n".join(blocks) + f"\n\n{tail}", attention


def main() -> int:
    text, attention = report()
    print(text)
    return 1 if attention else 0


if __name__ == "__main__":
    raise SystemExit(main())
