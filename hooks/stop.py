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

import context  # noqa: E402
import handover  # noqa: E402
import queue  # noqa: E402
from heater_hook import keep_going, log, now, role, run, say, stop  # noqa: E402


def handover_decision() -> dict[str, Any] | None:
    """Past the threshold, handing over comes before anything else.

    Returns None when there is nothing to say, so the queue wake runs normally.
    """
    if not context.due():
        return None

    used, limit = context.used() or 0.0, context.threshold()
    outstanding = handover.problems(quick=True)

    if outstanding:
        listed = "\n".join(f"  - {p}" for p in outstanding)
        log("handover_due", {"used_percentage": used, "outstanding": outstanding})
        return keep_going(
            f"Context is at {used:.0f}%, past the {limit:.0f}% handover threshold. "
            "Hand over now, before starting anything else.\n\n"
            f"Outstanding:\n{listed}\n\n"
            "Follow skills/handover/SKILL.md. Rewrite HANDOVER.md with only what the next "
            "session cannot look up, stamp it with the commit it describes, commit, push, "
            "and run bin/handover.py until every line reads ok. Then tell the operator to clear."
        )

    if not context.announced():
        context.mark_announced(now())
        log("handover_ready", {"used_percentage": used})
    return say(
        f"Context {used:.0f}% — handover is written, current and pushed. "
        "Clear now with /clear; the next session starts from HANDOVER.md."
    )


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    # The harness sets this on a turn that a Stop hook already continued.
    # Waking again here is how a hook turns into an infinite loop.
    if payload.get("stop_hook_active"):
        return stop()

    # Context pressure outranks the queue: picking up new work now only makes
    # the handover harder to write.
    if (decision := handover_decision()) is not None:
        return decision

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
