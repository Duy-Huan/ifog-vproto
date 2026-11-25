#!/usr/bin/env python3
"""CLI wrapper for Rule 16 Version-Document Synchronization verification in CI/CD."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tier3_analysis.doc_sync import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
