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
# it carries six things the reader has no use for and could not act on: where a
# file sits on this machine, which copy of the work a job was sent to, the
# number a record is filed under, the name of a file, a folder inside a project
# and a repository somebody owns. Each is swapped for what it is. Order matters:
# a path may end in a record number, a file name that owns the word after it
# reads better as the project owning that word, and a folder ending in a slash
# must be read as a folder before it is read as an owner and a project name.
_FILE = (r"\b[\w.\-]*(?:/[\w.\-]+)*"
         r"\.(?:py|md|sh|json|ya?ml|toml|txt|cfg|ini|lock|ts|js)\b")
MACHINE_PATH = re.compile(r"(?:~|\B/)[\w.\-]+(?:/[\w.\-]+)+/?")
PLAIN_WORDS = (
    (MACHINE_PATH, "a folder on this machine"),
    (re.compile(r"\b(?:worker|fixer|reviewer|agent)/[\w.\-]+"), "a separate copy of the work"),
    (re.compile(r"\b[\w\-]+(?:\.[a-z]{2,4})+/[\w.\-]+(?:/[\w.\-]+)*"),
     "a ready-made project from the internet"),
    (re.compile(_FILE + r"'s"), "the project's"),
    (re.compile(_FILE), "a file in the project"),
    (re.compile(r"\b[\w.\-]+(?:/[\w.\-]+)*/(?![\w.\-])"), "a folder in the project"),
    (re.compile(r"(?<![\w.\-/])[\w\-]+/[\w\-]*_[\w\-]+(?![\w.\-])"),
     "a ready-made project from the internet"),
    (re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{8,}\b"), "a record number"),
    (re.compile(r"(?<![\w.\-/])[a-z][a-z0-9\-]*_[a-z0-9_\-]+(?![\w.\-/])"),
     "another project"),
)

# Two words a brief uses as jargon and a person uses as neither: the short name
# for a project, and the name of the copy everyone's work is joined onto. They
# are ordinary words, not machinery, so a sentence carrying one is still worth
# saying -- it is said in the words the reader would use. The branch word is
# only swapped where it is the object of joining one copy to another, so "the
# main checkout" is left alone.
JARGON_WORDS = (
    (re.compile(r"\brepos\b"), "projects"),
    (re.compile(r"\brepo\b"), "project"),
    (re.compile(r"\b(and|onto|into|from|with|against|to)\s+(?:main|trunk)\b"),
     r"\1 the shared copy"),
)

# A word a brief shouts, which is how it points back at a file it has already
# named. The account is written in sentences and never shouts, and an acronym
# the reader would have to be taught is no use to them shouted either.
SHOUT = re.compile(r"(?<![\w'])[A-Z]{2,}(?![\w'])")

# What machinery looks like when no swap above has caught it. A sentence still
# carrying any of these was written for an agent, and no amount of rewording
# here will make it mean anything to the reader, so the sentence is passed over.
# The slash shapes are deliberately narrow: "engines/bots" and "session/repo"
# are how a person writes, and only a dot or an underscore in a slashed
# fragment makes it a path or a repository.
CODE_SHAPE = re.compile(
    r"`"                                                 # quoted as a command
    r"|\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+\b"            # a class: TestStopHook
    r"|\b\w+\.\w+\s*\("                                  # a call: context.state(
    r"|\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b"                    # a constant: MAX_SLOTS
    r"|(?<![\w.\-/])[\w.\-]+(?:/[\w.\-]+)*/(?![\w.\-])"  # a folder: vendor/lib/
    r"|(?<![\w.\-/])[\w\-]*[._][\w\-]*/[\w.\-]+"         # owner/name, either
    r"|(?<![\w.\-/])[\w\-]+/[\w\-]*[._][\w\-]*"          # half of it code-shaped
    r"|\s--\w"                                           # a flag: --check
)

# Where a reader would draw breath. Used both to drop a whole clause and to stop
# before the limit, so that nothing ever ends in the middle of one.
CLAUSE_BREAK = re.compile(r"(,|;|:|\s--|\s—|\s–)(\s+)")

# A marker in front of an item in a list: "(a)", "(b)". Where the trim keeps
# only the first item, the marker in front of it points at a list the account
# does not show, so it goes with its siblings.
LIST_MARKER = re.compile(r"\s*\((?:[a-z]|\d)\)\s*")

# An aside in brackets. Briefs do not nest them, and one that carries machinery
# is dropped whole rather than swapped inside: "(already on branch a separate
# copy of the work)" names what it replaced and says nothing else.
ASIDE = re.compile(r"\s*\([^()]*\)")

# A clause that cannot stand on its own. Kept where the whole sentence is kept,
# dropped where the sentence had to be cut short, so that the account never ends
# on "when a session has written, committed and pushed its handover".
SUBORDINATE = re.compile(
    r"^(?:when|while|if|unless|until|after|before|because|since|although|though"
    r"|whereas|whether|once|where|which|who|that|so that)\b", re.I)

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

# What is said where the brief cannot be said at all. An honest line beats a
# line of machinery, and beats an invented summary of a brief nobody read.
NOT_RECORDED = "no task was recorded"
DOES_NOT_TRANSLATE = ("what this one was about was written for another agent "
                      "and does not translate into plain words")

# What each note in the queue is, by what it is for, said of one and of several.
KIND_WORDS = {
    "finding": ("something an agent noticed in passing and wrote down",
                "things an agent noticed in passing and wrote down"),
    "escalation": ("a decision an agent needs from you",
                   "decisions an agent needs from you"),
    "report": ("an account an agent wrote for you",
               "accounts an agent wrote for you"),
    "failure": ("something that went wrong", "things that went wrong"),
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
        return f"{_minutes(round(minutes))} ago"
    hours, rest = divmod(round(minutes), 60)
    stem = "1 hour" if hours == 1 else f"{hours} hours"
    return f"{stem} ago" if rest == 0 else f"{stem} {_minutes(rest)} ago"


def _minutes(count: int) -> str:
    """"1 minute", not "1 minutes": the reader is a person, not a log file."""
    return "1 minute" if count == 1 else f"{count} minutes"


def _sentences(text: str) -> list[str]:
    """The brief, split into sentences.

    Split only where a full stop is followed by a capital, so that "e.g." and
    "bin/gate.sh" do not cut a sentence off in the middle of itself.
    """
    flat = " ".join((text or "").split())
    return [part for part in (s.strip().rstrip(".") for s in SENTENCE_END.split(flat)) if part]


def _plainly(text: str) -> str:
    """The sentence with the machinery in it said as what the machinery is."""
    for pattern, plain in PLAIN_WORDS + JARGON_WORDS:
        text = pattern.sub(plain, text)
    text = SHOUT.sub(lambda found: found.group(0).capitalize() if found.start() == 0
                     else found.group(0).lower(), text)
    return " ".join(text.split())


def _is_machinery(fragment: str) -> bool:
    return bool(CODE_SHAPE.search(fragment)
                or any(pattern.search(fragment) for pattern, _ in PLAIN_WORDS))


def _clauses(text: str) -> list[tuple[str, str]]:
    """The sentence in clauses, each with the punctuation that closed it.

    Cut only outside brackets, so an aside holding a comma stays one piece:
    "(not game-theory-optimal, which does not exist)" is one aside, not two
    clauses.
    """
    pieces, depth, start, index = [], 0, 0, 0
    while index < len(text):
        character = text[index]
        if character in "([":
            depth += 1
        elif character in ")]":
            depth = max(0, depth - 1)
        elif depth == 0 and (found := CLAUSE_BREAK.match(text, index)):
            pieces.append((text[start:index], found.group(0)))
            index = start = found.end()
            continue
        index += 1
    pieces.append((text[start:], ""))
    return pieces


def _without_asides(text: str) -> str:
    """The sentence with any bracketed aside that is pure machinery removed."""
    return ASIDE.sub(lambda found: "" if _is_machinery(found.group(0)) else found.group(0), text)


def _without_where_to_work(text: str) -> str:
    """The sentence with any clause that only says where on this machine to work.

    "working in the checkout at /Users/..." is the whole of what such a clause
    says, so swapping the path for words leaves "working in the checkout at a
    folder on this machine", which names what it replaced and nothing else.
    """
    kept = [body + separator for body, separator in _clauses(text)
            if not MACHINE_PATH.search(body)]
    return "".join(kept) if kept else ""


def _readable(text: str, limit: int) -> str:
    """As much of the sentence as reads cleanly: whole clauses, ended properly.

    Stops before the first clause that carries machinery and before the clause
    that would cross the limit, so the account never ends in the middle of one.
    Empty when even the first clause fails, which is the caller's signal to try
    the next sentence.
    """
    residue = CODE_SHAPE.search(text)
    ceiling = min(limit, residue.start() if residue else len(text))
    pieces = _clauses(text)
    kept, at = [], 0
    for body, separator in pieces:
        if at + len(body) > ceiling:
            break
        kept.append(body + separator)
        at += len(body) + len(separator)

    if len(kept) < len(pieces):
        for index in range(len(kept) - 1, 0, -1):
            if SUBORDINATE.match(kept[index].strip()):
                kept = kept[:index]
                break

    said = "".join(kept).strip().rstrip(",;:-—– ").strip()
    if len(LIST_MARKER.findall(said)) == 1:
        said = LIST_MARKER.sub(" ", said).strip()
    return f"{said}." if said else ""


def _in_plain_words(sentence: str, limit: int) -> str:
    """One sentence of a brief, or nothing when it cannot be said plainly."""
    return _readable(_plainly(_without_where_to_work(_without_asides(sentence))), limit)


def _describe(record: dict[str, Any], limit: int = 220) -> str:
    """What the job was, in the brief's own words with the machinery taken out.

    The first sentence of a brief often says what kind of work it is rather than
    what the work was, and several briefs can say that in identical words, so a
    clause like that is passed over for the sentence that says what was wanted.
    That sentence is the brief. What comes after it is the reasoning, the
    diagnosis and the housekeeping, so reaching further down the brief buys a
    line that says an agent was spent on tidying a comment. Where that sentence
    is machinery all the way down, what finishing would look like is tried
    instead, and where that fails too the account says so rather than printing
    something the reader cannot read.
    """
    for sentence in _sentences(record.get("task", "")):
        if META_CLAUSE.match(sentence):
            continue
        if (said := _in_plain_words(sentence, limit)):
            return said
        break
    for sentence in _sentences(record.get("done_when", "")):
        if (said := _in_plain_words(sentence, limit)):
            return _upper(f"done when {said[:1].lower() + said[1:]}")
    return NOT_RECORDED if not (record.get("task") or "").strip() else DOES_NOT_TRANSLATE


def _count(number: int, singular: str, plural: str) -> str:
    """"One note", not "1 note(s)": the reader is a person, not a log file."""
    return f"one {singular}" if number == 1 else f"{number} {plural}"


def _figure(number: int) -> str:
    """One is a word wherever it appears in a sentence; the rest are figures."""
    return "one" if number == 1 else str(number)


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
             else "Checked over twice" if len(rounds) == 2
             else f"Checked over {len(rounds)} times")
    if last.get("verdict") == "pass":
        return f"{count}, and the last check passed it."
    found = last.get("findings") or 0
    if not found:
        return f"{count}, and the last check sent it back for changes."
    thing = "one thing" if found == 1 else f"{found} things"
    return f"{count}, and the last check sent it back with {thing} to put right."


def _tally(jobs: int, sent: int, done: int, landed: int, running: int) -> str:
    """The opening count, with the plurals a person would actually use.

    An agent already out when the window opened was not sent out in it, and
    counting it as though it were says the window bought more than it did. Both
    figures are given, because both are true of what the window spent.
    """
    if jobs == 0:
        return "No agent was sent out in this window, though other work went on."
    if jobs == 1:
        opening = ("One agent was sent out in this window." if sent
                   else "One agent was already running when this window began.")
        ending = ("It is still running." if running else
                  "It finished, and its work is in the project." if landed else
                  "It has finished.")
        return f"{opening} {ending}"

    earlier = jobs - sent
    first = _upper(_count(jobs, "agent was", "agents were") + " working in this window")
    if not earlier:
        first += ", all of them sent out inside it."
    elif not sent:
        first += ", all of them already running when it began."
    else:
        first += (f", {_figure(sent)} of them sent out inside it "
                  f"and {_figure(earlier)} already running when it began.")

    parts = []
    if done:
        inside = ("" if not landed
                  else ", one of which is now in the project" if landed == 1
                  else f", {landed} of which are now in the project")
        parts.append(f"{_figure(done)} of them finished{inside}")
    parts.append("one is still running" if running == 1 else
                 f"{running} are still running" if running else "none are still running")
    rest = ", and ".join([", ".join(parts[:-1]), parts[-1]]) if len(parts) > 1 else parts[0]
    return f"{first} {_upper(rest)}."


def _same_work(record: dict[str, Any]) -> str:
    """A brief boiled down to what two dispatches of one job would share.

    Only what says where on this machine to work is taken out, because that is
    the whole of what changes when a brief is sent a second time. Everything
    else the brief says is kept, word for word.
    """
    text = _without_where_to_work(_without_asides(record.get("task", "")))
    return " ".join(text.lower().split()).strip(" .,;:")


def _repeats(jobs: list[dict[str, Any]]) -> str:
    """Whether some of these entries are work already listed further up.

    Four of nineteen entries on one live page were a brief sent out a second
    time, and a count that does not say so reads as more separate work than
    there was. Counted on the briefs as they were written down, never on the
    entries, because an entry says only as much of its brief as reads plainly
    and two different jobs can come out of that saying the same thing.
    """
    written = [key for key in (_same_work(record) for record in jobs) if key]
    again = len(written) - len(set(written))
    if not again:
        return ""
    subject = ("One of the entries below describes work already listed above it"
               if again == 1 else
               f"{again} of the entries below describe work already listed above them")
    return (f"{subject}: the same brief was sent out more than once, so this window "
            f"covers {len(jobs) - again} separate pieces of work, not {len(jobs)}.")


def _note_lines(notes: list[dict[str, Any]]) -> list[str]:
    """The queue, said as the two different things it holds.

    A finding is one agent's aside to the stoker, and it is judged rather than
    read by the operator. A report or an escalation is written for the operator.
    Counting them together told the operator that thirty-three notes were left
    for them when two were, and that they had seen them all when what had
    happened was that the stoker had been woken.
    """
    findings = [i for i in notes if i.get("kind") == "finding"]
    for_you = [i for i in notes if i.get("kind") != "finding"]
    said = []

    if findings:
        judged = len([i for i in findings if i.get("resolution")])
        waiting = len(findings) - judged
        how = ("it has been judged" if not waiting and len(findings) == 1
               else "all of them have been judged" if not waiting
               else "none of them have been judged yet" if not judged
               else f"{_figure(judged)} {'has' if judged == 1 else 'have'} been judged "
                    f"and {_figure(waiting)} {'is' if waiting == 1 else 'are'} still waiting")
        said.append(_upper(
            f"{_count(len(findings), 'thing was', 'things were')} noticed in passing by an "
            f"agent and written down for the stoker to judge rather than for you; {how}."))

    if for_you:
        kinds = sorted({i.get("kind", "") for i in for_you})
        unsent = [i for i in for_you if not i.get("delivered_at")]
        how = ("and all of them have been passed on to you" if not unsent
               else "and it has not been passed on to you yet" if len(for_you) == 1
               else "and none of them have been passed on to you yet"
               if len(unsent) == len(for_you)
               else f"{len(unsent)} of which have not been passed on to you yet")
        said.append(_upper(f"{_count(len(for_you), 'note was', 'notes were')} left for you "
                           f"in this window, {how}. {_what_they_are(kinds, len(for_you))}"))
    return said


def _kind_words(kind: str) -> tuple[str, str]:
    return KIND_WORDS.get(kind, (kind or "a note", kind or "notes"))


def _what_they_are(kinds: list[str], notes: int) -> str:
    """What the notes are, said of however many of them there turn out to be.

    "2 notes ... They are: an account an agent wrote for you" is a plural
    subject with a singular list under it, which reads as though one of the two
    went missing. Where they are all the one kind there is no list to make.
    """
    if len(kinds) > 1:
        return "They are: " + ", ".join(sorted(_kind_words(k)[0] for k in kinds)) + "."
    one, many = _kind_words(kinds[0])
    if notes == 1:
        return f"It is {one}."
    return f"Both are {many}." if notes == 2 else f"All of them are {many}."


def _job_lines(record: dict[str, Any], rounds: list[dict[str, Any]], now: datetime,
               told: str) -> list[str]:
    out = [_wrap(told, indent="   ")]
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
    sent = [j for j in jobs if (began := _moment(j.get("created"))) and began >= data["cutoff"]]

    told = [_describe(record) for record in jobs]

    body = ["", _wrap(_tally(len(jobs), len(sent), len(done), len(landed), len(running)),
                      indent="")]
    if (again := _repeats(jobs)):
        body += ["", _wrap(again, indent="")]

    for number, (record, description) in enumerate(zip(jobs, told), 1):
        rounds = data["checks_by_change"].get(record.get("id", ""), [])
        body.append("")
        body.append(f"{number}.")
        body.extend(_job_lines(record, rounds, now, description))

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

    for paragraph in _note_lines(notes):
        body += ["", _wrap(paragraph, indent="")]

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
