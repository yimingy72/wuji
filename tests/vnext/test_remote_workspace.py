"""C0 remote workspace integration over real TLS and the production P03/P06 stores."""

from __future__ import annotations

import asyncio
import base64
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from importlib import util
from pathlib import Path
import ssl
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest

from support.c0 import ScriptedHttpFault, TestCertificateAuthority, TlsAsgiServer
from support.p06 import OWNER, TASK, fresh_ledger, tool_case, tool_headers
from test_knowledge_admission import IDENTITY
from test_run_admission import workspace_tool_request
from wuji_core.admission.common import digest
from wuji_core.admission.registry import RuntimeProfile
from wuji_core.admission.remote_workspace import (
    ExecutorDeploymentBinding,
    ExecutorPermitAuthority,
    RemoteExecutorTransportError,
    RemoteToolAdmission,
    RemoteWorkspaceExecutor,
    receipt_from_wire,
    receipt_to_wire,
    restore_transport_permit,
)
from wuji_core.admission.tools import ToolExecutionReceipt, ToolPermit, WorkspaceReadExecutor
from wuji_core.contracts.admission import ToolCallRequest
from wuji_core.http import canonical_json_bytes, create_app, strict_json_loads
from wuji_core.http.executor_host import create_executor_host_router
from wuji_core.persistence.uow import DomainError


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _kali_factory():
    path = REPOSITORY_ROOT / "services" / "wuji-kali-executor" / "main.py"
    spec = util.spec_from_file_location("wuji_c0_kali_executor_main", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Kali executor service module is unavailable")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.create_kali_executor_app


def _binding() -> ExecutorDeploymentBinding:
    return ExecutorDeploymentBinding(
        tenant_id=OWNER[0],
        project_id=OWNER[1],
        task_id=OWNER[2],
        executor_ref="workspace-reader-fixture",
        receiver_id="receiver-fixture",
        environment_ref="environment-fixture",
        collector_subject="collector-fixture",
        gate_subject="tool-gate-fixture",
    )


def _tokens(case):
    provider = case.credential.provider
    return SimpleNamespace(
        collector=provider.issue(
            subject="collector-fixture", tenant_id=OWNER[0], roles=["collector"]
        ),
        gate=provider.issue(
            subject="tool-gate-fixture", tenant_id=OWNER[0], roles=["gateway"]
        ),
        wrong_gate=provider.issue(
            subject="other-gate-fixture", tenant_id=OWNER[0], roles=["gateway"]
        ),
    )


@contextmanager
def _remote_stack(
    case,
    tmp_path: Path,
    audit_directory: Path,
    *,
    callback_fault: ScriptedHttpFault | None = None,
    kali_fault: ScriptedHttpFault | None = None,
):
    binding = _binding()
    tokens = _tokens(case)
    certificates = TestCertificateAuthority(tmp_path / "c0-tls")
    authority = ExecutorPermitAuthority(case.admission, bindings=[binding])
    platform_app = create_app(
        token_verifier=case.credential.verifier,
        routers=[create_executor_host_router(authority)],
    )
    with TlsAsgiServer(
        platform_app,
        identity=certificates.issue_server("platform"),
        audit_path=audit_directory / "c0-platform-https.jsonl",
        fault=callback_fault,
    ) as platform_server:
        remote_admission = RemoteToolAdmission(
            binding=binding,
            base_url=platform_server.url,
            ca_file=str(certificates.ca_file),
            bearer_token=tokens.collector,
        )
        kali_app = _kali_factory()(
            token_verifier=case.credential.verifier,
            binding=binding,
            admission=remote_admission,
            root=case.workspace,
            receipt_root=case.receipt_root,
        )
        with TlsAsgiServer(
            kali_app,
            identity=certificates.issue_server("kali"),
            audit_path=audit_directory / "c0-kali-https.jsonl",
            fault=kali_fault,
        ) as kali_server:
            executor = RemoteWorkspaceExecutor(
                binding=binding,
                base_url=kali_server.url,
                ca_file=str(certificates.ca_file),
                bearer_token=tokens.gate,
            )
            yield SimpleNamespace(**locals(), remote=executor)


def _authorize(case, provider_call_id: str) -> ToolPermit:
    request = ToolCallRequest.model_validate(
        workspace_tool_request(provider_call_id=provider_call_id)
    )
    return case.admission.authorize(case.access, request)


def _https_post(url: str, *, ca_file: Path, token: str, payload: dict):
    context = ssl.create_default_context(cafile=str(ca_file))
    with httpx.Client(
        verify=context,
        trust_env=False,
        follow_redirects=False,
        timeout=5,
    ) as client:
        return client.post(
            url,
            content=canonical_json_bytes(payload),
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Accept-Encoding": "identity",
            },
        )


