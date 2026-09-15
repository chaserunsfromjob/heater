#!/usr/bin/env python3
"""CLI entry point for the review and suite stores."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import store  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(store.main(sys.argv))
