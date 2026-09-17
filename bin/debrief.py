#!/usr/bin/env python3
"""Entry point for the fleet debrief. All logic lives in tools/debrief.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import debrief  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(debrief.main(sys.argv))
