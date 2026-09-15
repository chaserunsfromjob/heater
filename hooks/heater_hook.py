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


def role() -> str:
    return os.environ.get(ROLE_ENV, "").strip().lower()


def is_dispatched() -> bool:
    return role() in DISPATCHED_ROLES


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
