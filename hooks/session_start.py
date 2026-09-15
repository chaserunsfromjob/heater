#!/usr/bin/env python3
"""Load the right role's rules into a session, based on an environment marker.

A session with `HEATER_ROLE=stoker` gets the stoker's rules; a dispatched worker
gets the worker wrapper; an unmarked session gets nothing but a note that this
machine is out of sync, if it is.

Only what the session cannot look up goes in. The global rules already arrive
through CLAUDE.md, so they are pointed at rather than pasted.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import context as context_state  # noqa: E402
from heater_hook import REPO, context, log, role, run, stop  # noqa: E402


def compaction_note() -> str:
    """Tell a session that came through compaction that its memory was edited."""
    state = context_state.read()
    if not state.get("compacted_at"):
        return ""
    context_state.write(compacted_at=None, compacted_trigger=None)
    return ("This session was compacted before a handover was written, so part of its "
            "memory was summarised by a machine rather than chosen. Write HANDOVER.md "
            "now, from the repository and the commit history, before anything else.")


def role_rules(name: str) -> str:
    path = REPO / "roles" / f"{name}.md"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def drift_note() -> str:
    """Deploy drift is a machine's problem, so it is reported here rather than gated."""
    try:
        import deploy
        drifted = [f"{target}: {reason}" for target, source in deploy.links().items()
                   if (reason := deploy.describe(target, source))]
        if (settings := deploy.settings_drift()):
            drifted.append(f"{deploy.SETTINGS}: {settings}")
    except Exception:
        return ""
    if not drifted:
        return ""
    listed = "\n".join(f"  - {d}" for d in drifted[:6])
    return f"This machine is out of sync with the fleet repository:\n{listed}\nRun `bin/deploy.py` to fix it."


def waiting_note() -> str:
    """The stoker's first question on waking is always what is waiting."""
    try:
        import inbox
        import queue
        pending, unjudged, tasks = len(queue.pending()), len(inbox.open_findings()), len(inbox.ranked())
    except Exception:
        return ""
    return (f"Fleet state: {pending} queue item(s) undelivered, "
            f"{unjudged} finding(s) unjudged, {tasks} task(s) on the list. "
            "Judge what is waiting before starting anything new.")


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    name = role(payload)
    parts = []

    rules = role_rules(name) if name else ""
    if rules:
        parts.append(f"You are running as **{name}**. These rules apply on top of "
                     f"the global rules already in your context.\n\n{rules}")
    parts.append(compaction_note())
    if name == "stoker":
        parts.append(waiting_note())
    parts.append(drift_note())

    text = "\n\n".join(p for p in parts if p)
    if not text:
        return stop()

    log("session_start", {"role": name or None, "source": payload.get("source")})
    return context(text, "SessionStart")


if __name__ == "__main__":
    raise SystemExit(run(handle, "session_start"))
