#!/usr/bin/env python3
"""Build a conservative P17 acceptance report from recorded results.

The acceptance catalog is the source of required case IDs.  A missing result is
always ``not_run``; the command never turns an empty or skipped result into a
pass.  It only summarizes recorded evidence and does not execute tests or
contact a model, tool, or target.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


VALID_STATUSES = {"pass", "fail", "not_run", "blocked"}


def build_report(catalog: list[dict[str, Any]], recorded: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge recorded results into every catalog case without inventing evidence."""

    by_id: dict[str, dict[str, Any]] = {}
    for item in recorded:
        case_id = item.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("every recorded result requires case_id")
        if case_id in by_id:
            raise ValueError(f"duplicate recorded result: {case_id}")
        status = item.get("status")
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid status for {case_id}: {status!r}")
        if status == "pass" and (
            not item.get("command")
            or item.get("exit_code") != 0
            or not item.get("evidence_refs")
        ):
            raise ValueError(f"pass result lacks command, exit_code=0, or evidence: {case_id}")
        by_id[case_id] = dict(item)

    results: list[dict[str, Any]] = []
    catalog_ids: set[str] = set()
    for case in catalog:
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("every catalog case requires id")
        if case_id in catalog_ids:
            raise ValueError(f"duplicate catalog case: {case_id}")
        catalog_ids.add(case_id)
        result = dict(by_id.pop(case_id, {"case_id": case_id, "status": "not_run"}))
        results.append({
            "case_id": case_id,
            "title": case.get("title"),
            "tasks": case.get("tasks", []),
            "status": result["status"],
            "command": result.get("command"),
            "exit_code": result.get("exit_code"),
            "evidence_refs": result.get("evidence_refs", []),
            "note": result.get("note"),
        })
    if by_id:
        raise ValueError("recorded result is not in the catalog: " + ", ".join(sorted(by_id)))

    counts = {status: sum(item["status"] == status for item in results) for status in VALID_STATUSES}
    overall = "pass" if results and counts["pass"] == len(results) else "incomplete"
    return {
        "schema_version": "wuji.acceptance-report.v1",
        "overall_status": overall,
        "case_count": len(results),
        "counts": counts,
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
        recorded = json.loads(args.results.read_text(encoding="utf-8")) if args.results else []
        if not isinstance(catalog, list) or not isinstance(recorded, list):
            raise ValueError("catalog and results must be JSON arrays")
        report = build_report(catalog, recorded)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
