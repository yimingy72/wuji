"""P06 model/tool admission over signed HTTP and an isolated PostgreSQL."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
import yaml

from support.p06 import (
    BlockingSettlementExecutor,
    CancelDeliveryProbe,
    NATIVE_MODEL_REQUEST,
    NATIVE_MODEL_RESPONSE,
    OWNER,
    PARTIAL_SSE,
    SimulatedProcessExit,
    TASK,
    WORKSPACE_INPUT_SCHEMA,
    bind_same_run_purpose,
    bind_secondary_model_run,
    fresh_ledger,
    migrate_earliest_v8_then_current,
    model_case,
    model_headers,
    tool_case,
    tool_headers,
)
from wuji_core.contracts.admission import ToolCallRequest
from wuji_core.contracts.execution import ChatCompletionRequest
from test_work_state_guards import command
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError


MODEL_ROUTE = "/internal/v2/model/chat/completions"


def workspace_tool_request(
    *, provider_call_id: str = "call-p06-read", path: str = "version.txt"
) -> dict[str, object]:
    return {
        "session_lineage": "session-lineage-fixture",
        "message_id": "message-p06-tool-1",
        "provider_call_id": provider_call_id,
        "tool_definition_ref": "fixture-reader-v1",
        "arguments": {"path": path},
        "sdk_content_id": None,
        "sdk_approval_id": None,
        "approval_ref": None,
    }


def test_current_run_model_gate_forwards_native_and_records_attempt(
    db_environment, tmp_path, audit_directory
):
    """Catch a Gate that sends before admission or keeps only an in-memory count."""

    with model_case(db_environment, tmp_path, audit_directory) as case:
        before = fresh_ledger(case).snapshot(case.access, TASK)
        request_body = canonical_json_bytes(NATIVE_MODEL_REQUEST)

        response = case.client.post(
            MODEL_ROUTE,
            content=request_body,
            headers=model_headers(case, "model-request-current-1"),
        )

        assert response.status_code == 200
        assert response.content == canonical_json_bytes(NATIVE_MODEL_RESPONSE)
        assert response.headers["x-wuji-replayed"] == "false"
        attempt_id = response.headers["x-wuji-model-attempt-id"]

        assert len(case.upstream.exchanges) == 1
        outbound = case.upstream.exchanges[0]
        assert outbound.path == "/v1/chat/completions"
        assert outbound.headers["authorization"] == (
            "Bearer " + case.key_resolver.secret
        )
        outbound_body = strict_json_loads(outbound.request_body)
        assert outbound_body == {
            **NATIVE_MODEL_REQUEST,
            "model": "fixture-upstream-model",
        }
        assert case.key_resolver.resolved_refs == ["fixture-task-key-ref"]
        assert case.key_resolver.secret not in response.text

        receipt_response = case.client.get(
            f"/internal/v2/model-attempts/{attempt_id}",
            headers={"Authorization": "Bearer " + case.credential.token},
        )
        assert receipt_response.status_code == 200
        receipt = receipt_response.json()
        expected_size = len(canonical_json_bytes(NATIVE_MODEL_RESPONSE))
        assert receipt["model_attempt_id"] == attempt_id
        assert receipt["input_digest"] == sha256(request_body).hexdigest()
        assert receipt["logical_request_id"] == "model-request-current-1"
        assert receipt["grouping_state"] == "known"
        assert receipt["admission_state"] == "admitted"
        assert receipt["send_state"] == "sent"
        assert receipt["response_state"] == "complete"
        assert receipt["billing_state"] == "pending"
        assert receipt["local_state"] == "ended"
        assert receipt["inflight"] is False
        assert receipt["upstream_status"] == 200
        assert receipt["response_available"] is True
        assert receipt["gateway_usage_ref"] is None
        assert receipt["gateway_spend_ref"] is None
        assert receipt["received_bytes"] == str(expected_size)
        assert receipt["retained_bytes"] == str(expected_size)
        assert receipt["forwarded_bytes"] == str(expected_size)
        assert receipt["output_bytes"] == str(expected_size)

        after = fresh_ledger(case).snapshot(case.access, TASK)
        assert before.model_attempts == 0
        assert after.model_attempts == 1
        assert after.tool_attempts == 0
        assert after.output_bytes == expected_size
        assert after.received_bytes == expected_size
        assert after.retained_bytes == expected_size
        assert after.forwarded_bytes == expected_size
        with db_environment.migration_connection() as connection:
            used = dict(
                connection.execute(
                    "SELECT pool_key,used FROM vnext.capacity_pool WHERE pool_key IN ('platform','model:fixture-model-v1')"
                ).fetchall()
            )
        assert used == {"model:fixture-model-v1": 1, "platform": 1}


def test_revoked_run_cannot_request_model(
    db_environment, tmp_path, audit_directory
):
    """Catch authorization that checks Task only and ignores credential revocation."""

    with model_case(db_environment, tmp_path, audit_directory) as case:
        before = fresh_ledger(case).snapshot(case.access, TASK)
        with db_environment.migration_connection() as connection:
            case.registry_module.revoke_run_credential(
                connection,
                tenant_id=case.credential.principal.tenant_id,
                subject=case.credential.principal.subject,
                token_id=case.credential.principal.token_id,
            )

        response = case.client.post(
            MODEL_ROUTE,
            content=canonical_json_bytes(NATIVE_MODEL_REQUEST),
            headers=model_headers(case, "model-request-revoked-1"),
        )

        assert response.status_code == 409
        assert response.json()["code"] == "STALE_EXECUTION"
        assert len(case.upstream.exchanges) == 0
        assert case.key_resolver.resolved_refs == []
        after = fresh_ledger(case).snapshot(case.access, TASK)
        assert after == before
        assert after.model_attempts == 0
        with db_environment.migration_connection() as connection:
            used = connection.execute(
                "SELECT used FROM vnext.capacity_pool WHERE pool_key='platform'"
            ).fetchone()[0]
        assert used == 1


def test_p05_pause_makes_bound_run_identity_stale(
    db_environment, tmp_path, audit_directory
):
    """Catch a Gate that trusts a valid binding after P05 revokes execution."""

    with model_case(db_environment, tmp_path, audit_directory) as case:
        command(case.control, "pause")

        response = case.client.post(
            MODEL_ROUTE,
            content=canonical_json_bytes(NATIVE_MODEL_REQUEST),
            headers=model_headers(case, "model-request-paused-1"),
        )

        assert response.status_code == 409
        assert response.json()["code"] == "STALE_EXECUTION"
        assert len(case.upstream.exchanges) == 0
        assert fresh_ledger(case).snapshot(case.access, TASK).model_attempts == 0


def test_model_request_replay_conflict_and_new_id_have_distinct_attempts(
    db_environment, tmp_path, audit_directory
):
    """Catch digest-only replay or a changed body reusing an existing attempt."""

    with model_case(db_environment, tmp_path, audit_directory) as case:
        first = case.client.post(
            MODEL_ROUTE,
            content=canonical_json_bytes(NATIVE_MODEL_REQUEST),
            headers=model_headers(case, "model-logical-replay-1"),
        )
        replay = case.client.post(
            MODEL_ROUTE,
            content=canonical_json_bytes(NATIVE_MODEL_REQUEST),
            headers=model_headers(case, "model-logical-replay-1"),
        )
        changed_request = deepcopy(NATIVE_MODEL_REQUEST)
        changed_request["messages"][1]["content"] = "A changed logical request."
        conflict = case.client.post(
            MODEL_ROUTE,
            content=canonical_json_bytes(changed_request),
            headers=model_headers(case, "model-logical-replay-1"),
        )
        new_request = case.client.post(
            MODEL_ROUTE,
            content=canonical_json_bytes(NATIVE_MODEL_REQUEST),
            headers=model_headers(case, "model-logical-replay-2"),
        )

        assert first.status_code == replay.status_code == new_request.status_code == 200
        assert first.headers["x-wuji-replayed"] == "false"
        assert replay.headers["x-wuji-replayed"] == "true"
        assert first.headers["x-wuji-model-attempt-id"] == replay.headers[
            "x-wuji-model-attempt-id"
        ]
        assert new_request.headers["x-wuji-replayed"] == "false"
        assert new_request.headers["x-wuji-model-attempt-id"] != first.headers[
            "x-wuji-model-attempt-id"
        ]
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "INPUT_DIGEST_CONFLICT"
        assert len(case.upstream.exchanges) == 2
        assert fresh_ledger(case).snapshot(case.access, TASK).model_attempts == 2


def test_two_runs_cannot_both_take_the_last_task_model_request(
    db_environment, tmp_path, audit_directory
):
    """Catch non-atomic quota checks that admit two concurrent final requests."""

    with model_case(
        db_environment,
        tmp_path,
        audit_directory,
        max_model_requests=1,
    ) as case:
        second_credential = bind_secondary_model_run(case)
        case.upstream.behavior = "blocking_json"

        with ThreadPoolExecutor(max_workers=2) as pool:
            first_future = pool.submit(
                case.client.post,
                MODEL_ROUTE,
                content=canonical_json_bytes(NATIVE_MODEL_REQUEST),
                headers=model_headers(case, "model-final-slot-a"),
            )
            assert case.upstream.request_started.wait(timeout=5)
            second_future = pool.submit(
                case.client.post,
                MODEL_ROUTE,
                content=canonical_json_bytes(NATIVE_MODEL_REQUEST),
                headers=model_headers(
                    case, "model-final-slot-b", credential=second_credential
                ),
            )
            try:
                second = second_future.result(timeout=3)
            except FutureTimeout:
                case.upstream.release_response.set()
                second = second_future.result(timeout=5)
            finally:
                case.upstream.release_response.set()
            first = first_future.result(timeout=5)

        assert first.status_code == 200
        assert second.status_code == 429
        assert second.json()["code"] == "LIMIT_BLOCKED"
        assert len(case.upstream.exchanges) == 1
        snapshot = fresh_ledger(case).snapshot(case.access, TASK)
        assert snapshot.model_attempts == 1
        with db_environment.migration_connection() as connection:
            used = connection.execute(
                "SELECT used FROM vnext.capacity_pool WHERE pool_key='platform'"
            ).fetchone()[0]
        assert used == 2


def test_partial_stream_releases_local_inflight_without_settling_billing(
    db_environment, tmp_path, audit_directory
):
    """Catch billing-pending or partial response state pinning local inflight forever."""

    with model_case(db_environment, tmp_path, audit_directory) as case:
        partial_request = {**NATIVE_MODEL_REQUEST, "stream": True}
        case.upstream.behavior = "partial_stream"
        partial = case.client.post(
            MODEL_ROUTE,
            content=canonical_json_bytes(partial_request),
            headers=model_headers(case, "model-partial-1"),
        )

        assert partial.status_code == 200
        assert partial.content == PARTIAL_SSE
        assert b"[DONE]" not in partial.content
        attempt_id = partial.headers["x-wuji-model-attempt-id"]
        receipt_response = case.client.get(
            f"/internal/v2/model-attempts/{attempt_id}",
            headers={"Authorization": "Bearer " + case.credential.token},
        )
        assert receipt_response.status_code == 200
        receipt = receipt_response.json()
        assert receipt["send_state"] == "sent"
        assert receipt["response_state"] == "partial"
        assert receipt["billing_state"] == "pending"
        assert receipt["local_state"] == "ended"
        assert receipt["inflight"] is False
        assert receipt["response_available"] is False

        case.upstream.behavior = "json"
        continued = case.client.post(
            MODEL_ROUTE,
            content=canonical_json_bytes(NATIVE_MODEL_REQUEST),
            headers=model_headers(case, "model-after-partial-2"),
        )

        assert continued.status_code == 200
        assert continued.headers["x-wuji-replayed"] == "false"
        assert len(case.upstream.exchanges) == 2
        assert fresh_ledger(case).snapshot(case.access, TASK).model_attempts == 2
        with db_environment.migration_connection() as connection:
            used = connection.execute(
                "SELECT used FROM vnext.capacity_pool WHERE pool_key='platform'"
            ).fetchone()[0]
        assert used == 1


def test_workspace_read_returns_only_after_persisting_evidence(
    db_environment, tmp_path, audit_directory
):
    """Catch a tool Gate returning self-reported success before real evidence exists."""

    with tool_case(db_environment, tmp_path, audit_directory) as case:
        before = fresh_ledger(case).snapshot(case.access, TASK)
        response = case.client.post(
            "/internal/v2/tool-calls",
            json=workspace_tool_request(),
            headers=tool_headers(case, "tool-workspace-read-1"),
        )

        assert response.status_code == 200
        receipt = response.json()
        assert receipt["status"] == "complete"
        assert receipt["operation_id"] == receipt["tool_call_id"]
        assert receipt["tool_attempt_id"] is not None
        assert receipt["evidence_receipt"] is not None
        assert receipt["result_ref"] is not None
        assert receipt["reason_code"] is None
        receiver_receipt = (
            case.receipt_root / f"{receipt['tool_attempt_id']}.json"
        )
        assert receiver_receipt.is_file()
        assert list(case.receipt_root.glob("*.json")) == [receiver_receipt]

        result_ref = receipt["result_ref"]
        artifact = case.client.get(
            f"/api/v2/artifacts/{result_ref['id']}/content",
            params={"version": result_ref["version"]},
            headers={"Authorization": "Bearer " + case.credential.token},
        )
        assert artifact.status_code == 200
        assert artifact.content == case.expected_output

        lookup = case.client.get(
            f"/internal/v2/tool-calls/{receipt['tool_call_id']}",
            headers={"Authorization": "Bearer " + case.credential.token},
        )
        assert lookup.status_code == 200
        assert lookup.json() == receipt
        assert list(case.receipt_root.glob("*.json")) == [receiver_receipt]
        after = fresh_ledger(case).snapshot(case.access, TASK)
        assert before.tool_attempts == 0
        assert after.tool_attempts == 1
        assert after.model_attempts == 0
        assert after.output_bytes == len(case.expected_output)
        with db_environment.migration_connection() as connection:
            claims = connection.execute(
                "SELECT count(*) FROM vnext.claim_revision WHERE task_id=%s",
                (TASK,),
            ).fetchone()[0]
        assert claims == 0


def test_revoked_run_cannot_dispatch_workspace_tool(
    db_environment, tmp_path, audit_directory
):
    """Catch tool admission that ignores the same real Run credential revocation."""

    with tool_case(db_environment, tmp_path, audit_directory) as case:
        with db_environment.migration_connection() as connection:
            case.registry_module.revoke_run_credential(
                connection,
                tenant_id=case.credential.principal.tenant_id,
                subject=case.credential.principal.subject,
                token_id=case.credential.principal.token_id,
            )

        response = case.client.post(
            "/internal/v2/tool-calls",
            json=workspace_tool_request(provider_call_id="call-p06-revoked"),
            headers=tool_headers(case, "tool-workspace-revoked-1"),
        )

        assert response.status_code == 409
        assert response.json()["code"] == "STALE_EXECUTION"
        assert list(case.receipt_root.glob("*.json")) == []
        snapshot = fresh_ledger(case).snapshot(case.access, TASK)
        assert snapshot.tool_attempts == 0
        assert snapshot.output_bytes == 0


def test_task_output_limit_is_cumulative_across_model_attempts(
    db_environment, tmp_path, audit_directory
):
    """Catch an output limit reset between otherwise independent model requests."""

    response_size = len(canonical_json_bytes(NATIVE_MODEL_RESPONSE))
    limit = response_size + 1
    with model_case(
        db_environment,
        tmp_path,
        audit_directory,
        max_total_output_bytes=limit,
    ) as case:
        first = case.client.post(
            MODEL_ROUTE,
            content=canonical_json_bytes(NATIVE_MODEL_REQUEST),
            headers=model_headers(case, "model-output-budget-1"),
        )
        second = case.client.post(
            MODEL_ROUTE,
            content=canonical_json_bytes(NATIVE_MODEL_REQUEST),
            headers=model_headers(case, "model-output-budget-2"),
        )

        assert first.status_code == 200
        assert second.status_code == 429
        assert second.json()["code"] == "LIMIT_BLOCKED"
        assert len(case.upstream.exchanges) == 2
        snapshot = fresh_ledger(case).snapshot(case.access, TASK)
        assert snapshot.model_attempts == 2
        assert snapshot.received_bytes == response_size * 2
        assert snapshot.retained_bytes == response_size
        assert snapshot.forwarded_bytes == response_size
        assert snapshot.output_bytes == response_size
        assert snapshot.output_bytes <= limit


def test_approval_required_tool_does_not_create_an_execution_attempt(
    db_environment, tmp_path, audit_directory
):
    """Catch a client proposal or approval string being treated as execution consent."""

    with tool_case(
        db_environment,
        tmp_path,
        audit_directory,
        approval_required=True,
    ) as case:
        response = case.client.post(
            "/internal/v2/tool-calls",
            json=workspace_tool_request(),
            headers=tool_headers(case, "tool-awaiting-approval-1"),
        )

        assert response.status_code == 200
        receipt = response.json()
        assert receipt["status"] == "pending_approval"
        assert receipt["tool_attempt_id"] is None
        assert receipt["evidence_receipt"] is None
        assert receipt["result_ref"] is None
        assert list(case.receipt_root.glob("*")) == []
        snapshot = fresh_ledger(case).snapshot(case.access, TASK)
        assert snapshot.tool_attempts == 0
        assert snapshot.output_bytes == 0


def test_tool_operation_replay_conflict_and_new_call_id_control_execution(
    db_environment, tmp_path, audit_directory
):
    """Catch parameter drift or a new provider call ID reusing an old ToolCall."""

    with tool_case(db_environment, tmp_path, audit_directory) as case:
        first = case.client.post(
            "/internal/v2/tool-calls",
            json=workspace_tool_request(),
            headers=tool_headers(case, "tool-operation-first"),
        )
        replay = case.client.post(
            "/internal/v2/tool-calls",
            json=workspace_tool_request(),
            headers=tool_headers(case, "tool-operation-replay"),
        )
        conflict = case.client.post(
            "/internal/v2/tool-calls",
            json=workspace_tool_request(path="missing.txt"),
            headers=tool_headers(case, "tool-operation-conflict"),
        )
        new_call = case.client.post(
            "/internal/v2/tool-calls",
            json=workspace_tool_request(provider_call_id="call-p06-read-new"),
            headers=tool_headers(case, "tool-operation-new-call"),
        )

        assert first.status_code == replay.status_code == new_call.status_code == 200
        assert first.json() == replay.json()
        assert first.json()["tool_call_id"] != new_call.json()["tool_call_id"]
        assert first.json()["tool_attempt_id"] != new_call.json()["tool_attempt_id"]
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "INPUT_DIGEST_CONFLICT"
        assert len(list(case.receipt_root.glob("*.json"))) == 2
        snapshot = fresh_ledger(case).snapshot(case.access, TASK)
        assert snapshot.tool_attempts == 2
        assert snapshot.output_bytes == len(case.expected_output) * 2


def test_missing_mcp_type_and_revoked_function_adapter_do_not_execute(
    db_environment, tmp_path, audit_directory
):
    """Catch adapter-local fallback types or function dispatch after server revocation."""

    with tool_case(db_environment, tmp_path, audit_directory) as case:
        with pytest.raises(DomainError) as missing_mcp:
            asyncio.run(
                case.gate.invoke_mcp(
                    case.access,
                    object(),
                    session_lineage="session-lineage-fixture",
                    message_id="message-p06-mcp",
                    provider_call_id="call-p06-mcp",
                    tool_definition_ref="fixture-reader-v1",
                )
            )
        assert missing_mcp.value.code == "CAPABILITY_UNAVAILABLE"

        with db_environment.migration_connection() as connection:
            case.registry_module.revoke_tool_definition(
                connection,
                tenant_id=case.credential.principal.tenant_id,
                tool_definition_ref="fixture-reader-v1",
            )
        with pytest.raises(DomainError) as revoked_function:
            asyncio.run(
                case.gate.invoke_function(
                    case.access,
                    name="read_fixture",
                    arguments={"path": "version.txt"},
                    session_lineage="session-lineage-fixture",
                    message_id="message-p06-function",
                    provider_call_id="call-p06-function",
                    tool_definition_ref="fixture-reader-v1",
                )
            )
        assert revoked_function.value.code == "STALE_EXECUTION"
        assert list(case.receipt_root.glob("*")) == []
        assert fresh_ledger(case).snapshot(case.access, TASK).tool_attempts == 0


def test_started_tool_can_settle_after_revocation_but_new_work_is_rejected(
    db_environment, tmp_path, audit_directory
):
    """Catch revocation discarding an old receipt or authorizing a new operation."""

    with tool_case(db_environment, tmp_path, audit_directory) as case:
        blocking = BlockingSettlementExecutor(
            case.tool_module, case.admission, case.workspace
        )
        case.gate.executors["workspace-reader-fixture"] = blocking
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                case.client.post,
                "/internal/v2/tool-calls",
                json=workspace_tool_request(provider_call_id="call-p06-late"),
                headers=tool_headers(case, "tool-late-settlement"),
            )
            assert blocking.started.wait(timeout=5)
            with db_environment.migration_connection() as connection:
                case.registry_module.revoke_run_credential(
                    connection,
                    tenant_id=case.credential.principal.tenant_id,
                    subject=case.credential.principal.subject,
                    token_id=case.credential.principal.token_id,
                )
            blocking.release.set()
            settled = future.result(timeout=5)

        assert settled.status_code == 200
        settled_receipt = settled.json()
        assert settled_receipt["status"] == "complete"
        assert settled_receipt["evidence_receipt"] is not None
        assert blocking.dispatches == 1

        lookup = case.client.get(
            f"/internal/v2/tool-calls/{settled_receipt['tool_call_id']}",
            headers={"Authorization": "Bearer " + case.credential.token},
        )
        assert lookup.status_code == 200
        assert lookup.json() == settled_receipt

        rejected = case.client.post(
            "/internal/v2/tool-calls",
            json=workspace_tool_request(provider_call_id="call-p06-after-revoke"),
            headers=tool_headers(case, "tool-new-after-revoke"),
        )
        assert rejected.status_code == 409
        assert rejected.json()["code"] == "STALE_EXECUTION"
        assert blocking.dispatches == 1
        snapshot = fresh_ledger(case).snapshot(case.access, TASK)
        assert snapshot.tool_attempts == 1
        assert snapshot.output_bytes == len(case.expected_output)


def test_run_credential_does_not_grant_control_admit_or_capture(
    db_environment, tmp_path, audit_directory
):
    """Catch purpose binding accidentally widening the Run principal's Task ACL."""

    with model_case(db_environment, tmp_path, audit_directory) as case:
        with db_environment.migration_connection() as connection:
            permissions = connection.execute(
                "SELECT can_read,can_control,can_admit,can_capture,can_observe FROM vnext.task_access WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND subject=%s",
                (*OWNER, case.credential.principal.subject),
            ).fetchone()
        assert permissions == (True, False, False, False, False)

        for capability in ("control", "admit", "capture"):
            with pytest.raises(DomainError) as denied:
                with case.control.uow.transaction(
                    case.access, TASK, capability=capability
                ):
                    pass
            assert denied.value.code == "NOT_FOUND_OR_FORBIDDEN"


