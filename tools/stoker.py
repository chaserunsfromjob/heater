#!/usr/bin/env python3
"""Supervise the stoker: run one `claude` session, and open its successor.

The handoff has to cost the operator nothing. Everything up to the handover was
already automatic — noticing the context mark, writing the note, committing,
pushing, verifying — and the last step was a person typing `/clear`. This is
what removes that step.

Nothing here types into a session, because nothing can: hook output cannot send
input, and injecting keystrokes into a terminal is off the table. So the process
lifecycle moves up one level instead. This supervisor is what the operator
starts; `claude` is its child. When the Stop hook has proved the handover is
written, current and pushed, it leaves a marker file. The supervisor sees the
marker, ends that session, and starts a fresh one in the same folder.

A relauncher spawned from a hook is not guaranteed to outlive the process that
ran the hook, so the relauncher has to be the thing that launched `claude` in
the first place. That is the whole reason this file exists rather than a few
lines in a hook.

    tools/stoker.py [extra claude arguments ...]

The operator's own plain `claude` in this folder is untouched by any of it.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO / "hooks"))

try:  # Logging is never worth failing a launch over.
    from heater_hook import log as _log
except Exception:  # pragma: no cover - only when the hooks directory is gone
    def _log(event: str, payload: dict[str, Any]) -> None:
        return None


def log(event: str, payload: dict[str, Any]) -> None:
    try:
        _log(event, payload)
    except Exception:
        pass


# A fresh interactive session sits idle forever with nobody to type into it, so
# every launch carries an opening instruction. Short on purpose: CLAUDE.md and
# the SessionStart hook already arrive with the role, the rules and the drift
# report, and repeating them here would just be a second place to keep current.
INITIAL_PROMPT = (
    "You are the stoker. Run bin/bearings.py, read HANDOVER.md, and continue the work."
)

DEFAULT_SESSION_NAME = "heater stoker"

# How often the supervisor looks for the marker. Fast enough that the handoff
# feels immediate, slow enough to cost nothing.
DEFAULT_POLL = 0.5

# SIGTERM first, SIGKILL after this. A session that is already finished has
# nothing to flush, so this is a bound on a hang, not a courtesy.
DEFAULT_GRACE = 10.0

# A breath between sessions, so the terminal settles and the ending session's
# own SessionEnd hook gets its budget.
DEFAULT_PAUSE = 2.0

# A launch that dies faster than this never became a session: bad flag, bad
# auth, missing binary. Three of those in a row is a loop, not a handoff.
DEFAULT_MIN_LIFETIME = 30.0
MAX_SHORT_LAUNCHES = 3

MARKER_NAME = "handover-complete"


def _number(name: str, fallback: float) -> float:
    try:
        return float(os.environ.get(name) or fallback)
    except ValueError:
        return fallback


def state_dir() -> Path:
    """Where per-session marks live. Same base the context snapshot uses."""
    return Path(os.environ.get("HEATER_STATE_DIR") or Path.home() / ".heater")


def marker_path() -> Path:
    return state_dir() / MARKER_NAME


def mark_complete(when: str) -> bool:
    """Say the handover is done and this session can end. Never raises.

    Returns True when this call is what wrote the marker. The marker's own
    existence is the guard against writing it twice.
    """
    try:
        path = marker_path()
        if path.exists():
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{when}\n", encoding="utf-8")
        return True
    except Exception:
        return False


def clear_marker() -> None:
    """Remove the marker, and nothing else. The only file this program deletes."""
    try:
        marker_path().unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def session_name() -> str:
    return os.environ.get("HEATER_SESSION_NAME") or DEFAULT_SESSION_NAME


def command(extra: list[str] | None = None) -> list[str]:
    """The exact `claude` command line a launch runs.

    Remote Control is what lets the operator talk to the stoker from the app
    without the stoker giving up the machine it governs, and the name is what
    makes the session findable in the app's list.
    """
    return ["claude", "--remote-control", session_name(), *(extra or []), INITIAL_PROMPT]


def child_env() -> dict[str, str]:
    return {**os.environ, "HEATER_ROLE": "stoker"}


# The session in progress, and whether the supervisor itself has been told to
# stop. A `kill` aimed at the supervisor has to take the session down with it
# and stay down, rather than being read as a session that crashed and relaunched.
_current: subprocess.Popen | None = None
_stopping = False


def _forward_stop(signum: int, _frame: Any) -> None:
    global _stopping
    _stopping = True
    child = _current
    if child is not None and child.poll() is None:
        try:
            child.terminate()
        except OSError:
            pass


def install_signal_handlers() -> None:
    """SIGINT is deliberately not handled: the session owns Ctrl-C.

    A Python handler is reset to the default on exec, so this never changes
    what the session itself does with a signal.
    """
    try:
        signal.signal(signal.SIGTERM, _forward_stop)
        signal.signal(signal.SIGHUP, _forward_stop)
    except (ValueError, OSError):  # pragma: no cover - not the main thread
        pass


def _terminate(child: subprocess.Popen, grace: float) -> int:
    """End a session that has already handed over. SIGTERM, then SIGKILL."""
    try:
        child.terminate()
    except OSError:
        pass
    try:
        return child.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        log("stoker_kill", {"pid": child.pid, "after_seconds": grace})
        try:
            child.kill()
        except OSError:
            pass
        try:
            return child.wait(timeout=grace)
        except subprocess.TimeoutExpired:  # pragma: no cover - unkillable child
            return -signal.SIGKILL


def watch(child: subprocess.Popen, poll: float, grace: float) -> tuple[int, bool, bool]:
    """Wait for the session to end or to hand over.

    Returns (exit code, handed over, interrupted).
    """
    interrupted = False
    while True:
        code = child.poll()
        if code is not None:
            return code, False, interrupted
        if marker_path().exists():
            clear_marker()
            log("handover_marker_seen", {"pid": child.pid})
            return _terminate(child, grace), True, interrupted
        try:
            time.sleep(poll)
        except KeyboardInterrupt:
            # Ctrl-C reached the whole foreground group, so the session got it
            # too and decides for itself what it means: in Claude Code one press
            # cancels the turn and two end the session. Killing the child here
            # would take the first press for the second. So this only remembers
            # that the operator is at the keyboard, and keeps watching.
            interrupted = True


def exit_code(code: int) -> int:
    """A shell's spelling of how the child ended. Killed by signal N is 128 + N."""
    return 128 - code if code < 0 else code


