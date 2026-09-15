#!/usr/bin/env python3
"""How full the context window is, and whether it is time to hand over.

Hooks are not told how full the context window is; only the status line is. So
the status line writes the number down and the hooks read it. That is the whole
trick, and it is why `hooks/statusline.py` must stay deployed for automatic
handover to work at all.

Handing over deliberately beats being compacted automatically. Compaction keeps
whatever it judges important and nobody chooses what it drops; a handover keeps
what this session knows and cannot be looked up.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Well before the window fills. Late enough that a fresh session is not paying
# re-orientation cost for nothing, early enough that there is room to write a
# good note and finish the thought in progress.
DEFAULT_HANDOVER_AT = 55.0


def threshold() -> float:
    try:
        return float(os.environ.get("HEATER_HANDOVER_AT") or DEFAULT_HANDOVER_AT)
    except ValueError:
        return DEFAULT_HANDOVER_AT


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


def used() -> float | None:
    value = read().get("used_percentage")
    return float(value) if isinstance(value, (int, float)) else None


def due() -> bool:
    """True once the window is full enough that handing over beats carrying on."""
    current = used()
    return current is not None and current >= threshold()


def announced() -> bool:
    return bool(read().get("announced_at"))


def mark_announced(when: str) -> None:
    write(announced_at=when)
