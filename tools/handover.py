#!/usr/bin/env python3
"""Prove a session is safe to end.

Clearing a session is cheap and safe exactly when the durable record is
complete. This checks that it is: the work is committed, it is pushed, the suite
is green, and HANDOVER.md describes the commit that is actually at the tip.

    bin/handover.py           # check, and say what is missing
    bin/handover.py --quick   # skip the suite, check the git state only

Exit 0 means safe to clear.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HANDOVER = REPO / "HANDOVER.md"
STAMP = re.compile(r"<!--\s*handover-commit:\s*([0-9a-f]{7,40})\s*-->")


def git(*args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def stamped_commit() -> str | None:
    if not HANDOVER.exists():
        return None
    match = STAMP.search(HANDOVER.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def check_handover_exists() -> str | None:
    if not HANDOVER.exists():
        return "HANDOVER.md does not exist; the next session starts blind"
    if stamped_commit() is None:
        return "HANDOVER.md has no <!-- handover-commit: SHA --> stamp, so staleness cannot be detected"
    return None


def check_worktree_clean() -> str | None:
    code, out = git("status", "--porcelain")
    if code != 0:
        return f"could not read git status: {out}"
    return f"uncommitted changes in {len(out.splitlines())} file(s); they do not survive a cleared session" if out else None


def check_handover_current() -> str | None:
    """The handover is stale once real work has landed on top of it."""
    sha = stamped_commit()
    if sha is None:
        return None  # already reported
    code, out = git("diff", "--name-only", sha, "HEAD")
    if code != 0:
        return f"HANDOVER.md names commit {sha}, which is not in this repository"
    changed = [line for line in out.splitlines() if line and line != "HANDOVER.md"]
    if changed:
        listed = ", ".join(changed[:4]) + (" and more" if len(changed) > 4 else "")
        return f"HANDOVER.md describes {sha}, but work has landed since: {listed}"
    return None


def check_pushed() -> str | None:
    code, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if code != 0:
        return None
    code, _ = git("rev-parse", "--verify", f"origin/{branch}")
    if code != 0:
        return f"branch {branch} has no counterpart on origin; push it before clearing"
    code, out = git("rev-list", "--count", f"origin/{branch}..HEAD")
    if code != 0:
        return None
    count = out.strip()
    return f"{count} commit(s) not pushed to origin/{branch}" if count.isdigit() and int(count) else None


def check_gate() -> str | None:
    result = subprocess.run(["bash", str(REPO / "bin" / "gate.sh")], cwd=REPO, capture_output=True, text=True)
    return None if result.returncode == 0 else "bin/gate.sh fails; a handover over a red suite hands over a broken repo"


CHECKS = [
    ("handover note", check_handover_exists),
    ("handover is current", check_handover_current),
    ("working tree clean", check_worktree_clean),
    ("pushed to origin", check_pushed),
]


def check_no_worker_out() -> str | None:
    """A dispatched worker still owes a report; its brief lives in this session."""
    try:
        sys.path.insert(0, str(REPO / "tools"))
        import dispatch
        out = dispatch.live()
    except Exception:
        return None
    return f"{len(out)} worker(s) still out" if out else None


def in_flight() -> list[str]:
    """Signs that work is mid-flow rather than at a natural stopping point.

    Being mid-task has an objective signature: changes not committed, commits not
    pushed, or a worker still owed a reply. At a real boundary all three are
    clear, and a fresh session can pick up from the repository alone.
    """
    checks = (("uncommitted work", check_worktree_clean),
              ("unpushed work", check_pushed),
              ("workers out", check_no_worker_out))
    return [problem for _, check in checks if (problem := check())]


def at_boundary() -> bool:
    return not in_flight()


def problems(quick: bool = True) -> list[str]:
    """Every reason this session is not safe to end, named. Empty means safe."""
    checks = list(CHECKS) + ([] if quick else [("suite green", check_gate)])
    return [f"{name}: {problem}" for name, check in checks if (problem := check())]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="skip the suite; check git state only")
    args = parser.parse_args(argv[1:])

    checks = list(CHECKS) + ([] if args.quick else [("suite green", check_gate)])

    problems = []
    for name, check in checks:
        problem = check()
        print(f"{'FAIL' if problem else ' ok '}  {name}" + (f"\n        {problem}" if problem else ""))
        if problem:
            problems.append(problem)

    print()
    if problems:
        print(f"handover: NOT safe to clear, {len(problems)} problem(s) above", file=sys.stderr)
        return 1
    print("handover: safe to clear")
    # Said here because this is the moment it is acted on, and getting it wrong
    # is invisible: the successor opens, works, and is filed under no project.
    print("next session: the operator opens it from the project, not this session")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
