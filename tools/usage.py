#!/usr/bin/env python3
"""How much of the plan's usage is spent, and what that still allows.

The subscription meters two rolling windows: a five-hour one that refills
several times a day, and a seven-day one that does not. Running the seven-day
window dry stops everything until it resets, so it is the one that governs here
and the five-hour one is only a brake on a burst.

Where the number comes from
---------------------------
Claude Code hands the status-line command a JSON payload on stdin. On a
Claude.ai Pro or Max subscription that payload carries `rate_limits`:

    rate_limits.five_hour.used_percentage    0 to 100
    rate_limits.five_hour.resets_at          Unix epoch seconds
    rate_limits.seven_day.used_percentage    0 to 100
    rate_limits.seven_day.resets_at          Unix epoch seconds

It is absent on API-key auth, and absent until the first API response of a
session. Nothing else on the machine reports the plan's windows without the
account's own credential, and `/usage` is interactive, so the status line is the
only source. `hooks/statusline.py` writes what it is told to `usage.json` in the
state directory, and everything here reads that file.

The bands
---------
`THRESHOLDS` below holds every band and the percentage on each window that
triggers it, tightest first, and `ALLOWS` holds the one plain-words line each
band says about what may still be started, which `allows()` fills in with the
figures that move. Those two are the definition; this docstring deliberately
does not restate them, because a paraphrase that drifts from the code is worse
than no paraphrase at all.

Weekly leads, because the weekly window is the one that runs out. The tightest
band stops the fleet: every agent still running is stopped there rather than
left to finish, and the operator is sent an account of what the whole window
bought (`bin/debrief.py`). Opinion 13 carries the operator's words for that.

OPEN is not a licence to ignore the number: the percentages are printed at every
band so that judgment about what is worth spending can tighten as they climb.

Every threshold moves with an environment variable, named for its band and its
window: HEATER_TAPER_NOTHING_NEW_SEVEN_DAY, HEATER_TAPER_TOP_OF_LIST_FIVE_HOUR,
and so on. How many agents the middle band leaves out at once moves the same
way, with HEATER_TAPER_TOP_OF_LIST_AGENTS, which is a count and not a
percentage. A value that is not a number is ignored in favour of the default.

A missing reading reads as OPEN. A taper that halts the fleet because a file was
never written would be a fleet halt caused by the guard against one.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NOTHING_NEW = "NOTHING_NEW"
REVIEWS_AND_LANDINGS_ONLY = "REVIEWS_AND_LANDINGS_ONLY"
TOP_OF_LIST_ONLY = "TOP_OF_LIST_ONLY"
OPEN = "OPEN"

# --- the constants block --------------------------------------------------
# One entry per band, tightest first: (seven-day %, five-hour %, env prefix).
# Crossing either percentage puts the fleet in that band. The five-hour stop sits
# at 95, level with the weekly one, because opinion 13 quotes the operator naming
# that figure as where the agents stop and the debrief is written.
THRESHOLDS: tuple[tuple[str, float, float, str], ...] = (
    (NOTHING_NEW, 95.0, 95.0, "HEATER_TAPER_NOTHING_NEW"),
    (REVIEWS_AND_LANDINGS_ONLY, 85.0, 93.0, "HEATER_TAPER_REVIEWS_ONLY"),
    (TOP_OF_LIST_ONLY, 75.0, 85.0, "HEATER_TAPER_TOP_OF_LIST"),
)

# A reading older than this is not evidence of anything. The status line
# re-renders on every assistant message, so a live session refreshes it
# constantly; six hours of silence outlasts a whole five-hour window.
STALE_HOURS = 6.0

# How many agents the middle band leaves out at once, and the variable that
# moves it: HEATER_TAPER_TOP_OF_LIST_AGENTS. Not a standing cap, which opinion
# 11 refuses; it applies only inside TOP_OF_LIST_ONLY.
TOP_OF_LIST_AGENTS = 3
TOP_OF_LIST_AGENTS_VAR = "HEATER_TAPER_TOP_OF_LIST_AGENTS"

ALLOWS = {
    NOTHING_NEW:
        "Stop every agent that is still running, then write the account of what the window "
        "bought and send it to the operator with bin/debrief.py --hours 5 --queue, "
        "then hand over. Start nothing.",
    REVIEWS_AND_LANDINGS_ONLY:
        "Only rounds that close a change already in flight. No new research, no new features. "
        "Stop the lowest-priority agents still running rather than letting them run on.",
    TOP_OF_LIST_ONLY:
        "Only the top task on the list and rounds already in flight, "
        "at most {agents} agents out at once; stop the least important first.",
    OPEN: "Dispatch whatever the task list justifies.",
}

SECONDS_PER_DAY = 86400.0


# --- where the reading lives ----------------------------------------------

def snapshot_path() -> Path:
    """Same state-directory convention as context.json, one file along."""
    base = os.environ.get("HEATER_STATE_DIR") or Path.home() / ".heater"
    return Path(base) / "usage.json"


def read() -> dict[str, Any]:
    """Nothing known, for every shape of broken file there is.

    A file whose bytes are not text is as unreadable as a missing one and no
    more alarming, and every reader downstream already says "present but
    unreadable" in plain words. Letting that one case raise instead took
    `bin/bearings.py` down with it and printed no report at all.
    """
    try:
        parsed = json.loads(snapshot_path().read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def write(reading: dict[str, Any]) -> None:
    """Never raises: a status line that crashes is worse than one that is stale."""
    try:
        path = snapshot_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(reading) + "\n", encoding="utf-8")
    except Exception:
        pass


def _window(source: Any) -> dict[str, Any] | None:
    """One window's two fields, or None when the payload does not carry it."""
    if not isinstance(source, dict):
        return None
    used = source.get("used_percentage")
    if not isinstance(used, (int, float)) or isinstance(used, bool):
        return None
    resets = source.get("resets_at")
    return {"used_percentage": float(used),
            "resets_at": resets if isinstance(resets, (int, float)) and not isinstance(resets, bool) else None}


