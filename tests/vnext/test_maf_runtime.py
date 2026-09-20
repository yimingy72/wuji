"""P07 M1 tests for the actual Microsoft Agent Framework worker path."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256

import httpx
import pytest
from pydantic import ValidationError

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
from support.p06 import NATIVE_MODEL_REQUEST, bind_secondary_model_run
from wuji_core.contracts.execution import ChatCompletionRequest
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError


def test_maf_runtime_exposes_the_formal_execute_operation_port():
    runtime_type = maf_runtime_type()

    assert callable(getattr(runtime_type, "execute", None))


def test_worker_host_resolves_an_explicitly_toolless_reason():
    from wuji_core.worker_host import _profile_tools_valid

    assert _profile_tools_valid("reason", ())
    assert _profile_tools_valid("report", ())
    assert _profile_tools_valid("explore", ("http-read-v1",))
    assert not _profile_tools_valid("explore", ())


def test_native_stream_contract_preserves_released_sdk_fields_and_token_dialect():
    native = {
        **NATIVE_MODEL_REQUEST,
        "stream": True,
        "parallel_tool_calls": False,
        "stream_options": {"include_usage": True},
        "max_completion_tokens": 64,
    }
    native.pop("max_tokens")

    parsed = ChatCompletionRequest.model_validate(native)

    assert parsed.model_dump(mode="json", exclude_none=True) == native
    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(
            {**native, "max_tokens": native["max_completion_tokens"]}
        )


def test_toolless_model_request_may_omit_tool_controls():
    """The released SDK omits both fields when function invocation is disabled."""

    from wuji_maf_worker.tools import ModelCallIdentity

    identity = ModelCallIdentity([], max_bytes=65_536)
    request = httpx.Request(
        "POST",
        "https://gate.invalid/internal/v2/model/chat/completions",
        json={
            "model": "fixture",
            "messages": [{"role": "user", "content": "bounded fixture"}],
            "stream": True,
            "stream_options": {"include_usage": True},
            "max_completion_tokens": 64,
        },
    )

    asyncio.run(identity.request(request))
    assert request.headers["X-Wuji-Request-ID"]

    request_with_tools = httpx.Request(
        "POST",
        "https://gate.invalid/internal/v2/model/chat/completions",
        json={
            **strict_json_loads(request.content),
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "read_fixture",
                        "parameters": {
                            "type": "object",
                            "additionalProperties": False,
                        },
                    },
                }
            ],
        },
    )
    tool_identity = ModelCallIdentity(
        [
            {
                "name": "read_fixture",
                "input_schema": {
                    "type": "object",
                    "additionalProperties": False,
                },
            }
        ],
        max_bytes=65_536,
    )

    with pytest.raises(ValueError, match="frozen M1 transport"):
        asyncio.run(tool_identity.request(request_with_tools))


def _unread_intent_output():
    return canonical_json_bytes(
        {
            "schema_version": "wuji.agent-payload.v2",
            "claims": [],
            "intent_proposals": [
                {
                    "client_ref": "unread",
                    "question": "Read the authorised entry.",
                    "basis_refs": [
                        {
                            "entity_type": "origin",
                            "id": "not-in-the-delivered-read-set",
                            "revision": "1",
                        }
                    ],
                    "expected_output": "A bounded observation.",
                }
            ],
            "limitations": [],
        }
    )


def test_invalid_unread_reference_is_rejected_once_without_duplicate_artifacts(
    db_environment, tmp_path, audit_directory
):
    with m1_case(db_environment, tmp_path, audit_directory) as case:
        values = {
            "raw_output": _unread_intent_output(),
            "context": case.context,
            "tool_receipts": (),
            "sdk_output": b'{"type":"message"}\n',
        }

        first = case.host.submit_result(case.assignment, **values)
        assert first.status.value == "rejected"
        assert first.code.value == "INVALID_REFERENCE"
        with db_environment.migration_connection() as connection:
            before = connection.execute(
                "SELECT count(*) FROM vnext.artifact WHERE task_id=%s",
                (case.assignment.identity.task_id,),
            ).fetchone()[0]
            assert connection.execute(
                "SELECT count(*) FROM vnext.result_submission WHERE task_id=%s",
                (case.assignment.identity.task_id,),
            ).fetchone()[0] == 1

        assert case.host.submit_result(case.assignment, **values) == first
        with db_environment.migration_connection() as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext.artifact WHERE task_id=%s",
                (case.assignment.identity.task_id,),
            ).fetchone()[0] == before


def test_initial_reason_drops_unread_basis_but_preserves_raw_output(
    db_environment, tmp_path, audit_directory
):
    with m1_case(db_environment, tmp_path, audit_directory) as case:
        assignment = case.assignment.model_copy(
            update={
                "work_kind": type(case.assignment.work_kind).reason,
                "tool_definition_refs": (),
            }
        )
        raw = _unread_intent_output()
        values = {
            "raw_output": raw,
            "context": case.context,
            "tool_receipts": (),
            "sdk_output": b'{"type":"message"}\n',
        }

        first = case.host.submit_result(assignment, **values)
        assert first.status.value == "accepted"
        assert first.components[0].status.value == "accepted_shared"
        with db_environment.migration_connection() as connection:
            basis, envelope = connection.execute(
                "SELECT i.basis_json,s.envelope_json FROM vnext.intent_revision i"
                " JOIN vnext.result_submission s USING(tenant_id,project_id,task_id)"
                " WHERE i.task_id=%s",
                (assignment.identity.task_id,),
            ).fetchone()
            before = connection.execute(
                "SELECT count(*) FROM vnext.artifact WHERE task_id=%s",
                (assignment.identity.task_id,),
            ).fetchone()[0]
        assert strict_json_loads(basis) == []
        raw_ref = strict_json_loads(envelope)["raw_output_ref"]
        stored, _digest = case.control.store.read(
            case.host_access, raw_ref["id"], raw_ref["version"]
        )
        assert stored == raw

        assert case.host.submit_result(assignment, **values) == first
        with db_environment.migration_connection() as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext.artifact WHERE task_id=%s",
                (assignment.identity.task_id,),
            ).fetchone()[0] == before


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


def test_verified_bearer_must_match_host_and_assignment_before_model_request(
    db_environment, tmp_path, audit_directory
):
    """Catch two valid Runs being spliced across Host and Gate transport."""

    with m1_case(db_environment, tmp_path, audit_directory) as case:
        other_run = bind_secondary_model_run(case)
        runtime = case.new_runtime(run_credential=other_run.token)

        with pytest.raises(DomainError) as mismatch:
            asyncio.run(_finish_with_worker_consumer(case, runtime))

        assert mismatch.value.code == "STALE_EXECUTION"
        assert case.upstream.exchanges == []
        assert _model_gate_exchanges(case) == []
        assert table_count(case, "model_attempt") == 0


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
        assert all(
            request["parallel_tool_calls"] is False
            and request["stream_options"] == {"include_usage": True}
            and request["max_completion_tokens"] == 2_048
            and "max_tokens" not in request
            for request in upstream_requests
        )
        with case.environment.migration_connection() as connection:
            settlements = [
                strict_json_loads(value[0])
                for value in connection.execute(
                    "SELECT settlement_json FROM vnext.model_call WHERE task_id=%s ORDER BY created_at",
                    ("task-fixture",),
                ).fetchall()
            ]
        assert [item["usage"] for item in settlements] == [
            {"prompt_tokens": 19, "completion_tokens": 7, "total_tokens": 26},
            {"prompt_tokens": 31, "completion_tokens": 13, "total_tokens": 44},
        ]
        assert all(item["usage_state"] == "reported" for item in settlements)
        assert all(item["usage_source"] == "terminal_content_chunk" for item in settlements)
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
        delivered = case.upstream.received_tool_receipt
        assert {
            key: value
            for key, value in delivered.items()
            if key not in {"material", "material_omitted"}
        } == tool_receipt.model_dump(mode="json")
        # The Run that produced the bytes receives them, whole and unbounded by
        # guesswork: a replayed receipt alone would leave the model blind.
        assert "material_omitted" not in delivered
        assert delivered["material"] == {
            "encoding": "utf-8",
            "byte_length": len(case.expected_output),
            "text": case.expected_output.decode(),
        }

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

        publication_id = "result:" + result.submission_id
        with db_environment.migration_connection() as connection:
            published = connection.execute(
                """SELECT a.entity_id,a.revision,a.media_type,a.sha256
                FROM vnext.publication_ref p JOIN vnext.artifact a
                ON (a.tenant_id,a.project_id,a.task_id,a.entity_id,a.revision)=
                   (p.tenant_id,p.project_id,p.task_id,p.artifact_id,p.artifact_revision)
                WHERE p.task_id=%s AND p.publication_id=%s ORDER BY a.media_type""",
                ("task-fixture", publication_id),
            ).fetchall()
        by_media_type = {row[2]: row for row in published}
        assert set(by_media_type) == {
            "application/vnd.wuji.maf-result-binding+json",
            "application/x-ndjson",
            "text/plain; charset=utf-8",
        }
        sdk_row = by_media_type["application/x-ndjson"]
        assert sdk_row[3] == sha256(runtime.sdk_output).hexdigest()
        binding_row = by_media_type[
            "application/vnd.wuji.maf-result-binding+json"
        ]
        binding_bytes, _digest = case.control.store.read(
            case.host_access, binding_row[0], str(binding_row[1])
        )
        binding = strict_json_loads(binding_bytes)
        assert binding["schema_version"] == "wuji.maf-result-binding.v1"
        assert binding["submission_id"] == result.submission_id
        assert binding["identity"] == case.assignment.identity.model_dump(mode="json")
        assert binding["operation_id"] == case.assignment.operation_id
        assert binding["raw_output"]["sha256"] == sha256(
            runtime.raw_output
        ).hexdigest()
        assert binding["sdk_output"] == {
            "ref": {
                "id": sdk_row[0],
                "version": str(sdk_row[1]),
                "sha256": sdk_row[3],
            },
            "sha256": sha256(runtime.sdk_output).hexdigest(),
            "size_bytes": len(runtime.sdk_output),
        }
        rendered_context = strict_json_loads(case.context.text)
        assert binding["context"] == {
            "schema_version": "wuji.context.v2",
            "snapshot_id": case.context.snapshot_id,
            "input_digest": case.context.input_digest,
            "text_digest": sha256(
                case.context.text.encode("utf-8")
            ).hexdigest(),
            "read_set": [],
            "record_refs": [],
            "relations_digest": sha256(
                canonical_json_bytes(rendered_context["relations"])
            ).hexdigest(),
        }
        assert binding["tool_receipts"] == [
            {
                "tool_call_id": tool_receipt.tool_call_id,
                "operation_id": tool_receipt.operation_id,
                "tool_attempt_id": tool_receipt.tool_attempt_id.root,
                "receipt_digest": sha256(
                    canonical_json_bytes(tool_receipt.model_dump(mode="python"))
                ).hexdigest(),
                "observation_ref": observation_ref.model_dump(mode="json"),
                "artifact_refs": [
                    ref.model_dump(mode="json")
                    for ref in tool_receipt.evidence_receipt.artifact_refs
                ],
                "result_ref": tool_receipt.result_ref.model_dump(mode="json"),
            }
        ]

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
        for changed in (
            {"sdk_output": runtime.sdk_output + b"changed"},
            {"tool_receipts": ()},
            {
                "context": replace(
                    case.context,
                    input_digest="0" * 64,
                    record_refs=(observation_ref,),
                )
            },
        ):
            replay_values = {
                "raw_output": runtime.raw_output,
                "context": case.context,
                "tool_receipts": tuple(runtime.tool_receipts),
                "sdk_output": runtime.sdk_output,
                **changed,
            }
            with pytest.raises(DomainError) as conflict:
                case.host.submit_result(case.assignment, **replay_values)
            assert conflict.value.code == "INPUT_DIGEST_CONFLICT"
        assert {
            name: table_count(case, name) for name in before
        } == before

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