def _permit_document() -> tuple[ToolPermit, dict]:
    runtime = RuntimeProfile.model_validate(
        {
            "ref": "fixture-runtime-v1",
            "revision": "1",
            "published_at": "2026-09-13T00:00:00Z",
            "lock_digest": "a" * 64,
            "limits": {
                "max_work_items": 4,
                "max_reason_runs": 2,
                "max_model_requests": 2,
                "max_tool_calls": 2,
                "max_single_output_bytes": 16,
                "max_total_output_bytes": 64,
                "max_elapsed_seconds": 300,
                "max_attempts_per_work": 2,
                "repair_attempts": 0,
            },
            "chunk_bytes": 8,
            "buffer_bytes": 16,
            "idle_timeout_seconds": 5,
            "total_timeout_seconds": 30,
            "max_pending_operations": 2,
            "max_inflight_tools": 1,
            "max_inflight_model_requests": 1,
            "allowed_tool_refs": ["fixture-reader-v1"],
        }
    )
    arguments = {"path": "version.txt"}
    document = {
        "tool_call_id": "tool-call-c0",
        "tool_attempt_id": "00000000-0000-4000-8000-000000000101",
        "identity": IDENTITY,
        "executor_ref": "workspace-reader-fixture",
        "tool_definition_ref": "fixture-reader-v1",
        "arguments": arguments,
        "arguments_digest": digest(arguments),
        "resource_keys": ["workspace:environment-fixture:version.txt"],
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
        "execution_token": "c0-execution-token",
        "subject": "run-worker-fixture",
        "token_id": "c0-token-id",
        "roles": ["worker"],
        "runtime": runtime.model_dump(mode="json"),
    }
    return ToolPermit.restore(document, request_id="c0-wire"), document


def _execution_receipt(permit: ToolPermit, output: bytes | None):
    receipt_id = "receipt-c0"
    source = {
        "tool_attempt_id": permit.tool_attempt_id,
        "receiver_id": "receiver-fixture",
        "environment_ref": "environment-fixture",
        "arguments_digest": permit.arguments_digest,
        "receipt_id": receipt_id,
    }
    if output is not None:
        source.update(
            output_bytes=len(output), output_sha256=sha256(output).hexdigest()
        )
    now = datetime.now(UTC)
    return ToolExecutionReceipt.model_validate(
        {
            "tool_attempt_id": permit.tool_attempt_id,
            "receiver_id": "receiver-fixture",
            "receipt_id": receipt_id,
            "status": "exited" if output is not None else "unknown",
            "started_at": now if output is not None else None,
            "exited_at": now if output is not None else None,
            "source_receipt": source,
            "output": output,
            "media_type": "application/octet-stream" if output is not None else None,
            "completeness": "complete" if output is not None else "unknown",
            "error_code": None if output is not None else "prepared_without_exit",
        }
    )


def test_permit_and_receipt_wire_are_exactly_bound():
    permit, document = _permit_document()
    binding = _binding()
    mutations = {
        "tool_call_id": "another-call",
        "tool_attempt_id": "00000000-0000-4000-8000-000000000102",
        "identity": {**IDENTITY, "work_item_id": "another-work"},
        "executor_ref": "another-executor",
        "tool_definition_ref": "another-tool",
        "arguments": {"path": "another.txt"},
        "arguments_digest": "b" * 64,
        "resource_keys": ["workspace:environment-fixture:another.txt"],
        "expires_at": (datetime.now(UTC) + timedelta(minutes=6)).isoformat(),
        "execution_token": "another-token",
        "subject": "another-worker",
        "token_id": "another-token-id",
        "roles": ["worker", "other"],
        "runtime": {**document["runtime"], "chunk_bytes": 4},
    }
    for field, value in mutations.items():
        changed = deepcopy(document)
        changed[field] = value
        with pytest.raises(DomainError):
            restore_transport_permit(
                changed,
                permit_digest=digest(document),
                request_id="c0-tamper-" + field,
                binding=binding,
            )

    empty = receipt_to_wire(
        permit,
        _execution_receipt(permit, b""),
        binding=binding,
        max_output_bytes=16,
    )
    assert empty["output_base64"] == ""
    assert empty["output_bytes"] == "0"
    assert receipt_from_wire(
        empty, permit, binding=binding, max_output_bytes=16
    ).output == b""
    null = receipt_to_wire(
        permit,
        _execution_receipt(permit, None),
        binding=binding,
        max_output_bytes=16,
    )
    assert [null[key] for key in ("output_base64", "output_bytes", "output_sha256")] == [
        None,
        None,
        None,
    ]

    invalid = []
    mixed = dict(empty, output_bytes=None)
    invalid.append(mixed)
    invalid.append(dict(empty, output_base64="A==="))
    invalid.append(dict(empty, output_bytes="1"))
    invalid.append(dict(empty, output_sha256="f" * 64))
    invalid.append(dict(null, output_bytes="0"))
    oversized = b"x" * 17
    invalid.append(
        dict(
            empty,
            output_base64=base64.b64encode(oversized).decode("ascii"),
            output_bytes=str(len(oversized)),
            output_sha256=sha256(oversized).hexdigest(),
        )
    )
    for value in invalid:
        with pytest.raises(RemoteExecutorTransportError):
            receipt_from_wire(value, permit, binding=binding, max_output_bytes=16)