def record(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Store the windows a status-line payload carried. None when it carried none.

    A payload without `rate_limits` leaves the last reading alone rather than
    overwriting it with nothing: an API-key session or a first render before the
    first API response must not erase what a subscriber session already knew.
    """
    try:
        limits = payload.get("rate_limits")
        if not isinstance(limits, dict):
            return None
        five, seven = _window(limits.get("five_hour")), _window(limits.get("seven_day"))
        if five is None and seven is None:
            return None
        reading = {"five_hour": five, "seven_day": seven,
                   "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        write(reading)
        return reading
    except Exception:
        return None


# --- reading it -----------------------------------------------------------

def _number(name: str, fallback: float) -> float:
    try:
        return float(os.environ.get(name) or fallback)
    except ValueError:
        return fallback


def thresholds() -> list[tuple[str, float, float]]:
    """The bands with any environment overrides applied, tightest first."""
    return [(name, _number(f"{prefix}_SEVEN_DAY", seven), _number(f"{prefix}_FIVE_HOUR", five))
            for name, seven, five, prefix in THRESHOLDS]


def percentage(reading: dict[str, Any] | None, window: str) -> float | None:
    source = (reading or {}).get(window)
    if not isinstance(source, dict):
        return None
    value = source.get("used_percentage")
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def resets_at(reading: dict[str, Any] | None, window: str) -> datetime | None:
    source = (reading or {}).get(window)
    if not isinstance(source, dict):
        return None
    value = source.get("resets_at")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        return datetime.fromtimestamp(float(value), timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def band(reading: dict[str, Any] | None = None) -> str:
    """The tightest band either window has reached. OPEN when nothing is known."""
    reading = read() if reading is None else reading
    seven, five = percentage(reading, "seven_day"), percentage(reading, "five_hour")
    for name, seven_at, five_at in thresholds():
        if (seven is not None and seven >= seven_at) or (five is not None and five >= five_at):
            return name
    return OPEN


def top_of_list_agents() -> int:
    """How many agents the middle band leaves out, with any override applied."""
    return max(1, int(_number(TOP_OF_LIST_AGENTS_VAR, TOP_OF_LIST_AGENTS)))


def allows(name: str) -> str:
    """One plain-words line saying what the band permits."""
    line = ALLOWS.get(name, ALLOWS[OPEN])
    return line.format(agents=top_of_list_agents()) if "{agents}" in line else line


def recorded_at(reading: dict[str, Any] | None = None) -> datetime | None:
    stamp = (read() if reading is None else reading).get("recorded_at")
    if not isinstance(stamp, str):
        return None
    try:
        parsed = datetime.fromisoformat(stamp)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def age_hours(reading: dict[str, Any] | None = None, now: datetime | None = None) -> float | None:
    when = recorded_at(reading)
    if when is None:
        return None
    return ((now or datetime.now(timezone.utc)) - when).total_seconds() / 3600


def days_left(reading: dict[str, Any] | None = None, now: datetime | None = None) -> float | None:
    """Days until the weekly window resets. None when the reading does not say."""
    when = resets_at(read() if reading is None else reading, "seven_day")
    if when is None:
        return None
    return max(0.0, (when - (now or datetime.now(timezone.utc))).total_seconds() / SECONDS_PER_DAY)


def missing(reading: dict[str, Any] | None = None) -> bool:
    reading = read() if reading is None else reading
    return percentage(reading, "seven_day") is None and percentage(reading, "five_hour") is None


def stale(reading: dict[str, Any] | None = None, now: datetime | None = None) -> bool:
    age = age_hours(read() if reading is None else reading, now)
    return age is None or age > STALE_HOURS


# --- saying it ------------------------------------------------------------

def _age_words(age: float | None) -> str:
    if age is None:
        return "age unknown"
    if age * 60 < 1:
        return "read just now"
    if age < 1:
        return f"read {age * 60:.0f} minutes ago"
    return f"read {age:.1f} hours ago"


def _clock(when: datetime | None) -> str:
    """When the window starts again, or nothing at all.

    A reading that carries a percentage without a reset time is common, and
    "resets reset time unknown" is the machinery talking to itself, so the
    clause is dropped rather than filled in with an apology.
    """
    return f", resets {when.astimezone().strftime('%a %d %b %H:%M %Z')}" if when else ""


def _time_left(days: float | None) -> str:
    """How long the week has left to run, written the way a person would say it."""
    if days is None:
        return ""
    if days < 1:
        hours = days * 24
        return ", less than an hour left" if hours < 1 else f", about {hours:.0f} hours left"
    return ", about a day left" if round(days) == 1 else f", about {days:.0f} days left"


def _window_line(reading: dict[str, Any], window: str, label: str, tail: str = "") -> str:
    """One window, or a plain sentence saying why it carries no figure.

    A window with no figure beside a window that has one is what Claude Code
    sends after that window has reset, so it is reported as a fresh window
    rather than as a gap in the reading.
    """
    used = percentage(reading, window)
    if used is None:
        return (f"  {label}: no figure given, which is what arrives once that window has "
                "reset; treat it as freshly reset with nothing used")
    return f"  {label}: {used:.0f}% used{_clock(resets_at(reading, window))}{tail}"


def lines(reading: dict[str, Any] | None = None, now: datetime | None = None) -> list[str]:
    """What bearings prints: both windows, what may be started, and the band's name."""
    reading = read() if reading is None else reading
    current = band(reading)
    age = age_hours(reading, now)

    if missing(reading):
        path = snapshot_path()
        where = (f"  {path} is present but unreadable, so it says nothing about the plan"
                 if path.exists() else
                 f"  nothing has written {path} yet")
        return [
            "  no usage reading",
            f"{where}; the status line writes it on its next render in an "
            "interactive session on a Pro or Max plan",
            f"  nothing is known about how much of the plan is spent, so nothing is held "
            f"back: {allows(current)} (that state is called the {current} band)",
        ]

    out = [
        _window_line(reading, "seven_day", "last 7 days", _time_left(days_left(reading, now))),
        _window_line(reading, "five_hour", "last 5 hours"),
        f"  what may be started now: {allows(current)} "
        f"({_age_words(age)}; that state is called the {current} band)",
    ]
    if stale(reading, now):
        out.append(f"  {_age_words(age)} — older than {STALE_HOURS:.0f} hours, "
                   "so treat it as a guess until it refreshes" if age is not None else
                   "  this reading does not say when it was taken, "
                   "so treat it as a guess until it refreshes")
    return out


def wake_line(reading: dict[str, Any] | None = None) -> str:
    """One line for the top of a wake summary, empty while the band is OPEN."""
    reading = read() if reading is None else reading
    current = band(reading)
    if current == OPEN:
        return ""
    seven, five = percentage(reading, "seven_day"), percentage(reading, "five_hour")
    figures = ", ".join(part for part in (
        f"weekly {seven:.0f}%" if seven is not None else "",
        f"5-hour {five:.0f}%" if five is not None else "",
    ) if part)
    return f"Usage band {current} ({figures}). {allows(current)}"