def stalled_message(count: int) -> str:
    return (
        f"bin/stoker.sh: the Claude session stopped {count} times in a row within seconds "
        f"of starting, so it is not being restarted again. Nothing was lost, and nothing "
        f"was deleted. Run `claude` in this folder by hand to see the error it prints — a "
        f"login that has expired and an unrecognised option both look like this."
    )


def supervise(extra: list[str] | None = None,
              spawn: Callable[..., subprocess.Popen] = subprocess.Popen) -> int:
    """Run sessions until the operator stops one, or until launches stop working."""
    global _current

    poll = _number("HEATER_STOKER_POLL", DEFAULT_POLL)
    grace = _number("HEATER_STOKER_GRACE", DEFAULT_GRACE)
    pause = _number("HEATER_STOKER_PAUSE", DEFAULT_PAUSE)
    minimum = _number("HEATER_STOKER_MIN_LIFETIME", DEFAULT_MIN_LIFETIME)

    short = 0
    while True:
        # A marker left by a session that is already gone would kill the next
        # one on its first poll. This is the only file the supervisor removes.
        clear_marker()

        line = command(extra)
        log("stoker_launch", {"command": line, "cwd": str(REPO)})
        started = time.monotonic()
        try:
            child = spawn(line, cwd=str(REPO), env=child_env())
        except (OSError, ValueError) as error:
            print(f"bin/stoker.sh: could not start Claude: {error}", file=sys.stderr)
            log("stoker_launch_failed", {"error": str(error)})
            return 127

        _current = child
        code, handed_over, interrupted = watch(child, poll, grace)
        _current = None
        lifetime = time.monotonic() - started
        short = short + 1 if lifetime < minimum else 0

        if _stopping:
            log("stoker_exit", {"exit_code": code, "stopped": True})
            return exit_code(code)

        if short >= MAX_SHORT_LAUNCHES:
            print(stalled_message(short), file=sys.stderr)
            log("stoker_stalled", {"launches": short, "exit_code": code})
            return exit_code(code) or 1

        if handed_over:
            log("stoker_restart", {"exit_code": code, "seconds": round(lifetime, 1)})
            time.sleep(pause)
            continue

        if interrupted or code == 0 or lifetime >= minimum:
            log("stoker_exit", {"exit_code": code, "seconds": round(lifetime, 1),
                                "interrupted": interrupted})
            return exit_code(code)

        log("stoker_relaunch_after_failure",
            {"exit_code": code, "seconds": round(lifetime, 1)})
        time.sleep(pause)


def main(argv: list[str]) -> int:
    install_signal_handlers()
    return supervise(list(argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
