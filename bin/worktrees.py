#!/usr/bin/env python3
"""Entry point for worktree leases. All logic lives in tools/worktrees.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import worktrees  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(worktrees.main(sys.argv))
