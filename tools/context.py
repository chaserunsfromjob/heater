#!/usr/bin/env python3
"""How full the context window is, and whether it is time to hand over.

Two sources, because one of them is not always there.

The transcript is the primary source: every hook is handed a `transcript_path`,
and the last usage record in it carries the exact token counts the API reported.
That works in a terminal and in a web session alike, and needs nothing deployed
beyond the hook itself.

The status line is the secondary source. It is told the context window size and
a pre-calculated percentage, which is cheaper to read and more precise about the
window, but it only runs in the interactive CLI and only if the operator has not
replaced it with their own.

Handing over deliberately beats being compacted automatically. Compaction keeps
whatever it judges important and nobody chooses what it drops; a handover keeps
what this session knows and cannot be looked up.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Two marks, not one. Handing over costs a re-orientation; being cut off
# mid-task costs the work done twice, which is worse and invisible in any cost
# model. So the first mark arms the handover and the second one forces it.
#
# 25% is where cost per turn of real work bottoms out before the curve flattens:
# measured against a real session, it is about a third cheaper per turn than 55%
# while still leaving roughly a dozen turns, which is a whole focused task.
DEFAULT_HANDOVER_AT = 25.0

# Discretion has to end somewhere, or "still mid-task" becomes a way of never
# handing over at all. Past this, whatever is in flight gets parked.
DEFAULT_CEILING = 45.0

QUIET, ARMED, FORCED = "quiet", "armed", "forced"


def _number(name: str, fallback: float) -> float:
    try:
        return float(os.environ.get(name) or fallback)
    except ValueError:
        return fallback


def threshold() -> float:
    return _number("HEATER_HANDOVER_AT", DEFAULT_HANDOVER_AT)


def ceiling() -> float:
    """Never below the arming mark, whatever the environment says."""
    return max(_number("HEATER_HANDOVER_CEILING", DEFAULT_CEILING), threshold())


DEFAULT_WINDOW = 1_000_000

# Usage records appear on every assistant message, so the tail of the transcript
# always holds several. Reading the whole file on every turn-end would be waste.
TAIL_BYTES = 512 * 1024


def window_size() -> int:
    """Tokens the context window holds. The status line knows exactly; otherwise assume."""
    try:
        if (override := os.environ.get("HEATER_CONTEXT_WINDOW")):
            return int(override)
    except ValueError:
        pass
    recorded = read().get("size")
    return int(recorded) if isinstance(recorded, (int, float)) and recorded else DEFAULT_WINDOW


def usage_tokens(record: dict[str, Any]) -> int | None:
    """What one usage record says is currently in the window.

    Input, cache writes and cache reads together are the context; output is not
    part of it until the next request carries it back in.
    """
    try:
        return (int(record.get("input_tokens") or 0)
                + int(record.get("cache_creation_input_tokens") or 0)
                + int(record.get("cache_read_input_tokens") or 0))
    except (TypeError, ValueError):
        return None


def last_usage(path: Path) -> dict[str, Any] | None:
    """The most recent usage record in a transcript, read from the end."""
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > TAIL_BYTES:
                handle.seek(size - TAIL_BYTES)
                handle.readline()  # discard a line the seek cut in half
            lines = handle.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None

    for line in reversed(lines):
        if '"usage"' not in line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        found = (record.get("message") or {}).get("usage") or record.get("usage")
        if isinstance(found, dict) and usage_tokens(found):
            return found
    return None


def from_transcript(transcript_path: str | None) -> float | None:
    """Percentage of the window in use, read straight from the transcript."""
    if not transcript_path:
        return None
    record = last_usage(Path(transcript_path))
    if record is None:
        return None
    tokens = usage_tokens(record)
    return None if not tokens else min(100.0, tokens / window_size() * 100)


def snapshot_path() -> Path:
    base = os.environ.get("HEATER_STATE_DIR") or Path.home() / ".heater"
    return Path(base) / "context.json"


def read() -> dict[str, Any]:
    try:
        parsed = json.loads(snapshot_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def write(**fields: Any) -> None:
    """Never raises: a status line that crashes is worse than one that is stale."""
    try:
        path = snapshot_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        current = read()
        current.update(fields)
        path.write_text(json.dumps(current) + "\n", encoding="utf-8")
    except Exception:
        pass


def record(payload: dict[str, Any]) -> float | None:
    """Store what the status line was told. Returns the percentage, if known."""
    window = payload.get("context_window") or {}
    used = window.get("used_percentage")
    if not isinstance(used, (int, float)):
        return None
    session = payload.get("session_id")
    if session and session != read().get("session"):
        # A new session starts its own announcement state.
        write(session=session, announced_at=None)
    write(used_percentage=float(used),
          size=window.get("context_window_size"),
          cost_usd=(payload.get("cost") or {}).get("total_cost_usd"),
          session=session)
    return float(used)


def used(transcript_path: str | None = None) -> float | None:
    """The transcript first; the status line's snapshot when there is no transcript."""
    if (live := from_transcript(transcript_path)) is not None:
        return live
    value = read().get("used_percentage")
    return float(value) if isinstance(value, (int, float)) else None


def state(transcript_path: str | None = None) -> str:
    """QUIET, ARMED (hand over at the next boundary), or FORCED (hand over now)."""
    current = used(transcript_path)
    if current is None:
        return QUIET
    if current >= ceiling():
        return FORCED
    return ARMED if current >= threshold() else QUIET


def due(transcript_path: str | None = None) -> bool:
    return state(transcript_path) != QUIET


def announced() -> bool:
    return bool(read().get("announced_at"))


def mark_announced(when: str) -> None:
    write(announced_at=when)