def test_real_https_workspace_read_persists_p03_and_old_receipt_after_revocation(
    db_environment, tmp_path, audit_directory
):
    with tool_case(db_environment, tmp_path, audit_directory) as case:
        with _remote_stack(case, tmp_path, audit_directory) as stack:
            case.gate.executors[(*stack.binding.owner, stack.binding.executor_ref)] = stack.remote
            response = case.client.post(
                "/internal/v2/tool-calls",
                json=workspace_tool_request(provider_call_id="call-c0-real-https"),
                headers=tool_headers(case, "c0-real-https"),
            )
            assert response.status_code == 200
            receipt = response.json()
            assert receipt["status"] == "complete"
            assert receipt["evidence_receipt"] is not None
            assert receipt["result_ref"] is not None
            artifact = case.client.get(
                f"/api/v2/artifacts/{receipt['result_ref']['id']}/content",
                params={"version": receipt["result_ref"]["version"]},
                headers={"Authorization": "Bearer " + case.credential.token},
            )
            assert artifact.status_code == 200
            assert artifact.content == case.expected_output
            permit = case.gate._existing_permit(case.access, receipt["tool_call_id"])

            with db_environment.migration_connection() as connection:
                case.registry_module.revoke_run_credential(
                    connection,
                    tenant_id=case.credential.principal.tenant_id,
                    subject=case.credential.principal.subject,
                    token_id=case.credential.principal.token_id,
                )
            (case.workspace / "version.txt").write_bytes(b"changed-after-revocation\n")
            old = asyncio.run(stack.remote.query(permit))
            assert old.tool_attempt_id == permit.tool_attempt_id
            assert old.output == case.expected_output

            rejected = case.client.post(
                "/internal/v2/tool-calls",
                json=workspace_tool_request(provider_call_id="call-c0-after-revoke"),
                headers=tool_headers(case, "c0-after-revoke"),
            )
            assert rejected.status_code == 409
            assert rejected.json()["code"] == "STALE_EXECUTION"
            assert fresh_ledger(case).snapshot(case.access, TASK).tool_attempts == 1
            assert [item.path for item in stack.kali_server.exchanges] == [
                "/internal/v2/executor/dispatch",
                "/internal/v2/executor/query",
            ]
            purposes = [
                strict_json_loads(item.request_body)["purpose"]
                for item in stack.platform_server.exchanges
            ]
            assert purposes.count("check_execution") == 1
            assert purposes.count("validate_receipt") == 2


@pytest.mark.parametrize("fault_mode", ["drop", "status_503", "bad_ack"])
def test_callback_commits_then_lost_or_invalid_ack_keeps_prepared_unknown(
    db_environment, tmp_path, audit_directory, fault_mode
):
    fault = ScriptedHttpFault(
        path="/internal/v2/executors/workspace-reader-fixture/permits/check",
        phase="after",
        mode=fault_mode,
        purpose="check_execution",
    )
    with tool_case(db_environment, tmp_path, audit_directory) as case:
        permit = _authorize(case, "call-c0-callback-" + fault_mode)
        with _remote_stack(
            case, tmp_path, audit_directory, callback_fault=fault
        ) as stack:
            local_kali = WorkspaceReadExecutor(
                root=case.workspace,
                receipt_root=case.receipt_root,
                admission=stack.remote_admission,
                receiver_id=stack.binding.receiver_id,
                environment_ref=stack.binding.environment_ref,
            )
            with pytest.raises(OSError) as ambiguous:
                asyncio.run(local_kali.dispatch(permit))
            assert isinstance(ambiguous.value, RemoteExecutorTransportError)
            assert not isinstance(ambiguous.value, DomainError)
            stored = asyncio.run(local_kali.query(permit))
            assert stored.status == "unknown"
            assert stored.error_code == "prepared_without_exit"
            assert stored.output is None
            raw = strict_json_loads(
                (case.receipt_root / f"{UUID(permit.tool_attempt_id)}.json").read_bytes()
            )
            assert raw["status"] == "unknown"
            assert raw["error_code"] == "prepared_without_exit"
            with db_environment.migration_connection() as connection:
                assert connection.execute(
                    "SELECT status,receipt_json FROM vnext.tool_attempt WHERE tool_attempt_id=%s",
                    (permit.tool_attempt_id,),
                ).fetchone() == ("dispatched", "{}")
            assert fault.hits == 1


