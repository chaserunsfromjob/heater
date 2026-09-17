#!/usr/bin/env python3
"""Who is still working, read from the beat a returning tool call leaves.

The PostToolUse hook writes one file per session saying when its last tool call
returned and where from. Every route that removes a checkout has to ask that
question before it removes anything, and the routes live in two modules that
cannot import each other: dispatch already imports worktrees, so worktrees
cannot import dispatch back. The answer lives here instead, below both of them,
so the fleet keeps one threshold and one reader rather than a second copy that
drifts into a second answer.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))

from heater_hook import heartbeat_dir

# A session whose last tool call is older than this has stopped saying anything.
# One threshold and one reader for the whole fleet: bearings shows the same
# beats through `beats()` and calls the same silence dead.
# How long a checkout has been silent, which is not `worktrees.STALE_MINUTES`:
# that one is how long a slot has been held. Two quantities, one name.
STALE_MINUTES = 30


def beats() -> list[dict[str, Any]]:
    """Every heartbeat on the machine, freshest first, each with its age.

    A heartbeat says a session's tool call returned. One reader for all of them,
    because the sweep deletes checkouts on this answer and bearings prints it,
    and two readers would drift into two answers.
    """
    directory = heartbeat_dir()
    found = []
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        try:
            beat = json.loads(path.read_text(encoding="utf-8"))
            beat["age_minutes"] = ((datetime.now(timezone.utc)
                                    - datetime.fromisoformat(beat["at"])).total_seconds() / 60)
        except (json.JSONDecodeError, OSError, KeyError, ValueError, TypeError):
            continue
        found.append(beat)
    return sorted(found, key=lambda b: b["age_minutes"])


def resolved(path: Path) -> Path | None:
    try:
        return path.resolve()
    except OSError:
        return None


def someone_working_in(path: Path) -> bool:
    """True when a session's tool call returned from inside this checkout lately."""
    here = resolved(path)
    if here is None:
        return False
    for beat in beats():
        if beat["age_minutes"] > STALE_MINUTES:
            continue
        where = resolved(Path(str(beat.get("cwd") or ""))) if beat.get("cwd") else None
        if where is not None and (where == here or here in where.parents):
            return True
    return False
