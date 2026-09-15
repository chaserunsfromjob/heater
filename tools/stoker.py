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
written, current and pushed, it leaves a marker file naming the session it was
written from and the supervisor waiting on that session. The supervisor sees a
marker naming its own child, ends that session, and starts a fresh one in the
same folder. A marker naming a session another running supervisor started is
left where it is. A marker whose supervisor is gone — the machine restarted
mid-session — is waited on by nobody, so it is cleared away rather than left to
hold the one path forever.

A relauncher spawned from a hook is not guaranteed to outlive the process that
ran the hook, so the relauncher has to be the thing that launched `claude` in
the first place. That is the whole reason this file exists rather than a few
lines in a hook.

    tools/stoker.py [extra claude arguments ...]

The operator's own plain `claude` in this folder is untouched by any of it.
"""

from __future__ import annotations

import json
import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, NamedTuple

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

# Between seeing the marker and ending the session. The Stop hook has to return
# and its closing message has to render, and neither is instant. Short enough
# that the handoff still feels immediate.
DEFAULT_GRACE = 2.0

# SIGTERM first, SIGKILL after this. A session that is already finished has
# nothing to flush, so this is a bound on a hang, not a courtesy.
DEFAULT_KILL_AFTER = 10.0

# A breath between sessions, so the terminal settles and the ending session's
# own SessionEnd hook gets its budget.
DEFAULT_PAUSE = 2.0

# A launch that dies faster than this never became a session: bad flag, bad
# auth, missing binary. Three of those in a row is a loop, not a handoff.
DEFAULT_MIN_LIFETIME = 30.0
MAX_SHORT_LAUNCHES = 3

# A session shut down by something outside this program — the machine running
# out of memory is the common one — is not the operator stopping the stoker, so
# it is opened again. Whatever is doing the shutting down can keep doing it, so
# more than this many inside the window below stops the supervisor.
DEFAULT_MAX_CRASHES = 3

# How a session ends when a person ends it: on its own (any exit code), by
# Ctrl-C, or by the plain terminate that a closing terminal sends to everything
# in it. Any other signal killed a session that was still working.
OPERATOR_SIGNALS = {int(signal.SIGINT), int(signal.SIGTERM)}

# A handover is a session doing its job, so it never counts as a stalled
# launch. But a session that opens, finds nothing to do and hands straight over
# again is a loop too, just a slower one, so the rate is bounded on its own:
# more than this many handoffs inside the window below stops the supervisor.
DEFAULT_MAX_HANDOFFS = 5
DEFAULT_HANDOFF_WINDOW = 3600.0

MARKER_NAME = "handover-complete"

# Set on the session the supervisor launches, and on nothing else. The marker is
# one shared path, and the fleet repository makes any unmarked session in it the
# stoker, so without an identity a plain `claude` opened in this folder would end
# the supervised session instead of its own. The hook writes this token into the
# marker, and the supervisor acts only on a marker naming the child it started.
CHILD_ENV = "HEATER_STOKER_CHILD"

# Which supervisor is waiting on the session, set on the session it launches and
# written into the marker with the token. A supervisor remembers the identities
# it issued only in memory, so after a restart its own leftover marker would
# read as somebody else's and sit there forever, disabling the handoff for good.
# The owner in the marker is what survives a restart: a marker whose owner is
# gone is reclaimed, and one whose owner is still running is left alone.
OWNER_ENV = "HEATER_STOKER_OWNER"

# How finely an interruptible wait notices that the supervisor has been told to
# stop. A `kill` during the pause between sessions must not open another one.
STOP_CHECK = 0.05


def _number(name: str, fallback: float) -> float:
    try:
        return float(os.environ.get(name) or fallback)
    except ValueError:
        return fallback


class Limits(NamedTuple):
    """Everything the supervisor's own timing is set by, read once per run."""

    poll: float
    grace: float
    kill_after: float
    pause: float
    minimum: float
    max_handoffs: float
    handoff_window: float
    max_crashes: float


