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
Weekly first, because the weekly window is the one that runs out:

    NOTHING_NEW                seven_day >= 95% or five_hour >= 98%
        Finish what is in flight and hand over. Start nothing.
    REVIEWS_AND_LANDINGS_ONLY  seven_day >= 85% or five_hour >= 93%
        Only rounds that close a change already in flight. No new research and
        no new features.
    TOP_OF_LIST_ONLY           seven_day >= 75% or five_hour >= 85%
        The top task on the list, plus rounds already in flight, with at most
        three agents out at once.
    OPEN                       below all of those
        Whatever the task list justifies.

OPEN is not a licence to ignore the number: the percentages are printed at every
band so that judgment about what is worth spending can tighten as they climb.

Every threshold moves with an environment variable, named for its band and its
window: HEATER_TAPER_NOTHING_NEW_SEVEN_DAY, HEATER_TAPER_TOP_OF_LIST_FIVE_HOUR,
and so on. A value that is not a number is ignored in favour of the default.

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
# Crossing either percentage puts the fleet in that band.
THRESHOLDS: tuple[tuple[str, float, float, str], ...] = (
    (NOTHING_NEW, 95.0, 98.0, "HEATER_TAPER_NOTHING_NEW"),
    (REVIEWS_AND_LANDINGS_ONLY, 85.0, 93.0, "HEATER_TAPER_REVIEWS_ONLY"),
    (TOP_OF_LIST_ONLY, 75.0, 85.0, "HEATER_TAPER_TOP_OF_LIST"),
)

# A reading older than this is not evidence of anything. The status line
# re-renders on every assistant message, so a live session refreshes it
# constantly; six hours of silence outlasts a whole five-hour window.
STALE_HOURS = 6.0

# How many agents the middle band leaves out at once. Not a standing cap:
# opinion 11 refuses one of those. It applies only inside TOP_OF_LIST_ONLY.
TOP_OF_LIST_AGENTS = 3

ALLOWS = {
    NOTHING_NEW: "Start nothing. Finish what is already out, then hand over.",
    REVIEWS_AND_LANDINGS_ONLY:
        "Only rounds that close a change already in flight. No new research, no new features.",
    TOP_OF_LIST_ONLY:
        f"Only the top task on the list and rounds already in flight, "
        f"at most {TOP_OF_LIST_AGENTS} agents out at once.",
    OPEN: "Dispatch whatever the task list justifies.",
}

SECONDS_PER_DAY = 86400.0


# --- where the reading lives ----------------------------------------------

def snapshot_path() -> Path:
    """Same state-directory convention as context.json, one file along."""
    base = os.environ.get("HEATER_STATE_DIR") or Path.home() / ".heater"
    return Path(base) / "usage.json"


def read() -> dict[str, Any]:
    try:
        parsed = json.loads(snapshot_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
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


def allows(name: str) -> str:
    """One plain-words line saying what the band permits."""
    return ALLOWS.get(name, ALLOWS[OPEN])


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
    if age < 1:
        return f"read {age * 60:.0f} minutes ago"
    return f"read {age:.1f} hours ago"


def _clock(when: datetime | None) -> str:
    return when.astimezone().strftime("%a %d %b %H:%M %Z") if when else "reset time unknown"


def lines(reading: dict[str, Any] | None = None, now: datetime | None = None) -> list[str]:
    """What bearings prints: both windows, the band, and what the band allows."""
    reading = read() if reading is None else reading
    current = band(reading)
    age = age_hours(reading, now)

    if missing(reading):
        return [
            "  no usage reading",
            f"  nothing has written {snapshot_path()} yet; the status line writes it "
            "on its next render in an interactive session on a Pro or Max plan",
            f"  band: {current} (unknown) — {allows(current)}",
        ]

    out = []
    seven, five = percentage(reading, "seven_day"), percentage(reading, "five_hour")
    left = days_left(reading, now)
    remaining = f", {left:.1f} day(s) left" if left is not None else ""
    out.append(f"  weekly (7 day): {seven:.0f}% used, resets {_clock(resets_at(reading, 'seven_day'))}{remaining}"
               if seven is not None else "  weekly (7 day): not reported")
    out.append(f"  session (5 hour): {five:.0f}% used, resets {_clock(resets_at(reading, 'five_hour'))}"
               if five is not None else "  session (5 hour): not reported")
    out.append(f"  band: {current} ({_age_words(age)}) — {allows(current)}")
    if stale(reading, now):
        out.append(f"  reading is older than {STALE_HOURS:.0f} hours; treat it as a guess until it refreshes")
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
