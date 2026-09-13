"""P07 M1 tests for the actual Microsoft Agent Framework worker path."""

from __future__ import annotations

import asyncio
from copy import deepcopy

import httpx

from support.m1 import (
    MODEL_ROUTE,
    TOOL_DEFINITION_REF,
    TOOL_ROUTE,
    gate_headers,
    m1_case,
    maf_runtime_type,
    recorded_requests,
    table_count,
)
from support.p06 import NATIVE_MODEL_REQUEST
from wuji_core.http import canonical_json_bytes, strict_json_loads


def test_maf_runtime_exposes_the_formal_execute_operation_port():
    runtime_type = maf_runtime_type()

    assert callable(getattr(runtime_type, "execute", None))


async def _finish_after_event_consumer_disconnects(case, runtime):
    iterator = runtime.execute(case.assignment).__aiter__()
    consumer = asyncio.create_task(anext(iterator))
    started = await asyncio.to_thread(case.upstream.first_request_started.wait, 5)
    if not started and consumer.done():
        await consumer
    assert started, "actual SDK never reached the localhost model through ModelGate"
    consumer.cancel()
    try:
        await consumer
    except asyncio.CancelledError:
        pass
    case.upstream.release_first_response.set()
    receipt = await runtime.wait(case.assignment.identity)
    await runtime.aclose()
    return receipt


async def _finish_with_worker_consumer(case, runtime):
    case.upstream.release_first_response.set()
    events = [event async for event in runtime.execute(case.assignment)]
    await runtime.aclose()
    return events, runtime.result


def _model_gate_exchanges(case):
    return [
        exchange
        for exchange in case.gate_server.exchanges
        if exchange.path == MODEL_ROUTE
    ]


def test_actual_maf_stream_tool_evidence_claim_and_result_replay(
    db_environment, tmp_path, audit_directory
):
    """Catch any SDK/Gate/tool/evidence/result shortcut or duplicate replay effect."""

    with m1_case(db_environment, tmp_path, audit_directory) as case:
        runtime = case.new_runtime()
        result = asyncio.run(_finish_after_event_consumer_disconnects(case, runtime))

        assert result.status.value == "accepted"
        assert len(result.components) == 1
        assert result.components[0].status.value == "accepted_shared"
        assert case.context.read_set == ()
        assert len(case.upstream.exchanges) == 2
        assert all(
            exchange.status_code == 200
            and exchange.response_headers["content-type"] == "text/event-stream"
            and exchange.response_body.startswith(b"data: ")
            and exchange.response_body.endswith(b"data: [DONE]\n\n")
            for exchange in case.upstream.exchanges
        )

        upstream_requests = [
            strict_json_loads(exchange.request_body)
            for exchange in case.upstream.exchanges
        ]
        assert [request["stream"] for request in upstream_requests] == [True, True]
        assert all(
            request["model"] == "fixture-upstream-model"
            for request in upstream_requests
        )
        advertised = upstream_requests[0]["tools"]
        assert len(advertised) == 1
        assert advertised[0]["type"] == "function"
        assert advertised[0]["function"]["name"] == "read_fixture"
        assert advertised[0]["function"]["parameters"] == {
            "type": "object",
            "properties": {"path": {"type": "string", "minLength": 1}},
            "required": ["path"],
            "additionalProperties": False,
        }

        model_exchanges = _model_gate_exchanges(case)
        tool_requests = recorded_requests(case, TOOL_ROUTE)
        assert len(model_exchanges) == 2
        assert len(tool_requests) == 1
        first_attempt = model_exchanges[0].response_headers[
            "x-wuji-model-attempt-id"
        ]
        tool_request = tool_requests[0]
        assert tool_request == {
            "session_lineage": "session-lineage-fixture",
            "message_id": f"model-attempt:{first_attempt}:choice:0",
            "provider_call_id": "call-m1-read",
            "tool_definition_ref": TOOL_DEFINITION_REF,
            "arguments": {"path": "version.txt"},
            "sdk_content_id": tool_request["sdk_content_id"],
            "sdk_approval_id": None,
            "approval_ref": None,
        }
        assert isinstance(tool_request["sdk_content_id"], str)
        assert tool_request["sdk_content_id"]
        assert runtime.identity_mapping == [
            {
                "model_attempt_id": first_attempt,
                "request": tool_request,
                "native_arguments": '{"path":"version.txt"}',
            }
        ]

        assert len(runtime.tool_receipts) == 1
        tool_receipt = runtime.tool_receipts[0]
        assert tool_receipt.status.value == "complete"
        assert tool_receipt.evidence_receipt is not None
        assert tool_receipt.evidence_receipt.status.value == "accepted"
        observation_ref = tool_receipt.evidence_receipt.observation_ref
        assert observation_ref is not None
        assert tool_receipt.result_ref is not None
        assert case.upstream.received_tool_receipt == tool_receipt.model_dump(
            mode="json"
        )

        artifact_ref = tool_receipt.evidence_receipt.artifact_refs[0]
        with httpx.Client(timeout=10, trust_env=False, follow_redirects=False) as client:
            artifact = client.get(
                case.gate_server.url
                + f"/api/v2/artifacts/{artifact_ref.id}/content",
                params={"version": artifact_ref.version.root},
                headers={"Authorization": "Bearer " + case.credential.token},
            )
            claim_ref = result.components[0].canonical_ref
            assert claim_ref is not None
            claim = client.get(
                case.gate_server.url
                + f"/api/v2/tasks/task-fixture/records/claim/{claim_ref.id}",
                params={"revision": claim_ref.revision.root},
                headers={"Authorization": "Bearer " + case.credential.token},
            )
        assert artifact.status_code == 200
        assert artifact.content == case.expected_output
        assert claim.status_code == 200, claim.text
        claim_body = claim.json()
        assert claim_body["display_kind"] == "claim"
        assert claim_body["assessment"]["eligible"] is False
        assert claim_body["record"]["producer_kind"] == "agent"
        assert claim_body["record"]["producer_ref"] == "run-fixture"
        assert claim_body["record"]["basis_refs"] == [
            observation_ref.model_dump(mode="json")
        ]
        assert table_count(case, "observation") == 1
        assert table_count(case, "assessment") == 0

        final_payload = strict_json_loads(runtime.raw_output)
        assert final_payload["claims"][0]["basis_refs"] == [
            observation_ref.model_dump(mode="json")
        ]
        assert runtime.sdk_output
        assert case.credential.token.encode("utf-8") not in runtime.sdk_output
        with db_environment.migration_connection() as connection:
            envelope = strict_json_loads(
                connection.execute(
                    "SELECT envelope_json FROM vnext.result_submission WHERE task_id=%s",
                    ("task-fixture",),
                ).fetchone()[0]
            )
            observation = connection.execute(
                "SELECT capture_id,tool_attempt_id FROM vnext.observation WHERE entity_id=%s AND revision=1",
                (observation_ref.id,),
            ).fetchone()
        assert envelope["snapshot_id"] == case.context.snapshot_id
        assert envelope["read_set"] == []
        assert observation[1] == tool_receipt.tool_attempt_id.root

        before = {
            name: table_count(case, name)
            for name in (
                "claim_revision",
                "model_attempt",
                "observation",
                "result_receipt",
                "result_submission",
                "tool_attempt",
            )
        }
        network_before = (
            len(case.upstream.exchanges),
            len(case.gate_server.exchanges),
        )
        replay = case.host.submit_result(
            case.assignment,
            raw_output=runtime.raw_output,
            context=case.context,
            tool_receipts=tuple(runtime.tool_receipts),
            sdk_output=runtime.sdk_output,
        )
        assert replay == result
        assert {
            name: table_count(case, name) for name in before
        } == before
        assert (
            len(case.upstream.exchanges),
            len(case.gate_server.exchanges),
        ) == network_before

        audit_directory.joinpath("m1-result-summary.json").write_bytes(
            canonical_json_bytes(
                {
                    "result": result.model_dump(mode="json"),
                    "model_requests": len(case.upstream.exchanges),
                    "tool_requests": len(tool_requests),
                    "observation_ref": observation_ref.model_dump(mode="json"),
                    "claim_ref": claim_ref.model_dump(mode="json"),
                    "replay_counts": before,
                }
            )
        )