def test_authorized_not_sent_model_attempt_can_be_reconciled_without_refund(
    db_environment, tmp_path, audit_directory
):
    """Catch a crash between committed admission and begin_send pinning the Run."""

    with model_case(db_environment, tmp_path, audit_directory) as case:
        request_body = canonical_json_bytes(NATIVE_MODEL_REQUEST)
        permit = case.admission.authorize(
            case.access,
            ChatCompletionRequest.model_validate(NATIVE_MODEL_REQUEST),
            request_id="model-authorized-not-sent",
            original_json=request_body,
        )
        assert len(case.upstream.exchanges) == 0
        assert fresh_ledger(case).snapshot(case.access, TASK).model_attempts == 1

        rebuilt_uow = case.control.uow.__class__(
            case.environment.additional_app_connection
        )
        rebuilt_registry = case.registry_module.AdmissionRegistry(rebuilt_uow)
        rebuilt_ledger = case.ledger_module.AdmissionLedger(rebuilt_uow)
        rebuilt_admission = case.model_module.ModelAdmission(
            rebuilt_uow, registry=rebuilt_registry, ledger=rebuilt_ledger
        )
        rebuilt_gate = case.model_module.ModelGate(
            rebuilt_admission,
            registry=rebuilt_registry,
            ledger=rebuilt_ledger,
            key_resolver=case.key_resolver,
            transport=case.model_module.HttpxModelTransport(case.upstream.client),
        )
        reconciled = asyncio.run(
            rebuilt_gate.reconcile(case.access, permit.model_attempt_id)
        )
        assert reconciled.send_state == "not_sent"
        assert reconciled.local_state == "ended"
        assert reconciled.inflight is False

        same = case.client.post(
            MODEL_ROUTE,
            content=request_body,
            headers=model_headers(case, "model-authorized-not-sent"),
        )
        new = case.client.post(
            MODEL_ROUTE,
            content=request_body,
            headers=model_headers(case, "model-after-not-sent"),
        )
        assert same.status_code == 409
        assert same.json()["code"] == "OPERATION_UNKNOWN"
        assert same.json()["details"]["model_attempt_id"] == permit.model_attempt_id
        assert new.status_code == 200
        assert len(case.upstream.exchanges) == 1
        assert fresh_ledger(case).snapshot(case.access, TASK).model_attempts == 2


