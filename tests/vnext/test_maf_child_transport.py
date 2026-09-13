"""M2 tests for the actual MAF controller/child transport."""

import base64
import runpy
import sqlite3
import time
from hashlib import sha256
from pathlib import Path
from threading import Event, Thread

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
from wuji_core.contracts.envelopes import ResultReceipt, WorkerAssignment
from wuji_core.execution.dispatch_outbox import DispatchOutbox
from wuji_core.execution.reconcile import RegisteredRun, validate_receipt
from wuji_core.execution.runtime_dispatcher import RuntimeDispatcher
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.http.auth import Principal
from wuji_core.persistence.uow import AccessContext, DomainError


def test_worker_host_bridge_exposes_the_start_permission_boundary():
    bridge_type = worker_host_bridge_type()

    assert callable(getattr(bridge_type, "await_start", None))


def test_runtime_dispatcher_exposes_the_product_outbox_entrypoint():
    from wuji_core.execution.runtime_dispatcher import RuntimeDispatcher

    assert callable(getattr(RuntimeDispatcher, "deliver_pending", None))


def test_process_receipt_rejects_a_non_harness_assignment_profile():
    body = assignment_body()
    body["profile_refs"] = [
        body["profile_refs"][0],
        "fixture-model-v1",
        "fixture-runtime-v1",
    ]
    assignment = WorkerAssignment.model_validate(body)
    receiver = receiver_body()
    run = RegisteredRun(
        identity=assignment.identity,
        start_operation_id=assignment.operation_id,
        environment_ref=receiver["environment_ref"],
        pod_uid=receiver["pod_uid"],
        assignment_digest=sha256(
            canonical_json_bytes(assignment.model_dump(mode="json"))
        ).hexdigest(),
        work_kind=assignment.work_kind.value,
        harness_profile_id=assignment.profile_refs[0].root,
        harness_profile_digest="a" * 64,
    )
    receipt = {
        "operation_id": assignment.operation_id,
        "identity": assignment.identity.model_dump(mode="json"),
        "receiver": receiver,
        "assignment_digest": run.assignment_digest,
        # This is the assigned model profile, not the fixed harness profile.
        "profile_id": assignment.profile_refs[1].root,
        "state": "prepared",
        "observation": None,
    }

    with pytest.raises(DomainError, match="STALE_EXECUTION"):
        validate_receipt(run, receipt)


def test_runtime_service_owns_its_real_dispatch_journal_thread(tmp_path):
    body = assignment_body()
    body["profile_refs"] = [
        body["profile_refs"][0],
        "fixture-model-v1",
        "fixture-runtime-v1",
    ]
    assignment = WorkerAssignment.model_validate(body)
    receiver = receiver_body()
    registered = RegisteredRun(
        identity=assignment.identity,
        start_operation_id=assignment.operation_id,
        environment_ref=receiver["environment_ref"],
        pod_uid=receiver["pod_uid"],
        assignment_digest=sha256(
            canonical_json_bytes(assignment.model_dump(mode="json"))
        ).hexdigest(),
        work_kind=assignment.work_kind.value,
        harness_profile_id=assignment.profile_refs[0].root,
        harness_profile_digest="a" * 64,
    )
    access = AccessContext(
        Principal(
            subject="observer-fixture",
            tenant_id="tenant-fixture",
            roles=frozenset({"controller"}),
            token_id="runtime-service-token",
        ),
        "runtime-service-thread",
    )
    journal_path = tmp_path / "runtime-dispatch.sqlite3"
    outbox = DispatchOutbox(
        None,
        access=access,
        transport=object(),
        journal_path=journal_path,
    )
    stop = Event()

    class JournalRuntime(RuntimeDispatcher):
        def run_once(self, *, limit=16):
            del limit
            stop.set()
            self.outbox.journal.reserve_send(registered)
            return ()

    dispatcher = JournalRuntime(
        None,
        access=access,
        authorized_task_ids=(),
        work_kinds=("explore",),
        outbox=outbox,
        reconciler=object(),
    )
    service = runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "services/wuji-runtime/main.py")
    )
    errors = []

    def invoke():
        try:
            service["run"](
                dispatcher,
                stop=stop,
                interval_seconds=0.001,
                batch_limit=1,
            )
        except Exception as error:
            errors.append(error)

    worker = Thread(target=invoke, name="runtime-service-test")
    worker.start()
    worker.join(timeout=2)

    assert not worker.is_alive()
    assert errors == []
    with sqlite3.connect(journal_path) as connection:
        assert connection.execute(
            "SELECT attempted FROM delivery"
        ).fetchall() == [(1,)]


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


