#!/usr/bin/env python3
"""Export an offline legacy SQLite/JSON copy into a vNext archive manifest.

This command is intentionally a copy reader.  It opens SQLite with
``mode=ro``, never contacts a legacy service, and writes only the requested
manifest path.  ``--dry-run`` is the default operating mode for a rehearsal;
pass ``--output`` without it to materialise the manifest.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from wuji_core.archive.importer import ARCHIVE_FORMAT

UTC = timezone.utc


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_value(value: object) -> object:
    if isinstance(value, bytes):
        return {"encoding": "base64", "sha256": sha256(value).hexdigest(), "size": len(value)}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return str(value)


def _entity_type(table: str) -> str:
    value = table.lower().strip().replace("-", "_")
    aliases = {
        "facts": "claim",
        "fact": "claim",
        "claims": "claim",
        "observations": "observation",
        "artifacts": "artifact",
        "artifact_objects": "artifact",
        "intents": "intent",
        "runs": "agent_run",
        "agent_runs": "agent_run",
        "work_items": "work_item",
        "goals": "goal",
    }
    if value in aliases:
        return aliases[value]
    if value.endswith("s"):
        value = value[:-1]
    return value or "record"


def _record_id(row: Mapping[str, Any], index: int) -> str:
    preferred = ("id", "record_id", "entity_id", "uuid", "key", "name")
    for key in preferred:
        if row.get(key) not in (None, ""):
            return str(row[key])
    for key, value in row.items():
        if key.endswith("_id") and value not in (None, ""):
            return str(value)
    return f"legacy-{index}"


def _source_hash(row: Mapping[str, Any]) -> str | None:
    for key in ("source_hash", "sha256", "digest", "body_sha256", "content_hash"):
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _read_json(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(document, Mapping) and isinstance(document.get("records"), list):
        records = [dict(item) for item in document["records"] if isinstance(item, Mapping)]
        relations = [dict(item) for item in document.get("relations", []) if isinstance(item, Mapping)]
        artifacts = [dict(item) for item in document.get("artifacts", []) if isinstance(item, Mapping)]
        permissions = document.get("permissions", {})
        return records, relations, artifacts, dict(permissions) if isinstance(permissions, Mapping) else {}
    if isinstance(document, list):
        return [
            {"entity_type": "record", "id": str(index), "payload": _json_value(item)}
            for index, item in enumerate(document, start=1)
        ], [], [], {}
    if isinstance(document, Mapping):
        return [
            {"entity_type": "record", "id": key, "payload": _json_value(value)}
            for key, value in document.items()
        ], [], [], {}
    raise ValueError("legacy JSON copy must contain an object, array, or records array")


def _read_sqlite(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    uri = f"file:{path.resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    records: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    try:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        record_index = 0
        for table_row in tables:
            table = table_row[0]
            columns = [item[1] for item in connection.execute(f'PRAGMA table_info("{table}")').fetchall()]
            if not columns:
                continue
            rows = connection.execute(f'SELECT * FROM "{table}"').fetchall()
            entity_type = _entity_type(table)
            for row in rows:
                record_index += 1
                raw = {column: _json_value(row[column]) for column in columns}
                record = {
                    "entity_type": entity_type,
                    "id": _record_id(raw, record_index),
                    "revision": raw.get("revision", "1"),
                    "source_id": _record_id(raw, record_index),
                    "source_hash": _source_hash(raw),
                    "display_kind": "LegacyClaim" if entity_type == "claim" else "LegacyRecord",
                    "payload": raw,
                }
                records.append(record)
                if entity_type == "artifact" or "artifact" in table.lower():
                    artifacts.append(
                        {
                            "id": record["id"],
                            "source_id": record["source_id"],
                            "sha256": record["source_hash"],
                            "metadata": raw,
                        }
                    )
                source = next((raw.get(key) for key in ("from_id", "source_id", "parent_id") if raw.get(key)), None)
                target = next((raw.get(key) for key in ("to_id", "target_id", "child_id") if raw.get(key)), None)
                if source is not None and target is not None:
                    relations.append(
                        {
                            "source_id": str(source),
                            "target_id": str(target),
                            "kind": str(raw.get("relation", raw.get("kind", table))),
                            "source_table": table,
                        }
                    )
    finally:
        connection.close()
    return records, relations, artifacts, {}


def build_manifest(
    source: str | Path,
    *,
    archive_id: str | None = None,
    source_version: str | None = None,
    permissions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source_path = Path(source).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if source_path.suffix.lower() in {".sqlite", ".sqlite3", ".db"}:
        records, relations, artifacts, embedded_permissions = _read_sqlite(source_path)
    else:
        records, relations, artifacts, embedded_permissions = _read_json(source_path)
    source_digest = sha256(source_path.read_bytes()).hexdigest()
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "format": ARCHIVE_FORMAT,
        "archive_id": archive_id or f"archive-{source_digest[:16]}",
        "source_version": source_version or f"legacy:{source_path.name}",
        "exported_at": now,
        "source": {"name": source_path.name, "sha256": source_digest},
        "source_sha256": source_digest,
        "permissions": dict(permissions if permissions is not None else embedded_permissions),
        "records": records,
        "relations": relations,
        "artifacts": artifacts,
        "executable": False,
    }


def write_manifest(manifest: Mapping[str, Any], destination: str | Path) -> None:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical(manifest) + "\n", encoding="utf-8")


def _permissions(path: str | None) -> dict[str, Any] | None:
    if path is None:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("permissions manifest must be a JSON object")
    return dict(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="offline SQLite or JSON copy")
    parser.add_argument("--output", type=Path, help="manifest output; omitted in dry-run mode")
    parser.add_argument("--archive-id")
    parser.add_argument("--source-version")
    parser.add_argument("--permissions", type=Path, help="offline permissions/authorization manifest")
    parser.add_argument("--dry-run", action="store_true", help="validate and print a bounded summary")
    args = parser.parse_args(argv)
    try:
        manifest = build_manifest(
            args.input,
            archive_id=args.archive_id,
            source_version=args.source_version,
            permissions=_permissions(str(args.permissions)) if args.permissions else None,
        )
        summary = {
            "archive_id": manifest["archive_id"],
            "source_version": manifest["source_version"],
            "source_sha256": manifest["source_sha256"],
            "record_count": len(manifest["records"]),
            "relation_count": len(manifest["relations"]),
            "artifact_count": len(manifest["artifacts"]),
            "executable": False,
            "dry_run": bool(args.dry_run or args.output is None),
        }
        if args.output and not args.dry_run:
            write_manifest(manifest, args.output)
            summary["output"] = str(args.output)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError) as error:
        print(f"archive export failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
