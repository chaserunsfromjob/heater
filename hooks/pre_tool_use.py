#!/usr/bin/env python3
"""The guard. Runs before every tool call and answers allow, deny, or warn.

It denies only the destructive spellings it is certain about. Everything else is
the agent's judgment, informed by a warning that names the rule it is about to
lean on. A warning never blocks, so the guard cannot stall work inside a
project's own domain.

Read from stdin, write a decision to stdout, always exit 0.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from heater_hook import allow, deny, is_dispatched, log, run, warn  # noqa: E402

RULES = "rules/global.md"

# Files whose contents are secrets. Matched anywhere in a command or a path.
SECRET_FILE = re.compile(
    r"(?:^|[\s/'\"=])(?:"
    r"\.env(?:\.[\w.-]+)?"
    r"|id_(?:rsa|dsa|ecdsa|ed25519)"
    r"|\.netrc|\.pgpass|\.npmrc|\.pypirc"
    r"|credentials(?:\.\w+)?"
    r"|secrets?\.(?:ya?ml|json|toml|env)"
    r"|service[-_]account.*\.json"
    r")(?:$|[\s'\":;)])",
    re.I,
)

# Commands that put a file's contents on screen or into the transcript.
READS_A_FILE = re.compile(
    r"\b(?:cat|bat|less|more|head|tail|strings|xxd|od|nl|grep|rg|ag|awk|sed|cp|"
    r"source|\.)\b",
    re.I,
)

# Environment dumps that would print every secret this process holds.
ENV_DUMP = re.compile(r"\b(?:printenv|env)\s*(?:\||>|$)|\bset\s*\|\s*grep\b", re.I)
SECRET_VAR = re.compile(r"\$\{?\w*(?:SECRET|TOKEN|PASSWORD|PASSWD|APIKEY|API_KEY|PRIVATE_KEY|ACCESS_KEY)\w*\}?", re.I)

# Deny list: each entry is (pattern, the rule it enforces).
DENY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bgit\s+push\b[^|;&]*(?:--force(?!-with-lease)\b|--force-with-lease\b|\s-f\b)"),
     "Never force-push."),
    (re.compile(r"\bgit\s+push\b[^|;&]*\s\+[\w./-]+:"),
     "Never force-push. A leading + in a refspec is a force-push."),
    (re.compile(r"\bgit\s+(?:filter-branch|filter-repo)\b"),
     "Never rewrite pushed history."),
    (re.compile(r"\bgit\s+reflog\s+expire\b"),
     "Never rewrite pushed history. Expiring the reflog destroys the recovery path."),
    (re.compile(r"\bgit\s+update-ref\s+-d\b"),
     "Never rewrite pushed history."),
    (re.compile(r"\brm\s+(?:-\w*[rf]\w*\s+)+(?:/|~|\$HOME|/\*|\*|\.|\.\.)\s*(?:$|;|&|\|)"),
     "Never mass-delete paths; stage and remove explicit paths."),
]

# Warn list: allowed, but the agent is told which rule it is standing on.
WARN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bgit\s+add\s+(?:-A\b|--all\b|\.\s*$|\.\s*(?:;|&|\|))"),
     "Never mass-delete paths; stage explicit paths with `git add <path>`."),
    (re.compile(r"\bgit\s+reset\s+--hard\b"),
     "State a real undo path before any irreversible action. A hard reset discards uncommitted work permanently."),
    (re.compile(r"\bgit\s+clean\s+-\w*[fdx]"),
     "State a real undo path before any irreversible action. Cleaning removes untracked files permanently."),
    (re.compile(r"\bgit\s+commit\b[^|;&]*--amend\b"),
     "Never rewrite pushed history. Amending is safe only while the commit is unpushed."),
]

# Git subcommands that change a repository's recorded state.
GIT_WRITE = re.compile(r"\bgit\s+(?:commit|push|merge|rebase|tag|cherry-pick|revert|am)\b")

STOKER_WARNING = (
    "Route every change to a repository through the stoker. "
    "This session carries no dispatch marker, so this write is an unrouted change."
)


def cited(rule: str) -> str:
    return f"{rule} [{RULES}]"


def check_command(command: str) -> dict[str, Any]:
    for pattern, rule in DENY_PATTERNS:
        if pattern.search(command):
            return deny(cited(rule))

    if ENV_DUMP.search(command) or SECRET_VAR.search(command):
        return deny(cited("Never read, print, or commit a secret; reference the variable name instead of its value."))

    if SECRET_FILE.search(command) and READS_A_FILE.search(command):
        return deny(cited("Never read, print, or commit a secret; reference the variable name instead of its value."))

    for pattern, rule in WARN_PATTERNS:
        if pattern.search(command):
            return warn(cited(rule))

    if GIT_WRITE.search(command) and not is_dispatched():
        return warn(cited(STOKER_WARNING))

    return allow()


def check_path(tool_name: str, path: str) -> dict[str, Any]:
    if not path:
        return allow()
    if SECRET_FILE.search(f" {path} ") and tool_name in ("Read", "NotebookRead"):
        return deny(cited("Never read, print, or commit a secret; reference the variable name instead of its value."))
    return allow()


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return allow()

    if tool_name == "Bash":
        decision = check_command(str(tool_input.get("command") or ""))
    else:
        decision = check_path(tool_name, str(tool_input.get("file_path") or ""))

    verdict = decision.get("hookSpecificOutput", {}).get("permissionDecision")
    if verdict:
        log("guard", {"tool": tool_name, "decision": verdict,
                      "reason": decision.get("hookSpecificOutput", {}).get("permissionDecisionReason")
                                or decision.get("systemMessage")})
    return decision


if __name__ == "__main__":
    raise SystemExit(run(handle, "pre_tool_use"))