def limits() -> Limits:
    return Limits(
        poll=_number("HEATER_STOKER_POLL", DEFAULT_POLL),
        grace=_number("HEATER_STOKER_GRACE", DEFAULT_GRACE),
        kill_after=_number("HEATER_STOKER_KILL_AFTER", DEFAULT_KILL_AFTER),
        pause=_number("HEATER_STOKER_PAUSE", DEFAULT_PAUSE),
        minimum=_number("HEATER_STOKER_MIN_LIFETIME", DEFAULT_MIN_LIFETIME),
        max_handoffs=_number("HEATER_STOKER_MAX_HANDOFFS", DEFAULT_MAX_HANDOFFS),
        handoff_window=_number("HEATER_STOKER_HANDOFF_WINDOW", DEFAULT_HANDOFF_WINDOW),
        max_crashes=_number("HEATER_STOKER_MAX_CRASHES", DEFAULT_MAX_CRASHES),
    )


def state_dir() -> Path:
    """Where per-session marks live. Same base the context snapshot uses."""
    return Path(os.environ.get("HEATER_STATE_DIR") or Path.home() / ".heater")


def marker_path() -> Path:
    return state_dir() / MARKER_NAME


def child_token() -> str:
    """The identity the supervisor gave this session. Empty when nobody did.

    Empty means this session was not launched by a supervisor, so no supervisor
    is waiting on it and it has no business leaving a marker.
    """
    return os.environ.get(CHILD_ENV, "").strip()


def process_start(pid: int) -> str:
    """When that process started, as the system reports it. Empty when unknown.

    A pid on its own is not an identity. Numbers are handed out again, so a
    marker naming pid 812 can find some unrelated program wearing that number by
    the time anybody reads it. The moment the process started is what tells the
    two apart.
    """
    try:
        done = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)],
                              capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def own_owner() -> str:
    """This supervisor's identity, to be carried by the marker its session writes."""
    pid = os.getpid()
    return f"{pid} {process_start(pid)}"


def owner_identity() -> tuple[int | None, str]:
    """The supervisor this session was told was waiting on it, or nobody."""
    raw = os.environ.get(OWNER_ENV, "").strip()
    number, _, start = raw.partition(" ")
    try:
        return int(number), start.strip()
    except ValueError:
        return None, ""


def owner_alive(marker: dict[str, Any]) -> bool:
    """Is the supervisor this marker names still running?

    Both halves have to match. A pid that is alive but started at a different
    moment is a different program that inherited the number, and a marker naming
    no owner at all — an older one, or a truncated write — names nobody alive.
    """
    pid = marker.get("owner_pid")
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # Somebody else's process, so alive and not ours.
        pass
    except OSError:
        return False
    recorded = marker.get("owner_start")
    recorded = recorded.strip() if isinstance(recorded, str) else ""
    return process_start(pid) == recorded


def owner_named(marker: dict[str, Any]) -> bool:
    """Does the marker say which supervisor is waiting on it at all?"""
    pid = marker.get("owner_pid")
    return isinstance(pid, int) and pid > 0


def owner_note(marker: dict[str, Any]) -> dict[str, Any]:
    """What to log about a marker: whose it says it is."""
    token = marker.get("token")
    return {"marker_token": token if isinstance(token, str) and token else None,
            "owner_pid": marker.get("owner_pid"),
            "owner_start": marker.get("owner_start") or None}


# What the marker on disk is to this supervisor.
MINE = "mine"        # the session this supervisor is watching right now
OURS = "ours"        # one this supervisor launched earlier and never cleared
LIVE = "live"        # another supervisor's, and that supervisor is still running
STALE = "stale"      # nobody is waiting on it, so it is this supervisor's to remove


def marker_state(token: str = "") -> tuple[str | None, dict[str, Any]]:
    """Classify the marker on disk, and hand back what it says.

    None means there is no marker. Everything else is one of the four above, and
    only STALE and OURS may be removed: removing a marker a running supervisor
    is waiting on would answer for that supervisor, and leaving a stale one is
    what disabled the handoff forever.
    """
    marker = read_marker()
    if marker is None:
        return None, {}
    found = marker.get("token")
    found = found.strip() if isinstance(found, str) else ""
    if token and found == token:
        return MINE, marker
    if found and found in _issued:
        return OURS, marker
    if owner_alive(marker):
        return LIVE, marker
    return STALE, marker


