from uuid import uuid4
from datetime import datetime, timedelta, timezone

import pytest

from support.p03 import access
from test_knowledge_admission import BASE, IDENTITY, TASK, case, headers
from test_model_material_v2 import exchange
from wuji_core.admission.model_material import HTTP_EXCHANGE_MEDIA_TYPE
from wuji_core.admission.registry import RunCredentialBinding
from wuji_core.blackboard.knowledge_reads import KnowledgeReadService
from wuji_core.contracts.envelopes import WorkerAssignment
from wuji_core.persistence.snapshots import SnapshotRepository
from wuji_core.persistence.uow import DomainError
from wuji_core.http import canonical_json_bytes
from wuji_core.http.auth import Principal
from wuji_core.persistence.uow import AccessContext


def _assignment():
    return WorkerAssignment.model_validate({
        "schema_version": "wuji.assignment.v2",
        "operation_id": "knowledge-read-operation",
        "identity": IDENTITY,
        "work_kind": "explore",
        "snapshot_id": "placeholder",
        "profile_refs": ["problem-profile"],
        "session_manifest_ref": None,
        "tool_definition_refs": [],
        "limits": {
            "max_work_items": 8,
            "max_reason_runs": 4,
            "max_model_requests": 16,
            "max_tool_calls": 4,
            "max_single_output_bytes": 1_048_576,
            "max_total_output_bytes": 2_097_152,
            "max_elapsed_seconds": 300,
            "max_attempts_per_work": 2,
            "repair_attempts": 0,
        },
        "resume_reason": None,
    })


def _captured_http(c, raw):
    ref = c.store.stage(
        access(), TASK, "attempt-fixture", raw, HTTP_EXCHANGE_MEDIA_TYPE,
        completeness="complete",
    )
    c.store.seal(access(), TASK, ref)
    envelope = {
        "schema_version": "wuji.capture.v2",
        "capture_id": str(uuid4()),
        "identity": IDENTITY,
        "tool_call_id": "tool-fixture",
        "tool_attempt_id": "attempt-fixture",
        "artifact_refs": [ref.model_dump(mode="json")],
        "capture_layer": "fixture_file_bytes",
        "observed_at": "2026-09-21T00:00:00Z",
        "received_at": "2026-09-21T00:00:01Z",
        "evidence_origin": "fixture_capture",
        "conditions": [],
        "completeness": "complete",
    }
    response = c.client.post(
        "/internal/v2/evidence", json=envelope,
        headers=headers(c, "collector", envelope["capture_id"]),
    )
    assert response.status_code == 202, response.text
    return ref


def test_large_fixed_material_is_read_in_ranges_and_old_snapshot_cannot_expand(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        secret = "sk-abcdefghijklmnopqrstuvwxyz123456"
        body = ("A" * 8_100 + secret + "B" * 271_900 + "second-range-marker").encode()
        ref = _captured_http(c, exchange(body))
        worker_subject, worker_token = "run.worker:knowledge", "knowledge-token"
        binding = RunCredentialBinding.model_validate({
            "identity": IDENTITY,
            "subject": worker_subject,
            "token_id": worker_token,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "purposes": ["model_request", "tool_request"],
            "session_lineage": "knowledge-lineage",
            "allowed_tool_refs": [],
        })
        with db_environment.migration_connection() as connection:
            connection.execute(
                "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,can_write,can_model_output,clearance) "
                "VALUES(%s,%s,%s,%s,true,true,true,1)",
                ("tenant-fixture", "project-fixture", TASK, worker_subject),
            )
            connection.execute(
                "INSERT INTO vnext.run_credential(tenant_id,project_id,task_id,subject,token_id,agent_run_id,document_json) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s)",
                ("tenant-fixture", "project-fixture", TASK, worker_subject, worker_token,
                 IDENTITY["agent_run_id"], canonical_json_bytes(binding.model_dump(mode="json")).decode()),
            )
        worker = AccessContext(
            Principal(worker_subject, "tenant-fixture", frozenset({"worker"}), worker_token),
            "knowledge-request",
        )
        snapshot = SnapshotRepository(c.uow).create(TASK, worker)
        assignment = _assignment().model_copy(update={"snapshot_id": snapshot.snapshot_id})
        service = KnowledgeReadService(c.uow, ledger=c.view, artifacts=c.store)

        first = service.read(
            worker, assignment, snapshot_id=snapshot.snapshot_id, ref={
                "entity_type": "artifact", "id": ref.id, "revision": "1",
            }, selector={"kind": "text_range", "start": 0, "end": 8192},
            native_occurrence="read-1",
        )
        second = service.read(
            worker, assignment, snapshot_id=snapshot.snapshot_id, ref={
                "entity_type": "artifact", "id": ref.id, "revision": "1",
            }, selector={"kind": "text_range", "start": 275000, "end": 310000},
            native_occurrence="read-2",
        )
        replay = service.read(
            worker, assignment, snapshot_id=snapshot.snapshot_id, ref={
                "entity_type": "artifact", "id": ref.id, "revision": "1",
            }, selector={"kind": "text_range", "start": 0, "end": 8192},
            native_occurrence="read-1",
        )

        assert first.delivery_id == replay.delivery_id
        assert first.byte_length <= 16 * 1024 and second.byte_length <= 16 * 1024
        assert first.source_digest.root == ref.sha256.root == second.source_digest.root
        assert secret not in first.text and secret not in second.text
        assert "second-range-marker" in second.text
        assert first.selector.root.end <= 8192
        assert second.selector.root.start == 275000
        with pytest.raises(DomainError, match="INPUT_DIGEST_CONFLICT"):
            service.read(
                worker, assignment, snapshot_id=snapshot.snapshot_id,
                ref={"entity_type": "artifact", "id": ref.id, "revision": "1"},
                selector={"kind": "text_range", "start": 1, "end": 8193},
                native_occurrence="read-1",
            )
        with pytest.raises(DomainError, match="INVALID_REFERENCE"):
            service.read(
                worker, assignment, snapshot_id=snapshot.snapshot_id,
                ref={"entity_type": "artifact", "id": "not-in-snapshot", "revision": "1"},
                selector={"kind": "text_range", "start": 0, "end": 10},
                native_occurrence="read-3",
            )
        with c.uow.transaction(worker, TASK) as tx:
            assert tx.connection.execute(
                "SELECT count(*),bool_and(state='prepared') FROM vnext.knowledge_delivery"
            ).fetchone() == (2, True)