def test_cancel_replay_delivers_same_persisted_cancel_operation(
    db_environment, tmp_path, audit_directory
):
    """Catch a crash after cancel registration making every replay skip delivery."""

    with tool_case(db_environment, tmp_path, audit_directory) as case:
        permit = case.admission.authorize(
            case.access, ToolCallRequest.model_validate(workspace_tool_request())
        )
        crasher = CancelDeliveryProbe(case.tool_module, case.admission, crash=True)
        case.gate.executors["workspace-reader-fixture"] = crasher
        with pytest.raises(SimulatedProcessExit):
            asyncio.run(
                case.gate.cancel(
                    case.access,
                    permit.tool_call_id,
                    operation_id="cancel-operation-stable",
                    reason="fixture cancellation",
                )
            )
        assert crasher.cancel_calls == 1

        retry = CancelDeliveryProbe(case.tool_module, case.admission, crash=False)
        case.gate.executors["workspace-reader-fixture"] = retry
        asyncio.run(
            case.gate.cancel(
                case.access,
                permit.tool_call_id,
                operation_id="cancel-operation-stable",
                reason="fixture cancellation",
            )
        )
        assert retry.cancel_calls == 1
        stored = case.ledger.tool_call(case.access, permit.tool_call_id)
        assert stored.status == "cancelled"
        assert fresh_ledger(case).snapshot(case.access, TASK).tool_attempts == 1