def _create_marker(path: Path, payload: str) -> bool:
    """Write the marker, or fail because there already is one. Never overwrite.

    Looking first and writing afterwards leaves a gap two sessions can both walk
    through, and the second one through it overwrites the first. Creating the
    file exclusively closes the gap: the operating system decides which session
    got there first, and only one call can be told it did.
    """
    try:
        handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return False
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write(payload)
    return True


def mark_complete(when: str, token: str | None = None,
                  session: str | None = None) -> bool:
    """Say the handover is done and this session can end. Never raises.

    Returns True when this call is what wrote the marker. The token in it says
    which session is asking to be ended, and the owner says which supervisor is
    waiting on that session. A session with no token writes nothing: only the
    supervisor's own child can ask the supervisor for anything.

    A marker already there is somebody's turn, not this session's — unless
    nobody is waiting on it any more, in which case it is a leftover and this
    session takes the path.
    """
    token = (token if token is not None else child_token()).strip()
    if not token:
        return False
    pid, start = owner_identity()
    payload = json.dumps({"at": when, "token": token, "session": session or None,
                          "owner_pid": pid, "owner_start": start}) + "\n"
    try:
        path = marker_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            if _create_marker(path, payload):
                return True
            marker = read_marker()
            if marker is None:  # It went away between the write and the read.
                continue
            if marker.get("token") == token:
                return False  # Already this session's. Asking twice changes nothing.
            if not owner_named(marker) or owner_alive(marker):
                # Somebody's turn, not this session's. A marker that names no
                # owner is left for the supervisor to clear on its next launch,
                # where clearing it cannot be a race with the session writing it.
                return False
            log("stoker_stale_marker", {**owner_note(marker), "seen": "writing a mark"})
            clear_marker()
        return False
    except Exception:
        return False


def read_marker() -> dict[str, Any] | None:
    """The marker as written, or None when there is none or it is unreadable."""
    try:
        raw = marker_path().read_text(encoding="utf-8")
    except (OSError, ValueError):
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def marker_token() -> str | None:
    """Which session the marker on disk names. None when there is no marker."""
    marker = read_marker()
    if marker is None:
        return None
    value = marker.get("token")
    return value.strip() if isinstance(value, str) else ""


def clear_marker() -> None:
    """Remove the marker, and nothing else. The only file this program deletes."""
    try:
        marker_path().unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def reclaim_marker() -> None:
    """Clear a leftover marker nobody is waiting on, before opening a session.

    A marker this supervisor's own last session left behind would end the next
    one on its first poll, so it goes. One naming a supervisor that is still
    running is that supervisor's business and is left where it is. Anything else
    was left by a supervisor that is gone — the usual way being a machine that
    restarted mid-session — and leaving it would mean no session here could ever
    hand over again, because the one path stays taken forever.
    """
    state, marker = marker_state()
    if state is None:
        return
    if state == OURS:
        clear_marker()
        return
    if state == LIVE:
        log("stoker_foreign_marker", {**owner_note(marker), "seen": "before launch"})
        return
    log("stoker_stale_marker", {**owner_note(marker), "seen": "before launch"})
    clear_marker()


def session_name() -> str:
    return os.environ.get("HEATER_SESSION_NAME") or DEFAULT_SESSION_NAME


def command(extra: list[str] | None = None) -> list[str]:
    """The exact `claude` command line a launch runs.

    Remote Control is what lets the operator talk to the stoker from the app
    without the stoker giving up the machine it governs, and the name is what
    makes the session findable in the app's list.
    """
    return ["claude", "--remote-control", session_name(), *(extra or []), INITIAL_PROMPT]


# Every identity this supervisor has handed out. A marker carrying one of these
# is its own session's, left behind; a marker carrying anything else is not.
_issued: set[str] = set()


def new_token() -> str:
    """A fresh identity for one launch. Unguessable so no other session wears it."""
    token = secrets.token_hex(8)
    _issued.add(token)
    return token


