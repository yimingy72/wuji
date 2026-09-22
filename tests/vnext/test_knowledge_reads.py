from uuid import uuid4
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest

from support.p03 import access
from test_knowledge_admission import BASE, IDENTITY, TASK, case, headers, proposal
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
from wuji_core.execution.worker_bridge import HostContext
from wuji_core.worker_host import PlatformWorkerHost


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


def test_native_handoff_result_and_raw_are_independent_of_prepared_and_checkpoint(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        sources = [
            _captured_http(c, exchange(body))
            for body in (b"confirmed material", b"unconfirmed material")
        ]
        worker = AccessContext(
            Principal("run.worker:knowledge-native", "tenant-fixture", frozenset({"worker"}),
                      "knowledge-native-token"),
            "knowledge-native-request",
        )
        binding = RunCredentialBinding.model_validate({
            "identity": IDENTITY, "subject": worker.principal.subject,
            "token_id": worker.principal.token_id,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "purposes": ["model_request", "tool_request"],
            "session_lineage": "knowledge-native-lineage", "allowed_tool_refs": [],
        })
        body = {
            "schema_version": "wuji.harness.problem.v2", "ref": "problem-profile",
            "revision": "1", "session_codec": "wuji.session.native.v2",
            "lock_digest": "a" * 64,
        }
        profile = {
            "ref": body["ref"], "revision": body["revision"], "body": body,
            "digest": sha256(canonical_json_bytes(body)).hexdigest(),
        }
        definition = canonical_json_bytes({"worker_profiles": {"explore": profile}})
        with db_environment.migration_connection() as connection:
            connection.execute(
                "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,can_write,can_model_output,clearance) "
                "VALUES(%s,%s,%s,%s,true,true,true,1)",
                ("tenant-fixture", "project-fixture", TASK, worker.principal.subject),
            )
            connection.execute(
                "INSERT INTO vnext.run_writer(tenant_id,project_id,task_id,agent_run_id,subject,agent_subject,can_settle) "
                "VALUES(%s,%s,%s,%s,%s,'agent-fixture',true)",
                ("tenant-fixture", "project-fixture", TASK, IDENTITY["agent_run_id"],
                 worker.principal.subject),
            )
            connection.execute(
                "INSERT INTO vnext.run_credential(tenant_id,project_id,task_id,subject,token_id,agent_run_id,document_json) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s)",
                ("tenant-fixture", "project-fixture", TASK, worker.principal.subject,
                 worker.principal.token_id, IDENTITY["agent_run_id"],
                 canonical_json_bytes(binding.model_dump(mode="json")).decode()),
            )
            connection.execute(
                "UPDATE vnext.task SET definition_json=%s,definition_digest=%s WHERE task_id=%s",
                (definition.decode(), sha256(definition).hexdigest(), TASK),
            )
        snapshot = SnapshotRepository(c.uow).create(TASK, worker)
        assignment = _assignment().model_copy(update={"snapshot_id": snapshot.snapshot_id})
        service = KnowledgeReadService(c.uow, ledger=c.view, artifacts=c.store)
        deliveries = [
            service.read(
                worker, assignment, snapshot_id=snapshot.snapshot_id,
                ref={"entity_type": "artifact", "id": ref.id, "revision": "1"},
                selector={"kind": "text_range", "start": 0, "end": 8192},
                native_occurrence=f"native-read-{index}",
            )
            for index, ref in enumerate(sources)
        ]
        # Reads currently start as v1; explicitly cover an unconfirmed v2 row too.
        with db_environment.migration_connection() as connection:
            connection.execute(
                "UPDATE vnext.knowledge_delivery SET protocol_version='v2' "
                "WHERE task_id=%s AND delivery_id=%s",
                (TASK, deliveries[1].delivery_id),
            )
        handoff = {
            "delivery_id": deliveries[0].delivery_id,
            "representation_digest": deliveries[0].representation_digest.root,
        }
        with pytest.raises(DomainError, match="INVALID_REFERENCE"):
            service.attach(worker, assignment, channel="function_result", deliveries=[
                {**handoff, "representation_digest": "0" * 64},
            ])
        with pytest.raises(DomainError, match="INVALID_REFERENCE"):
            service.attach(worker, assignment, channel="initial_input", deliveries=[handoff])
        confirmed = service.attach(
            worker, assignment, channel="function_result", deliveries=[handoff],
        )
        assert confirmed["returned_to_framework"] == [deliveries[0].delivery_id]
        host = PlatformWorkerHost(
            uow=c.uow, registry=None, access=worker, artifacts=c.store,
            committer=c.committer, profiles=[profile], lock_digest=body["lock_digest"],
        )
        text = canonical_json_bytes({
            "schema_version": "wuji.work-brief.v1", "brief": {},
            "knowledge_index": [], "initial_deliveries": [],
        }).decode()
        context = HostContext(snapshot.snapshot_id, (), (), text, sha256(text.encode()).hexdigest())
        manifest = host._delivery_manifest(assignment, context)
        assert manifest["schema_version"] == "wuji.delivery-manifest.v2"
        assert [item["delivery"]["delivery_id"] for item in manifest["handoffs"]] == [
            deliveries[0].delivery_id,
        ]
        for index, ref in enumerate(sources):
            current = assignment.model_copy(update={"operation_id": f"native-result-{index}"})
            basis = {"entity_type": "artifact", "id": ref.id, "revision": "1"}
            raw = canonical_json_bytes({
                "schema_version": "wuji.agent-payload.v3",
                "claims": [proposal(basis=[basis])], "intent_proposals": [],
                "reason_decision": None,
                "work_result": {
                    "outcome": "answered", "summary": "fixture answer",
                    "answer_basis_refs": [basis], "unresolved_items": [], "capability_gaps": [],
                },
                "input_acknowledgements": [],
            })
            raw_ref = host.retain_final_output(current, raw_output=raw)
            publication_id = "raw-result:maf-m1:" + host._operation_digest(current)
            retained = host._published_artifacts(current, publication_id)
            assert len(retained) == 1 and c.store.checked_bytes(retained[0]) == raw
            # No Session service or checkpoint exists, yet P04 must settle the result.
            receipt = host.submit_result(
                current, raw_output=raw, context=context, tool_receipts=(), sdk_output=b"{}\n",
            )
            if index == 0:
                assert receipt.status.value == "accepted", receipt.model_dump(mode="json")
                assert len(receipt.components) == 1
                assert receipt.components[0].canonical_ref is not None
            else:
                assert receipt.status.value == "rejected"
                assert receipt.code.value == "INVALID_REFERENCE"
            assert host.retain_final_output(current, raw_output=raw) == raw_ref
            retained = host._published_artifacts(current, publication_id)
            assert len(retained) == 1 and c.store.checked_bytes(retained[0]) == raw
        with c.uow.transaction(worker, TASK) as tx:
            states = tx.connection.execute(
                "SELECT delivery_id,protocol_version,state FROM vnext.knowledge_delivery "
                "WHERE task_id=%s AND agent_run_id=%s",
                (TASK, IDENTITY["agent_run_id"]),
            ).fetchall()
            assert set(states) == {
                (deliveries[0].delivery_id, "v2", "returned_to_framework"),
                (deliveries[1].delivery_id, "v2", "prepared"),
            }
            assert tx.connection.execute(
                "SELECT count(*) FROM vnext.session_manifest WHERE task_id=%s", (TASK,),
            ).fetchone() == (0,)
