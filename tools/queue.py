#!/usr/bin/env python3
"""The fleet queue: notes waiting for the stoker.

A directory of small JSON files, one per item, inside the fleet repository. It
is readable in a diff, greppable, and hand-editable, which a database is not.
Swap it for something with real queries when the volume earns that.

    bin/queue.py add --kind escalation --summary "..." --project heater
    bin/queue.py list
    bin/queue.py list --all
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jsonstore

KINDS = ("finding", "escalation", "report", "failure")
URGENCIES = ("low", "normal", "high")
# low=0, normal=1, high=2. `pending` negates this, so high sorts first.
URGENCY_RANK = {name: index for index, name in enumerate(URGENCIES)}


def queue_dir() -> Path:
    return jsonstore.resolve_dir("HEATER_QUEUE_DIR", "queue")


def add(kind: str, summary: str, *, project: str = "", path: str = "",
        urgency: str = "normal", origin: str = "") -> dict[str, Any]:
    """Write one item. Never overwrites: the id is unique per call."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
    if urgency not in URGENCIES:
        raise ValueError(f"urgency must be one of {URGENCIES}, got {urgency!r}")
    if not summary.strip():
        raise ValueError("summary must not be empty")

    item = {
        "id": jsonstore.new_id(),
        "created": jsonstore.now(),
        "kind": kind,
        "urgency": urgency,
        "project": project,
        "path": path,
        "origin": origin or os.environ.get("HEATER_ROLE", ""),
        "summary": summary.strip(),
        "delivered_at": None,
        # Set by the inbox when the stoker judges the item. None means unjudged.
        "resolution": None,
    }
    write(item)
    return item


def item_path(item: dict[str, Any]) -> Path:
    return queue_dir() / jsonstore.filename(item)


def write(item: dict[str, Any]) -> Path:
    return jsonstore.write(queue_dir(), item)


def load_all() -> list[dict[str, Any]]:
    return jsonstore.load(queue_dir())


def find(item_id: str) -> dict[str, Any] | None:
    """One item by id, or None. Ids are unique, so the first match is the only one."""
    return next((i for i in load_all() if i["id"] == item_id), None)


def pending() -> list[dict[str, Any]]:
    """Items the stoker has not been woken for, most urgent first."""
    undelivered = [i for i in load_all() if not i.get("delivered_at")]
    return sorted(
        undelivered,
        key=lambda i: (-URGENCY_RANK.get(i.get("urgency", "normal"), 1), i.get("created", "")),
    )


def mark_delivered(items: list[dict[str, Any]]) -> None:
    """Stamp items as delivered so the next turn does not wake the stoker again."""
    stamp = jsonstore.now()
    for item in items:
        item["delivered_at"] = stamp
        write(item)


def summarise(items: list[dict[str, Any]]) -> str:
    lines = [f"{len(items)} item(s) waiting in the fleet queue:"]
    for item in items:
        where = f" {item['project']}" if item.get("project") else ""
        at = f" ({item['path']})" if item.get("path") else ""
        lines.append(f"- [{item['urgency']}] {item['kind']}{where}: {item['summary']}{at} #{item['id']}")
    lines.append("Judge each item, then act. Dismiss with a recorded reason or promote it onto the task list.")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    adder = sub.add_parser("add", help="file one item for the stoker")
    adder.add_argument("--kind", choices=KINDS, required=True)
    adder.add_argument("--summary", required=True)
    adder.add_argument("--project", default="")
    adder.add_argument("--path", default="")
    adder.add_argument("--urgency", choices=URGENCIES, default="normal")

    lister = sub.add_parser("list", help="show waiting items")
    lister.add_argument("--all", action="store_true", help="include already-delivered items")

    args = parser.parse_args(argv[1:])

    if args.command == "add":
        item = add(args.kind, args.summary, project=args.project,
                   path=args.path, urgency=args.urgency)
        print(f"queued {item['id']} -> {item_path(item)}")
        return 0

    items = load_all() if args.all else pending()
    if not items:
        print("queue: empty")
        return 0
    print(summarise(items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
