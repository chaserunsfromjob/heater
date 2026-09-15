#!/usr/bin/env python3
"""Shared plumbing for heater's Claude Code hooks.

Every hook fails open. A hook that raises, times out, or writes malformed JSON
must never wedge a session: a broken guard is an annoyance, a broken guard that
blocks every tool call is a fleet halt, and a fleet halt is one of the four
things the opinions file allows hardening before it happens.

So `run` catches everything, logs what it can, and exits 0 with no decision.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parents[1]

# Set by the SessionStart loader to "stoker" or "worker". Unset means a session
# nobody dispatched — normally the operator working by hand.
ROLE_ENV = "HEATER_ROLE"
DISPATCHED_ROLES = ("stoker", "worker")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def marked_role() -> str:
    """The role explicitly set on the session. Empty when nobody set one."""
    return os.environ.get(ROLE_ENV, "").strip().lower()


def in_fleet_repo(payload: dict[str, Any] | None = None) -> bool:
    """True when the session is working inside the fleet repository itself."""
    # Most authoritative source wins outright. Taking any match instead would
    # let the process's own working directory overrule a payload that says the
    # session is somewhere else entirely.
    candidate = (payload or {}).get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR")
    if not candidate:
        try:
            candidate = str(Path.cwd())
        except OSError:
            return False
    try:
        here = Path(candidate).resolve()
    except OSError:
        return False
    return here == REPO or REPO in here.parents


def role(payload: dict[str, Any] | None = None) -> str:
    """The session's role.

    An explicit marker always wins: that is how a worker and a reviewer are
    dispatched, and a reviewer's write ban hangs off it. An unmarked session
    opened in the fleet repository is the stoker, because that is the one
    conversation the operator talks to, and requiring them to remember a marker
    failed silently — the session opened, looked ordinary, and was not it.
    """
    return marked_role() or ("stoker" if in_fleet_repo(payload) else "")


def is_dispatched() -> bool:
    """Deliberately reads the explicit marker only.

    Routing enforcement is about whether the stoker sent this session, which
    only a marker can answer. Letting the fleet-repo default satisfy it would
    silently retire the unrouted-write warning.
    """
    return marked_role() in DISPATCHED_ROLES


def log_dir() -> Path:
    return Path(os.environ.get("HEATER_LOG_DIR") or Path.home() / ".heater" / "logs")


def heartbeat_dir() -> Path:
    return log_dir().parent / "heartbeat"


def context(text: str, event: str) -> dict[str, Any]:
    """Inject text into the session as a system reminder."""
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}


def log(event: str, payload: dict[str, Any]) -> None:
    """Append one JSONL record. Never raises: logging is not worth a wedged session."""
    try:
        directory = log_dir()
        directory.mkdir(parents=True, exist_ok=True)
        record = {"at": now(), "event": event, "role": role() or None, **payload}
        with (directory / "hooks.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
    except Exception:
        pass


def read_input() -> dict[str, Any]:
    """Parse the hook payload from stdin, returning {} when there is nothing usable."""
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


# --- PreToolUse decisions -------------------------------------------------

def allow() -> dict[str, Any]:
    """Say nothing. The tool call proceeds exactly as it would without the hook."""
    return {}


def deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def warn(message: str) -> dict[str, Any]:
    """Allow the call and name the rule.

    A warning never blocks. The guard denies only the spellings it is certain
    about; everything else is the agent's judgment, informed.
    """
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        },
        "systemMessage": message,
    }


# --- Stop decisions -------------------------------------------------------

def stop() -> dict[str, Any]:
    """Let the turn end."""
    return {}


def say(message: str) -> dict[str, Any]:
    """Let the turn end, but put a message in front of the operator."""
    return {"systemMessage": message}


def keep_going(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "decision": "continue",
            "reason": reason,
        }
    }


def run(handler: Callable[[dict[str, Any]], dict[str, Any]], name: str) -> int:
    """Run a hook handler, failing open on anything at all."""
    try:
        payload = read_input()
        decision = handler(payload) or {}
        if decision:
            print(json.dumps(decision))
        return 0
    except Exception:
        log("hook_error", {"hook": name, "traceback": traceback.format_exc()})
        return 0
