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

One decision about what the page will not do, recorded here so that it is not
guessed at again. A brief gives its order in one sentence and then spends
several more saying how much of that order to do -- "Cover at least:",
"Include:", "Measure:". Where the order itself cannot be said, because the
words saying what the work was about name a tool this page must not print,
none of those later sentences may stand in for it: each continues an order it
does not repeat, and a page built from them says how much of a job was wanted
without ever saying what the job was. Two such briefs, for two quite different
pieces of research, read as though one of them had been done twice. So the
entry says plainly that it does not translate. The page never guesses.

The one sentence allowed to stand in is a sentence saying what the operator
wanted, because that says what the work was for rather than telling the agent
how much of it to do.

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
    # A copy of the work is named after whoever cut it, so the name itself can
    # be anything: "codex/tonight" is one, and only the word in front of it says
    # so. The possessive is swapped first, or "the classmate's branch x/y" comes
    # out as "the classmate's a separate copy of the work".
    (re.compile(r"'s\s+branch(?:es)?\s+[\w.\-]+/[\w.\-]+"), "'s separate copy of the work"),
    (re.compile(r"\bbranch(?:es)?\s+[\w.\-]+/[\w.\-]+"), "a separate copy of the work"),
    (re.compile(r"\b(?:worker|fixer|reviewer|agent)/[\w.\-]+"), "a separate copy of the work"),
    (re.compile(r"\b[\w\-]+(?:\.[a-z]{2,4})+/[\w.\-]+(?:/[\w.\-]+)*"),
     "a ready-made project from the internet"),
    (re.compile(_FILE + r"'s"), "the project's"),
    (re.compile(_FILE), "a file in the project"),
    (re.compile(r"\b[\w.\-]+(?:/[\w.\-]+)*/(?![\w.\-])"), "a folder in the project"),
    (re.compile(r"(?<![\w.\-/])[\w\-]+/[\w\-]*_[\w\-]+(?![\w.\-])"),
     "a ready-made project from the internet"),
    # Seven characters, not eight: a commit is written down that short -- "tip
    # ca8339e" -- and it is as much a number nobody can read as a twelve-
    # character one. Seven letters that are all a-f and hold a digit are not a
    # word in any brief the store holds.
    (re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{7,}\b"), "a record number"),
    (re.compile(r"(?<![\w.\-/])[a-z][a-z0-9\-]*_[a-z0-9_\-]+(?![\w.\-/])"),
     "another project"),
)

# Two words a brief uses as jargon and a person uses as neither: the short name
# for a project, and the name of the copy everyone's work is joined onto. They
# are ordinary words, not machinery, so a sentence carrying one is still worth
# saying -- it is said in the words the reader would use. The branch word is
# only swapped where a preposition puts it there -- joined onto it, sitting on
# it -- so "the main checkout" is left alone.
JARGON_WORDS = (
    # To read something read-only is to look at it without changing it, which is
    # what the words say once they are said in full.
    (re.compile(r"\bread-only\b", re.I), "without changing anything"),
    (re.compile(r"\brepos\b"), "projects"),
    (re.compile(r"\brepo\b"), "project"),
    (re.compile(r"\b(and|onto|into|from|with|against|to|on)\s+(?:main|trunk)\b"),
     r"\1 the shared copy"),
    # To vendor something is to bring a copy of somebody else's project into
    # yours. Only the verb is swapped: a vendor who sells things is a different
    # word, and it is never the word a brief opens an order with.
    (re.compile(r"^Vendor\b"), "Bring"),
    (re.compile(r"\b(to|and|then|please)\s+vendor\b"), r"\1 bring"),
    (re.compile(r"\bvendoring\b"), "bringing in"),
    (re.compile(r"\bvendored\b"), "brought in"),
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
    r"|\b\w+\(\)"                                        # a call with nothing in it
    r"|\b(?:True|False)\b"                               # what such a call gives back
    r"|(?:^|(?<=\s))\.\w+"                               # a name led by a dot: .venv
    r"|\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b"                    # a constant: MAX_SLOTS
    r"|(?<![\w.\-/])[\w.\-]+(?:/[\w.\-]+)*/(?![\w.\-])"  # a folder: vendor/lib/
    r"|(?<![\w.\-/])[\w\-]*[._][\w\-]*/[\w.\-]+"         # owner/name, either
    r"|(?<![\w.\-/])[\w\-]+/[\w\-]*[._][\w\-]*"          # half of it code-shaped
    r"|\s--\w"                                           # a flag: --check
)

