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
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]

KINDS = ("finding", "escalation", "report", "failure")
URGENCIES = ("low", "normal", "high")
# low=0, normal=1, high=2. `pending` negates this, so high sorts first.
URGENCY_RANK = {name: index for index, name in enumerate(URGENCIES)}


def queue_dir() -> Path:
    return Path(os.environ.get("HEATER_QUEUE_DIR") or REPO / "queue")


def now() -> str:
    # Microseconds, not seconds: two items filed in the same second must still
    # sort in arrival order, both in `pending` and in the on-disk filenames.
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


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
        "id": uuid.uuid4().hex[:12],
        "created": now(),
        "kind": kind,
        "urgency": urgency,
        "project": project,
        "path": path,
        "origin": origin or os.environ.get("HEATER_ROLE", ""),
        "summary": summary.strip(),
        "delivered_at": None,
    }
    write(item)
    return item


def item_path(item: dict[str, Any]) -> Path:
    stamp = item["created"].replace(":", "").replace("-", "")
    return queue_dir() / f"{stamp}-{item['id']}.json"


def write(item: dict[str, Any]) -> Path:
    """Write atomically, so a reader never sees a half-written item."""
    directory = queue_dir()
    directory.mkdir(parents=True, exist_ok=True)
    target = item_path(item)
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(item, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    return target


def load_all() -> list[dict[str, Any]]:
    """Every readable item, newest last. A corrupt file is skipped, not fatal."""
    items = []
    for path in sorted(queue_dir().glob("*.json")):
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(parsed, dict) and parsed.get("id"):
            items.append(parsed)
    return items


def pending() -> list[dict[str, Any]]:
    """Items the stoker has not been woken for, most urgent first."""
    undelivered = [i for i in load_all() if not i.get("delivered_at")]
    return sorted(
        undelivered,
        key=lambda i: (-URGENCY_RANK.get(i.get("urgency", "normal"), 1), i.get("created", "")),
    )


def mark_delivered(items: list[dict[str, Any]]) -> None:
    """Stamp items as delivered so the next turn does not wake the stoker again."""
    stamp = now()
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