def test_revoked_run_rejects_new_model_and_tool_gate_actions(
    db_environment, tmp_path, audit_directory
):
    """Catch either Gate trusting a still-valid JWT after binding revocation."""

    with m1_case(db_environment, tmp_path, audit_directory) as case:
        runtime = case.new_runtime()
        _events, result = asyncio.run(_finish_with_worker_consumer(case, runtime))
        assert result.status.value == "accepted"
        before = {
            "model_attempt": table_count(case, "model_attempt"),
            "tool_attempt": table_count(case, "tool_attempt"),
            "upstream": len(case.upstream.exchanges),
        }
        with db_environment.migration_connection() as connection:
            case.registry_module.revoke_run_credential(
                connection,
                tenant_id=case.credential.principal.tenant_id,
                subject=case.credential.principal.subject,
                token_id=case.credential.principal.token_id,
            )

        model_body = deepcopy(NATIVE_MODEL_REQUEST)
        model_body["stream"] = True
        tool_body = {
            "session_lineage": "session-lineage-fixture",
            "message_id": "model-attempt:revoked-probe:choice:0",
            "provider_call_id": "call-m1-revoked",
            "tool_definition_ref": TOOL_DEFINITION_REF,
            "arguments": {"path": "version.txt"},
            "sdk_content_id": "revoked-sdk-content",
            "sdk_approval_id": None,
            "approval_ref": None,
        }
        with httpx.Client(timeout=10, trust_env=False, follow_redirects=False) as client:
            model_response = client.post(
                case.gate_server.url + MODEL_ROUTE,
                content=canonical_json_bytes(model_body),
                headers=gate_headers(case, "m1-revoked-model"),
            )
            tool_response = client.post(
                case.gate_server.url + TOOL_ROUTE,
                content=canonical_json_bytes(tool_body),
                headers=gate_headers(case, "m1-revoked-tool"),
            )
        assert model_response.status_code == 409
        assert model_response.json()["code"] == "STALE_EXECUTION"
        assert tool_response.status_code == 409
        assert tool_response.json()["code"] == "STALE_EXECUTION"
        assert table_count(case, "model_attempt") == before["model_attempt"]
        assert table_count(case, "tool_attempt") == before["tool_attempt"]
        assert len(case.upstream.exchanges) == before["upstream"]

        audit_directory.joinpath("m1-revocation-summary.json").write_bytes(
            canonical_json_bytes(
                {
                    "model": {
                        "status": model_response.status_code,
                        "body": model_response.json(),
                    },
                    "tool": {
                        "status": tool_response.status_code,
                        "body": tool_response.json(),
                    },
                    "unchanged_counts": before,
                }
            )
        )
