#!/usr/bin/env python3
"""A heartbeat, so a watcher can tell a quiet worker from a dead one.

Runs after every tool call, so it must stay cheap: one small file overwritten,
no reads, no appends that grow without bound. It records that a tool call
returned, not what it returned.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from heater_hook import heartbeat_dir, now, role, run, stop  # noqa: E402

SAFE_ID = re.compile(r"[^A-Za-z0-9_-]")


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    session = SAFE_ID.sub("_", str(payload.get("session_id") or "unknown"))[:64]
    directory = heartbeat_dir()
    directory.mkdir(parents=True, exist_ok=True)
    beat = {"at": now(), "session": session, "role": role() or None,
            "tool": payload.get("tool_name"), "cwd": payload.get("cwd")}
    (directory / f"{session}.json").write_text(json.dumps(beat) + "\n", encoding="utf-8")
    return stop()


if __name__ == "__main__":
    raise SystemExit(run(handle, "post_tool_use"))