def child_env(token: str | None = None) -> dict[str, str]:
    return {**os.environ, "HEATER_ROLE": "stoker",
            CHILD_ENV: token or os.environ.get(CHILD_ENV, ""),
            OWNER_ENV: own_owner()}


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
    """SIGINT gets no handler of its own: while a session is running it owns Ctrl-C.

    Python raises KeyboardInterrupt for SIGINT instead, and everywhere the
    supervisor is the one waiting — the grace, the pause, ending a session —
    that is caught and treated exactly like being killed. A handler is reset to
    the default on exec, so none of this changes what the session itself does
    with a signal.
    """
    try:
        signal.signal(signal.SIGTERM, _forward_stop)
        signal.signal(signal.SIGHUP, _forward_stop)
    except (ValueError, OSError):  # pragma: no cover - not the main thread
        pass


def _terminate(child: subprocess.Popen, kill_after: float) -> int:
    """End a session that has already handed over. SIGTERM, then SIGKILL.

    A Ctrl-C landing partway through is not a reason to walk away from a child
    that is still alive, so the wait is retried rather than abandoned; that is
    what keeps a stopped supervisor from leaving a session behind it.
    """
    try:
        child.terminate()
    except OSError:
        pass
    code = _wait_through_interrupts(child, kill_after)
    if code is not None:
        return code
    log("stoker_kill", {"pid": child.pid, "after_seconds": kill_after})
    try:
        child.kill()
    except OSError:
        pass
    code = _wait_through_interrupts(child, kill_after)
    if code is not None:
        return code
    return -signal.SIGKILL  # pragma: no cover - unkillable child


def _wait_through_interrupts(child: subprocess.Popen, seconds: float) -> int | None:
    """Wait up to `seconds` for the child, ignoring Ctrl-C. None means still alive."""
    deadline = time.monotonic() + seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return child.poll()
        try:
            return child.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            return child.poll()
        except KeyboardInterrupt:
            continue


def wait_unless_stopping(seconds: float) -> bool:
    """Wait, and stop waiting the moment the supervisor is told to stop.

    A bare sleep here is what let a `kill` during the pause between sessions be
    slept through and a fresh session opened over it. Returns True when the full
    wait elapsed, False when it was cut short.

    Ctrl-C during one of these waits is the operator stopping the stoker, and is
    treated exactly as a `kill` is. Nothing is waiting on the keyboard here: the
    session this wait belongs to has either already handed over or already
    ended, so there is no turn for the press to be cancelling.
    """
    global _stopping
    deadline = time.monotonic() + seconds
    while not _stopping:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return True
        try:
            time.sleep(min(STOP_CHECK, remaining))
        except KeyboardInterrupt:
            _stopping = True
            log("stoker_interrupted", {"waiting_seconds": round(seconds, 2)})
    return False


def watch(child: subprocess.Popen, poll: float, token: str, grace: float,
          kill_after: float) -> tuple[int, bool, bool]:
    """Wait for the session to end or to hand over.

    Only a marker naming this child is a handover. A marker naming a session
    another running supervisor started — the operator's own `claude` in this
    folder counts as the stoker too — is logged once and left where it is,
    because ending this session on it would end the wrong conversation. One
    nobody is waiting on is cleared out of the way.

    Returns (exit code, handed over, interrupted).
    """
    interrupted = False
    left_alone: set[str] = set()
    while True:
        # The marker is read before the exit is, because a session that hands
        # over and then ends inside one poll interval has still handed over.
        # Reading the exit first took that for the operator closing the session,
        # and with a clean exit the supervisor stopped instead of opening the
        # successor: the handoff quietly needed a person again.
        found = marker_token()
        if found is not None and found == token:
            clear_marker()
            log("handover_marker_seen", {"pid": child.pid, "grace_seconds": grace})
            # The Stop hook that wrote the marker has to return, and its closing
            # message has to reach the screen, before the session is ended.
            wait_unless_stopping(grace)
            return _terminate(child, kill_after), True, interrupted
        if found is not None and found not in left_alone and _judge_other_marker(token, child.pid):
            left_alone.add(found)
        code = child.poll()
        if code is not None:
            return code, False, interrupted
        try:
            time.sleep(poll)
        except KeyboardInterrupt:
            # Ctrl-C reached the whole foreground group, so the session got it
            # too and decides for itself what it means: in Claude Code one press
            # cancels the turn and two end the session. Killing the child here
            # would take the first press for the second. So this only remembers
            # that the operator is at the keyboard, and keeps watching.
            interrupted = True