# The fleet's own words for its machinery. They are not identifiers, so no swap
# above catches them, and they are not English the reader has met: a brief that
# says the tests pass "in a clean worktree" but fail "in the main checkout with
# a different context-usage reading" is four unexplained terms in one line. The
# page explains "checkout" once, where it says how many are set aside; anywhere
# else the word is machinery, so the sentence carrying it is passed over.
# The names of the tools a brief orders the work with belong here too: a brief
# that says to run pytest, install with pip, stand up a venv or grep for a word
# has named programs the reader has never run, and the sentence carrying one of
# them was written for the agent that would run it.
FLEET_JARGON = re.compile(
    r"(?i:\b(?:worktrees?|checkouts?|stubs?|stubbed|stubbing|monkeypatch\w*"
    r"|context-usage|statusline|autopush"
    r"|bash|pytest|pip|venv|grep|git|pull requests?)\b)")

# Everything a sentence is passed over for, in one pattern, so that what is
# rejected in a brief is rejected in what finishing it would look like too.
MACHINERY = re.compile(CODE_SHAPE.pattern + r"|" + FLEET_JARGON.pattern)

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
# on "when a session has written, committed and pushed its handover". A clause
# promising something about each item of a list is the same thing from the other
# end: cut before it says what, "; for each." is a promise and nothing else.
SUBORDINATE = re.compile(
    r"^(?:when|while|if|unless|until|after|before|because|since|although|though"
    r"|whereas|whether|once|where|which|who|that|so that"
    r"|for (?:each|every|all|both)|each with)\b", re.I)

# An opening clause that says what kind of work this is not -- "Research task,
# not code" -- has said nothing about the job, and several briefs in a row can
# say it in the same words. Stepped over in favour of what follows it. The tail
# is left unanchored because such a clause often ends by naming a file, and a
# file name has a full stop inside it.
META_CLAUSE = re.compile(r"^(?:this is\s+)?[^.]{0,120}?\bnot\b[^.]{0,60}?\bcode\b", re.I)

# The verbs a brief gives an order in. A brief carries more than the job: the
# background that led to it, the diagnosis that found the fault, the reasoning
# and the housekeeping. Taking whichever sentence happened to survive the
# machinery told the operator that an agent had been sent to notice "We have no
# testing strategy yet". Only a sentence that orders the work, or one that says
# what the operator wanted, is the job, and without grammar the only way to
# know an order is to know the verb it is given in. Every verb the briefs in
# the store open a clause with is here; one that is not is passed over.
WORK_VERBS = frozenset("""
add adapt adopt apply audit begin bring build call carry change check choose
clean close collect compare conclude confirm connect continue cover create cut
delete deliver describe design dispatch document draft drop end ensure explain
extend file fill find finish fix follow gather give go hold implement install
judge keep land leave list load look lower make measure merge move name note
open pick port print produce prove pull push put raise rank rate read record
remove rename render repeat replace report research resolve restore rewrite
run save say send set show sort split start stop store survey sweep switch
take teach tell test tidy trim turn update use vendor verify weigh wire work
wrap write
""".split())

# An order that has been put off to the end of the sentence, and an order that
# says what not to do. A sentence opening with what not to do is the fence
# around the job, never the job.
ORDER_LEAD = re.compile(r"^(?:also|then|first|next|finally|now|please|start by"
                        r"|begin by|instead)\s+", re.I)
NOT_AN_ORDER = re.compile(r"^(?:do not|don't|never|no)\b", re.I)

# A brief that says what was wanted rather than ordering it. "The operator
# wants more concurrent workers per project" is the job, said the way the
# person who asked for it said it.
WANTED = re.compile(r"\b(?:the operator|operator|we|i|they)\s+"
                    r"(?:wants?|wanted|asked|needs?|needed|would like)\b", re.I)

# The swap puts a file where the brief named one, and a brief that names a file
# straight after the word "file" -- "Write ONE new file DECISION_LAYER.md" --
# comes back saying file twice: "one new file a file in the project". One file
# is one file, so the second is dropped along with the commas that held it.
DOUBLED_FILE = (
    (re.compile(r"\b(files?),\s+a file in the project,", re.I), r"\1"),
    (re.compile(r"\b(files?)\s+a file in the project\b", re.I), r"\1"),
)

# Where in a project a new file goes. It says where to put the thing and never
# what the thing is, so it counts for nothing when the account asks whether a
# rendering said anything of its own.
WHERE_IT_GOES = re.compile(r"\b(?:at|in|under|to)\s+the\s+[\w\-]+\s+root\b", re.I)