def test_database_write_policies_separate_model_and_tool_purposes(
    db_environment, tmp_path, audit_directory
):
    """Catch a valid request purpose mutating the other admission ledger."""

    with tool_case(db_environment, tmp_path, audit_directory) as case:
        executed = case.client.post(
            "/internal/v2/tool-calls",
            json=workspace_tool_request(),
            headers=tool_headers(case, "tool-purpose-fixture"),
        )
        assert executed.status_code == 200
        _, model_access = bind_same_run_purpose(
            case, subject="model-only-worker-fixture", purpose="model_request"
        )

        def update(access, capability, statement):
            try:
                with case.control.uow.transaction(
                    access, TASK, capability=capability
                ) as tx:
                    return tx.connection.execute(statement, tx.owner).fetchone()
            except psycopg.Error:
                return None

        model_counter = update(
            case.access,
            "tool_request",
            "UPDATE vnext.admission_counter SET model_attempts=model_attempts+1 WHERE tenant_id=%s AND project_id=%s AND task_id=%s RETURNING model_attempts",
        )
        tool_resource = update(
            model_access,
            "model_request",
            "UPDATE vnext.tool_resource_claim SET active=true WHERE tenant_id=%s AND project_id=%s AND task_id=%s RETURNING active",
        )
        assert model_counter is None
        assert tool_resource is None

        with db_environment.migration_connection() as connection:
            counts = connection.execute(
                "SELECT model_attempts,tool_attempts FROM vnext.admission_counter WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                OWNER,
            ).fetchone()
            active = connection.execute(
                "SELECT active FROM vnext.tool_resource_claim WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                OWNER,
            ).fetchone()[0]
        assert counts == (0, 1)
        assert active is False


