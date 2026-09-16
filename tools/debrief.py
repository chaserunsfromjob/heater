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
import re
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

# A full stop that ends a sentence: one that follows an ordinary word and is
# followed by a capital. "e.g." and a file name with a suffix both fail it.
SENTENCE_END = re.compile(r"(?<=[a-z0-9)\"'])\.\s+(?=[A-Z])")

# A brief is written by one machine's operator for another machine's agent, so
# it carries four things the reader has no use for and could not act on: where a
# file sits on this machine, which copy of the work a job was sent to, the
# number a record is filed under, and the name of a file. Each is swapped for
# what it is. Order matters: a path may end in a record number, and a file name
# that owns the word after it reads better as the project owning that word.
_FILE = (r"\b[\w.\-]*(?:/[\w.\-]+)*"
         r"\.(?:py|md|sh|json|ya?ml|toml|txt|cfg|ini|lock|ts|js)\b")
PLAIN_WORDS = (
    (re.compile(r"(?:~|\B/)[\w.\-]+(?:/[\w.\-]+)+/?"), "a folder on this machine"),
    (re.compile(r"\b(?:worker|fixer|reviewer|agent)/[\w.\-]+"), "a separate copy of the work"),
    (re.compile(_FILE + r"'s"), "the project's"),
    (re.compile(_FILE), "a file in the project"),
    (re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{8,}\b"), "a record number"),
)

# An opening clause that says what kind of work this is not -- "Research task,
# not code" -- has said nothing about the job, and several briefs in a row can
# say it in the same words. Stepped over in favour of what follows it. The tail
# is left unanchored because such a clause often ends by naming a file, and a
# file name has a full stop inside it.
META_CLAUSE = re.compile(r"^(?:this is\s+)?[^.]{0,120}?\bnot\b[^.]{0,60}?\bcode\b", re.I)

# What each ending means, said the way it would be said out loud.
OUTCOME_WORDS = {
    "landed": "finished, and the work is now part of the project",
    "pushed": "finished, and the work is saved on its own copy of the project, "
              "waiting to be joined onto the shared one (joining it on is called merging)",
    "escalated": "stopped partway and asked for a decision",
    "failed": "could not finish",
    "abandoned": "was called off",
}

# What kind of agent it was, by what it was there to do. Any kind may be
# dispatched, so one that is not named here is still given a purpose.
AGENT_WORDS = {
    "worker": "to build something",
    "reviewer": "to check someone else's work",
    "fixer": "to apply the corrections a check asked for",
    "general-purpose": "to look something up and write up what it found",
}
AGENT_FALLBACK = "to carry out a piece of work"

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


def _started_or_ended_since(record: dict[str, Any], cutoff: datetime,
                            ended_key: str = "closed_at") -> bool:
    """In the window if it began in it, ended in it, or has not ended at all.

    A job that is still running belongs in the account whatever hour it started,
    because the account is written at the moment those jobs are stopped. A
    working copy handed back inside the window belongs to it for the same
    reason, however long before the window it was opened.
    """
    if not record.get(ended_key):
        return True
    began, ended = _moment(record.get("created")), _moment(record.get(ended_key))
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
                  if _started_or_ended_since(l, cutoff, ended_key="released_at")]

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


def _sentences(text: str) -> list[str]:
    """The brief, split into sentences.

    Split only where a full stop is followed by a capital, so that "e.g." and
    "bin/gate.sh" do not cut a sentence off in the middle of itself.
    """
    flat = " ".join((text or "").split())
    return [part for part in (s.strip().rstrip(".") for s in SENTENCE_END.split(flat)) if part]


def _plainly(text: str) -> str:
    """The sentence with the machinery in it said as what the machinery is."""
    for pattern, plain in PLAIN_WORDS:
        text = pattern.sub(plain, text)
    return " ".join(text.split())


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."