def _judge_other_marker(token: str, pid: int) -> bool:
    """A marker that is not this session's. True when it was left where it is.

    Judging it costs a look at the process it names, so the caller remembers the
    answer rather than asking again on every poll for as long as the session runs.
    """
    state, marker = marker_state(token)
    if state is None or state == MINE:
        return False
    if state == LIVE:
        log("stoker_foreign_marker", {"pid": pid, **owner_note(marker)})
        return True
    log("stoker_stale_marker", {"pid": pid, **owner_note(marker)})
    clear_marker()
    return False


def is_crash(code: int) -> bool:
    """Did something outside this program shut the session down?

    A session ending on its own is the operator ending it, whatever code it
    ends with. So is Ctrl-C, and so is the plain terminate that a closing
    terminal sends to everything running in it. Anything else — a machine out of
    memory reaching for the session, a fault — killed a session that was still
    working, and that is not the operator saying stop.
    """
    return code < 0 and -code not in OPERATOR_SIGNALS


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


def churning_message(handoffs: int, allowed: float, window: float) -> str:
    minutes = max(1, int(round(window / 60)))
    return (
        f"bin/stoker.sh: the Claude session finished and was replaced {handoffs} times in the "
        f"last {minutes} minute(s), which is more than the {int(allowed)} this expects, so it "
        f"is not being restarted again. Nothing was lost, and nothing was deleted. A session "
        f"that finishes the moment it starts usually opened with nothing left to do: read "
        f"HANDOVER.md, then run bin/stoker.sh again when there is."
    )


def shutdown_message(crashes: int, allowed: float, window: float) -> str:
    minutes = max(1, int(round(window / 60)))
    return (
        f"bin/stoker.sh: the Claude session was shut down by the machine {crashes} times in "
        f"the last {minutes} minute(s), which is more than the {int(allowed)} this expects, so "
        f"it is not being restarted again. Nothing was lost, and nothing was deleted. "
        f"Something outside this program is closing the session down: a machine that has run "
        f"out of memory does exactly this. Run `claude` in this folder by hand and watch what "
        f"happens to it."
    )


def supervise(extra: list[str] | None = None,
              spawn: Callable[..., subprocess.Popen] = subprocess.Popen) -> int:
    """Run sessions until the operator stops one, or until launches stop working.

    Ctrl-C is the way the operator stops this, so it never reaches them as a
    traceback and never leaves a session running behind it.
    """
    bounds = limits()
    try:
        return _run_sessions(extra, spawn, bounds)
    except KeyboardInterrupt:
        return _stopped_by_interrupt(bounds.kill_after)


def _stopped_by_interrupt(kill_after: float) -> int:
    """Ctrl-C reached the supervisor itself. Stop, and take the session with it."""
    global _current, _stopping
    _stopping = True
    child, _current = _current, None
    code = 0
    if child is not None:
        code = child.poll()
        if code is None:
            code = _terminate(child, kill_after)
    log("stoker_exit", {"exit_code": code, "stopped": True, "interrupted": True})
    return exit_code(code)