def test_explicit_null_tools_is_a_valid_native_model_request(
    db_environment, tmp_path, audit_directory
):
    """Catch legal tools:null falling through to an unhandled TypeError."""

    with model_case(db_environment, tmp_path, audit_directory) as case:
        request = {**NATIVE_MODEL_REQUEST, "tools": None}
        try:
            response = case.client.post(
                MODEL_ROUTE,
                content=canonical_json_bytes(request),
                headers=model_headers(case, "model-tools-null"),
            )
        except TypeError as error:
            pytest.fail(f"legal tools:null raised TypeError: {error}")
        assert response.status_code == 200
        assert strict_json_loads(case.upstream.exchanges[0].request_body)["tools"] is None


def test_model_tool_advertisement_requires_actual_gate_assembly(
    db_environment, tmp_path, audit_directory
):
    """Catch a registered definition being advertised without an executor Gate."""

    with model_case(
        db_environment,
        tmp_path,
        audit_directory,
        advertise_workspace_tool=True,
    ) as case:
        request = {
            **NATIVE_MODEL_REQUEST,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "read_fixture",
                        "description": "Read an isolated fixture file.",
                        "parameters": WORKSPACE_INPUT_SCHEMA,
                    },
                }
            ],
        }
        response = case.client.post(
            MODEL_ROUTE,
            content=canonical_json_bytes(request),
            headers=model_headers(case, "model-unassembled-tool"),
        )
        assert response.status_code == 503
        assert response.json()["code"] == "CAPABILITY_UNAVAILABLE"
        assert len(case.upstream.exchanges) == 0
        assert fresh_ledger(case).snapshot(case.access, TASK).model_attempts == 0


