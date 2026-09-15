#!/usr/bin/env python3
"""A directory of JSON files, written atomically and read tolerantly.

Shared by the fleet queue and the review and suite stores. Small enough to read
in one sitting, which is the point: the notes call for a directory of receipts
and one query script, not a database.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]


def now() -> str:
    """Microseconds, not seconds: two records written in the same second must
    still sort in the order they arrived, on disk and in memory."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def resolve_dir(env_var: str, default: str) -> Path:
    return Path(os.environ.get(env_var) or REPO / default)


def filename(record: dict[str, Any]) -> str:
    stamp = record["created"].replace(":", "").replace("-", "")
    return f"{stamp}-{record['id']}.json"


def write(directory: Path, record: dict[str, Any]) -> Path:
    """Write via a temporary file and rename, so a reader never sees half a record."""
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename(record)
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    return target


def load(directory: Path) -> list[dict[str, Any]]:
    """Every readable record, oldest first. A corrupt or partial file is skipped.

    One unreadable file must not hide the rest: the store is evidence, and
    evidence that vanishes when a single write went wrong is worse than none.
    """
    records = []
    for path in sorted(directory.glob("*.json")):
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(parsed, dict) and parsed.get("id"):
            records.append(parsed)
    return records
