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

import fcntl
import json
import os
import secrets
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, NamedTuple

REPO = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO / "hooks"))
sys.path.insert(0, str(REPO / "tools"))

try:  # Logging is never worth failing a launch over.
    from heater_hook import log as _log
except Exception:  # pragma: no cover - only when the hooks directory is gone
    def _log(event: str, payload: dict[str, Any]) -> None:
        return None

# The fleet queue: tools/queue.py, which stands ahead of the standard library's
# module of that name on the path above. It is where a warning outlives the
# screen, and never a reason to fail a launch. With the tools directory gone the
# standard library's queue answers to the name instead and has nothing to file
# with, and file_orphan_note treats that like any other failure to file: the
# import itself cannot fail, so guarding it would be guarding nothing.
import queue as fleet_queue


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

# Which session each supervisor here last started, kept beside the marker. A
# kill the supervisor cannot catch leaves that session running with nobody
# watching it, and the next run would open a second one in the same folder
# without a word. This file is how a later run can see the first one and say so.
#
# One entry per supervisor, keyed by that supervisor's own identity. A single
# entry meant the second supervisor in a folder wrote over the first's, which
# both hid a session left running and made the first's live session look like
# one — an operator told to `kill` a session somebody is working in.
CHILD_RECORD_NAME = "stoker-session"

