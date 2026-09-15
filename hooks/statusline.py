#!/usr/bin/env python3
"""The status line, and the only place that learns how full the context is.

Hooks are never told the context window size or usage, so this records it for
them. Rendering is the visible job; recording is the one that matters.

Runs on every render, so it stays cheap and never raises.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import context  # noqa: E402

BAR_WIDTH = 10


def bar(percentage: float) -> str:
    filled = min(BAR_WIDTH, max(0, round(percentage / 100 * BAR_WIDTH)))
    return "#" * filled + "." * (BAR_WIDTH - filled)


def render(payload: dict, used: float | None) -> str:
    model = (payload.get("model") or {}).get("display_name") or "claude"
    branch = (payload.get("workspace") or {}).get("git_worktree") or ""
    cost = (payload.get("cost") or {}).get("total_cost_usd")

    parts = [f"[{model}]"]
    if used is not None:
        mark = " HANDOVER DUE" if used >= context.threshold() else ""
        parts.append(f"{bar(used)} {used:.0f}%{mark}")
    if isinstance(cost, (int, float)):
        parts.append(f"${cost:.2f}")
    if branch:
        parts.append(branch)
    return "  ".join(parts)


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        payload = payload if isinstance(payload, dict) else {}
    except (json.JSONDecodeError, OSError):
        payload = {}
    try:
        used = context.record(payload)
        print(render(payload, used))
    except Exception:
        print("[claude]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