def test_ambiguous_dispatch_queries_same_attempt_once_and_not_registered_stays_unknown(
    db_environment, tmp_path, audit_directory
):
    fault = ScriptedHttpFault(
        path="/internal/v2/executor/dispatch",
        phase="before",
        mode="drop",
        times=None,
    )
    with tool_case(db_environment, tmp_path, audit_directory) as case:
        permit = _authorize(case, "call-c0-not-registered")
        with _remote_stack(case, tmp_path, audit_directory, kali_fault=fault) as stack:
            case.gate.executors[(*stack.binding.owner, stack.binding.executor_ref)] = stack.remote
            result = asyncio.run(case.gate.execute_permit(case.access, permit))
            assert result.status == "unknown"
            assert result.tool_attempt_id.root == permit.tool_attempt_id
            assert [item.path for item in stack.kali_server.exchanges] == [
                "/internal/v2/executor/dispatch",
                "/internal/v2/executor/query",
            ]
            sent = [strict_json_loads(item.request_body) for item in stack.kali_server.exchanges]
            assert {item["permit"]["tool_attempt_id"] for item in sent} == {
                permit.tool_attempt_id
            }
            assert list(case.receipt_root.glob("*.json")) == []
            with pytest.raises(DomainError) as retry:
                case.admission.retry(
                    case.access,
                    permit.tool_call_id,
                    prior_attempt_id=permit.tool_attempt_id,
                    retry_request_id="c0-forbidden-retry",
                )
            assert retry.value.code == "OPERATION_UNKNOWN"
            assert fresh_ledger(case).snapshot(case.access, TASK).tool_attempts == 1


def test_https_tamper_wrong_executor_and_wrong_gate_are_rejected_from_db_authority(
    db_environment, tmp_path, audit_directory
):
    with tool_case(db_environment, tmp_path, audit_directory) as case:
        permit = _authorize(case, "call-c0-tamper")
        with _remote_stack(case, tmp_path, audit_directory) as stack:
            original = permit.stored()
            tampered = deepcopy(original)
            tampered["arguments"] = {"path": "other.txt"}
            tamper_response = _https_post(
                stack.kali_server.url + "/internal/v2/executor/dispatch",
                ca_file=stack.certificates.ca_file,
                token=stack.tokens.gate,
                payload={"permit": tampered, "permit_digest": digest(tampered)},
            )
            assert tamper_response.status_code in {403, 404}
            assert tamper_response.json()["code"] == "NOT_FOUND_OR_FORBIDDEN"

            check_payload = {
                "identity": original["identity"],
                "tool_attempt_id": original["tool_attempt_id"],
                "execution_token": original["execution_token"],
                "permit_digest": digest(original),
                "purpose": "check_execution",
            }
            wrong_executor = _https_post(
                stack.platform_server.url
                + "/internal/v2/executors/not-this-executor/permits/check",
                ca_file=stack.certificates.ca_file,
                token=stack.tokens.collector,
                payload=check_payload,
            )
            assert wrong_executor.status_code in {403, 404}
            assert wrong_executor.json()["code"] == "NOT_FOUND_OR_FORBIDDEN"

            wrong_gate = _https_post(
                stack.kali_server.url + "/internal/v2/executor/dispatch",
                ca_file=stack.certificates.ca_file,
                token=stack.tokens.wrong_gate,
                payload={"permit": original, "permit_digest": digest(original)},
            )
            assert wrong_gate.status_code in {403, 404}
            assert wrong_gate.json()["code"] == "NOT_FOUND_OR_FORBIDDEN"
            assert list(case.receipt_root.glob("*.json")) == []
            with db_environment.migration_connection() as connection:
                assert connection.execute(
                    "SELECT status FROM vnext.tool_attempt WHERE tool_attempt_id=%s",
                    (permit.tool_attempt_id,),
                ).fetchone() == ("admitted",)
