#!/usr/bin/env python3
"""Import an offline legacy manifest into an archive-only SQLite store."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "wuji-core" / "src"))

from wuji_core.archive import ArchiveImporter, ArchiveStore  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="offline archive manifest")
    parser.add_argument("--database", required=True, type=Path, help="archive-only SQLite path")
    parser.add_argument("--output", type=Path, help="receipt JSON destination")
    args = parser.parse_args(argv)
    try:
        with ArchiveStore(args.database) as store:
            receipt = ArchiveImporter(store).import_archive(args.input)
            document = receipt.as_mapping()
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    encoded = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