def test_model_tool_advertisement_accepts_the_actual_tool_gate_assembly(
    db_environment, tmp_path, audit_directory
):
    """Catch the shared resolver rejecting an actually assembled workspace tool."""

    with tool_case(db_environment, tmp_path, audit_directory) as case:
        model_credential, _ = bind_same_run_purpose(
            case,
            subject="assembled-model-worker-fixture",
            purpose="model_request",
            allowed_tool_refs=["fixture-reader-v1"],
        )
        request = {
            **NATIVE_MODEL_REQUEST,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "read_fixture",
                        "description": "Read an isolated fixture file.",
                        "parameters": WORKSPACE_INPUT_SCHEMA,
                    },
                }
            ],
        }
        response = case.client.post(
            MODEL_ROUTE,
            content=canonical_json_bytes(request),
            headers=model_headers(
                case, "model-assembled-tool", credential=model_credential
            ),
        )
        assert response.status_code == 200
        assert len(case.upstream.exchanges) == 1
        assert fresh_ledger(case).snapshot(case.access, TASK).model_attempts == 1


def test_workspace_output_limit_returns_partial_evidence_and_reason(
    db_environment, tmp_path, audit_directory
):
    """Catch a real tool result being discarded without evidence at its byte limit."""

    retained = 5
    with tool_case(
        db_environment,
        tmp_path,
        audit_directory,
        max_total_output_bytes=retained,
    ) as case:
        response = case.client.post(
            "/internal/v2/tool-calls",
            json=workspace_tool_request(),
            headers=tool_headers(case, "tool-partial-output-limit"),
        )
        assert response.status_code == 200
        receipt = response.json()
        assert receipt["status"] == "complete"
        assert receipt["reason_code"] == "LIMIT_BLOCKED"
        assert receipt["evidence_receipt"] is not None
        assert receipt["result_ref"] is not None
        result_ref = receipt["result_ref"]
        artifact = case.client.get(
            f"/api/v2/artifacts/{result_ref['id']}/content",
            params={"version": result_ref["version"]},
            headers={"Authorization": "Bearer " + case.credential.token},
        )
        assert artifact.status_code == 200
        assert artifact.content == case.expected_output[:retained]
        snapshot = fresh_ledger(case).snapshot(case.access, TASK)
        assert snapshot.received_bytes == len(case.expected_output)
        assert snapshot.retained_bytes == retained
        assert snapshot.output_bytes == retained


def test_partial_workspace_receipt_replay_compares_original_output_metadata(
    db_environment, tmp_path, audit_directory
):
    """Catch a retained prefix being compared with the receiver's full replay."""

    with tool_case(
        db_environment,
        tmp_path,
        audit_directory,
        max_total_output_bytes=5,
    ) as case:
        permit = case.admission.authorize(
            case.access, ToolCallRequest.model_validate(workspace_tool_request())
        )
        original = asyncio.run(case.executor.dispatch(permit))
        case.gate._receive_execution(permit, original)
        case.gate._capture(permit)
        before = fresh_ledger(case).snapshot(case.access, TASK)

        replay = asyncio.run(case.executor.query(permit))
        assert replay.receipt_id == original.receipt_id
        assert replay.output == original.output == case.expected_output
        case.gate._receive_execution(permit, replay)

        after = fresh_ledger(case).snapshot(case.access, TASK)
        assert after == before
        stored = case.ledger.tool_call(case.access, permit.tool_call_id)
        assert stored.status == "complete"
        assert stored.reason_code == "LIMIT_BLOCKED"


def test_model_openapi_declares_runtime_correlation_headers():
    """Catch generated clients losing the attempt/replay correlation contract."""

    root = Path(__file__).resolve().parents[2]
    contract = yaml.safe_load(
        (root / "packages/contracts/openapi-v2.yaml").read_text(encoding="utf-8")
    )
    response = contract["paths"]["/internal/v2/model/chat/completions"]["post"][
        "responses"
    ]["200"]
    assert "headers" in response
    headers = response["headers"]
    assert headers["X-Wuji-Model-Attempt-ID"]["schema"]["type"] == "string"
    assert headers["X-Wuji-Replayed"]["schema"] == {
        "type": "string",
        "enum": ["true", "false"],
    }


def test_model_request_cannot_write_model_settlement_fields(
    db_environment, tmp_path, audit_directory
):
    """Catch model_request forging a response or releasing its own inflight slot."""

    with model_case(db_environment, tmp_path, audit_directory) as case:
        permit = case.admission.authorize(
            case.access,
            ChatCompletionRequest.model_validate(NATIVE_MODEL_REQUEST),
            request_id="model-purpose-settlement-forgery",
            original_json=canonical_json_bytes(NATIVE_MODEL_REQUEST),
        )
        try:
            with case.control.uow.transaction(
                case.access, TASK, capability="model_request"
            ) as tx:
                forged = tx.connection.execute(
                    "UPDATE vnext.model_call SET local_state='ended',inflight=false,response_state='complete',response_available=true,billing_state='reported' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND model_attempt_id=%s RETURNING local_state",
                    (*tx.owner, permit.model_attempt_id),
                ).fetchone()
        except psycopg.Error:
            forged = None
        assert forged is None
        with db_environment.migration_connection() as connection:
            stored = connection.execute(
                "SELECT local_state,inflight,response_state,response_available,billing_state FROM vnext.model_call WHERE model_attempt_id=%s",
                (permit.model_attempt_id,),
            ).fetchone()
        assert stored == ("inflight", True, "pending", False, "pending")


