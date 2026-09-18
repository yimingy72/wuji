from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from vnext.export_legacy_readonly import build_manifest, write_manifest
from wuji_core.archive import ArchiveError, ArchiveImporter, ArchiveStore


def _legacy_copy(path):
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE claims(id TEXT, revision INTEGER, source_hash TEXT, text TEXT);
        CREATE TABLE relations(from_id TEXT, to_id TEXT, kind TEXT);
        CREATE TABLE artifacts(id TEXT, sha256 TEXT, media_type TEXT);
        INSERT INTO claims VALUES ('claim-17', 2, 'aabb', '旧系统观察');
        INSERT INTO relations VALUES ('claim-17', 'artifact-17', 'supported-by');
        INSERT INTO artifacts VALUES ('artifact-17', 'c' || printf('%064d', 0), 'text/plain');
        """
    )
    connection.commit()
    connection.close()


def test_archive_export_import_roundtrip_is_non_executable(tmp_path):
    source = tmp_path / "legacy.sqlite"
    _legacy_copy(source)
    manifest = build_manifest(source, archive_id="archive-fixture", source_version="legacy-v7")
    manifest_path = tmp_path / "archive.json"
    write_manifest(manifest, manifest_path)

    with ArchiveStore(tmp_path / "archive-store.sqlite") as store:
        receipt = ArchiveImporter(store).import_archive(manifest_path)
        assert receipt.imported_records == len(manifest["records"])
        assert receipt.source_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
        assert store.connection.execute(
            "SELECT count(*) FROM vnext.work_item WHERE source_archive_id = ?",
            (receipt.archive_id,),
        ).fetchone()[0] == 0

        view = store.view(receipt.archive_id)
        assert view is not None
        assert view.executable is False
        assert view.source_version == "legacy-v7"
        assert any(record.display_kind == "LegacyClaim" for record in view.records)

        replay = ArchiveImporter(store).import_archive(json.loads(manifest_path.read_text()))
        assert replay.imported_records == receipt.imported_records

    with ArchiveStore(tmp_path / "archive-store.sqlite") as reopened:
        persisted = reopened.view("archive-fixture")
        assert persisted is not None and len(persisted.records) == receipt.imported_records


def test_archive_import_rejects_active_cutover_fields_and_conflicting_replay(tmp_path):
    manifest = {
        "format": "wuji.legacy-archive.v1",
        "archive_id": "archive-1",
        "source_version": "legacy-v1",
        "records": [],
        "executable": False,
    }
    with ArchiveStore() as store:
        importer = ArchiveImporter(store)
        with pytest.raises(ArchiveError, match="active field"):
            importer.import_archive({**manifest, "active_identity": {"run_id": "run-1"}})
        importer.import_archive(manifest)
        with pytest.raises(ArchiveError, match="different manifest"):
            importer.import_archive({**manifest, "source_version": "legacy-v2"})