# What a supervisor holds while it reads the record above and writes it back, so
# two that start in the same second cannot each erase the other's entry. A file
# of its own, because the record is replaced rather than written in place, and
# holding a file that is about to be replaced holds nothing.
CHILD_LOCK_NAME = "stoker-session.lock"

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

    The answer is two identities compared as plain text, so it has to be spelled
    the same way every time it is asked for. The system names the day in the
    language the terminal is set to — "Di" in one, "Tue" in another — and one
    supervisor reading another's start time in a different language would take a
    live supervisor for a dead one. Asking in a fixed language settles that.
    """
    try:
        done = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)],
                              capture_output=True, text=True, timeout=5,
                              env={**os.environ, "LC_ALL": "C", "LANG": "C"})
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def process_alive(pid: Any, start: Any) -> bool:
    """Is that exact process — that number, started at that moment — running?

    A start time nobody can read is not evidence of life. Without it all that is
    left is a number the system hands out again, so a mark naming one would read
    as a live supervisor's forever and no session here could hand over again.
    """
    if not isinstance(pid, int) or pid <= 0:
        return False
    recorded = start.strip() if isinstance(start, str) else ""
    if not recorded:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # Somebody else's process, so alive and not ours.
        pass
    except OSError:
        return False
    return process_start(pid) == recorded


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
    """Is the supervisor this mark — or this session record — names still running?

    Both halves have to match. A pid that is alive but started at a different
    moment is a different program that inherited the number, and a marker naming
    no owner at all — an older one, or a truncated write — names nobody alive.
    """
    return process_alive(marker.get("owner_pid"), marker.get("owner_start"))


def supervisor_alive() -> bool:
    """Is the supervisor that launched this session still running?

    Only that supervisor can end this session, so it is what the Stop hook asks
    before promising the session is ending. A session that outlived the program
    watching it is on its own, and its mark would sit on the one path with
    nobody to act on it, blocking the next session's handover as well.
    """
    pid, start = owner_identity()
    return process_alive(pid, start)


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


def child_record_path() -> Path:
    return state_dir() / CHILD_RECORD_NAME


def child_lock_path() -> Path:
    return state_dir() / CHILD_LOCK_NAME


@contextmanager
def hold_records() -> Iterator[None]:
    """Hold the session note for as long as it takes to read it and write it back.

    Reading it, changing a copy and writing the copy back is three steps, and two
    supervisors starting in the same second interleave them: both read, both
    change their own copy, and the one that writes second erases the other's
    entry. The entry erased is the whole record of a session left running.

    A separate file is what is held, because the note itself is replaced rather
    than written in place and a hold on a file that is about to be replaced
    holds nothing. Failing to take the hold is not a reason to refuse a launch:
    this is a note, not the work, and a lost entry beats no session at all.
    """
    handle: int | None = None
    try:
        path = child_lock_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
        fcntl.flock(handle, fcntl.LOCK_EX)
    except OSError:
        if handle is not None:
            os.close(handle)
            handle = None
    try:
        yield
    finally:
        if handle is not None:
            try:
                fcntl.flock(handle, fcntl.LOCK_UN)
            except OSError:  # pragma: no cover - the hold went with the file
                pass
            os.close(handle)


def record_child(pid: int, token: str) -> None:
    """Write down which session this supervisor just started. Never raises.

    The supervisor holds this in memory as well, and memory is what a kill takes
    away. What is on disk is all a later run has to go on.

    This supervisor writes its own entry and leaves every other supervisor's
    where it is, except the ones whose session has ended: those are nothing to
    anybody, and dropping them as they are passed is what keeps the file to the
    handful of sessions actually still running.
    """
    started = process_start(os.getpid())
    entry = {"pid": pid, "start": process_start(pid), "token": token,
             "owner_pid": os.getpid(), "owner_start": started}
    # Both start times are read before the hold is taken: asking the system when
    # a process started is the slowest thing here, and every moment spent
    # holding the note is a moment another supervisor waits for it.
    with hold_records():
        records = {key: kept for key, kept in read_child_records().items()
                   if child_alive(kept)}
        records[f"{os.getpid()} {started}"] = entry
        write_child_records(records)


def write_child_records(records: dict[str, Any]) -> None:
    """Put the sessions back on disk. Never raises: this is a note, not the work.

    Written beside the note and moved onto it, rather than into it. Writing into
    it empties the file first, so a reader arriving in the middle of the write
    gets a fragment, and a fragment reads as no sessions at all — the session
    left running vanishes from the note, which is the one thing it is for. The
    move puts the whole file in place in one step or not at all.
    """
    path = child_record_path()
    spare = path.with_name(f".{path.name}.{secrets.token_hex(4)}")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        spare.write_text(json.dumps(records) + "\n", encoding="utf-8")
        os.replace(spare, path)
    except OSError:
        try:
            spare.unlink()
        except OSError:  # pragma: no cover - it was never written
            pass


def read_child_records() -> dict[str, Any]:
    """Every session a supervisor started here, as far as disk knows.

    Keyed by the identity of the supervisor that started it. Anything in the
    file that is not a session is skipped rather than raising, because a file
    somebody edited by hand is not a reason to refuse to open a session.
    """
    try:
        parsed = json.loads(child_record_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {key: entry for key, entry in parsed.items() if isinstance(entry, dict)}


def child_alive(entry: dict[str, Any]) -> bool:
    """Is the session in this entry — that number, started at that moment — running?"""
    return process_alive(entry.get("pid"), entry.get("start"))


def keep_unended(pid: int) -> dict[str, Any]:
    """Keep a session that would not end where the next run can still find it.

    Under this supervisor's own key the next launch writes straight over it, and
    after one launch nothing knows about the session any more — which is exactly
    when nobody has read the warning yet. So it is kept under a key of its own,
    and marked as one nobody is watching: this supervisor has stopped trying to
    end it, so nothing is waiting on it whether or not the supervisor runs on.
    """
    started = process_start(os.getpid())
    start = process_start(pid)
    with hold_records():
        records = read_child_records()
        entry = {**records.get(f"{os.getpid()} {started}", {}),
                 "pid": pid, "start": start, "owner_pid": os.getpid(),
                 "owner_start": started, "unwatched": True}
        records[f"{os.getpid()} {started} left {pid}"] = entry
        write_child_records(records)
    return entry


def orphan_sessions() -> list[dict[str, Any]]:
    """Sessions still running here that nothing is watching. Empty normally.

    Normally there are none: a supervisor ends its session before opening the
    next one, so the process in its entry is gone by the time anybody asks.

    The session has to still be running, and nothing can be waiting on it. That
    second half is either the supervisor that started it being gone, or that
    supervisor having given up on ending it and said so in the entry. A session
    whose supervisor is still watching it is that supervisor doing its job,
    however much it looks like a leftover from here — naming it would send the
    operator to close a session somebody is working in.

    What happened to the supervisor is not something this can see. `kill -9`, a
    fault, and a machine that went down all leave exactly this behind.
    """
    return [entry for entry in read_child_records().values()
            if child_alive(entry) and (entry.get("unwatched") or not owner_alive(entry))]


def claim_orphan_report(entry: dict[str, Any], reported: bool = True) -> bool:
    """Take the one queue item this session gets. True when this call took it.

    Taken before the item is written rather than after, because two supervisors
    that both read "not filed yet" in the same moment both go on to file one,
    and the stoker is woken twice about one session. Only one call can be told
    it took it, so only one files anything.

    Handing it back — reported False — is what a write that failed does, so the
    next launch files it instead of the item being lost for good.
    """
    with hold_records():
        records = read_child_records()
        matching = [candidate for candidate in records.values()
                    if candidate.get("pid") == entry.get("pid")
                    and candidate.get("start") == entry.get("start")]
        if not matching or any(bool(c.get("reported")) for c in matching) == reported:
            return False
        for candidate in matching:
            candidate["reported"] = reported
        write_child_records(records)
        return True


def file_orphan_note(pid: int) -> bool:
    """Put the warning where the screen cannot lose it. True when it landed.

    stderr is read by whoever is watching at that second, and a fresh session
    opens on top of it and paints its own display over the lot. The fleet queue
    is the other half: the next session is woken with it, and bin/bearings.py
    reports it for as long as the session is still running.
    """
    try:
        fleet_queue.add("failure", orphan_message(pid), project="heater",
                        urgency="high", origin="stoker.sh")
        return True
    except Exception:
        return False


def announce_orphan(entry: dict[str, Any]) -> None:
    """Say, in all three places, that a session here was left running."""
    pid = entry.get("pid")
    if not isinstance(pid, int):  # pragma: no cover - a session with no number
        return
    print(orphan_message(pid), file=sys.stderr)
    log("stoker_orphan_session", {"pid": pid, "owner_pid": entry.get("owner_pid")})
    if claim_orphan_report(entry) and not file_orphan_note(pid):
        claim_orphan_report(entry, reported=False)


def orphan_message(pid: int) -> str:
    return (
        f"bin/stoker.sh: the Claude session that was running here last is still going, and the "
        f"program that was watching it is not running any more, so nothing is watching it now. A "
        f"fresh session is being opened, so two of them will be working this folder at once and "
        f"they will undo each other's changes. Close the old one: find its window and quit it, or "
        f"run `kill {pid}` in a terminal."
    )


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


def end_session(child: subprocess.Popen, kill_after: float) -> int:
    """End the session, and say so out loud when it will not end.

    A session still running after both signals is about to be joined by a fresh
    one in the same folder, and two of them undo each other's work. That is the
    same trouble as a session a killed supervisor left behind, so it is said in
    the same three places: on the screen, in the log, and as one item the next
    session is woken with. Taking it for a session that finished is what let a
    second one open on top of it without a word.
    """
    code, ended = _terminate(child, kill_after)
    if not ended:
        announce_orphan(keep_unended(child.pid))
    return code


def _terminate(child: subprocess.Popen, kill_after: float) -> tuple[int, bool]:
    """End a session that has already handed over. SIGTERM, then SIGKILL.

    Returns how it ended, and whether it ended at all. The second half is the
    part a caller cannot work out for itself: a session that took both signals
    and kept running reports the same code as one the second signal ended.

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
        return code, True
    log("stoker_kill", {"pid": child.pid, "after_seconds": kill_after})
    try:
        child.kill()
    except OSError:
        pass
    code = _wait_through_interrupts(child, kill_after)
    if code is not None:
        return code, True
    return -signal.SIGKILL, False


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
            return end_session(child, kill_after), True, interrupted
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
            code = end_session(child, kill_after)
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

        # A session still running with nobody watching it is about to be joined
        # by a second one in the same folder. Opening it anyway is right — this
        # is how the stoker comes back after a crash — but it is never right to
        # do it silently, because the two will undo each other's work. A session
        # another supervisor is watching is not one of these and is never named.
        for orphan in orphan_sessions():
            announce_orphan(orphan)

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
        # Written down before anything else happens to it: a kill that lands on
        # this supervisor takes every memory of the session with it, and what is
        # on disk is the only way a later run can see the session left behind.
        record_child(child.pid, token)
        if _stopping:
            # The signal landed while this one was being spawned, so the handler
            # had nothing to aim at. Take it down here instead of watching it.
            code = end_session(child, kill_after)
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
