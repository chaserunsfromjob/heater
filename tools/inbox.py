#!/usr/bin/env python3
"""The findings inbox: judge each finding, then dismiss it or promote it.

A worker that notices something off-task never fixes it and never drops it. It
files a one-line finding with a path and moves on. The stoker judges each one.
Most findings die here, and the recorded reason is what stops the next worker
from filing the same thing.

Findings live in the queue store rather than a second directory of their own, so
there is one record of a finding and not two that can disagree. This module is
the lifecycle over them; `inbox/tasks/` holds what survives it.

    bin/inbox.py list
    bin/inbox.py check --summary "stale TODO in the parser"
    bin/inbox.py dismiss <id> --reason "intentional; the parser owns that TODO"
    bin/inbox.py promote <id> --score 70
    bin/inbox.py tasks
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jsonstore
import queue
import textmatch

# Opinion 5: the task list has a hard cap and a rank. What falls off the bottom
# is deleted, not archived. If it mattered it comes back on its own.
TASK_CAP = 20

# Lower than the rule linter's 0.85: findings are free text written in a hurry,
# so the same observation arrives worded differently far more often than a rule does.
REFILE_SIMILARITY = 0.75


def tasks_dir() -> Path:
    return jsonstore.resolve_dir("HEATER_TASKS_DIR", "inbox/tasks")


def findings() -> list[dict[str, Any]]:
    return [i for i in queue.load_all() if i.get("kind") == "finding"]


def open_findings() -> list[dict[str, Any]]:
    """Findings the stoker has not yet judged."""
    return [f for f in findings() if not f.get("resolution")]


def dismissed() -> list[dict[str, Any]]:
    return [f for f in findings() if (f.get("resolution") or {}).get("action") == "dismissed"]


def would_refile(summary: str) -> dict[str, Any] | None:
    """The dismissed finding this summary restates, if there is one.

    This is the whole point of recording a dismissal reason: a worker checks
    here before filing, and a question already answered is not asked again.
    """
    prior = dismissed()
    match = textmatch.best_match(summary, [f["summary"] for f in prior], REFILE_SIMILARITY)
    return prior[match[0]] if match else None


def resolve(finding_id: str, action: str, **detail: Any) -> dict[str, Any]:
    item = queue.find(finding_id)
    if item is None:
        raise ValueError(f"no finding with id {finding_id!r}")
    if item.get("kind") != "finding":
        raise ValueError(f"{finding_id} is a {item.get('kind')}, not a finding")
    if item.get("resolution"):
        raise ValueError(f"{finding_id} was already {item['resolution']['action']}")
    item["resolution"] = {"action": action, "at": jsonstore.now(), **detail}
    queue.write(item)
    return item


def dismiss(finding_id: str, reason: str) -> dict[str, Any]:
    if not reason.strip():
        raise ValueError("a dismissal without a reason teaches the next worker nothing")
    return resolve(finding_id, "dismissed", reason=reason.strip())


def promote(finding_id: str, score: int, title: str = "") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Promote a finding onto the task list. Returns the task and anything the cap dropped."""
    if not 0 <= score <= 100:
        raise ValueError("score is 0 to 100")
    item = queue.find(finding_id)
    if item is None:
        raise ValueError(f"no finding with id {finding_id!r}")

    task = {
        "id": jsonstore.new_id(), "created": jsonstore.now(), "score": score,
        "title": (title or item["summary"]).strip(), "source_finding": finding_id,
        "project": item.get("project", ""), "path": item.get("path", ""), "done_at": None,
    }
    jsonstore.write(tasks_dir(), task)
    resolve(finding_id, "promoted", score=score, task_id=task["id"])
    return task, enforce_cap()


def ranked() -> list[dict[str, Any]]:
    """Open tasks, best first. Ties go to whichever was raised earlier."""
    live = [t for t in jsonstore.load(tasks_dir()) if not t.get("done_at")]
    return sorted(live, key=lambda t: (-t.get("score", 0), t.get("created", "")))


def enforce_cap() -> list[dict[str, Any]]:
    """Delete everything past the cap. Deleted, not archived — opinion 5."""
    dropped = ranked()[TASK_CAP:]
    for task in dropped:
        (tasks_dir() / jsonstore.filename(task)).unlink(missing_ok=True)
    return dropped


def complete(task_id: str) -> dict[str, Any]:
    task = next((t for t in jsonstore.load(tasks_dir()) if t["id"] == task_id), None)
    if task is None:
        raise ValueError(f"no task with id {task_id!r}")
    task["done_at"] = jsonstore.now()
    jsonstore.write(tasks_dir(), task)
    return task


def render_findings(items: list[dict[str, Any]]) -> str:
    if not items:
        return "inbox: no findings waiting"
    lines = [f"{len(items)} finding(s) waiting to be judged:"]
    for f in items:
        where = f" {f['project']}" if f.get("project") else ""
        at = f" ({f['path']})" if f.get("path") else ""
        lines.append(f"  {f['id']}  [{f['urgency']}]{where} {f['summary']}{at}")
    lines.append("Dismiss with a reason, or promote with a score. Leaving it open is neither.")
    return "\n".join(lines)


def render_tasks(items: list[dict[str, Any]]) -> str:
    if not items:
        return "tasks: none"
    lines = [f"{len(items)} task(s), best first, cap {TASK_CAP}:"]
    for position, t in enumerate(items, 1):
        where = f" {t['project']}" if t.get("project") else ""
        at = f" ({t['path']})" if t.get("path") else ""
        lines.append(f"  {position:>2}. [{t['score']:>3}] {t['title']}{where}{at}  {t['id']}")
    lines.append("The top is always being worked. The bottom is dropped, not kept.")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("list", help="findings waiting to be judged")
    sub.add_parser("tasks", help="the ranked task list")

    check = sub.add_parser("check", help="has this already been dismissed?")
    check.add_argument("--summary", required=True)

    drop = sub.add_parser("dismiss", help="dismiss a finding, with the reason recorded")
    drop.add_argument("finding_id")
    drop.add_argument("--reason", required=True)

    up = sub.add_parser("promote", help="promote a finding onto the task list")
    up.add_argument("finding_id")
    up.add_argument("--score", type=int, required=True)
    up.add_argument("--title", default="")

    done = sub.add_parser("done", help="mark a task complete")
    done.add_argument("task_id")

    args = parser.parse_args(argv[1:])

    if args.action == "list":
        print(render_findings(open_findings()))
    elif args.action == "tasks":
        print(render_tasks(ranked()))
    elif args.action == "check":
        prior = would_refile(args.summary)
        if prior is None:
            print("check: nothing like this was dismissed; file it")
            return 0
        print(f"check: already dismissed as {prior['id']} — {prior['resolution']['reason']}")
        return 1
    elif args.action == "dismiss":
        item = dismiss(args.finding_id, args.reason)
        print(f"dismissed {item['id']}: {item['resolution']['reason']}")
    elif args.action == "promote":
        task, dropped = promote(args.finding_id, args.score, args.title)
        print(f"promoted to task {task['id']} at score {task['score']}")
        for lost in dropped:
            print(f"  dropped past the cap: [{lost['score']}] {lost['title']}")
    elif args.action == "done":
        print(f"completed {complete(args.task_id)['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
