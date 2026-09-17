#!/usr/bin/env python3
"""When a review loop has ended, for the two readers that have to agree on it.

`dispatch` asks this to decide what may land. `store`'s query asks it to count
how many changes landed. One store, two readers, and they have to read it the
same way: a figure saying eleven changes landed while the sweep refuses to land
any of them is a report nobody can act on. dispatch already imports store, so
store cannot import dispatch back, and the judgement lives here below both of
them rather than as a second copy that drifts.

Nothing here opens a store. It is handed the rounds and says what they mean, so
either caller can pass the rounds it already has in hand.
"""

from __future__ import annotations

from typing import Any

# Review ends when this many consecutive rounds pass finding only wording, which
# is `skills/adversarial-review/SKILL.md`'s rule and not a number picked here.
# One wording-only pass is the second-to-last step of the loop, not its end.
ROUNDS_TO_END_REVIEW = 2

# Except for a change that is only documents, where one such round ends it.
ROUNDS_TO_END_DOCUMENT_REVIEW = 1

# What makes a changed path a document. Suffixes first, then whole directories
# whose contents are prose whatever each file is called.
DOCUMENT_SUFFIXES = (".md", ".txt")
DOCUMENT_DIRECTORIES = ("handover/", "research/results/")


def document(path: str) -> bool:
    """True when this one changed path is prose rather than something that runs."""
    cleaned = path.strip().replace("\\", "/").removeprefix("./")
    if not cleaned:
        return False
    if cleaned.lower().endswith(DOCUMENT_SUFFIXES):
        return True
    return any(cleaned.startswith(d) for d in DOCUMENT_DIRECTORIES)


def document_only(paths: list[str]) -> bool:
    """True when every path a change touches is a document.

    A diff with nothing in it is not a document-only change: it says nothing
    about what changed, and reading silence as prose would land code on one
    round. The same goes for a diff that could not be read at all, which arrives
    here as the same empty list.
    """
    cleaned = [p for p in paths if p.strip()]
    return bool(cleaned) and all(document(p) for p in cleaned)


def rounds_needed(paths: list[str]) -> int:
    """How many consecutive wording-only passes a change over these paths needs."""
    return ROUNDS_TO_END_DOCUMENT_REVIEW if document_only(paths) else ROUNDS_TO_END_REVIEW


def rule_phrase(needed: int) -> str:
    """The rule a refusal quotes, in the words the rule file uses."""
    if needed == ROUNDS_TO_END_DOCUMENT_REVIEW:
        return ("one round passing with wording-only findings, because this branch "
                "changes documents only")
    return f"{needed} consecutive rounds passing with wording-only findings"


def ordered(rounds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """These rounds oldest first, by round number and then by when each arrived.

    Two rounds both called "round 6" settle on the one recorded last rather than
    on whichever the filesystem happened to list first.
    """
    return sorted(rounds, key=lambda r: (r.get("round", 0), r.get("created", "")))


def settled(round_record: dict[str, Any]) -> bool:
    """True when this round is a pass with nothing substantive left outstanding.

    `bin/store.py review` already refuses to record a pass with substantive
    findings. This refuses to act on one anyway: the store is a directory of
    files, and a file can arrive by some route other than that command.
    """
    if round_record.get("verdict") != "pass":
        return False
    return not round_record.get("findings") or bool(round_record.get("wording_only"))


def ended(rounds: list[dict[str, Any]], needed: int = ROUNDS_TO_END_REVIEW) -> bool:
    """True when these rounds are the end of a review loop.

    The latest round decides, never the best one on record: a pass from round 4
    says nothing about a change that rounds 5, 6 and 7 failed. And for anything
    but a document-only change one pass is not the end of the loop — review ends
    on two consecutive rounds that find only wording, so the last two rounds must
    both be settled passes.

    `needed` is how many of those consecutive passes this change takes, which
    only what it changed can say. Callers that cannot see a diff leave it alone
    and get the stricter rule, so a change nobody classified is never landed on
    fewer rounds than code takes.
    """
    counted = ordered(rounds)
    if len(counted) < needed:
        return False
    return all(settled(r) for r in counted[-needed:])