def test_tool_request_cannot_write_tool_settlement_or_release_resources(
    db_environment, tmp_path, audit_directory
):
    """Catch tool_request forging a terminal receipt or releasing its own lock."""

    with tool_case(db_environment, tmp_path, audit_directory) as case:
        permit = case.admission.authorize(
            case.access, ToolCallRequest.model_validate(workspace_tool_request())
        )

        def update(statement):
            try:
                with case.control.uow.transaction(
                    case.access, TASK, capability="tool_request"
                ) as tx:
                    return tx.connection.execute(
                        statement, (*tx.owner, permit.tool_attempt_id)
                    ).fetchone()
            except psycopg.Error:
                return None

        forged_receipt = update(
            "UPDATE vnext.tool_attempt SET status='complete',receipt_json='{\"forged\":true}',result_receipt_json='{}',output=decode('00','hex') WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s RETURNING status"
        )
        released = update(
            "UPDATE vnext.resource_reservation SET state='released' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND source_receipt_json::jsonb->>'tool_attempt_id'=%s RETURNING state"
        )
        assert forged_receipt is None
        assert released is None

        with db_environment.migration_connection() as connection:
            status = connection.execute(
                "SELECT status,receipt_json,result_receipt_json,output FROM vnext.tool_attempt WHERE tool_attempt_id=%s",
                (permit.tool_attempt_id,),
            ).fetchone()
            reservation = connection.execute(
                "SELECT state FROM vnext.resource_reservation WHERE source_receipt_json::jsonb->>'tool_attempt_id'=%s",
                (permit.tool_attempt_id,),
            ).fetchone()[0]
        assert status == ("admitted", "{}", None, None)
        assert reservation == "reserved"


def test_request_inserts_require_zero_counters_and_initial_model_state(
    db_environment, tmp_path, audit_directory
):
    """Catch INSERT bypassing UPDATE-only counter and model settlement guards."""

    with model_case(db_environment, tmp_path, audit_directory) as case:
        def insert(statement, parameters):
            try:
                with case.control.uow.transaction(
                    case.access, TASK, capability="model_request"
                ) as tx:
                    return tx.connection.execute(statement, parameters(tx)).fetchone()
            except psycopg.Error:
                return None

        forged_counter = insert(
            "INSERT INTO vnext.admission_counter(tenant_id,project_id,task_id,model_attempts,tool_attempts,output_bytes,received_bytes,retained_bytes,forwarded_bytes) VALUES(%s,%s,%s,5,7,11,13,17,19) RETURNING model_attempts",
            lambda tx: tx.owner,
        )
        forged_model = insert(
            "INSERT INTO vnext.model_call(tenant_id,project_id,task_id,model_attempt_id,agent_run_id,subject,token_id,logical_request_id,input_digest,request_json,profile_json,settlement_token,send_state,response_state,billing_state,local_state,inflight,response_available,access_level) VALUES(%s,%s,%s,%s,'run-fixture',%s,%s,'forged-insert','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','{}','{}','forged-token','sent','complete','reported','ended',false,true,1) RETURNING local_state",
            lambda tx: (
                *tx.owner,
                str(uuid4()),
                case.credential.principal.subject,
                case.credential.principal.token_id,
            ),
        )
        assert forged_counter is None
        assert forged_model is None


def test_tool_request_inserts_require_admitted_reserved_pending_state(
    db_environment, tmp_path, audit_directory
):
    """Catch tool_request inserting terminal attempts or pre-settled side effects."""

    with tool_case(db_environment, tmp_path, audit_directory) as case:
        def insert(statement, parameters):
            try:
                with case.control.uow.transaction(
                    case.access, TASK, capability="tool_request"
                ) as tx:
                    return tx.connection.execute(statement, parameters(tx)).fetchone()
            except psycopg.Error:
                return None

        forged_attempt = insert(
            "INSERT INTO vnext.tool_attempt(tenant_id,project_id,task_id,tool_attempt_id,tool_call_id,agent_run_id,evidence_origin,capture_layer,receipt_json,status,permit_json,output,output_media_type,output_completeness,result_receipt_json) VALUES(%s,%s,%s,%s,'tool-fixture','run-fixture','fixture_capture','fixture_file_bytes','{\"forged\":true}','complete','{}',decode('00','hex'),'application/octet-stream','complete','{}') RETURNING status",
            lambda tx: (*tx.owner, str(uuid4())),
        )
        forged_resource = insert(
            "INSERT INTO vnext.resource_reservation(tenant_id,project_id,task_id,resource_key,agent_run_id,state,source_receipt_json) VALUES(%s,%s,%s,'forged-resource','run-fixture','released','{\"forged\":true}') RETURNING state",
            lambda tx: tx.owner,
        )
        forged_settlement = insert(
            "INSERT INTO vnext.run_operation_settlement(tenant_id,project_id,task_id,agent_run_id,status,source_receipt_json) VALUES(%s,%s,%s,'run-fixture','settled','{\"forged\":true}') RETURNING status",
            lambda tx: tx.owner,
        )
        assert forged_attempt is None
        assert forged_resource is None
        assert forged_settlement is None


def test_explicit_tool_retry_reopens_only_from_registered_stopped_attempt(
    db_environment, tmp_path, audit_directory
):
    """Catch the request guard blocking the one legitimate terminal retry transition."""

    with tool_case(db_environment, tmp_path, audit_directory) as case:
        first = case.admission.authorize(
            case.access, ToolCallRequest.model_validate(workspace_tool_request())
        )
        stopped = CancelDeliveryProbe(case.tool_module, case.admission, crash=False)
        case.gate._receive_execution(first, asyncio.run(stopped.cancel(first, reason="stop")))
        assert case.ledger.tool_call(case.access, first.tool_call_id).status == "cancelled"

        retry = case.admission.retry(
            case.access,
            first.tool_call_id,
            prior_attempt_id=first.tool_attempt_id,
            retry_request_id="retry-operation-stable",
        )
        replay = case.admission.retry(
            case.access,
            first.tool_call_id,
            prior_attempt_id=first.tool_attempt_id,
            retry_request_id="retry-operation-stable",
        )
        assert retry.tool_attempt_id != first.tool_attempt_id
        assert replay.tool_attempt_id == retry.tool_attempt_id
        completed = asyncio.run(case.gate.execute_permit(case.access, retry))
        assert completed.status == "complete"
        assert fresh_ledger(case).snapshot(case.access, TASK).tool_attempts == 2


