"""Read-only import of an offline legacy snapshot.

The importer deliberately has no legacy runtime dependency.  It accepts the
JSON manifest emitted by ``export_legacy_readonly.py`` (or an equivalent
mapping), stores it in archive-only SQLite tables, and exposes a small view
used by the v2 read endpoint.  In particular, importing a historical work
record never creates a vNext ``WorkItem`` or a runnable identity.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from wuji_core.contracts.generated import (
    ArchiveView,
    GenericRecord,
    KnowledgeRef,
    NodeEntityType,
    RecordView,
)

ARCHIVE_FORMAT = "wuji.legacy-archive.v1"
_KNOWN_ENTITY_TYPES = {item.value for item in NodeEntityType}
_UTC = timezone.utc


class ArchiveError(ValueError):
    """The archive is malformed or would violate the read-only boundary."""


def _utc_now() -> datetime:
    return datetime.now(_UTC).replace(microsecond=0)


def _iso(value: datetime) -> str:
    return value.astimezone(_UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: object, *, fallback: datetime) -> datetime:
    if not isinstance(value, str) or not value:
        return fallback
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return fallback
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=_UTC)
    return parsed.astimezone(_UTC)


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _text(value: object, default: str) -> str:
    return value if isinstance(value, str) and value else default


def _revision(value: object) -> str:
    if isinstance(value, int) and value > 0:
        return str(value)
    if isinstance(value, str) and value.isdecimal() and int(value) > 0:
        return value
    return "1"


def _safe_json(value: object) -> object:
    """Make sqlite values and arbitrary legacy values JSON serialisable."""

    if isinstance(value, bytes):
        return {"encoding": "base64", "sha256": sha256(value).hexdigest(), "size": len(value)}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_json(item) for item in value]
    return str(value)


@dataclass(frozen=True, slots=True)
class ArchiveRecord:
    """One immutable legacy record retained outside the executable schema."""

    entity_type: str
    record_id: str
    revision: str
    payload: Mapping[str, Any]
    source_id: str
    source_hash: str | None = None
    display_kind: str = "LegacyRecord"

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], *, index: int) -> "ArchiveRecord":
        ref = value.get("ref") if isinstance(value.get("ref"), Mapping) else {}
        payload = value.get("payload", value.get("record"))
        if not isinstance(payload, Mapping):
            payload = {"raw": _safe_json(payload)}
        entity_type = _text(value.get("entity_type", ref.get("entity_type")), "record")
        record_id = _text(
            value.get("record_id", value.get("id", ref.get("id"))), f"legacy-{index}"
        )
        revision = _revision(value.get("revision", ref.get("revision")))
        source_id = _text(value.get("source_id", value.get("original_id")), record_id)
        source_hash = value.get("source_hash", value.get("sha256", value.get("digest")))
        if source_hash is not None and not isinstance(source_hash, str):
            source_hash = str(source_hash)
        default_kind = "LegacyClaim" if entity_type == "claim" else "LegacyRecord"
        return cls(
            entity_type=entity_type,
            record_id=record_id,
            revision=revision,
            payload=_safe_json(payload),  # type: ignore[arg-type]
            source_id=source_id,
            source_hash=source_hash,
            display_kind=_text(value.get("display_kind", value.get("label")), default_kind),
        )

    def as_mapping(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "id": self.record_id,
            "revision": self.revision,
            "source_id": self.source_id,
            "source_hash": self.source_hash,
            "display_kind": self.display_kind,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class ArchiveManifest:
    archive_id: str
    source_version: str
    exported_at: datetime
    records: tuple[ArchiveRecord, ...]
    relations: tuple[Mapping[str, Any], ...] = ()
    artifacts: tuple[Mapping[str, Any], ...] = ()
    permissions: Mapping[str, Any] = None  # type: ignore[assignment]
    source_sha256: str | None = None
    executable: bool = False
    format: str = ARCHIVE_FORMAT

    def __post_init__(self) -> None:
        if self.permissions is None:
            object.__setattr__(self, "permissions", {})

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ArchiveManifest":
        if not isinstance(value, Mapping):
            raise ArchiveError("archive manifest must be a JSON object")
        archive_format = value.get("format", value.get("schema_version", ARCHIVE_FORMAT))
        if archive_format != ARCHIVE_FORMAT:
            raise ArchiveError(f"unsupported archive format: {archive_format!r}")
        if value.get("executable", False) is not False:
            raise ArchiveError("legacy archives are never executable")
        archive_id = _text(value.get("archive_id"), "")
        source_version = _text(value.get("source_version"), "")
        if not archive_id or not source_version:
            raise ArchiveError("archive_id and source_version are required")
        raw_records = value.get("records", [])
        if not isinstance(raw_records, list):
            raise ArchiveError("records must be an array")
        records = tuple(
            ArchiveRecord.from_mapping(item, index=index)
            for index, item in enumerate(raw_records, start=1)
            if isinstance(item, Mapping)
        )
        if len(records) != len(raw_records):
            raise ArchiveError("each archive record must be an object")
        relations = value.get("relations", [])
        artifacts = value.get("artifacts", [])
        permissions = value.get("permissions", {})
        if not isinstance(relations, list) or not all(isinstance(item, Mapping) for item in relations):
            raise ArchiveError("relations must be an array of objects")
        if not isinstance(artifacts, list) or not all(isinstance(item, Mapping) for item in artifacts):
            raise ArchiveError("artifacts must be an array of objects")
        if not isinstance(permissions, Mapping):
            raise ArchiveError("permissions must be an object")
        # A manifest must not smuggle an active execution identity or usable
        # credentials into a read-only copy.  Historical identity fields inside
        # a record remain opaque payload and are never used for dispatch.
        for key in ("active_identity", "credentials", "execution_token", "cutover"):
            if value.get(key) not in (None, False, {}, [], ""):
                raise ArchiveError(f"archive contains forbidden active field: {key}")
        exported_at = _parse_datetime(value.get("exported_at"), fallback=_utc_now())
        source = value.get("source")
        source_sha256 = value.get("source_sha256")
        if source_sha256 is None and isinstance(source, Mapping):
            source_sha256 = source.get("sha256")
        return cls(
            archive_id=archive_id,
            source_version=source_version,
            exported_at=exported_at,
            records=records,
            relations=tuple(dict(item) for item in relations),
            artifacts=tuple(dict(item) for item in artifacts),
            permissions=dict(permissions),
            source_sha256=str(source_sha256) if source_sha256 is not None else None,
            format=archive_format,
        )

    def as_mapping(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "archive_id": self.archive_id,
            "source_version": self.source_version,
            "exported_at": _iso(self.exported_at),
            "source_sha256": self.source_sha256,
            "permissions": dict(self.permissions),
            "records": [record.as_mapping() for record in self.records],
            "relations": [_safe_json(item) for item in self.relations],
            "artifacts": [_safe_json(item) for item in self.artifacts],
            "executable": False,
        }


@dataclass(frozen=True, slots=True)
class ArchiveReceipt:
    archive_id: str
    source_version: str
    imported_at: datetime
    imported_records: int
    source_sha256: str | None
    executable: bool = False

    def as_mapping(self) -> dict[str, Any]:
        return {
            "archive_id": self.archive_id,
            "source_version": self.source_version,
            "imported_at": _iso(self.imported_at),
            "imported_records": self.imported_records,
            "source_sha256": self.source_sha256,
            "executable": False,
        }


def load_archive_manifest(value: ArchiveManifest | Mapping[str, Any] | str | Path) -> ArchiveManifest:
    if isinstance(value, ArchiveManifest):
        return value
    if isinstance(value, (str, Path)):
        path = Path(value)
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ArchiveError(f"cannot read archive manifest: {path}") from error
        value = document
    if not isinstance(value, Mapping):
        raise ArchiveError("archive manifest must be a mapping or JSON path")
    return ArchiveManifest.from_mapping(value)


class ArchiveStore:
    """SQLite archive store with no executable tables or runtime callbacks."""

    def __init__(self, database: str | Path = ":memory:") -> None:
        self.database = str(database)
        # Keep the connection wrapper private and attach the requested file as
        # the vnext database.  This preserves the schema-qualified queries
        # while making a file-backed ArchiveStore survive close/reopen.
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        if self.database == ":memory:":
            self.connection.execute("ATTACH DATABASE ':memory:' AS vnext")
        else:
            self.connection.execute("ATTACH DATABASE ? AS vnext", (str(Path(self.database).resolve()),))
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "ArchiveStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS vnext.archive_catalog (
              archive_id TEXT PRIMARY KEY,
              source_version TEXT NOT NULL,
              exported_at TEXT NOT NULL,
              imported_at TEXT NOT NULL,
              source_sha256 TEXT,
              permissions_json TEXT NOT NULL,
              manifest_json TEXT NOT NULL,
              executable INTEGER NOT NULL CHECK (executable = 0)
            );
            CREATE TABLE IF NOT EXISTS vnext.archive_record (
              archive_id TEXT NOT NULL REFERENCES archive_catalog(archive_id),
              entity_type TEXT NOT NULL,
              record_id TEXT NOT NULL,
              revision TEXT NOT NULL,
              source_id TEXT NOT NULL,
              source_hash TEXT,
              display_kind TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              PRIMARY KEY (archive_id, entity_type, record_id, revision)
            );
            CREATE TABLE IF NOT EXISTS vnext.archive_relation (
              archive_id TEXT NOT NULL REFERENCES archive_catalog(archive_id),
              relation_index INTEGER NOT NULL,
              relation_json TEXT NOT NULL,
              PRIMARY KEY (archive_id, relation_index)
            );
            CREATE TABLE IF NOT EXISTS vnext.archive_artifact (
              archive_id TEXT NOT NULL REFERENCES archive_catalog(archive_id),
              artifact_index INTEGER NOT NULL,
              artifact_json TEXT NOT NULL,
              PRIMARY KEY (archive_id, artifact_index)
            );
            -- Kept as an inert compatibility surface for callers that verify
            -- the archive did not create executable work.
            CREATE TABLE IF NOT EXISTS vnext.work_item (
              source_archive_id TEXT
            );
            """
        )
        self.connection.commit()

    def import_manifest(self, manifest: ArchiveManifest) -> ArchiveReceipt:
        raw = _canonical_json(manifest.as_mapping())
        now = _utc_now()
        existing = self.connection.execute(
            "SELECT manifest_json, imported_at FROM vnext.archive_catalog WHERE archive_id = ?",
            (manifest.archive_id,),
        ).fetchone()
        if existing is not None:
            if existing["manifest_json"] != raw:
                raise ArchiveError("archive_id is already bound to different manifest bytes")
            imported_at = _parse_datetime(existing["imported_at"], fallback=now)
            count = self.connection.execute(
                "SELECT count(*) FROM vnext.archive_record WHERE archive_id = ?",
                (manifest.archive_id,),
            ).fetchone()[0]
            return ArchiveReceipt(
                manifest.archive_id, manifest.source_version, imported_at, int(count), manifest.source_sha256
            )

        with self.connection:
            self.connection.execute(
                "INSERT INTO vnext.archive_catalog(archive_id,source_version,exported_at,imported_at,source_sha256,permissions_json,manifest_json,executable)"
                " VALUES(?,?,?,?,?,?,?,0)",
                (
                    manifest.archive_id,
                    manifest.source_version,
                    _iso(manifest.exported_at),
                    _iso(now),
                    manifest.source_sha256,
                    _canonical_json(manifest.permissions),
                    raw,
                ),
            )
            for record in manifest.records:
                self.connection.execute(
                    "INSERT INTO vnext.archive_record(archive_id,entity_type,record_id,revision,source_id,source_hash,display_kind,payload_json)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (
                        manifest.archive_id,
                        record.entity_type,
                        record.record_id,
                        record.revision,
                        record.source_id,
                        record.source_hash,
                        record.display_kind,
                        _canonical_json(record.payload),
                    ),
                )
            for index, relation in enumerate(manifest.relations):
                self.connection.execute(
                    "INSERT INTO vnext.archive_relation(archive_id,relation_index,relation_json) VALUES(?,?,?)",
                    (manifest.archive_id, index, _canonical_json(relation)),
                )
            for index, artifact in enumerate(manifest.artifacts):
                self.connection.execute(
                    "INSERT INTO vnext.archive_artifact(archive_id,artifact_index,artifact_json) VALUES(?,?,?)",
                    (manifest.archive_id, index, _canonical_json(artifact)),
                )
        return ArchiveReceipt(
            manifest.archive_id, manifest.source_version, now, len(manifest.records), manifest.source_sha256
        )

    def manifest(self, archive_id: str) -> ArchiveManifest | None:
        row = self.connection.execute(
            "SELECT manifest_json FROM vnext.archive_catalog WHERE archive_id = ?", (archive_id,)
        ).fetchone()
        if row is None:
            return None
        return load_archive_manifest(json.loads(row["manifest_json"]))

    def can_read(self, archive_id: str, principal: object | None = None) -> bool:
        manifest = self.manifest(archive_id)
        if manifest is None:
            return False
        permissions = manifest.permissions
        if not permissions:
            return True
        subject = getattr(principal, "subject", None)
        tenant_id = getattr(principal, "tenant_id", None)
        roles = set(getattr(principal, "roles", ()))
        subjects = set(permissions.get("subjects", ()))
        allowed_roles = set(permissions.get("roles", ()))
        required_tenant = permissions.get("tenant_id")
        if required_tenant and tenant_id != required_tenant:
            return False
        if subjects and subject not in subjects:
            return False
        if allowed_roles and not roles.intersection(allowed_roles):
            return False
        return bool(subject or not (subjects or allowed_roles or required_tenant))

    def view(self, archive_id: str, *, principal: object | None = None) -> ArchiveView | None:
        if not self.can_read(archive_id, principal):
            return None
        manifest = self.manifest(archive_id)
        if manifest is None:
            return None
        records = [self._record_view(record, manifest.exported_at) for record in manifest.records]
        return ArchiveView(
            archive_id=manifest.archive_id,
            source_version=manifest.source_version,
            imported_at=self._imported_at(archive_id, fallback=_utc_now()),
            records=records,
            executable=False,
        )

    def _imported_at(self, archive_id: str, *, fallback: datetime) -> datetime:
        row = self.connection.execute(
            "SELECT imported_at FROM vnext.archive_catalog WHERE archive_id = ?", (archive_id,)
        ).fetchone()
        return _parse_datetime(row["imported_at"] if row else None, fallback=fallback)

    @staticmethod
    def _record_view(record: ArchiveRecord, created_at: datetime) -> RecordView:
        entity_type = record.entity_type if record.entity_type in _KNOWN_ENTITY_TYPES else "claim"
        ref = KnowledgeRef(entity_type=entity_type, id=record.record_id, revision=record.revision)
        payload = dict(record.payload)
        candidate = payload if "ref" in payload else None
        if candidate is None or not isinstance(candidate, Mapping):
            candidate = {
                "ref": ref.model_dump(mode="python"),
                "title": record.display_kind,
                "summary": _canonical_json(
                    {
                        "source_id": record.source_id,
                        "source_hash": record.source_hash,
                        "payload": payload,
                    }
                ),
                "created_at": _iso(created_at),
            }
        else:
            candidate = dict(candidate)
            candidate.setdefault("ref", ref.model_dump(mode="python"))
        try:
            return RecordView(
                ref=ref,
                display_kind=record.display_kind,
                record=candidate,
            )
        except Exception:
            generic = GenericRecord(
                ref=ref,
                title=record.display_kind,
                summary=_canonical_json(
                    {
                        "source_id": record.source_id,
                        "source_hash": record.source_hash,
                        "payload": payload,
                    }
                ),
                created_at=created_at,
            )
            return RecordView(ref=ref, display_kind=record.display_kind, record=generic)


class ArchiveImporter:
    """Import manifests into an archive-only store."""

    def __init__(self, store: ArchiveStore | str | Path | None = None) -> None:
        self.store = store if isinstance(store, ArchiveStore) else ArchiveStore(store or ":memory:")

    def import_archive(
        self, manifest: ArchiveManifest | Mapping[str, Any] | str | Path
    ) -> ArchiveReceipt:
        return self.store.import_manifest(load_archive_manifest(manifest))

    def read_archive(self, archive_id: str, *, principal: object | None = None) -> ArchiveView | None:
        return self.store.view(archive_id, principal=principal)
