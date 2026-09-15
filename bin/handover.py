#!/usr/bin/env python3
"""Entry point for the handover check. All logic lives in tools/handover.py.

bin/ holds only entry points. Nothing here is ever imported, because a module in
bin/ with the same name as one in tools/ shadows it on the import path.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import handover  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(handover.main(sys.argv))