@pytest.mark.parametrize(
    ("stored_status", "forged_status"),
    [
        ("running", "cancelled"),
        ("unknown", "admitted"),
        ("evidence_pending", "admitted"),
    ],
)
def test_tool_request_cannot_replace_nonterminal_status_with_result_state(
    db_environment,
    tmp_path,
    audit_directory,
    stored_status,
    forged_status,
):
    """Catch request status writes bypassing cancel-intent and receipt transitions."""

    with tool_case(db_environment, tmp_path, audit_directory) as case:
        call_id = str(uuid4())
        with db_environment.migration_connection() as connection:
            connection.execute(
                "INSERT INTO vnext.tool_call(tenant_id,project_id,task_id,tool_call_id,session_lineage,message_id,provider_call_id,tool_definition_version,work_item_id,input_digest,request_json,status,access_level) VALUES(%s,%s,%s,%s,'matrix-lineage','matrix-message',%s,'fixture-reader-v1','work-fixture',%s,'{}',%s,1)",
                (*OWNER, call_id, "matrix-" + stored_status, "d" * 64, stored_status),
            )
        try:
            with case.control.uow.transaction(
                case.access, TASK, capability="tool_request"
            ) as tx:
                changed = tx.connection.execute(
                    "UPDATE vnext.tool_call SET status=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_call_id=%s RETURNING status",
                    (forged_status, *tx.owner, call_id),
                ).fetchone()
        except psycopg.Error:
            changed = None
        assert changed is None


def test_tool_request_cannot_insert_an_inactive_resource_claim(
    db_environment, tmp_path, audit_directory
):
    """Catch an inactive claim bypassing the unique active resource holder."""

    with tool_case(db_environment, tmp_path, audit_directory) as case:
        permit = case.admission.authorize(
            case.access, ToolCallRequest.model_validate(workspace_tool_request())
        )
        try:
            with case.control.uow.transaction(
                case.access, TASK, capability="tool_request"
            ) as tx:
                inserted = tx.connection.execute(
                    "INSERT INTO vnext.tool_resource_claim(tenant_id,project_id,task_id,resource_key,tool_attempt_id,active) VALUES(%s,%s,%s,'workspace:inactive-forgery',%s,false) RETURNING active",
                    (*tx.owner, permit.tool_attempt_id),
                ).fetchone()
        except psycopg.Error:
            inserted = None
        assert inserted is None


def test_model_settle_cannot_insert_response_bytes_before_send(
    db_environment, tmp_path, audit_directory
):
    """Catch settlement creating response bytes for a model attempt never sent."""

    with model_case(db_environment, tmp_path, audit_directory) as case:
        permit = case.admission.authorize(
            case.access,
            ChatCompletionRequest.model_validate(NATIVE_MODEL_REQUEST),
            request_id="model-never-sent-chunk",
            original_json=canonical_json_bytes(NATIVE_MODEL_REQUEST),
        )
        try:
            with case.control.uow.transaction(
                case.access, TASK, capability="model_settle"
            ) as tx:
                inserted = tx.connection.execute(
                    "INSERT INTO vnext.model_response_chunk(tenant_id,project_id,task_id,model_attempt_id,ordinal,data,access_level) VALUES(%s,%s,%s,%s,0,decode('00','hex'),1) RETURNING ordinal",
                    (*tx.owner, permit.model_attempt_id),
                ).fetchone()
        except psycopg.Error:
            inserted = None
        assert inserted is None


def test_earliest_v8_upgrade_installs_model_update_guard(
    db_environment, tmp_path, audit_directory
):
    """Catch v9 assuming a model UPDATE trigger existed in every v8 variant."""

    migrate_earliest_v8_then_current(db_environment)
    with db_environment.migration_connection() as connection:
        triggers = {
            value[0]
            for value in connection.execute(
                "SELECT tgname FROM pg_trigger WHERE NOT tgisinternal"
            ).fetchall()
        }
    assert {"admission_counter_purpose", "model_call_purpose"} <= triggers

    with model_case(db_environment, tmp_path, audit_directory) as case:
        permit = case.admission.authorize(
            case.access,
            ChatCompletionRequest.model_validate(NATIVE_MODEL_REQUEST),
            request_id="historical-v8-model-update",
            original_json=canonical_json_bytes(NATIVE_MODEL_REQUEST),
        )
        try:
            with case.control.uow.transaction(
                case.access, TASK, capability="model_request"
            ) as tx:
                forged = tx.connection.execute(
                    "UPDATE vnext.model_call SET local_state='ended',inflight=false,response_state='complete',response_available=true WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND model_attempt_id=%s RETURNING local_state",
                    (*tx.owner, permit.model_attempt_id),
                ).fetchone()
        except psycopg.Error:
            forged = None
        assert forged is None


def test_earliest_v8_upgrade_installs_tool_update_guards(
    db_environment, tmp_path, audit_directory
):
    """Catch v9 defining tool guards without installing their triggers."""

    migrate_earliest_v8_then_current(db_environment)
    with db_environment.migration_connection() as connection:
        triggers = {
            value[0]
            for value in connection.execute(
                "SELECT tgname FROM pg_trigger WHERE NOT tgisinternal"
            ).fetchall()
        }
    assert {
        "tool_call_purpose",
        "tool_attempt_purpose",
        "tool_claim_purpose",
        "resource_reservation_purpose",
        "run_settlement_purpose",
    } <= triggers

    with tool_case(db_environment, tmp_path, audit_directory) as case:
        permit = case.admission.authorize(
            case.access, ToolCallRequest.model_validate(workspace_tool_request())
        )
        try:
            with case.control.uow.transaction(
                case.access, TASK, capability="tool_request"
            ) as tx:
                forged = tx.connection.execute(
                    "UPDATE vnext.tool_attempt SET status='complete',receipt_json='{\"forged\":true}',result_receipt_json='{}' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s RETURNING status",
                    (*tx.owner, permit.tool_attempt_id),
                ).fetchone()
        except psycopg.Error:
            forged = None
        assert forged is None