def _describe(record: dict[str, Any], limit: int = 220) -> str:
    """What the job was, in the brief's own words with the machinery taken out.

    The first sentence of a brief often says what kind of work it is rather than
    what the work was, and several briefs can say that in identical words, so a
    clause like that is passed over for the sentence that says what was wanted.
    Where the whole brief is such a clause, what finishing would look like says
    more than repeating it would.
    """
    said = _sentences(record.get("task", ""))
    wanted = next((s for s in said if not META_CLAUSE.match(s)), "")
    if wanted:
        return _clip(_plainly(wanted), limit)
    done = _sentences(record.get("done_when", ""))
    if done:
        return _clip(_plainly(f"Done when {done[0][:1].lower() + done[0][1:]}"), limit)
    if said:
        return _clip(_plainly(said[0]), limit)
    return "no task was recorded"


def _count(number: int, singular: str, plural: str) -> str:
    """"One note", not "1 note(s)": the reader is a person, not a log file."""
    return f"one {singular}" if number == 1 else f"{number} {plural}"


def _upper(text: str) -> str:
    """A sentence that begins with a counted word still begins with a capital."""
    return text[:1].upper() + text[1:]


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


def _tally(jobs: int, done: int, landed: int, running: int) -> str:
    """The opening count, with the plurals a person would actually use."""
    if jobs == 0:
        return "No agent was sent out in this window, though other work went on."
    if jobs == 1:
        ending = ("It is still running." if running else
                  "It finished, and its work is in the project." if landed else
                  "It has finished.")
        return f"One job went out. {ending}"
    parts = [f"{jobs} jobs went out"]
    if done:
        inside = ("" if not landed
                  else ", one of which is now in the project" if landed == 1
                  else f", {landed} of which are now in the project")
        parts.append(f"{done} of them finished{inside}")
    parts.append("one is still running" if running == 1 else
                 f"{running} are still running" if running else "none are still running")
    return ", and ".join([", ".join(parts[:-1]), parts[-1]]) + "."


def _job_lines(record: dict[str, Any], rounds: list[dict[str, Any]], now: datetime) -> list[str]:
    out = [_wrap(_describe(record), indent="   ")]
    purpose = AGENT_WORDS.get(record.get("agent", ""), AGENT_FALLBACK)
    began = _ago(_moment(record.get("created")), now)
    out.append(_wrap(f"Sent out {began}, {purpose}."))

    if record.get("closed_at"):
        # The closing note is the machinery talking to itself -- branch names and
        # record numbers -- so the ending is said in words instead of quoted.
        ending = OUTCOME_WORDS.get(record.get("outcome") or "", "ended in a way nobody recorded")
        finished = _ago(_moment(record["closed_at"]), now)
        out.append(_wrap(f"It {ending}, {finished}."))
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

    body = ["", _wrap(_tally(len(jobs), len(done), len(landed), len(running)), indent="")]

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
            f"{_count(elsewhere, 'further round', 'further rounds')} of checking went "
            "on work that was not sent out in this window.", indent="")]

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
        unseen = ("all of which you have already seen" if not waiting
                  else "and you have not seen it yet" if len(notes) == 1
                  else "and you have not seen any of them yet" if len(waiting) == len(notes)
                  else f"{len(waiting)} of which you have not seen yet")
        body += ["", _wrap(_upper(f"{_count(len(notes), 'note was', 'notes were')} left for "
                                  f"you in this window, {unseen}. They are: {kinds}."),
                           indent="")]

    open_spaces = [w for w in data["workspaces"] if not w.get("released_at")]
    handed_back = len(data["workspaces"]) - len(open_spaces)
    if data["workspaces"]:
        body += ["", _wrap(_upper(
            f"{_count(len(open_spaces), 'separate working copy', 'separate working copies')} "
            f"of a project {'is' if len(open_spaces) == 1 else 'are'} still set aside for "
            f"these agents to work in (a copy set aside like that is called a checkout), "
            f"and {_count(handed_back, 'other was', 'others were')} "
            "handed back."), indent="")]

    if running:
        body += ["", _wrap(
            f"Still out: {_count(len(running), 'agent', 'agents')}. Stopping now leaves "
            "their work where it stands, on its own copy, and it can be picked up again.",
            indent="")]

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
