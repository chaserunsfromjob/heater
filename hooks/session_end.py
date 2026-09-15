#!/usr/bin/env python3
"""Record how a session ended, and what it left unsynced.

SessionEnd shares a 1.5 second budget across every hook, and it cannot block
termination. That rules out committing and pushing the fleet repository here: a
push that is cut off halfway is worse than no push, and there is no way to report
the failure. So this records what is outstanding and leaves the write to a
session that can supervise it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from heater_hook import REPO, heartbeat_dir, log, role, run, stop  # noqa: E402

TRACKED = ("queue/", "store/", "inbox/")


def unsynced() -> list[str]:
    """Fleet state changed in this session and not yet committed."""
    try:
        result = subprocess.run(["git", "status", "--porcelain", *TRACKED], cwd=REPO,
                                capture_output=True, text=True, timeout=1)
    except (subprocess.SubprocessError, OSError):
        return []
    if result.returncode != 0:
        return []
    return [line[3:] for line in result.stdout.splitlines() if line.strip()]


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    outstanding = unsynced()
    log("session_end", {"reason": payload.get("reason"), "role": role() or None,
                        "unsynced": outstanding[:20], "unsynced_count": len(outstanding)})

    session = payload.get("session_id")
    if session:
        beat = heartbeat_dir() / f"{session}.json"
        beat.unlink(missing_ok=True)
    return stop()


if __name__ == "__main__":
    raise SystemExit(run(handle, "session_end"))
