#!/usr/bin/env python3
"""Dispatch records: what the stoker sent out, and whether it came back.

The stoker never builds. It sends a worker a brief and waits for a report. This
records both ends, so "what is running" and "what did we send out this week" are
queries rather than something the stoker has to hold in its head across a wake.

A brief is composed here rather than written freehand, so every worker arrives
wrapped in the same standing instructions.

    bin/dispatch.py open --task "..." --project api
    bin/dispatch.py list
    bin/dispatch.py close <id> --outcome pushed --note "branch fix-auth"
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jsonstore
import worktrees

OUTCOMES = ("pushed", "escalated", "failed", "abandoned")
REPO = jsonstore.REPO


def dispatches_dir() -> Path:
    return jsonstore.resolve_dir("HEATER_DISPATCHES_DIR", "store/dispatches")


def worker_wrapper() -> str:
    path = REPO / "roles" / "worker.md"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def compose_brief(record: dict[str, Any]) -> str:
    """The task, wrapped in the standing instructions every worker gets."""
    header = [f"# Brief {record['id']}"]
    if record.get("project"):
        header.append(f"Project: {record['project']}")
    if record.get("task_id"):
        header.append(f"Task: {record['task_id']}")
    if record.get("workdir"):
        header.append(f"Work in: {record['workdir']}")
    if record.get("branch"):
        header.append(f"On branch: {record['branch']} (already checked out for you)")
    parts = ["\n".join(header), "## Your task", record["task"]]
    if record.get("done_when"):
        parts += ["## Done when", record["done_when"]]
    wrapper = worker_wrapper()
    if wrapper:
        parts.append(wrapper)
    parts.append(f"Close this dispatch by reporting; the stoker runs "
                 f"`bin/dispatch.py close {record['id']}`.")
    return "\n\n".join(parts)


def needs_its_own_checkout(project: str) -> bool:
    """True once somebody else is already working this project.

    Nobody decides this. The first worker uses the project's own checkout; the
    second onwards would trample it, so each gets a slot of its own.
    """
    return any(d.get("project") == project for d in live())


def open_dispatch(task: str, *, project: str = "", done_when: str = "",
                  task_id: str = "", agent: str = "worker",
                  repo: str = "") -> dict[str, Any]:
    if not task.strip():
        raise ValueError("a dispatch needs a task")
    record = {
        "id": jsonstore.new_id(), "created": jsonstore.now(), "task": task.strip(),
        "project": project, "done_when": done_when.strip(), "task_id": task_id,
        "agent": agent, "repo": repo, "workdir": repo, "lease_id": "", "branch": "",
        "closed_at": None, "outcome": None, "note": "",
    }

    if repo and needs_its_own_checkout(project or Path(repo).name):
        held = worktrees.lease(Path(repo), project or Path(repo).name,
                               f"worker/{record['id']}", dispatch_id=record["id"])
        record.update(lease_id=held["id"], workdir=held["path"], branch=held["branch"])

    jsonstore.write(dispatches_dir(), record)
    return record


def close_dispatch(dispatch_id: str, outcome: str, note: str = "") -> dict[str, Any]:
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}, got {outcome!r}")
    record = next((d for d in jsonstore.load(dispatches_dir()) if d["id"] == dispatch_id), None)
    if record is None:
        raise ValueError(f"no dispatch with id {dispatch_id!r}")
    if record.get("closed_at"):
        raise ValueError(f"{dispatch_id} was already closed as {record['outcome']}")
    record.update(closed_at=jsonstore.now(), outcome=outcome, note=note.strip())
    jsonstore.write(dispatches_dir(), record)

    # Giving the slot back is part of closing, not a separate chore somebody
    # remembers. Release refuses while the branch still holds unpushed work.
    if record.get("lease_id"):
        try:
            worktrees.release(record["lease_id"], f"dispatch {outcome}")
        except (RuntimeError, ValueError) as error:
            record["note"] = (record["note"] + f" [slot held: {error}]").strip()
            jsonstore.write(dispatches_dir(), record)
    return record


def live() -> list[dict[str, Any]]:
    """Dispatches still out, oldest first: the oldest is the one most likely stuck."""
    return sorted((d for d in jsonstore.load(dispatches_dir()) if not d.get("closed_at")),
                  key=lambda d: d.get("created", ""))


def age_minutes(record: dict[str, Any]) -> float | None:
    try:
        started = datetime.fromisoformat(record["created"])
    except (ValueError, KeyError):
        return None
    return (datetime.now(timezone.utc) - started).total_seconds() / 60


def render(records: list[dict[str, Any]]) -> str:
    if not records:
        return "dispatches: none out"
    lines = [f"{len(records)} dispatch(es) still out:"]
    for record in records:
        age = age_minutes(record)
        stamp = f"{age:.0f}m" if age is not None else "?"
        where = f" {record['project']}" if record.get("project") else ""
        lines.append(f"  {record['id']}  {stamp:>6} ago{where}  {record['task'][:70]}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)

    start = sub.add_parser("open", help="record a dispatch and print the brief to hand the worker")
    start.add_argument("--task", required=True)
    start.add_argument("--project", default="")
    start.add_argument("--done-when", default="")
    start.add_argument("--task-id", default="", help="the inbox task this serves, if any")
    start.add_argument("--agent", default="worker")
    start.add_argument("--repo", default="", help="the project checkout; a slot is leased automatically if one is needed")

    sub.add_parser("list", help="dispatches still out")

    end = sub.add_parser("close", help="record that a worker reported")
    end.add_argument("dispatch_id")
    end.add_argument("--outcome", choices=OUTCOMES, required=True)
    end.add_argument("--note", default="")

    args = parser.parse_args(argv[1:])

    if args.action == "open":
        record = open_dispatch(args.task, project=args.project, done_when=args.done_when,
                               task_id=args.task_id, agent=args.agent, repo=args.repo)
        print(f"# dispatch {record['id']} recorded; hand the brief below to the {record['agent']} agent\n")
        print(compose_brief(record))
    elif args.action == "list":
        print(render(live()))
    else:
        record = close_dispatch(args.dispatch_id, args.outcome, args.note)
        print(f"closed {record['id']} as {record['outcome']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