class _WrongProfileReceiptTransport:
    """Mutate only the profile field of an actual Supervisor receipt."""

    def __init__(self, delegate, profile_id):
        self.delegate = delegate
        self.profile_id = profile_id

    def query(self, operation_id):
        return self.delegate.query(operation_id)

    def start(self, assignment, *, profile_id):
        receipt = self.delegate.start(assignment, profile_id=profile_id)
        changed = strict_json_loads(canonical_json_bytes(receipt))
        changed["profile_id"] = self.profile_id
        return changed

    def control(self, *args, **kwargs):
        return self.delegate.control(*args, **kwargs)


def _registered_process_state(db_environment, assignment):
    with db_environment.migration_connection() as connection:
        run = connection.execute(
            """SELECT process_state,last_observation_id FROM vnext.agent_run
            WHERE agent_run_id=%s""",
            (assignment.identity.agent_run_id,),
        ).fetchone()
        reservations = connection.execute(
            """SELECT state FROM vnext.capacity_reservation
            WHERE agent_run_id=%s ORDER BY pool_key""",
            (assignment.identity.agent_run_id,),
        ).fetchall()
    return run, reservations


def test_actual_receipt_with_a_wrong_harness_profile_cannot_advance_p05(
    db_environment, tmp_path, audit_directory
):
    with m2_case(db_environment, tmp_path, audit_directory) as case:
        case.runtime.outbox.transport = _WrongProfileReceiptTransport(
            case.transport, case.assignment.profile_refs[1].root
        )
        with pytest.raises(DomainError, match="STALE_EXECUTION"):
            case.dispatcher.deliver_pending(limit=1)

        run, reservations = _registered_process_state(
            db_environment, case.assignment
        )
        assert run == ("registered", None)
        assert reservations and {state for (state,) in reservations} == {"reserved"}
        assert case.upstream.exchanges == []


def test_mismatched_registered_pod_is_rejected_before_node_launch(
    db_environment, tmp_path, audit_directory
):
    with m2_case(db_environment, tmp_path, audit_directory) as case:
        with db_environment.migration_connection() as connection:
            connection.execute(
                """UPDATE vnext.scheduler_receiver SET pod_uid='wrong-pod-uid'
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                AND runtime_attempt=%s""",
                (
                    case.assignment.identity.tenant_id,
                    case.assignment.identity.project_id,
                    case.assignment.identity.task_id,
                    case.assignment.identity.runtime_attempt.root,
                ),
            )
        delivered = case.dispatcher.deliver_pending(limit=1)

        assert len(delivered) == 1
        assert delivered[0].state == "unknown"
        repeated = case.dispatcher.deliver_pending(limit=1)
        assert len(repeated) == 1
        assert repeated[0].state == "unknown"
        node_requests = [
            strict_json_loads(line)
            for line in case.node.audit_path.read_text().splitlines()
        ]
        assert [
            request["request"]["method"] for request in node_requests[:2]
        ] == ["GET", "PUT"]
        assert sum(
            request["request"]["method"] == "PUT" for request in node_requests
        ) == 1
        launches = case.node.directory / "inbox/launches"
        assert not launches.exists() or list(launches.iterdir()) == []
        run, reservations = _registered_process_state(
            db_environment, case.assignment
        )
        assert run == ("registered", None)
        assert reservations and {state for (state,) in reservations} == {"reserved"}
        assert case.upstream.exchanges == []


