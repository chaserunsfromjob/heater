#!/usr/bin/env python3
"""What the agents did over the last few hours, written for the operator.

At the point where the plan's five-hour window is nearly spent, the fleet stops
and the operator is owed an account of what the window bought. This writes that
account: one page of plain sentences saying what each agent was sent to do, what
came back, what the checks found, what is still running, and what it cost.

Everything here is read from what the agents recorded while they worked -- the
job records, the check records, the workspace records and the notes queue -- so
no number in it is remembered rather than looked up.

It is written for someone who does not program. Identifiers, file paths and
branch names are left out unless the reader would have to go there, and a thing
is described by what it does before it is named.

    bin/debrief.py --hours 5
    bin/debrief.py --hours 5 --queue
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dispatch
import jsonstore
import queue
import store
import worktrees

DEFAULT_HOURS = 5.0
WIDTH = 78

# What each ending means, said the way it would be said out loud.
OUTCOME_WORDS = {
    "landed": "finished, and the work is now part of the project",
    "pushed": "finished, and the work is saved on its own copy, waiting to be merged in",
    "escalated": "stopped partway and asked for a decision",
    "failed": "could not finish",
    "abandoned": "was called off",
}

# What kind of agent it was, by what it was there to do.
AGENT_WORDS = {
    "worker": "to build something",
    "reviewer": "to check someone else's work",
    "fixer": "to apply the corrections a check asked for",
}

# What each note in the queue is, by what it is for.
KIND_WORDS = {
    "finding": "something an agent noticed in passing and wrote down",
    "escalation": "a decision an agent needs from you",
    "report": "an account an agent wrote for you",
    "failure": "something that went wrong",
}


# --- reading the stores ---------------------------------------------------

def _moment(stamp: Any) -> datetime | None:
    if not isinstance(stamp, str):
        return None
    try:
        parsed = datetime.fromisoformat(stamp)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def since(hours: float, now: datetime | None = None) -> datetime:
    return (now or datetime.now(timezone.utc)) - timedelta(hours=hours)


def _started_or_ended_since(record: dict[str, Any], cutoff: datetime) -> bool:
    """In the window if it began in it, ended in it, or has not ended at all.

    A job that is still running belongs in the account whatever hour it started,
    because the account is written at the moment those jobs are stopped.
    """
    if not record.get("closed_at"):
        return True
    began, ended = _moment(record.get("created")), _moment(record.get("closed_at"))
    return bool((began and began >= cutoff) or (ended and ended >= cutoff))


def gather(hours: float = DEFAULT_HOURS, now: datetime | None = None) -> dict[str, Any]:
    """Every record the account draws on, already narrowed to the window."""
    cutoff = since(hours, now)

    jobs = [d for d in jsonstore.load(dispatch.dispatches_dir())
            if _started_or_ended_since(d, cutoff)]
    jobs.sort(key=lambda d: d.get("created", ""))

    checks = [r for r in jsonstore.load(store.reviews_dir())
              if (when := _moment(r.get("created"))) and when >= cutoff]
    by_change: dict[str, list[dict[str, Any]]] = {}
    for round_record in checks:
        by_change.setdefault(round_record.get("change", ""), []).append(round_record)
    for rounds in by_change.values():
        rounds.sort(key=lambda r: r.get("round", 0))

    notes = [i for i in jsonstore.load(queue.queue_dir())
             if (when := _moment(i.get("created"))) and when >= cutoff]

    workspaces = [l for l in jsonstore.load(worktrees.leases_dir())
                  if not l.get("released_at")
                  or ((when := _moment(l.get("created"))) and when >= cutoff)]

    return {"at": now or datetime.now(timezone.utc), "hours": hours, "cutoff": cutoff,
            "jobs": jobs, "checks": checks, "checks_by_change": by_change,
            "notes": notes, "workspaces": workspaces}


# --- saying it ------------------------------------------------------------

def _ago(when: datetime | None, now: datetime) -> str:
    if when is None:
        return "at a time it did not record"
    minutes = max(0.0, (now - when).total_seconds() / 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes:.0f} minutes ago"
    hours, rest = divmod(round(minutes), 60)
    stem = "1 hour" if hours == 1 else f"{hours} hours"
    return f"{stem} ago" if rest == 0 else f"{stem} {rest} minutes ago"


def _first_sentence(text: str, limit: int = 220) -> str:
    """The opening of the brief, which is the part that says what it was for."""
    flat = " ".join((text or "").split())
    if not flat:
        return "no task was recorded"
    head = flat.split(". ")[0].rstrip(".")
    if len(head) > limit:
        head = head[:limit].rsplit(" ", 1)[0] + "..."
    return head


def _wrap(text: str, indent: str = "   ") -> str:
    return textwrap.fill(text, width=WIDTH, initial_indent=indent, subsequent_indent=indent)


def _money(total: float | None) -> str:
    return "not recorded" if total is None else f"${total:,.2f}"


def _checks_sentence(rounds: list[dict[str, Any]]) -> str:
    """How many times the work was checked, and how the last check went."""
    if not rounds:
        return "It has not been checked over yet."
    last = rounds[-1]
    count = ("Checked over once" if len(rounds) == 1
             else f"Checked over {len(rounds)} times")
    if last.get("verdict") == "pass":
        return f"{count}, and the last check passed it."
    found = last.get("findings") or 0
    if not found:
        return f"{count}, and the last check sent it back for changes."
    thing = "one thing" if found == 1 else f"{found} things"
    return f"{count}, and the last check sent it back with {thing} to put right."


def _job_lines(record: dict[str, Any], rounds: list[dict[str, Any]], now: datetime) -> list[str]:
    out = [_wrap(_first_sentence(record.get("task", "")), indent="   ")]
    purpose = AGENT_WORDS.get(record.get("agent", ""), "")
    began = _ago(_moment(record.get("created")), now)
    out.append(_wrap(f"Sent out {began}" + (f", {purpose}." if purpose else ".")))

    if record.get("closed_at"):
        ending = OUTCOME_WORDS.get(record.get("outcome") or "", "ended in a way nobody recorded")
        finished = _ago(_moment(record["closed_at"]), now)
        note = f" It said: {record['note']}" if record.get("note") else ""
        out.append(_wrap(f"It {ending}, {finished}.{note}"))
    else:
        out.append(_wrap("Still running: nothing has come back from it yet."))

    out.append(_wrap(_checks_sentence(rounds)))
    costs = [r["cost_usd"] for r in rounds if isinstance(r.get("cost_usd"), (int, float))]
    if costs:
        out.append(_wrap(f"Checking it cost {_money(sum(costs))} so far."))
    return out


def render(data: dict[str, Any]) -> str:
    now, hours = data["at"], data["hours"]
    jobs, notes = data["jobs"], data["notes"]
    span = "5 hours" if abs(hours - 5.0) < 0.01 else f"{hours:g} hours"

    head = [f"What the agents did in the last {span}",
            f"Written {now.astimezone().strftime('%a %d %b %Y, %H:%M %Z')}.",
            "",
            _wrap("Every line below is read back from what the agents wrote down as "
                  "they worked, so none of it is anybody's recollection.", indent="")]

    if not jobs and not data["checks"] and not notes:
        return "\n".join(head + [
            "",
            _wrap(f"Nothing happened in the last {span}: no agent was sent out, "
                  "nothing was checked over, and no agent left you a note.", indent=""),
        ])

    running = [j for j in jobs if not j.get("closed_at")]
    done = [j for j in jobs if j.get("closed_at")]
    landed = [j for j in done if j.get("outcome") == "landed"]

    count = ("No job went out" if not jobs
             else "One job went out" if len(jobs) == 1
             else f"{len(jobs)} jobs went out")
    tail = (f" {len(done)} of them finished, {len(landed)} of those ending up in the "
            f"project itself, and {len(running)} are still running."
            if jobs else "")
    body = ["", _wrap(count + "." + tail, indent="")]

    for number, record in enumerate(jobs, 1):
        rounds = data["checks_by_change"].get(record.get("id", ""), [])
        body.append("")
        body.append(f"{number}.")
        body.extend(_job_lines(record, rounds, now))

    # Checks of work that did not itself start in this window still spent the
    # window, so they are named rather than quietly dropped.
    known = {j.get("id") for j in jobs}
    elsewhere = sum(len(v) for k, v in data["checks_by_change"].items() if k not in known)
    if elsewhere:
        body += ["", _wrap(
            f"{elsewhere} further round(s) of checking went on work that was not sent "
            "out in this window.", indent="")]

    all_costs = [r["cost_usd"] for r in data["checks"]
                 if isinstance(r.get("cost_usd"), (int, float))]
    missing = len(data["checks"]) - len(all_costs)
    money = (f"Checking cost {_money(sum(all_costs))} in this window."
             if all_costs else "No check recorded what it cost.")
    if all_costs and missing:
        money += f" {missing} of the checks did not record a cost, so the real figure is higher."
    body += ["", _wrap(money, indent="")]

    waiting = [i for i in notes if not i.get("delivered_at")]
    if notes:
        kinds = ", ".join(sorted({KIND_WORDS.get(i.get("kind", ""), i.get("kind", "a note"))
                                  for i in notes}))
        body += ["", _wrap(f"{len(notes)} note(s) were left for you in this window, of "
                           f"which {len(waiting)} you have not seen yet. They are: {kinds}.",
                           indent="")]

    open_spaces = [w for w in data["workspaces"] if not w.get("released_at")]
    if data["workspaces"]:
        body += ["", _wrap(
            f"{len(open_spaces)} separate working copy(ies) of a project are still "
            f"checked out for these agents; "
            f"{len(data['workspaces']) - len(open_spaces)} were handed back.", indent="")]

    if running:
        body += ["", _wrap(
            f"Still out: {len(running)} agent(s). Stopping now means their work is left "
            "where it stands, on its own copy, and can be picked up again.", indent="")]

    return "\n".join(head + body)


def write(hours: float = DEFAULT_HOURS, now: datetime | None = None) -> str:
    return render(gather(hours, now))


def file_it(text: str) -> dict[str, Any]:
    """Put the account in the queue, which is the one route to the operator."""
    return queue.add("report", text, urgency="high", origin="debrief")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=float, default=DEFAULT_HOURS,
                        help="how far back to look; the plan's short window is 5 hours")
    parser.add_argument("--queue", action="store_true",
                        help="send the account to the operator through the fleet queue")
    args = parser.parse_args(argv[1:])

    if args.hours <= 0:
        parser.error("--hours must be more than zero")

    text = write(args.hours)
    print(text)
    if args.queue:
        item = file_it(text)
        print(f"\nfiled for the operator as {item['id']} at {jsonstore.now()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
