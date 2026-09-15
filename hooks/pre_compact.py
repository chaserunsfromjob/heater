#!/usr/bin/env python3
"""Fires when the conversation is about to be summarised automatically.

Reaching this point is a defect, not a routine event: the handover threshold is
well below the compaction point, so something stopped the Stop hook from being
heard. Compaction keeps whatever it judges important and nobody chose what it
drops, which is exactly what a handover exists to avoid.

Nothing here can prevent it. What it can do is leave a mark, so the session that
comes out the other side knows its memory was edited by a machine and writes a
handover immediately.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import context  # noqa: E402
from heater_hook import log, now, run, say  # noqa: E402


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    trigger = payload.get("trigger") or payload.get("matcher") or "auto"
    context.write(compacted_at=now(), compacted_trigger=trigger)
    log("pre_compact", {"trigger": trigger, "used_percentage": context.used()})
    return say(
        "Compacting before a handover was written. Whatever this summary drops is gone. "
        "Write HANDOVER.md as the first thing after compaction finishes."
    )


if __name__ == "__main__":
    raise SystemExit(run(handle, "pre_compact"))