# The frame a brief builds an order in: what to do with a file, and which file
# of the several it is. Two live entries for two different jobs both read "Write
# one new file a file in the project at the pokerbot root", which is the frame
# and nothing else -- the one word that said which job it was, the file's name,
# is the word the swap took out. A rendering made of these alone has not said
# what the agent was sent to do, so the next sentence is tried instead.
SCAFFOLDING = frozenset("""
add adds adding write writes writing create creates creating file files new
one root project
""".split())

# A word that points back at something a sentence further up named. The whole of
# one live entry was "Sweep every such passage.", where the passages were named
# in a sentence the account had already passed over, so the reader was sent
# looking for a list that is not on the page.
POINTS_BACK = re.compile(r"^(?:it|them|that|these|those|the same)\b", re.I)
POINTS_AT_A_WORD = re.compile(r"\b(?:such|these|those|the same)\s+(?!as\b)([a-z]+)", re.I)

# Words that carry no information of their own once a swap has taken the
# machinery out. "Done when a file in the project passes" is made of nothing
# else: it was on the live page for a job that raised the limit on working
# copies, and it told the reader nothing that job did.
SAID_NOTHING = frozenset("""
a an the and or of in on at to it its this that these those there here is are
was were be been being do does did done when while all any both each every no
not with for from by so still again now up out same result
pass passes passed passing run runs ran running work works working
""".split())

