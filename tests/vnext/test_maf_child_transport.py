"""M2 tests for the actual MAF controller/child transport."""

import base64
import time
from hashlib import sha256

import httpx
import pytest
from pydantic import ValidationError

from support.m2 import (
    assignment_body,
    bridge_wire_types,
    m2_case,
    receiver_body,
    TASK,
    worker_host_bridge_type,
)
from wuji_core.admission.registry import revoke_run_credential
from wuji_core.contracts.envelopes import ResultReceipt
from wuji_core.http import canonical_json_bytes, strict_json_loads


def test_worker_host_bridge_exposes_the_start_permission_boundary():
    bridge_type = worker_host_bridge_type()

    assert callable(getattr(bridge_type, "await_start", None))


def test_generated_worker_bridge_wire_is_bounded_and_strict():
    wire = bridge_wire_types()
    assignment = assignment_body()
    receiver = receiver_body()
    digest = "a" * 64
    ready = wire["WorkerStartPermission"].model_validate(
        {
            "status": "ready",
            "identity": assignment["identity"],
            "start_operation_id": assignment["operation_id"],
            "assignment_digest": digest,
            "receiver": receiver,
            "birth_id": "birth-m2-child",
            "observation_id": "observation-m2-child",
            "source_digest": "b" * 64,
            "valid_until": "2026-09-13T16:00:00Z",
        }
    )
    assert ready.status.value == "ready"
    assert ready.receiver.pod_uid == "pod-fixture"

    context = {
        "snapshot_id": assignment["snapshot_id"],
        "read_set": [],
        "record_refs": [],
        "text": '{"schema_version":"wuji.context.v2"}',
        "input_digest": "c" * 64,
    }
    submit = wire["WorkerSubmitRequest"].model_validate(
        {
            "assignment": assignment,
            "context": context,
            "raw_output_base64": base64.b64encode(b"raw").decode("ascii"),
            "sdk_output_base64": base64.b64encode(b"sdk").decode("ascii"),
            "raw_digest": "d" * 64,
            "sdk_digest": "e" * 64,
            "tool_receipts": [],
        }
    )
    assert submit.context.snapshot_id == assignment["snapshot_id"]
    with pytest.raises(ValidationError):
        wire["WorkerBridgeRequest"].model_validate(
            {"assignment": assignment, "caller_context": context}
        )
    with pytest.raises(ValidationError):
        wire["WorkerBootstrap"].model_validate(
            {
                "assignment": assignment,
                "assignment_digest": digest,
                "receiver": receiver,
                "run_credential": "fixture-token",
                "public_key_pem": "fixture-public-key",
                "issuer": "https://identity.fixture.invalid",
                "audience": "wuji-vnext-tests",
                "host_origin": "http://127.0.0.1:8000",
                "model_gate_url": "http://127.0.0.1:8000/internal/v2/model",
                "tool_gate_url": "http://127.0.0.1:8000/internal/v2/tool-calls",
                "wait_timeout_seconds": 301,
                "transport_timeout_seconds": 10,
                "max_transport_bytes": 65536,
            }
        )


def _wait_for(check, *, timeout=10):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = check()
        if last:
            return last
        time.sleep(0.02)
    raise AssertionError(f"M2 condition was not met; last={last!r}")


