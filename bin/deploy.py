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
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLAUDE_HOME = Path.home() / ".claude"

# target on this machine -> file in this repo
LINKS: dict[Path, Path] = {
    CLAUDE_HOME / "CLAUDE.md": REPO / "rules" / "global.md",
}


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
    args = parser.parse_args(argv[1:])

    drifted = 0
    for target, source in LINKS.items():
        drift = describe(target, source)
        if args.check:
            if drift:
                drifted += 1
                print(f"DRIFT {target}: {drift}")
            continue
        print(f"{target}: {deploy(target, source)}")

    if args.check:
        if drifted:
            print(f"\ndeploy: {drifted} target(s) drifted; run bin/deploy.py", file=sys.stderr)
            return 1
        print(f"deploy: {len(LINKS)} target(s) in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
