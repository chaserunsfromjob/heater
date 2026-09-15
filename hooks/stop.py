#!/usr/bin/env python3
"""The one channel to the stoker.

When a turn ends, this checks the fleet queue and, if anything is waiting, keeps
the stoker going with a single summary message. That is the whole mechanism: a
wake delivered as one message at a turn boundary. Nothing reaches the stoker
mid-turn, and there is no listener.

Only the stoker is woken. A worker's turn ends normally.

It is also where a stoker session ends. Once the handover is written, current
and pushed, this leaves the marker that `tools/stoker.py` is watching for, named
with the identity that supervisor gave this session, and the supervisor ends
this session and opens the next one. A session nobody is supervising leaves no
marker. Nothing here can end a session itself, and nothing is asked of the
operator.
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
import stoker  # noqa: E402
from heater_hook import keep_going, log, now, role, run, say, stop  # noqa: E402


def handover_decision(transcript: str | None = None,
                      session_role: str | None = None,
                      session_id: str | None = None) -> dict[str, Any] | None:
    """Past the arming mark, handing over outranks starting anything new.

    Armed is not the same as due. Cutting a session off mid-task costs the work
    twice, which no cost model shows, so while work is in flight the handover
    waits for a boundary — until the ceiling, where waiting stops being a choice.
    """
    condition = context.state(transcript)
    if condition == context.QUIET:
        return None

    used, arm, cap = context.used(transcript) or 0.0, context.threshold(), context.ceiling()
    flight = handover.in_flight()

    if condition == context.ARMED and flight:
        listed = ", ".join(flight)
        if not context.announced():
            context.mark_announced(now())
            log("handover_armed", {"used_percentage": used, "in_flight": flight})
            return say(
                f"Context {used:.0f}%, past the {arm:.0f}% handover mark. Finish what is in "
                f"flight ({listed}), then hand over. Do not start anything new; the hard "
                f"ceiling is {cap:.0f}%."
            )
        # Already said once. Fall through rather than swallowing the turn: being
        # armed means finish what you are doing, and the queue still has to reach
        # the stoker while it does.
        return None

    outstanding = handover.problems(quick=True)
    if outstanding:
        listed = "\n".join(f"  - {p}" for p in outstanding)
        forced = condition == context.FORCED
        log("handover_due", {"used_percentage": used, "forced": forced,
                             "outstanding": outstanding})
        preamble = (
            f"Context is at {used:.0f}%, past the {cap:.0f}% ceiling. Discretion has run out: "
            "park whatever is in flight — commit it, name it in the note as unfinished — and "
            "hand over now."
            if forced else
            f"Context is at {used:.0f}% and the work is at a clean boundary. Hand over now, "
            "before starting anything else."
        )
        return keep_going(
            f"{preamble}\n\nOutstanding:\n{listed}\n\n"
            "Follow skills/handover/SKILL.md. Rewrite HANDOVER.md with only what the next "
            "session cannot look up, stamp it with the commit it describes, commit, push, "
            "and run bin/handover.py until every line reads ok. The session ends by itself "
            "once it does."
        )

    if not context.announced():
        context.mark_announced(now())
        log("handover_ready", {"used_percentage": used})

    # Nothing here can end the session, and nothing can type into one. The mark
    # is the whole signal: the supervisor that launched this `claude` is
    # watching for it, and ends this session and opens the next one when it
    # appears. Only the stoker is handed over this way, and only once — the
    # marker's own existence is what makes it once.
    if (session_role if session_role is not None else role()) != "stoker":
        return say(f"Context {used:.0f}% — handover is written, current and pushed.")

    # Which session is asking. A supervisor gives its own child a token; a
    # session opened by hand in this folder is the stoker too but has none, and
    # nothing is waiting to end it. Writing an unnamed marker would end whatever
    # session the supervisor happens to be running, which is not this one.
    token = stoker.child_token()
    if not token:
        log("handover_complete", {"used_percentage": used, "supervised": False})
        return say(
            f"Context {used:.0f}% — handover is written, current and pushed. Nothing is "
            "outstanding, so this session can be closed whenever you like."
        )

    if stoker.mark_complete(now(), token, session_id):
        log("handover_complete", {"used_percentage": used, "supervised": True})
    return say(
        f"Context {used:.0f}% — handover is written, current and pushed. This session is "
        "ending now and bin/stoker.sh is opening the next one from HANDOVER.md. "
        "Nothing to type."
    )


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    # The harness sets this on a turn that a Stop hook already continued.
    # Waking again here is how a hook turns into an infinite loop.
    if payload.get("stop_hook_active"):
        return stop()

    # Context pressure outranks the queue: picking up new work now only makes
    # the handover harder to write.
    decision = handover_decision(payload.get("transcript_path"), role(payload),
                                 payload.get("session_id"))
    if decision is not None:
        return decision

    if role(payload) != "stoker":
        return stop()

    waiting = queue.pending()
    if not waiting:
        return stop()

    queue.mark_delivered(waiting)
    log("wake", {"items": [i["id"] for i in waiting]})
    return keep_going(queue.summarise(waiting))


if __name__ == "__main__":
    raise SystemExit(run(handle, "stop"))