def test_actual_supervisor_child_waits_for_start_and_receiver_replays_bytes(
    db_environment, tmp_path, audit_directory
):
    """Catch an early SDK call, hosted substitute, or fake late-result ack."""

    with m2_case(db_environment, tmp_path, audit_directory) as case:
        started = case.node.start()
        assert started.status_code == 200, started.text
        started_body = started.json()
        assert started_body["state"] == "running"
        assert started_body["observation"]["kind"] == "started"
        process = started_body["observation"]["process"]
        assert process["pid"] > 0
        assert process["birth_id"] != str(process["pid"])

        # The child exists and polls the controller, but P05 has not accepted its
        # birth observation. No MAF model request may start in this interval.
        assert case.upstream.exchanges == []
        assert case.mapped_model.requested_urls == []
        assert not any(
            exchange.path.endswith("/chat/completions")
            for exchange in case.gate_server.exchanges
        )
        worker_directory = case.node.worker_directory()
        assert _wait_for(lambda: (worker_directory / "child-entered").exists())

        registered = case.reconciler.registered(
            task_id=TASK, operation_id=case.assignment.operation_id
        )
        running = case.reconciler.reconcile(registered)
        assert running.state == "running"
        assert running.observation.process.birth_id == process["birth_id"]
        assert case.upstream.first_request_started.wait(timeout=5)
        case.upstream.release_first_response.set()

        exited_response = _wait_for(
            lambda: (
                response
                if (response := case.node.query()).status_code == 200
                and response.json()["state"] == "exited"
                else None
            ),
            timeout=15,
        )
        exited = exited_response.json()
        assert exited["observation"]["process"]["pid"] == process["pid"]
        assert exited["observation"]["process"]["birth_id"] == process["birth_id"]
        assert exited["observation"]["process"]["exit_code"] == 1
        assert case.controller_fault.rejections == 1
        assert (worker_directory / "result-request.json").is_file()
        assert (worker_directory / "sdk-request.json").is_file()
        assert not (worker_directory / "result-receipt.json").exists()

        final = case.reconciler.reconcile(registered)
        assert final.state == "exited"
        with db_environment.migration_connection() as connection:
            result_row = connection.execute(
                """SELECT r.receipt_json FROM vnext.result_submission s
                JOIN vnext.result_receipt r USING(tenant_id,project_id,task_id,submission_id)
                WHERE s.agent_run_id=%s""",
                (case.assignment.identity.agent_run_id,),
            ).fetchone()
            claim = connection.execute(
                """SELECT producer_kind,producer_ref,basis_json FROM vnext.claim_revision
                WHERE agent_run_id=%s""",
                (case.assignment.identity.agent_run_id,),
            ).fetchone()
            observation_count = connection.execute(
                """SELECT count(*) FROM vnext.observation o JOIN vnext.tool_attempt a
                ON (a.tenant_id,a.project_id,a.task_id,a.tool_attempt_id)=
                   (o.tenant_id,o.project_id,o.task_id,o.tool_attempt_id)
                WHERE a.agent_run_id=%s""",
                (case.assignment.identity.agent_run_id,),
            ).fetchone()[0]
            task_state = connection.execute(
                "SELECT observed_state FROM vnext.task WHERE task_id=%s", (TASK,)
            ).fetchone()[0]
        assert result_row is not None
        result = ResultReceipt.model_validate(strict_json_loads(result_row[0]))
        assert result.status.value == "accepted"
        assert claim[0:2] == ("agent", case.assignment.identity.agent_run_id)
        assert len(strict_json_loads(claim[2])) == 1
        assert observation_count == 1
        assert task_state == "running"

        assert len(case.upstream.exchanges) == 2
        assert len(case.mapped_model.requested_urls) == 2
        first_request = strict_json_loads(case.upstream.exchanges[0].request_body)
        rendered_context = strict_json_loads(first_request["messages"][1]["content"])
        assert rendered_context["snapshot_id"] == case.assignment.snapshot_id
        assert rendered_context["read_set"]
        assert rendered_context["records"]
        assert first_request["parallel_tool_calls"] is False
        assert first_request["stream_options"] == {"include_usage": True}
        assert first_request["max_completion_tokens"] == 2_048
        assert "max_tokens" not in first_request

        replay = case.node.start()
        assert replay.status_code == 200
        assert (
            replay.json()["observation"]["process"] == exited["observation"]["process"]
        )
        assert len(list((case.node.directory / "inbox/launches").iterdir())) == 1
        launch = worker_directory.parent
        public_bytes = b"".join(
            path.read_bytes()
            for path in (
                launch / "launch.json",
                launch / "stdout.log",
                launch / "stderr.log",
            )
        )
        assert case.worker.token.encode("utf-8") not in public_bytes
        assert case.receiver_credential.token.encode("utf-8") not in public_bytes
        assert case.worker.token in (worker_directory / "bridge.json").read_text()

        before_network = (
            len(case.upstream.exchanges),
            len(case.gate_server.exchanges),
        )
        with db_environment.migration_connection() as connection:
            revoke_run_credential(
                connection,
                tenant_id=case.worker.principal.tenant_id,
                subject=case.worker.principal.subject,
                token_id=case.worker.principal.token_id,
            )
        original_result_request = (
            worker_directory / "result-request.json"
        ).read_bytes()
        with httpx.Client(
            timeout=10, trust_env=False, follow_redirects=False
        ) as client:
            receiver_replay = client.post(
                case.controller_server.url + "/internal/v2/worker-host/receiver-replay",
                content=original_result_request,
                headers={
                    "Authorization": "Bearer " + case.receiver_credential.token,
                    "Content-Type": "application/json",
                },
            )
            old_worker = client.post(
                case.controller_server.url + "/internal/v2/worker-host/await-start",
                content=canonical_json_bytes(
                    {"assignment": case.assignment.model_dump(mode="json")}
                ),
                headers={
                    "Authorization": "Bearer " + case.worker.token,
                    "Content-Type": "application/json",
                },
            )
        assert receiver_replay.status_code == 200, receiver_replay.text
        assert receiver_replay.json() == result.model_dump(mode="json")
        assert old_worker.status_code == 200
        assert old_worker.json()["status"] == "revoked"
        assert old_worker.json()["birth_id"] is None
        assert old_worker.json()["observation_id"] is None
        assert (
            len(case.upstream.exchanges),
            len(case.gate_server.exchanges),
        ) == before_network

        audit_directory.joinpath("m2-result-summary.json").write_bytes(
            canonical_json_bytes(
                {
                    "assignment_digest": sha256(
                        canonical_json_bytes(case.assignment.model_dump(mode="json"))
                    ).hexdigest(),
                    "child_process": exited["observation"]["process"],
                    "model_requests": len(case.upstream.exchanges),
                    "result": result.model_dump(mode="json"),
                    "receiver_replay_status": receiver_replay.status_code,
                    "old_worker_status": old_worker.status_code,
                    "task_state": task_state,
                }
            )
        )
