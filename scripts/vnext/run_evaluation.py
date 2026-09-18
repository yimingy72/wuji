#!/usr/bin/env python3
"""Summarize an already-recorded vNext evaluation without making requests.

Example::

    scripts/vnext/run_evaluation.py --input run.json --output summary.json

The input is intentionally offline JSON.  Real-model execution is a separate,
explicitly authorized operation and is not implemented by this command.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "wuji-core" / "src"))

from wuji_core.evaluation.accounting import AccountingError, evaluate_run  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        document = json.loads(args.input.read_text(encoding="utf-8"))
        summary = evaluate_run(document)
    except (OSError, json.JSONDecodeError, AccountingError) as exc:
        parser.error(str(exc))
    encoded = json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
