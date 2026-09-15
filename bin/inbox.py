#!/usr/bin/env python3
"""CLI entry point for the findings inbox."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import inbox  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(inbox.main(sys.argv))
