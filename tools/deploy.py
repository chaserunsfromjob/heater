#!/usr/bin/env python3
"""Deploy fleet files onto this machine as symlinks into the repo.

A copy can go stale between deploys; a symlink cannot. Edit a rule here, pull on
a machine, and that machine is already following the new rule.

    bin/deploy.py            # create or repair every link
    bin/deploy.py --check    # report drift only, change nothing (used by the gate)

Anything already at a target path that is not our symlink is moved aside to
`<name>.pre-heater` rather than deleted.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLAUDE_HOME = Path.home() / ".claude"

def links() -> dict[Path, Path]:
    """target on this machine -> file or directory in this repo.

    Agents and skills are discovered rather than listed, so adding one is a
    matter of adding the file. Each is linked individually: linking the whole
    ~/.claude/agents directory would displace anything else the operator keeps
    there.
    """
    table: dict[Path, Path] = {
        CLAUDE_HOME / "CLAUDE.md": REPO / "rules" / "global.md",
    }
    for agent in sorted((REPO / "agents").glob("*.md")):
        table[CLAUDE_HOME / "agents" / agent.name] = agent
    for skill in sorted((REPO / "skills").iterdir() if (REPO / "skills").exists() else []):
        if (skill / "SKILL.md").is_file():
            table[CLAUDE_HOME / "skills" / skill.name] = skill
    return table


LINKS: dict[Path, Path] = links()

SETTINGS = CLAUDE_HOME / "settings.json"
HOOK_DIR = REPO / "hooks"


def hook_groups() -> dict[str, list[dict]]:
    """The hook registrations this repo owns, with absolute paths to its scripts."""
    return {
        "PreToolUse": [{
            # create_session is matched too: the guard denies a session opening
            # its own successor, and that tool is not a Bash command.
            "matcher": "Bash|Read|Edit|Write|NotebookEdit|.*create_session",
            "hooks": [{"type": "command", "command": str(HOOK_DIR / "pre_tool_use.py"), "timeout": 10}],
        }],
        "PostToolUse": [{
            "matcher": "*",
            "hooks": [{"type": "command", "command": str(HOOK_DIR / "post_tool_use.py"), "timeout": 5}],
        }],
        "Stop": [{
            "hooks": [{"type": "command", "command": str(HOOK_DIR / "stop.py"), "timeout": 10}],
        }],
        "SessionStart": [{
            "hooks": [{"type": "command", "command": str(HOOK_DIR / "session_start.py"), "timeout": 10}],
        }],
        "PreCompact": [{
            "hooks": [{"type": "command", "command": str(HOOK_DIR / "pre_compact.py"), "timeout": 5}],
        }],
        # SessionEnd hooks share a 1.5s budget unless a longer timeout raises it.
        "SessionEnd": [{
            "hooks": [{"type": "command", "command": str(HOOK_DIR / "session_end.py"), "timeout": 5}],
        }],
    }


# Claude Code expands this to the project root, so a settings file committed in
# the repository works in any copy of it without knowing where it lives.
PROJECT_ROOT_VAR = "${CLAUDE_PROJECT_DIR}"
PROJECT_SETTINGS = REPO / ".claude" / "settings.json"


def portable(text: str) -> str:
    return str(text).replace(str(REPO), PROJECT_ROOT_VAR)


def project_settings() -> dict:
    """The same registration, with paths that travel.

    A machine-level install reaches every project on that machine. This reaches
    every copy of this project on any machine, with nothing to run first — which
    is what makes a fresh clone, including a cloud container, arrive switched on.
    """
    hooks = {
        event: [{**group, "hooks": [{**h, "command": portable(h["command"])} for h in group["hooks"]]}
                for group in groups]
        for event, groups in hook_groups().items()
    }
    line = {**status_line(), "command": portable(status_line()["command"])}
    return {"hooks": hooks, "statusLine": line}


def write_project_settings() -> Path:
    PROJECT_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    PROJECT_SETTINGS.write_text(json.dumps(project_settings(), indent=2) + "\n", encoding="utf-8")
    return PROJECT_SETTINGS


def status_line() -> dict:
    """The status line is the only thing told how full the context window is, so
    it is what makes automatic handover possible. Hooks are never told."""
    return {"type": "command", "command": str(HOOK_DIR / "statusline.py"), "padding": 0}


def is_ours(group: dict) -> bool:
    """True when every handler in the group points at a script in this repo."""
    handlers = group.get("hooks") or []
    return bool(handlers) and all(
        str(h.get("command", "")).startswith(str(HOOK_DIR)) for h in handlers
    )


def merge_hooks(existing: dict) -> dict:
    """Replace only the groups this repo owns; leave every other hook untouched.

    Symlinking settings.json would wipe whatever else the operator has configured,
    so this merges instead.
    """
    merged = {event: list(groups) for event, groups in existing.items()}
    for event, ours in hook_groups().items():
        theirs = [g for g in merged.get(event, []) if not is_ours(g)]
        merged[event] = theirs + ours
    return merged


def read_settings() -> dict:
    if not SETTINGS.exists():
        return {}
    try:
        parsed = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def settings_drift() -> str | None:
    current = read_settings()
    if not SETTINGS.exists():
        return "not deployed"
    if current.get("hooks") != merge_hooks(current.get("hooks") or {}):
        return "hook registration out of date"
    existing = current.get("statusLine") or {}
    if not existing:
        return "no status line, so nothing can see context usage and handover cannot fire"
    if not str(existing.get("command", "")).startswith(str(HOOK_DIR)):
        return ("a status line is configured that is not this repository's, so context usage "
                "is invisible and automatic handover will never fire; replace it or merge it "
                "with hooks/statusline.py")
    return None


def deploy_settings() -> str:
    current = read_settings()
    updated = {**current, "hooks": merge_hooks(current.get("hooks") or {})}

    # Never replace an operator's own status line. Deploy reports it as drift
    # instead, because silently taking it over is worse than saying so.
    existing = current.get("statusLine") or {}
    if not existing or str(existing.get("command", "")).startswith(str(HOOK_DIR)):
        updated["statusLine"] = status_line()
    if updated == current and SETTINGS.exists():
        return "already correct"
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    if SETTINGS.exists():
        backup = SETTINGS.with_name(SETTINGS.name + ".pre-heater")
        backup.write_text(SETTINGS.read_text(encoding="utf-8"), encoding="utf-8")
    SETTINGS.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    return "hooks registered"


def describe(target: Path, source: Path) -> str | None:
    """Return a drift description, or None when the link is already correct."""
    if not source.exists():
        return f"source missing: {source}"
    if not target.exists() and not target.is_symlink():
        return "not deployed"
    if not target.is_symlink():
        return "occupied by a real file"
    if target.resolve() != source.resolve():
        return f"points at {target.resolve()}"
    return None


def deploy(target: Path, source: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or target.exists():
        if target.is_symlink() and target.resolve() == source.resolve():
            return "already correct"
        if target.is_symlink():
            target.unlink()
            action = "relinked"
        else:
            aside = target.with_name(target.name + ".pre-heater")
            target.replace(aside)
            action = f"moved existing file to {aside.name}, linked"
    else:
        action = "linked"
    target.symlink_to(source)
    return action


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift without changing anything")
    parser.add_argument("--write-project-settings", action="store_true",
                        help="regenerate .claude/settings.json, which makes a fresh clone self-installing")
    args = parser.parse_args(argv[1:])

    if args.write_project_settings:
        print(f"wrote {write_project_settings()}")
        return 0

    drifted = 0
    table = links()
    for target, source in table.items():
        drift = describe(target, source)
        if args.check:
            if drift:
                drifted += 1
                print(f"DRIFT {target}: {drift}")
            continue
        print(f"{target}: {deploy(target, source)}")

    drift = settings_drift()
    if args.check:
        if drift:
            drifted += 1
            print(f"DRIFT {SETTINGS}: {drift}")
    else:
        print(f"{SETTINGS}: {deploy_settings()}")

    if args.check:
        if drifted:
            print(f"\ndeploy: {drifted} target(s) drifted; run bin/deploy.py", file=sys.stderr)
            return 1
        print(f"deploy: {len(table) + 1} target(s) in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
