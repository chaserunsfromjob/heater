"""Deciding whether two pieces of text say the same thing.

Used twice: the rule linter refuses a rule restated anywhere in the tree, and the
findings inbox refuses a finding already dismissed. Both questions are "is this a
restatement", so both ask it the same way.

Character-level, not token overlap. Measured against the real rule files, a
plural variant of the same sentence scores 0.99 while the closest genuinely
different pair scores 0.60, so a threshold in between separates them with room
to spare. Token overlap scored the same pairs 0.82 and 0.33 — too close.
"""

from __future__ import annotations

import difflib
import re

CODE_SPAN = re.compile(r"`[^`]*`")
NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


def mask_code(text: str) -> str:
    """Collapse each code span to one token so a long command is not the text."""
    return CODE_SPAN.sub("CMD", text)


def normalise(text: str) -> str:
    """Lowercase, strip punctuation and collapse whitespace, so wording is all that is left."""
    return NON_ALPHANUMERIC.sub(" ", mask_code(text).lower()).strip()


def ratio(first: str, second: str) -> float:
    """How identical two already-normalised strings are, from 0.0 to 1.0."""
    if not first or not second:
        return 0.0
    # Strings this different in length cannot clear any useful threshold, and
    # skipping them keeps an all-pairs comparison cheap.
    if min(len(first), len(second)) < 0.5 * max(len(first), len(second)):
        return 0.0
    return difflib.SequenceMatcher(None, first, second).ratio()


def best_match(text: str, candidates: list[str], threshold: float) -> tuple[int, float] | None:
    """The closest candidate at or above the threshold, as (index, ratio)."""
    target = normalise(text)
    best: tuple[int, float] | None = None
    for index, candidate in enumerate(candidates):
        score = ratio(target, normalise(candidate))
        if score >= threshold and (best is None or score > best[1]):
            best = (index, score)
    return best
