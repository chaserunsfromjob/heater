#!/usr/bin/env python3
"""Style linter for heater rule files.

Rules are files, and the files are tested. This enforces the writing style that
keeps a rule file from drifting into prose: one rule per bullet, imperative,
under fifty words, no history, no dates, and each rule stated in exactly one
place across the whole tree.

    tools/style_lint.py [PATH ...]

Defaults to `rules/` and `roles/`. Exits 0 when everything passes, 1 otherwise.
"""

from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

MAX_WORDS = 50
MAX_SENTENCES = 2
# Character-level, so a plural or a swapped article still reads as a restatement.
# Measured against the real rule files, genuine near-misses sit below 0.60.
NEAR_DUPLICATE_RATIO = 0.85
NEAR_DUPLICATE_MIN_TOKENS = 5

DEFAULT_TARGETS = ("rules", "roles")

# A rule is a command. These openers make it a statement, a hedge, or a story.
BANNED_OPENERS = {
    "a", "agents", "all", "an", "any", "consider", "every", "generally", "i",
    "ideally", "it", "maybe", "our", "perhaps", "possibly", "probably",
    "should", "that", "the", "there", "they", "this", "try", "typically",
    "usually", "we", "workers", "you",
}

# Prose that belongs in a commit message, not in a rule.
BANNED_PHRASES = (
    "as of",
    "for now",
    "going forward",
    "historically",
    "in the past",
    "note that",
    "previously",
    "same as above",
    "see above",
    "used to",
    "we decided",
)

DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b", re.I)
CODE_SPAN_RE = re.compile(r"`[^`]*`")
FENCE_RE = re.compile(r"^\s*```")
BULLET_RE = re.compile(r"^- +(\S.*)$")
CONTINUATION_RE = re.compile(r"^ {2,}(\S.*)$")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
NORMALISE_RE = re.compile(r"[^a-z0-9]+")


class Finding:
    def __init__(self, path: Path, line: int, code: str, message: str) -> None:
        self.path = path
        self.line = line
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.code} {self.message}"


def mask_code(text: str) -> str:
    """Collapse each code span to one token so commands do not blow the budget."""
    return CODE_SPAN_RE.sub("CMD", text)


def normalise(text: str) -> str:
    return NORMALISE_RE.sub(" ", mask_code(text).lower()).strip()


def parse_rules(path: Path) -> list[tuple[int, str]]:
    """Return (line number, full text) for every top-level bullet in the file."""
    rules: list[tuple[int, str]] = []
    in_fence = False
    current: list[str] | None = None
    start = 0

    def flush() -> None:
        nonlocal current, start
        if current is not None:
            rules.append((start, " ".join(current).strip()))
            current = None

    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if FENCE_RE.match(raw):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        bullet = BULLET_RE.match(raw)
        if bullet:
            flush()
            current, start = [bullet.group(1)], number
            continue

        if current is not None:
            continuation = CONTINUATION_RE.match(raw)
            if continuation:
                current.append(continuation.group(1))
            else:
                flush()

    flush()
    return rules


def check_rule(path: Path, line: int, text: str) -> list[Finding]:
    findings: list[Finding] = []
    masked = mask_code(text)

    words = masked.split()
    if len(words) > MAX_WORDS:
        findings.append(Finding(path, line, "LONG", f"{len(words)} words, limit {MAX_WORDS}"))

    sentences = [s for s in SENTENCE_SPLIT_RE.split(masked.strip()) if s.strip()]
    if len(sentences) > MAX_SENTENCES:
        findings.append(
            Finding(path, line, "MULTI", f"{len(sentences)} sentences, limit {MAX_SENTENCES}; split into one rule per bullet")
        )

    opener = re.sub(r"[^a-z]", "", words[0].lower()) if words else ""
    if opener in BANNED_OPENERS:
        findings.append(Finding(path, line, "OPENER", f"starts with {words[0]!r}; write the rule as a command"))

    lowered = masked.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            findings.append(Finding(path, line, "HISTORY", f"contains {phrase!r}; the commit carries the reason"))

    if DATE_RE.search(masked):
        findings.append(Finding(path, line, "DATE", "contains a date; a rule is timeless"))

    return findings


def check_duplicates(collected: list[tuple[Path, int, str]]) -> list[Finding]:
    """Opinion 8: a rule restated anywhere in the tree is a defect."""
    findings: list[Finding] = []
    seen: dict[str, tuple[Path, int]] = {}

    for path, line, text in collected:
        key = normalise(text)
        if not key:
            continue
        if key in seen:
            first_path, first_line = seen[key]
            findings.append(Finding(path, line, "DUP", f"restates {first_path}:{first_line}"))
        else:
            seen[key] = (path, line)

    keys = [(k, w) for k, w in seen.items() if len(k.split()) >= NEAR_DUPLICATE_MIN_TOKENS]
    for i, (key_a, where_a) in enumerate(keys):
        for key_b, where_b in keys[i + 1:]:
            # Cheap reject: strings this different in length cannot clear the ratio.
            if min(len(key_a), len(key_b)) < NEAR_DUPLICATE_RATIO * max(len(key_a), len(key_b)):
                continue
            ratio = difflib.SequenceMatcher(None, key_a, key_b).ratio()
            if ratio >= NEAR_DUPLICATE_RATIO:
                findings.append(
                    Finding(where_b[0], where_b[1], "NEARDUP", f"{ratio:.0%} identical to {where_a[0]}:{where_a[1]}")
                )

    return findings


def gather(targets: list[str]) -> list[Path]:
    paths: list[Path] = []
    for target in targets:
        path = Path(target)
        if path.is_dir():
            paths.extend(sorted(path.rglob("*.md")))
        elif path.is_file():
            paths.append(path)
    return paths


def lint(targets: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    collected: list[tuple[Path, int, str]] = []

    for path in gather(targets):
        for line, text in parse_rules(path):
            collected.append((path, line, text))
            findings.extend(check_rule(path, line, text))

    findings.extend(check_duplicates(collected))
    findings.sort(key=lambda f: (str(f.path), f.line, f.code))
    return findings


def main(argv: list[str]) -> int:
    targets = argv[1:] or [t for t in DEFAULT_TARGETS if Path(t).exists()]
    if not targets:
        print("style_lint: nothing to check", file=sys.stderr)
        return 0

    findings = lint(targets)
    for finding in findings:
        print(finding)

    checked = len(gather(targets))
    if findings:
        print(f"\nstyle_lint: {len(findings)} problem(s) in {checked} file(s)", file=sys.stderr)
        return 1

    print(f"style_lint: {checked} file(s) clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