def _run_sessions(extra: list[str] | None, spawn: Callable[..., subprocess.Popen],
                  bounds: Limits) -> int:
    global _current

    poll, grace = bounds.poll, bounds.grace
    kill_after, pause, minimum = bounds.kill_after, bounds.pause, bounds.minimum

    short = 0
    code = 0
    handoffs: list[float] = []
    shutdowns: list[float] = []
    while True:
        # Asked to stop is asked to stop, whether that arrived while a session
        # ran or during the pause between two of them.
        if _stopping:
            log("stoker_exit", {"exit_code": code, "stopped": True})
            return exit_code(code)

        # A marker left by this supervisor's own last session would kill the
        # next one on its first poll, and one left by a supervisor that is gone
        # would take the one path forever. A running supervisor's is left alone.
        reclaim_marker()

        token = new_token()
        line = command(extra)
        log("stoker_launch", {"command": line, "cwd": str(REPO)})
        started = time.monotonic()
        try:
            child = spawn(line, cwd=str(REPO), env=child_env(token))
        except (OSError, ValueError) as error:
            print(f"bin/stoker.sh: could not start Claude: {error}", file=sys.stderr)
            log("stoker_launch_failed", {"error": str(error)})
            return 127

        _current = child
        if _stopping:
            # The signal landed while this one was being spawned, so the handler
            # had nothing to aim at. Take it down here instead of watching it.
            code = _terminate(child, kill_after)
            _current = None
            log("stoker_exit", {"exit_code": code, "stopped": True})
            return exit_code(code)

        code, handed_over, interrupted = watch(child, poll, token, grace, kill_after)
        _current = None
        lifetime = time.monotonic() - started
        # A handover is a session doing its job, however fast it got there, so it
        # is never evidence that launching is broken. It is not evidence that
        # launching works either, so it leaves the tally where it found it.
        if not handed_over:
            short = short + 1 if lifetime < minimum else 0
        else:
            now = time.monotonic()
            handoffs = [t for t in handoffs if now - t < bounds.handoff_window] + [now]

        if _stopping:
            log("stoker_exit", {"exit_code": code, "stopped": True})
            return exit_code(code)

        if short >= MAX_SHORT_LAUNCHES:
            print(stalled_message(short), file=sys.stderr)
            log("stoker_stalled", {"launches": short, "exit_code": code})
            return exit_code(code) or 1

        # Handing over costs nothing to do, so a session that opens with nothing
        # to do can hand over again immediately, forever. This is the bound.
        if len(handoffs) > bounds.max_handoffs:
            print(churning_message(len(handoffs), bounds.max_handoffs,
                                   bounds.handoff_window), file=sys.stderr)
            log("stoker_churning", {"handoffs": len(handoffs),
                                    "allowed": bounds.max_handoffs,
                                    "window_seconds": bounds.handoff_window})
            return exit_code(code) or 1

        if handed_over:
            log("stoker_restart", {"exit_code": code, "seconds": round(lifetime, 1)})
            wait_unless_stopping(pause)
            continue

        # A session the machine shut down is not the operator stopping the
        # stoker, so it is opened again — but whatever did the shutting down can
        # do it again, and a session that lived long enough never trips the
        # stalled-launch rule above. This is the bound on that.
        if is_crash(code) and not interrupted:
            now = time.monotonic()
            shutdowns = [t for t in shutdowns if now - t < bounds.handoff_window] + [now]
            if len(shutdowns) > bounds.max_crashes:
                print(shutdown_message(len(shutdowns), bounds.max_crashes,
                                       bounds.handoff_window), file=sys.stderr)
                log("stoker_shutdowns", {"shutdowns": len(shutdowns),
                                         "allowed": bounds.max_crashes,
                                         "window_seconds": bounds.handoff_window,
                                         "exit_code": code})
                return exit_code(code) or 1
            log("stoker_relaunch_after_shutdown",
                {"exit_code": code, "seconds": round(lifetime, 1)})
            wait_unless_stopping(pause)
            continue

        if interrupted or code == 0 or lifetime >= minimum:
            log("stoker_exit", {"exit_code": code, "seconds": round(lifetime, 1),
                                "interrupted": interrupted})
            return exit_code(code)

        log("stoker_relaunch_after_failure",
            {"exit_code": code, "seconds": round(lifetime, 1)})
        wait_unless_stopping(pause)


def main(argv: list[str]) -> int:
    install_signal_handlers()
    try:
        return supervise(list(argv[1:]))
    except KeyboardInterrupt:  # pragma: no cover - a press during the stop itself
        # The last guard: pressing Ctrl-C is never answered with a page of
        # Python, whenever it lands.
        return 128 + int(signal.SIGINT)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
