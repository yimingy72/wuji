#!/usr/bin/env python3
"""CLI wrapper for the isolated vNext web manifest renderer."""

from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from ops.vnext.kubernetes.web import main  # noqa: E402


if __name__ == "__main__":
    main()
