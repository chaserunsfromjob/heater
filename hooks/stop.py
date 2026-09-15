#!/usr/bin/env python3
"""The one channel to the stoker.

When a turn ends, this checks the fleet queue and, if anything is waiting, keeps
the stoker going with a single summary message. That is the whole mechanism: a
wake delivered as one message at a turn boundary. Nothing reaches the stoker
mid-turn, and there is no listener.

Only the stoker is woken. A worker's turn ends normally.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import queue  # noqa: E402
from heater_hook import keep_going, log, role, run, stop  # noqa: E402


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    # The harness sets this on a turn that a Stop hook already continued.
    # Waking again here is how a hook turns into an infinite loop.
    if payload.get("stop_hook_active"):
        return stop()

    if role() != "stoker":
        return stop()

    waiting = queue.pending()
    if not waiting:
        return stop()

    queue.mark_delivered(waiting)
    log("wake", {"items": [i["id"] for i in waiting]})
    return keep_going(queue.summarise(waiting))


if __name__ == "__main__":
    raise SystemExit(run(handle, "stop"))