# What each ending means, said the way it would be said out loud.
OUTCOME_WORDS = {
    "landed": "finished, and the work is now part of the project",
    "pushed": "finished, and the work is saved on its own copy of the project, "
              "waiting to be joined onto the shared one (joining it on is called merging)",
    "escalated": "stopped partway and asked for a decision",
    "failed": "could not finish",
    "abandoned": "stopped without producing anything",
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

# How far into a brief its order is still the order. A brief states what it
# wants at the top; an order further down is as likely to be the preparation --
# one live brief says which documents to read in its third sentence, and the
# list of them is all that sentence carries. Only an order this near the top
# counts as the one the rest of the brief is carrying on.
OPENS_A_BRIEF = 2

# What is said where the brief cannot be said at all. An honest line beats a
# line of machinery, and beats an invented summary of a brief nobody read.
NOT_RECORDED = "No task was recorded for this one."
DOES_NOT_TRANSLATE = ("What this one was about was written for another agent "
                      "and does not translate into plain words.")

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

    # Every file the stores could not read, from all four of them. The page says
    # it is read back from the records, so one it never saw is one it has to
    # count: two review records with a stray backslash in them were dropped in
    # silence, and the page said eleven rounds of checking where there were 13.
    unreadable: list[Path] = []

    jobs = [d for d in jsonstore.load(dispatch.dispatches_dir(), unreadable)
            if _started_or_ended_since(d, cutoff)]
    jobs.sort(key=lambda d: d.get("created", ""))

    checks = [r for r in jsonstore.load(store.reviews_dir(), unreadable)
              if (when := _moment(r.get("created"))) and when >= cutoff]
    by_change: dict[str, list[dict[str, Any]]] = {}
    for round_record in checks:
        by_change.setdefault(round_record.get("change", ""), []).append(round_record)
    for rounds in by_change.values():
        rounds.sort(key=lambda r: r.get("round", 0))

    notes = [i for i in jsonstore.load(queue.queue_dir(), unreadable)
             if (when := _moment(i.get("created"))) and when >= cutoff]

    workspaces = [l for l in jsonstore.load(worktrees.leases_dir(), unreadable)
                  if _started_or_ended_since(l, cutoff, ended_key="released_at")]

    return {"at": now or datetime.now(timezone.utc), "hours": hours, "cutoff": cutoff,
            "jobs": jobs, "checks": checks, "checks_by_change": by_change,
            "notes": notes, "workspaces": workspaces,
            "unreadable": len(unreadable)}


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
    for pattern, kept in DOUBLED_FILE:
        text = pattern.sub(kept, text)
    return " ".join(text.split())


def _is_machinery(fragment: str) -> bool:
    return bool(MACHINERY.search(fragment)
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


def _list_runs(pieces: list[tuple[str, str]]) -> list[list[tuple[str, str]]]:
    """The clauses, with the items of one marked list gathered into one piece.

    "(a) no-limit betting, and (b) two to nine players" is one thing the brief
    said. Keeping the first item and dropping the second left the account
    promising a list after a colon and then showing one line of it, so a list
    now stands or falls whole.
    """
    runs: list[list[tuple[str, str]]] = []
    for piece in pieces:
        opening = re.sub(r"^(?:and|or)\s+", "", piece[0].strip(), flags=re.I)
        if LIST_MARKER.match(opening) and runs and LIST_MARKER.search(runs[-1][-1][0]):
            runs[-1].append(piece)
        else:
            runs.append([piece])
    return runs


def _readable(text: str, limit: int) -> str:
    """As much of the sentence as reads cleanly: whole clauses, ended properly.

    Stops before the first clause that carries machinery and before the clause
    that would cross the limit, so the account never ends in the middle of one.
    A list is allowed to run half as long again over the limit rather than lose
    half its items; a list longer than that goes, and the clause that promised
    it goes with it, because "engines that natively support." says nothing on
    its own. Empty when even the first clause fails, which is the caller's
    signal to try the next sentence.
    """
    residue = MACHINERY.search(text)
    cut = residue.start() if residue else len(text)
    ceiling = min(limit, cut)
    runs = _list_runs(_clauses(text))
    kept, at, lost_a_list = [], 0, False
    for run in runs:
        body = "".join(part + separator for part, separator in run)
        room = min(cut, ceiling + limit // 2) if len(run) > 1 else ceiling
        if at + len(body) - len(run[-1][1]) > room:
            lost_a_list = len(run) > 1
            break
        kept.append(body)
        at += len(body)

    while lost_a_list and kept and kept[-1].rstrip().endswith(":"):
        kept.pop()

    # Over and over, because cutting at one clause that cannot stand on its own
    # can leave another one last: "...each with: what it is, which document
    # settles it" loses its tail and ends on the promise that opened it.
    while len(kept) < len(runs):
        for index in range(len(kept) - 1, 0, -1):
            if SUBORDINATE.match(kept[index].strip()):
                kept = kept[:index]
                break
        else:
            break

    said = "".join(kept).strip().rstrip(",;:-—– ").strip()
    if len(LIST_MARKER.findall(said)) == 1:
        said = LIST_MARKER.sub(" ", said).strip()
    return f"{said}." if said else ""


def _in_plain_words(sentence: str, limit: int) -> str:
    """One sentence of a brief, or nothing when it cannot be said plainly.

    Where it will not fit, the asides go first: an aside is beside the point by
    construction, and one long enough to carry the opening clause past the limit
    on its own threw away a live entry's "The operator wants more concurrent
    workers per project" and left the account quoting the housekeeping below it.
    """
    plain = _without_where_to_work(_without_asides(sentence))
    return (_readable(_plainly(plain), limit)
            or _readable(_plainly(_without_where_to_work(ASIDE.sub("", sentence))), limit))


def _says_the_work(sentence: str) -> bool:
    """Whether this sentence of a brief is the job rather than its surroundings.

    A brief is written in four registers: the order, the background that led to
    it, the diagnosis that found the fault, and the housekeeping at the end.
    Only the first is what an agent was sent to do. Two of eighteen live entries
    read "The operator has confirmed firm requirements..." and "We have no
    testing strategy yet...", which is the background answering for the job.
    A sentence counts as the order when one of its clauses opens with a verb a
    brief gives orders in, or when it says what the operator wanted. A sentence
    that opens by saying what not to do is the fence around the job, not the job.
    """
    if NOT_AN_ORDER.match(sentence.strip()):
        return False
    if WANTED.search(sentence):
        return True
    for body, _ in _clauses(sentence):
        opening = ORDER_LEAD.sub("", body.strip().lstrip("(*-\u2013\u2014 "))
        if (first := re.match(r"[a-z']+", opening, re.I)) and first.group(0).lower() in WORK_VERBS:
            return True
    return False


def _says_something(said: str, project: str = "") -> bool:
    """Whether a rendering has content of its own, or only what a swap put there.

    "bin/gate.sh passes" becomes "a file in the project passes", which is a swap
    and a verb and nothing the reader did not already know. Said of a job that
    raised the limit on working copies, it named none of that. A list of file
    names goes the same way from the other end: nine of them in a row become the
    same phrase nine times, which is a list the reader cannot act on either.
    The frame the order was written in goes with them: "Write one new file a
    file in the project at the pokerbot root" is where a file went and what was
    done with it, and two different jobs came out of it word for word alike.

    The name of the project the work was in counts for nothing either. One live
    entry read "Add a file in the project to pokerbot", which is the frame plus
    the name of the project -- and every job in that project could say it.

    A rendering that opens on a swap is the same failure from the front: what
    the sentence is about is the one word the swap took out, so "a file in the
    project committed and pushed with at least five options" could be said of
    any of them.
    """
    if any(said.strip().lower().startswith(plain) for _, plain in PLAIN_WORDS):
        return False
    left = WHERE_IT_GOES.sub(" ", said)
    if project.strip():
        left = re.sub(rf"\b{re.escape(project.strip())}\b", " ", left, flags=re.I)
    for _, plain in PLAIN_WORDS:
        if left.count(plain) > 2:
            return False
        left = left.replace(plain, " ")
    return any(word not in SAID_NOTHING and word not in SCAFFOLDING
               for word in re.findall(r"[a-z']+", left.lower()))


def _points_outside(said: str) -> bool:
    """Whether the rendering leans on a word no sentence of it carries.

    "Sweep every such passage." is an order about passages the reader has not
    been shown, and so is anything opening with "it", "them" or "those": the
    sentence that named them is one the account passed over. A rendering that
    points at a word it does not itself carry is no rendering, so the next
    sentence is tried instead.
    """
    body = said.strip()
    if POINTS_BACK.match(body):
        return True
    for found in POINTS_AT_A_WORD.finditer(body):
        pointed = found.group(1).lower().rstrip("s")
        earlier = body[:found.start()].lower()
        if pointed and not re.search(rf"\b{re.escape(pointed)}s?\b", earlier):
            return True
    return False


def _lost_its_content_to_machinery(sentence: str, said: str, project: str) -> bool:
    """Whether the order a brief opened with was cut down to nothing by a name.

    The opening order says what the work is for, and it often says it in a
    clause naming the engine or the tool the work sits on -- a name this page
    does not print. Cut there, what is left is the frame every such order is
    written in: a file was written, something was added to a project. The rest
    of the brief is no help, because the rest is how much of the order to do.
    So the account stops taking orders from that brief rather than offering a
    sentence that was never the point: two briefs for two quite different pieces
    of research both went on to say "Cover at least:", then to rate their
    options against the same five requirements, and the page read as though one
    of them had been done twice.
    """
    return (bool(MACHINERY.search(_plainly(sentence)))
            and not (said and _says_something(said, project)))


def _describe(record: dict[str, Any], limit: int = 220) -> str:
    """What the job was, in the brief's own words with the machinery taken out.

    Every sentence of the brief is offered, and the ones that are its
    surroundings rather than its order are passed over, because the order is as
    often the fourth sentence as the first. Where the brief's opening order lost
    what it was about to a name this page does not print, the sentences after it
    are passed over too -- they carry on that order rather than giving it, and
    the page does not guess. A sentence saying what the operator wanted is the
    exception, because it says what the work was for. Where no sentence of the
    brief can be said plainly, what finishing would look like is tried instead,
    held to the same tests, since a line built out of swaps tells the reader
    nothing. Where that fails too the account says so, which is worth more than
    a sentence the reader cannot read.
    """
    project, opening, gutted = record.get("project") or "", True, False
    for place, sentence in enumerate(_sentences(record.get("task", ""))):
        if META_CLAUSE.match(sentence) or not _says_the_work(sentence):
            continue
        said = _in_plain_words(sentence, limit)
        stands = bool(said) and (opening or not gutted or bool(WANTED.search(sentence)))
        if stands and _says_something(said, project) and not _points_outside(said):
            return said
        if opening:
            gutted = (place < OPENS_A_BRIEF
                      and _lost_its_content_to_machinery(sentence, said, project))
            opening = False
    for sentence in _sentences(record.get("done_when", "")):
        if ((said := _in_plain_words(sentence, limit))
                and _says_something(said, project) and not _points_outside(said)):
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

    Four of nineteen jobs on one live page were a brief sent out a second time,
    and a count that does not say so reads as more separate work than there was.
    It is said of the jobs rather than of the entries, because the reader who
    counts the entries that read alike finds a pair the count left out: an entry
    says only as much of its brief as reads plainly, so two different jobs can
    come out of it saying the same thing. Counted on the briefs as they were
    written down for the same reason.
    """
    written = [key for key in (_same_work(record) for record in jobs) if key]
    again = len(written) - len(set(written))
    if not again:
        return ""
    subject = ("One of the jobs below was the same brief sent out a second time"
               if again == 1 else
               f"{again} of the jobs below were the same brief sent out a second time")
    separate = _count(len(jobs) - again, "separate piece of work",
                      "separate pieces of work")
    return f"{subject}, so this window covers {separate}, not {len(jobs)}."


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
        how = ("and it has been passed on to you" if not unsent and len(for_you) == 1
               else "and all of them have been passed on to you" if not unsent
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

    # Said next to that promise, because it is the exception to it.
    if (lost := data.get("unreadable") or 0):
        head += ["", _wrap(_upper(f"{_count(lost, 'record', 'records')} could not be read "
                                  f"and {'is' if lost == 1 else 'are'} not counted below."),
                           indent="")]

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