def test_worker_revoked_after_ready_is_rejected_at_result_writepoint(
    db_environment, tmp_path, audit_directory
):
    with m2_case(
        db_environment,
        tmp_path,
        audit_directory,
        reject_first_submit=False,
        revoke_worker_on_result_write=True,
    ) as case:
        started = case.dispatcher.deliver_pending(limit=1)[0]
        case.dispatcher.reconcile(started.run)
        # This case verifies the output writepoint, not model-start timing. Let
        # the localhost peer respond immediately, then wait on actual durable
        # Worker files and the real revoked write response.
        case.upstream.release_first_response.set()
        worker_directory = case.node.worker_directory()
        assert _wait_for(
            lambda: (
                (worker_directory / "result-request.json").is_file()
                and (worker_directory / "sdk-request.json").is_file()
                and case.worker_write_state["revocations"] == 1
                and any(
                    exchange.path
                    == "/internal/v2/worker-host/submit-result"
                    and exchange.status_code == 409
                    for exchange in case.controller_server.exchanges
                )
            ),
            timeout=15,
        )
        _wait_for(
            lambda: (
                response
                if (response := case.node.query()).status_code == 200
                and response.json()["state"] == "exited"
                else None
            ),
            timeout=15,
        )

        assert case.worker_write_state["revocations"] == 1
        with db_environment.migration_connection() as connection:
            result_row = connection.execute(
                """SELECT r.receipt_json FROM vnext.result_submission s
                JOIN vnext.result_receipt r
                USING(tenant_id,project_id,task_id,submission_id)
                WHERE s.agent_run_id=%s""",
                (case.assignment.identity.agent_run_id,),
            ).fetchone()
            claim_count = connection.execute(
                """SELECT count(*) FROM vnext.claim_revision
                WHERE agent_run_id=%s""",
                (case.assignment.identity.agent_run_id,),
            ).fetchone()[0]
        assert result_row is not None
        result = ResultReceipt.model_validate(strict_json_loads(result_row[0]))
        assert result.status.value == "historical_only"
        assert claim_count == 0


@pytest.mark.parametrize(
    "revoke_before_first_intake",
    [False, True],
    ids=["current-receiver-intake", "revoked-first-intake"],
)
def test_actual_supervisor_child_waits_for_start_and_receiver_replays_bytes(
    db_environment,
    tmp_path,
    audit_directory,
    revoke_before_first_intake,
):
    """Catch an early SDK call, hosted substitute, or fake late-result ack."""

    with m2_case(db_environment, tmp_path, audit_directory) as case:
        deliveries = case.dispatcher.deliver_pending(limit=1)
        assert len(deliveries) == 1
        started = deliveries[0]
        assert started.state == "running"
        assert started.observation.kind == "started"
        process = started.observation.process
        assert process.pid > 0
        assert process.birth_id != str(process.pid)

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

        registered = started.run
        running = case.dispatcher.reconcile(registered)
        assert running.state == "running"
        assert running.observation.process.birth_id == process.birth_id
        assert case.upstream.first_request_started.wait(timeout=5)
        case.upstream.release_first_response.set()

        # The two restricted files prove the child produced the exact retained
        # requests. Do not query Node yet: query invokes persistResults.
        assert _wait_for(
            lambda: (
                (worker_directory / "result-request.json").is_file()
                and (worker_directory / "sdk-request.json").is_file()
                and case.controller_fault.rejections == 1
            ),
            timeout=15,
        )
        before_network = (
            len(case.upstream.exchanges),
            len(case.gate_server.exchanges),
        )
        if revoke_before_first_intake:
            with db_environment.migration_connection() as connection:
                revoke_run_credential(
                    connection,
                    tenant_id=case.worker.principal.tenant_id,
                    subject=case.worker.principal.subject,
                    token_id=case.worker.principal.token_id,
                )
        # This is the first Node observation allowed to invoke persistResults.
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
        assert exited["observation"]["process"]["pid"] == process.pid
        assert exited["observation"]["process"]["birth_id"] == process.birth_id
        assert exited["observation"]["process"]["exit_code"] == 1
        assert case.controller_fault.rejections == 1
        assert not (worker_directory / "result-receipt.json").exists()

        final = case.dispatcher.reconcile(registered)
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
        if revoke_before_first_intake:
            assert result.status.value == "historical_only"
            assert claim is None
        else:
            assert result.status.value == "accepted"
            assert claim[0:2] == (
                "agent",
                case.assignment.identity.agent_run_id,
            )
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

        replay = case.runtime.outbox.deliver(TASK, case.assignment.operation_id)
        assert replay.state == "exited"
        expected_process = type(replay.observation.process).model_validate(
            exited["observation"]["process"]
        )
        assert replay.observation.process == expected_process
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

        original_result_request = (
            worker_directory / "result-request.json"
        ).read_bytes()
        if not revoke_before_first_intake:
            with db_environment.migration_connection() as connection:
                revoke_run_credential(
                    connection,
                    tenant_id=case.worker.principal.tenant_id,
                    subject=case.worker.principal.subject,
                    token_id=case.worker.principal.token_id,
                )
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
                    "revoke_before_first_intake": revoke_before_first_intake,
                    "task_state": task_state,
                }
            )
        )
