"""Real API/bytes/SQL; tests fail on forged identity, split capture or lost commit."""

import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from support.p03 import (
    access,
    capture_case,
    control_access,
    module,
    seed_capacity,
    seed_control_actor,
)


def submit(case, envelope=None, headers=None):
    return case.client.post(
        "/internal/v2/evidence",
        json=envelope or case.envelope,
        headers=headers or case.headers,
    )


def count(case, table):
    from psycopg import sql

    with case.uow.transaction(access(), "task-fixture") as tx:
        return tx.connection.execute(
            sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier("vnext", table))
        ).fetchone()[0]


def test_agent_cannot_use_capture_endpoint(
    db_environment, tmp_path, audit_directory, test_tokens
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        response = submit(
            c, headers={**c.headers, "Authorization": "Bearer " + test_tokens.agent}
        )
        assert (response.status_code, response.json()["code"]) == (
            403,
            "FORBIDDEN_COLLECTOR",
        )
        assert count(c, "observation") == 0


def test_bound_collector_persists_one_observation_all_bytes_without_extractor(
    db_environment, tmp_path, audit_directory, test_tokens
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        before = datetime.now(timezone.utc)
        response = submit(c)
        assert response.status_code == 202, response.text
        receipt = response.json()
        assert receipt["status"] == "accepted"
        assert receipt["observation_ref"]["entity_type"] == "observation"
        assert receipt["observation_ref"]["revision"] == "1"
        assert count(c, "observation") == 1 and count(c, "observation_artifact") == 2
        assert count(c, "assessment") == 0 and count(c, "claim_revision") == 0
        with c.uow.transaction(access(), "task-fixture") as tx:
            obs = tx.connection.execute(
                "SELECT received_at,collector_ref,environment_ref FROM vnext.observation"
            ).fetchone()
            assert before <= obs[0] <= datetime.now(timezone.utc)
            assert obs[1:] == ("collector-fixture", "environment-fixture")
            stored = json.loads(
                tx.connection.execute(
                    "SELECT original_envelope FROM vnext.evidence_receipt"
                ).fetchone()[0]
            )
            assert stored == c.envelope
            assert tx.connection.execute(
                "SELECT observation_count,board_revision,event_seq FROM vnext.task"
            ).fetchone() == (1, 1, 1)
        for ref, data in zip(c.refs, c.data):
            response = c.client.get(
                f'/api/v2/artifacts/{ref["id"]}/content?version=1',
                headers={"Authorization": "Bearer " + test_tokens.reader},
            )
            assert response.status_code == 200 and response.content == data
            assert (
                response.headers["digest"]
                == "sha-256=" + base64.b64encode(hashlib.sha256(data).digest()).decode()
            )
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["content-type"] == "application/octet-stream"


def test_replay_is_stable_and_conflicting_arrays_or_text_are_rejected(
    db_environment, tmp_path, audit_directory, test_tokens
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        first = submit(c)
        reordered = json.dumps(dict(reversed(list(c.envelope.items()))), indent=2)
        second = c.client.post(
            "/internal/v2/evidence",
            content=reordered,
            headers={**c.headers, "Content-Type": "application/json"},
        )
        assert first.status_code == second.status_code == 202
        assert first.content == second.content
        for field, value in [
            ("artifact_refs", list(reversed(c.refs))),
            ("conditions", ["fixture bytes "]),
        ]:
            changed = {**c.envelope, field: value}
            response = submit(c, changed)
            assert (response.status_code, response.json()["code"]) == (
                409,
                "INPUT_DIGEST_CONFLICT",
            )
        assert count(c, "observation") == 1 and count(c, "outbox") == 1


@pytest.mark.parametrize(
    "key,value",
    [
        ("tenant_id", "tenant-other"),
        ("project_id", "project-other"),
        ("task_id", "task-sibling"),
        ("work_item_id", "work-b"),
        ("agent_run_id", "missing"),
        ("receiver_id", "other"),
        ("execution_epoch", "2"),
        ("run_epoch", "2"),
        ("runtime_attempt", "2"),
        ("tool_call_id", "provider-opaque-call"),
        ("tool_attempt_id", "missing"),
    ],
)
def test_capture_rejects_unbound_or_mismatched_identity(
    db_environment, tmp_path, audit_directory, test_tokens, key, value
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        body = deepcopy(c.envelope)
        (body if key.startswith("tool_") else body["identity"])[key] = value
        response = submit(c, body)
        assert response.status_code in {403, 422}, response.text
        assert count(c, "observation") == 0
        assert count(c, "tool_attempt") == 1


@pytest.mark.parametrize("key", [None, "different-operation"])
def test_evidence_requires_capture_id_as_idempotency_key(
    db_environment, tmp_path, audit_directory, test_tokens, key
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        headers = {"Authorization": "Bearer " + test_tokens.collector}
        if key is not None:
            headers["Idempotency-Key"] = key
        response = submit(c, headers=headers)
        assert response.status_code == 422
        assert count(c, "observation") == 0


def test_replay_and_artifact_download_recheck_current_permission(
    db_environment, tmp_path, audit_directory, test_tokens
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        assert submit(c).status_code == 202
        with db_environment.migration_connection() as db:
            db.execute(
                "UPDATE vnext.task_access SET can_read=false WHERE tenant_id='tenant-fixture' AND task_id='task-fixture'"
            )
        assert submit(c).status_code == 403
        response = c.client.get(
            f'/api/v2/artifacts/{c.refs[0]["id"]}/content?version=1',
            headers={"Authorization": "Bearer " + test_tokens.reader},
        )
        assert response.status_code == 404
        assert c.refs[0]["id"] not in response.text


@pytest.mark.parametrize("settlement", [True, False])
def test_started_late_attempt_is_historical_only_with_settlement_authority(
    db_environment, tmp_path, audit_directory, test_tokens, settlement
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        with db_environment.migration_connection() as db:
            db.execute(
                "UPDATE vnext.task SET execution_allowed=false,execution_epoch=2 WHERE tenant_id='tenant-fixture' AND task_id='task-fixture'"
            )
            db.execute(
                "UPDATE vnext.collector_binding SET can_settle=%s WHERE tenant_id='tenant-fixture' AND task_id='task-fixture'",
                (settlement,),
            )
        response = submit(c)
        assert response.status_code == (202 if settlement else 403)
        if settlement:
            assert response.json()["status"] == "historical_only"
            assert response.json()["observation_ref"]["entity_type"] == "observation"
        with c.uow.transaction(access(), "task-fixture") as tx:
            assert tx.connection.execute(
                "SELECT execution_allowed,execution_epoch FROM vnext.task"
            ).fetchone() == (False, 2)
        assert count(c, "work_item") == 2


@pytest.mark.parametrize("damage", ["missing", "changed"])
def test_capture_rejects_missing_or_changed_actual_bytes(
    db_environment, tmp_path, audit_directory, test_tokens, damage
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        with c.uow.transaction(access(), "task-fixture") as tx:
            key = tx.connection.execute(
                "SELECT storage_key FROM vnext.artifact WHERE entity_id=%s",
                (c.refs[0]["id"],),
            ).fetchone()[0]
        path = tmp_path / "objects" / f"{key}.blob"
        if damage == "missing":
            path.unlink()
        else:
            path.chmod(0o600)
            path.write_bytes(b"tampered fixture")
        response = submit(c)
        assert (response.status_code, response.json()["code"]) == (
            422,
            "INVALID_REFERENCE",
        )
        assert count(c, "observation") == 0


def test_capture_publication_database_failure_rolls_back_all_domain_state(
    db_environment, tmp_path, audit_directory, test_tokens
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        with db_environment.migration_connection() as db:
            db.execute(
                "ALTER TABLE vnext.outbox ADD CONSTRAINT fixture_fail_commit CHECK(kind<>'evidence_ingested')"
            )
        response = submit(c)
        assert response.status_code == 503
        assert (
            count(c, "observation")
            == count(c, "evidence_receipt")
            == count(c, "publication")
            == count(c, "outbox")
            == 0
        )
        with c.uow.transaction(access(), "task-fixture") as tx:
            assert tx.connection.execute(
                "SELECT board_revision,observation_count,event_seq FROM vnext.task"
            ).fetchone() == (0, 0, 0)
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.entity_revision_registry WHERE entity_type='observation'"
                ).fetchone()[0]
                == 0
            )
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.artifact WHERE state='sealed'"
                ).fetchone()[0]
                == 2
            )
        with db_environment.migration_connection() as db:
            db.execute("ALTER TABLE vnext.outbox DROP CONSTRAINT fixture_fail_commit")
        assert submit(c).status_code == 202


def test_partial_output_and_source_axes_do_not_certify_business_truth(
    db_environment, tmp_path, audit_directory, test_tokens
):
    with capture_case(
        db_environment, tmp_path, audit_directory, test_tokens, completeness="partial"
    ) as c:
        changed = {**c.envelope, "completeness": "complete"}
        assert submit(c, changed).status_code == 422
        assert submit(c).status_code == 202
        with c.uow.transaction(access(), "task-fixture") as tx:
            assert tx.connection.execute(
                "SELECT completeness,evidence_origin,conditions_json FROM vnext.observation"
            ).fetchone() == (
                "partial",
                "fixture_capture",
                '["fixture bytes; remainder unavailable"]',
            )
            assert (
                tx.connection.execute(
                    "SELECT model_mode FROM vnext.agent_run"
                ).fetchone()[0]
                == "synthetic"
            )
            assert (
                json.loads(
                    tx.connection.execute(
                        "SELECT receipt_json FROM vnext.tool_attempt"
                    ).fetchone()[0]
                )["exit_code"]
                == 0
            )
        assert count(c, "assessment") == 0
        assert count(c, "claim_revision") == 0


@pytest.mark.parametrize("provenance", ["model_output", "import"])
def test_model_or_imported_bytes_cannot_be_laundered_into_capture(
    db_environment, tmp_path, audit_directory, test_tokens, provenance
):
    with capture_case(
        db_environment, tmp_path, audit_directory, test_tokens, provenance=provenance
    ) as c:
        response = submit(c)
        assert response.status_code == 422
        assert count(c, "observation") == 0


def test_snapshot_pins_revisions_states_relations_after_connection_close(
    db_environment, tmp_path, audit_directory, test_tokens
):
    from support.p03 import claim

    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        assert submit(c).status_code == 202
        with c.uow.transaction(access(), "task-fixture", capability="write") as tx:
            claim(tx, text="version one")
        with db_environment.migration_connection() as m:
            seed_control_actor(m)
            seed_capacity(m)
        with c.uow.transaction(
            control_access(), "task-fixture", capability="control"
        ) as tx:
            tx.add_dependency("work-fixture", "work-b", "settled")
        snapshots = module("persistence.snapshots").SnapshotRepository(c.uow)
        manifest = snapshots.create("task-fixture", access())
        first = snapshots.page(
            "task-fixture", access(), manifest.snapshot_id, offset=0, limit=2
        )
        assert len(first) == 2
        with c.uow.transaction(access(), "task-fixture", capability="write") as tx:
            claim(tx, revision=2, text="version two")
            tx.semantic_event("claim_appended", {"revision": "2"})
        with db_environment.migration_connection() as db:
            db.execute(
                "UPDATE vnext.work_item SET state='done',revision=2 WHERE tenant_id='tenant-fixture' AND task_id='task-fixture' AND work_item_id='work-b'"
            )
        second = snapshots.page(
            "task-fixture", access(), manifest.snapshot_id, offset=2, limit=100
        )
        claim_ref = next(ref for ref in second if ref.entity_type.value == "claim")
        assert claim_ref.revision.root == "1"
        saved = snapshots.get("task-fixture", access(), manifest.snapshot_id)
        assert saved.snapshot_id == manifest.snapshot_id
        assert saved.states["work_items"]["work-b"]["state"] == "ready"
        assert saved.dependencies[0]["condition"] == "settled"
        assert (
            snapshots.read_ref(
                "task-fixture", access(), manifest.snapshot_id, claim_ref
            )["text"]
            == "version one"
        )
        assert len(saved.refs) == 4


def test_snapshot_query_scope_current_access_and_expiration(
    db_environment, tmp_path, audit_directory, test_tokens
):
    from support.p03 import claim

    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        with c.uow.transaction(access(), "task-fixture", capability="write") as tx:
            claim(tx)
        snapshots_module = module("persistence.snapshots")
        snapshots = snapshots_module.SnapshotRepository(c.uow)
        manifest = snapshots.create(
            "task-fixture",
            access(),
            query=snapshots_module.SnapshotQuery(entity_types=("claim",)),
        )
        assert [ref.entity_type.value for ref in manifest.refs] == ["claim"]
        with db_environment.migration_connection() as db:
            db.execute(
                "UPDATE vnext.snapshot_manifest SET expires_at=clock_timestamp()-interval '1 second' WHERE tenant_id='tenant-fixture' AND snapshot_id=%s",
                (manifest.snapshot_id,),
            )
        with pytest.raises(module("persistence.uow").DomainError) as error:
            snapshots.get("task-fixture", access(), manifest.snapshot_id)
        assert (error.value.status, error.value.code) == (410, "SNAPSHOT_EXPIRED")
        with db_environment.migration_connection() as db:
            db.execute(
                "UPDATE vnext.task_access SET can_read=false WHERE tenant_id='tenant-fixture' AND task_id='task-fixture'"
            )
        with pytest.raises(module("persistence.uow").DomainError) as error:
            snapshots.get("task-fixture", access(), manifest.snapshot_id)
        assert error.value.code == "NOT_FOUND_OR_FORBIDDEN"


def test_gc_retains_live_commit_leases_and_published_snapshot_bytes(
    db_environment, tmp_path, audit_directory, test_tokens
):
    from wuji_core.contracts.envelopes import BlobRef

    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        snapshots = module("persistence.snapshots").SnapshotRepository(c.uow)
        manifest = snapshots.create("task-fixture", access())
        for wire in c.refs:
            c.store.release_lease(
                access(),
                "task-fixture",
                BlobRef.model_validate(wire),
                lease_owner="staging",
            )
        orphan = c.store.stage(
            access(), "task-fixture", "attempt-fixture", b"orphan fixture", "text/plain"
        )
        c.store.seal(access(), "task-fixture", orphan)
        c.store.acquire_lease(
            access(),
            "task-fixture",
            orphan,
            lease_owner="publishing-fixture",
            seconds=60,
        )
        c.store.release_lease(access(), "task-fixture", orphan, lease_owner="staging")
        assert (
            c.store.collect_garbage(
                access(), "task-fixture", older_than=datetime.now(timezone.utc)
            )
            == []
        )
        c.store.release_lease(
            access(), "task-fixture", orphan, lease_owner="publishing-fixture"
        )
        removed = c.store.collect_garbage(
            access(), "task-fixture", older_than=datetime.now(timezone.utc)
        )
        assert removed == [orphan.id]
        assert (
            c.store.collect_garbage(
                access(), "task-fixture", older_than=datetime.now(timezone.utc)
            )
            == []
        )
        with c.uow.transaction(access(), "task-fixture") as tx:
            row = tx.connection.execute(
                "SELECT state,storage_key FROM vnext.artifact WHERE entity_id=%s",
                (orphan.id,),
            ).fetchone()
            assert row[0] == "tombstoned"
            assert not (tmp_path / "objects" / f"{row[1]}.blob").exists()
        for wire, data in zip(c.refs, c.data):
            assert c.store.read(access(), wire["id"], "1")[0] == data
        assert (
            len(snapshots.get("task-fixture", access(), manifest.snapshot_id).refs) == 2
        )


def test_snapshot_publication_and_gc_use_two_coordinated_connections(
    db_environment, tmp_path, audit_directory, test_tokens
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from wuji_core.contracts.envelopes import BlobRef

    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        snapshots = module("persistence.snapshots").SnapshotRepository(c.uow)
        barrier = Barrier(2)

        def publish():
            barrier.wait(timeout=5)
            return snapshots.create("task-fixture", access())

        def gc():
            barrier.wait(timeout=5)
            return c.store.collect_garbage(
                access(), "task-fixture", older_than=datetime.now(timezone.utc)
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            p = pool.submit(publish)
            g = pool.submit(gc)
            manifest = p.result(timeout=10)
            assert g.result(timeout=10) == []
        for wire in c.refs:
            c.store.release_lease(
                access(),
                "task-fixture",
                BlobRef.model_validate(wire),
                lease_owner="staging",
            )
        assert (
            c.store.collect_garbage(
                access(), "task-fixture", older_than=datetime.now(timezone.utc)
            )
            == []
        )
        assert len(snapshots.page("task-fixture", access(), manifest.snapshot_id)) == 2


def test_partial_body_and_complete_metadata_remain_one_partial_observation(
    db_environment, tmp_path, audit_directory, test_tokens
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        body = c.store.stage(
            access(),
            "task-fixture",
            "attempt-fixture",
            b'{"version":17',
            "application/json",
            completeness="partial",
            conditions=["body truncated"],
        )
        c.store.seal(access(), "task-fixture", body)
        envelope = {
            **c.envelope,
            "artifact_refs": [body.model_dump(mode="json"), c.refs[1]],
            "completeness": "partial",
            "conditions": ["fixture bytes", "body truncated"],
        }
        response = submit(c, envelope)
        assert response.status_code == 202, response.text
        assert count(c, "observation") == 1
        with c.uow.transaction(access(), "task-fixture") as tx:
            assert (
                tx.connection.execute(
                    "SELECT completeness FROM vnext.observation"
                ).fetchone()[0]
                == "partial"
            )


def test_late_receipt_requires_a_trusted_start_record(
    db_environment, tmp_path, audit_directory, test_tokens
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        with db_environment.migration_connection() as db:
            db.execute(
                "UPDATE vnext.task SET execution_allowed=false WHERE tenant_id='tenant-fixture' AND task_id='task-fixture'"
            )
            db.execute(
                "UPDATE vnext.tool_attempt SET started_at=NULL WHERE tenant_id='tenant-fixture' AND task_id='task-fixture'"
            )
        response = submit(c)
        assert (response.status_code, response.json()["code"]) == (
            403,
            "STALE_EXECUTION",
        )
        assert count(c, "observation") == 0


def test_private_publication_pin_protects_visible_bytes_from_lower_clearance_gc(
    db_environment, tmp_path, audit_directory, test_tokens
):
    from wuji_core.contracts.envelopes import BlobRef

    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        private = c.store.stage(
            access(),
            "task-fixture",
            "attempt-fixture",
            b"private fixture",
            "text/plain",
            conditions=["fixture bytes"],
            access_level=1,
        )
        c.store.seal(access(), "task-fixture", private)
        envelope = {
            **c.envelope,
            "artifact_refs": [c.refs[0], private.model_dump(mode="json")],
        }
        assert submit(c, envelope).status_code == 202
        with db_environment.migration_connection() as db:
            db.execute(
                "UPDATE vnext.task_access SET clearance=0 WHERE tenant_id='tenant-fixture' AND task_id='task-fixture'"
            )
        assert (
            c.store.collect_garbage(
                access(), "task-fixture", older_than=datetime.now(timezone.utc)
            )
            == []
        )
        assert c.store.read(access(), c.refs[0]["id"], "1")[0] == c.data[0]
        with c.uow.transaction(access(), "task-fixture") as tx:
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.observation"
                ).fetchone()[0]
                == 0
            )
            assert (
                tx.connection.execute("SELECT count(*) FROM vnext.outbox").fetchone()[0]
                == 0
            )


def test_read_only_member_can_create_a_snapshot_without_domain_write(
    db_environment, tmp_path, audit_directory, test_tokens
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        with db_environment.migration_connection() as db:
            db.execute(
                "UPDATE vnext.task_access SET can_write=false WHERE tenant_id='tenant-fixture' AND subject='reader-fixture'"
            )
        snapshots = module("persistence.snapshots").SnapshotRepository(c.uow)
        manifest = snapshots.create(
            "task-fixture", access("reader-fixture", role="reader")
        )
        assert len(manifest.refs) == 2


def test_revoked_collector_cannot_release_commit_lease(
    db_environment, tmp_path, audit_directory, test_tokens
):
    from wuji_core.contracts.envelopes import BlobRef

    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        with db_environment.migration_connection() as db:
            db.execute(
                "UPDATE vnext.collector_binding SET revoked=true WHERE tenant_id='tenant-fixture' AND task_id='task-fixture'"
            )
        with pytest.raises(module("persistence.uow").DomainError) as error:
            c.store.release_lease(
                access(),
                "task-fixture",
                BlobRef.model_validate(c.refs[0]),
                lease_owner="staging",
            )
        assert error.value.code == "FORBIDDEN_COLLECTOR"


def test_gc_preserves_artifact_cited_by_claim_before_snapshot(
    db_environment, tmp_path, audit_directory, test_tokens
):
    from support.p03 import claim
    from wuji_core.contracts.envelopes import BlobRef

    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as c:
        with c.uow.transaction(access(), "task-fixture", capability="write") as tx:
            claim(tx)
            tx.connection.execute(
                "INSERT INTO vnext.entity_relation(tenant_id,project_id,task_id,source_type,source_id,source_revision,relation,target_type,target_id,target_revision) VALUES (%s,%s,%s,'claim','claim-1',1,'cites','artifact',%s,1)",
                (*tx.owner, c.refs[0]["id"]),
            )
        for wire in c.refs:
            c.store.release_lease(
                access(),
                "task-fixture",
                BlobRef.model_validate(wire),
                lease_owner="staging",
            )
        assert c.store.collect_garbage(
            access(), "task-fixture", older_than=datetime.now(timezone.utc)
        ) == [c.refs[1]["id"]]
        assert c.store.read(access(), c.refs[0]["id"], "1")[0] == c.data[0]
