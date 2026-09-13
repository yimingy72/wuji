"""P08 contract helpers that import the real production session boundary."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from importlib import import_module
from inspect import Parameter, signature
import json
from pathlib import Path
from types import SimpleNamespace
import time

import httpx
from agent_framework import AgentResponse, Content, Message
from openai.types.chat.chat_completion_chunk import (
    ChoiceDeltaToolCall,
    ChoiceDeltaToolCallFunction,
)

from wuji_core.contracts.admission import ToolCallReceipt
from wuji_core.contracts.sessions import NATIVE_REJECTION_TEXT_CORE_1_18_0, SessionLimits
from wuji_core.http import canonical_json_bytes, create_app, strict_json_loads
from wuji_core.persistence.snapshots import SnapshotRepository
from wuji_maf_worker.context import ContextLimits, build_context_bundle
from wuji_maf_worker.tools import ModelCallIdentity

from support.m1 import LocalAsgiServer, NativeSseModel
from support.http_capture import RecordedTestClient
from support.p03 import access
from support.p06 import (
    ENVIRONMENT,
    OWNER,
    RECEIVER,
    TASK,
    SyntheticTaskKeyResolver,
)


REQUIRED = Parameter.empty
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MODEL_ATTEMPT_ID = "model-attempt-p08"
PROVIDER_CALL_ID = "provider-call-p08"
SDK_CONTENT_ID = "af-call-p08"
SESSION_LINEAGE = "run:first-p08-run"
TOOL_CALL_ID = "tool-call-p08"
TOOL_DEFINITION = {
    "ref": "fixture-reader-p08-v1",
    "revision": "1",
    "name": "read_fixture",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
        "additionalProperties": False,
    },
    "executor_ref": "fixture-reader-p08",
    "approval_required": True,
    "allowed_target_kinds": ["workspace_read"],
}
NATIVE_ARGUMENTS = '{"path":"version.txt"}'
ACTUAL_TOOL_REF = "fixture-reader-v1"


def session_repository_type():
    """Return the production repository type without a test substitute."""

    try:
        module = import_module("wuji_core.execution.sessions")
    except ModuleNotFoundError as error:
        if error.name != "wuji_core.execution.sessions":
            raise
        raise AssertionError(
            "P08 SessionRepository production module is absent"
        ) from error
    repository_type = getattr(module, "SessionRepository", None)
    if repository_type is None:
        raise AssertionError("P08 SessionRepository production type is absent")
    return repository_type


def parameter_shape(callable_object):
    """Return names, kinds, and defaults from one frozen public call shape."""

    return tuple(
        (parameter.name, parameter.kind, parameter.default)
        for parameter in signature(callable_object).parameters.values()
    )


def session_limits():
    return SessionLimits(
        max_objects=32,
        max_reference_depth=8,
        max_object_bytes=65_536,
        max_total_bytes=262_144,
        max_messages=128,
        max_pending_approvals=4,
    )


def pending_native_identity():
    """Drive production identity hooks with public OpenAI/MAF content types."""

    identity = ModelCallIdentity([TOOL_DEFINITION], max_bytes=65_536)
    response = httpx.Response(
        200,
        headers={
            "X-Wuji-Model-Attempt-ID": MODEL_ATTEMPT_ID,
            "Content-Type": "text/event-stream",
        },
    )
    asyncio.run(identity.response(response))
    delta = ChoiceDeltaToolCall(
        index=0,
        id=PROVIDER_CALL_ID,
        type="function",
        function=ChoiceDeltaToolCallFunction(
            name=TOOL_DEFINITION["name"],
            arguments=NATIVE_ARGUMENTS,
        ),
    )
    identity.parse_response(SimpleNamespace(tool_calls=[delta]), [])
    function_call = Content.from_function_call(
        PROVIDER_CALL_ID,
        TOOL_DEFINITION["name"],
        arguments=NATIVE_ARGUMENTS,
        id=SDK_CONTENT_ID,
    )
    approval = Content.from_function_approval_request(
        SDK_CONTENT_ID,
        function_call,
    )
    native_response = AgentResponse(
        messages=[Message(role="assistant", contents=[function_call, approval])],
        finish_reason="tool_calls",
    )
    pending = identity.capture_pending(native_response, SESSION_LINEAGE)
    assert len(pending) == 1
    content, request = pending[0]
    receipt = ToolCallReceipt.model_validate(
        {
            "tool_call_id": TOOL_CALL_ID,
            "operation_id": "operation-p08",
            "tool_attempt_id": None,
            "status": "pending_approval",
            "evidence_receipt": None,
            "result_ref": None,
            "reason_code": None,
        }
    )
    identity.record_receipt(request, receipt)
    return identity, content, native_response


@contextmanager
def p08_candidate_case(
    environment,
    tmp_path,
    audit_directory,
    *,
    reject=False,
    initial_child=False,
):
    """One production Scheduler assignment through PG, Gates and released MAF."""

    factory = import_module("wuji_maf_worker.factory")
    runtime_module = import_module("wuji_maf_worker.runtime")
    host_module = import_module("wuji_core.worker_host")
    registry_module = import_module("wuji_core.admission.registry")
    ledger_module = import_module("wuji_core.admission.ledger")
    model_module = import_module("wuji_core.admission.models")
    tool_module = import_module("wuji_core.admission.tools")
    model_http = import_module("wuji_core.http.model_gate")
    tool_http = import_module("wuji_core.http.tool_gate")
    sessions_module = import_module("wuji_core.execution.sessions")
    inputs_module = import_module("wuji_core.execution.inputs")
    approvals_module = import_module("wuji_core.execution.approvals")
    approvals_http = import_module("wuji_core.http.approvals")
    from support.p09 import (
        AUDIENCE,
        ISSUER,
        POD_UID,
        RECEIVER_ACCESS,
        explore_assignment,
        scheduler_case,
        worker_credential,
    )
    from wuji_core.http.auth import TokenVerifier

    lock_digest = sha256(
        (REPOSITORY_ROOT / "packages/maf-worker/uv.lock").read_bytes()
    ).hexdigest()
    fixed_limits = SessionLimits(
        max_objects=64,
        max_reference_depth=8,
        max_object_bytes=32_768,
        max_total_bytes=65_536,
        max_messages=128,
        max_pending_approvals=4,
    )
    profiles = {}
    for work_kind in ("explore", "reason", "report"):
        instructions = (
            "Request approval to read the fixed workspace version file once."
            if work_kind == "explore"
            else f"Use the fixed synthetic P08 {work_kind} inputs."
        )
        profiles[work_kind] = factory.SessionHarnessProfile(
            ref=f"harness.{work_kind}.p08-candidate.v1",
            revision="1",
            work_kind=work_kind,
            instructions=instructions,
            tool_definition_refs=(ACTUAL_TOOL_REF,),
            lock_digest=lock_digest,
            max_context_records=128,
            max_context_bytes=65_536,
            max_output_tokens=2_048,
            history_source_id=f"history_p08_{work_kind}",
            memory_mode="disabled",
            memory_source_id=f"memory_p08_{work_kind}",
            session_limits=fixed_limits,
            max_context_window_tokens=8_192,
            compaction_enabled=False,
        ).snapshot()
    upstream = NativeSseModel(
        audit_directory / "model-upstream-http.jsonl",
        expected_rejection=(
            {
                "role": "tool",
                "tool_call_id": "call-m1-read",
                "content": NATIVE_REJECTION_TEXT_CORE_1_18_0,
            }
            if reject
            else None
        ),
    )
    gate_server = None
    approval_client = None
    try:
        with scheduler_case(
            environment,
            tmp_path,
            audit_directory,
            profiles=profiles,
            gateway_url=upstream.url,
            approval_required=True,
            max_single_output_bytes=fixed_limits.max_object_bytes,
            evaluation_mode="mechanism_synthetic",
        ) as scheduler:
            control = scheduler.control
            task_config = control.scheduler_config
            profile_snapshot = profiles["explore"]
            profile = factory.SessionHarnessProfile.from_snapshot(profile_snapshot)
            now = datetime.now(timezone.utc)
            client_snapshot = registry_module.session_client_snapshot(task_config)
            runtime_snapshot = task_config.runtime.model_dump(mode="json")
            framework_snapshot = {
                "python": "3.13.15",
                "agent_framework_core": "1.18.0",
                "agent_framework_openai": "1.14.3",
            }
            with environment.migration_connection() as connection:
                registry_module.register_session_capability(
                    connection,
                    tenant_id=OWNER[0],
                    capability={
                        "ref": "session-capability-p08-candidate",
                        "revision": "1",
                        "published_at": now,
                        "validation_status": "mechanism_candidate",
                        "candidate_binding": {
                            "tenant_id": OWNER[0],
                            "project_id": OWNER[1],
                            "task_id": TASK,
                            "receiver_id": RECEIVER,
                            "runtime_attempt": "1",
                            "pod_uid": POD_UID,
                            "model_gateway_digest": registry_module.model_gateway_digest(
                                upstream.url
                            ),
                            "expires_at": now + timedelta(minutes=30),
                        },
                        "profile_snapshot": profile_snapshot,
                        "profile_digest": profile_snapshot["digest"],
                        "client_snapshot": client_snapshot,
                        "client_digest": registry_module.configuration_digest(
                            client_snapshot
                        ),
                        "runtime_snapshot": runtime_snapshot,
                        "runtime_digest": registry_module.configuration_digest(
                            runtime_snapshot
                        ),
                        "framework_snapshot": framework_snapshot,
                        "framework_digest": registry_module.configuration_digest(
                            framework_snapshot
                        ),
                        "lock_digest": lock_digest,
                        "limits": fixed_limits.model_dump(mode="json"),
                        "recovery_classes": [
                            "settled_boundary",
                            "approval_boundary",
                        ],
                        "memory_mode": "disabled",
                        "approver_subjects": ["operator-fixture"],
                        "approval_ttl_seconds": 300,
                        "evidence_refs": [
                            "docs/vnext/evidence/P01/pytest-probe.json"
                        ],
                    },
                )
                for candidate_kind in ("reason", "report"):
                    candidate_profile = profiles[candidate_kind]
                    registry_module.register_session_capability(
                        connection,
                        tenant_id=OWNER[0],
                        capability={
                            "ref": "session-capability-p08-candidate-"
                            + candidate_kind,
                            "revision": "1",
                            "published_at": now,
                            "validation_status": "mechanism_candidate",
                            "candidate_binding": {
                                "tenant_id": OWNER[0],
                                "project_id": OWNER[1],
                                "task_id": TASK,
                                "receiver_id": RECEIVER,
                                "runtime_attempt": "1",
                                "pod_uid": POD_UID,
                                "model_gateway_digest": registry_module.model_gateway_digest(
                                    upstream.url
                                ),
                                "expires_at": now + timedelta(minutes=30),
                            },
                            "profile_snapshot": candidate_profile,
                            "profile_digest": candidate_profile["digest"],
                            "client_snapshot": client_snapshot,
                            "client_digest": registry_module.configuration_digest(
                                client_snapshot
                            ),
                            "runtime_snapshot": runtime_snapshot,
                            "runtime_digest": registry_module.configuration_digest(
                                runtime_snapshot
                            ),
                            "framework_snapshot": framework_snapshot,
                            "framework_digest": registry_module.configuration_digest(
                                framework_snapshot
                            ),
                            "lock_digest": lock_digest,
                            "limits": fixed_limits.model_dump(mode="json"),
                            "recovery_classes": [
                                "settled_boundary",
                                "approval_boundary",
                            ],
                            "memory_mode": "disabled",
                            "approver_subjects": ["operator-fixture"],
                            "approval_ttl_seconds": 300,
                            "evidence_refs": [
                                "docs/vnext/evidence/P01/pytest-probe.json"
                            ],
                        },
                    )
            assignment = explore_assignment(scheduler.scheduler.tick(limit=2))
            process_identities = {}

            def record_process(target, kind, *, access=RECEIVER_ACCESS):
                observed_at = datetime.now(timezone.utc)
                observed_text = observed_at.isoformat().replace("+00:00", "Z")
                exited = kind == "exited"
                run_id = target.identity.agent_run_id
                if kind == "started":
                    process_identities[run_id] = {
                        "pid": 12345,
                        "birth_id": "p08-candidate-process-" + run_id,
                        "started_at": (
                            observed_at - timedelta(seconds=1)
                        ).isoformat().replace("+00:00", "Z"),
                    }
                fixed_process = process_identities[run_id]
                observation_body = {
                    "receipt_id": f"p08-{kind}-" + run_id,
                    "identity": target.identity.model_dump(mode="json"),
                    "operation_id": target.operation_id,
                    "environment_ref": ENVIRONMENT,
                    "pod_uid": POD_UID,
                    "kind": kind,
                    "observed_at": observed_text,
                    "process": {
                        **fixed_process,
                        "exited_at": observed_text if exited else None,
                        "exit_code": 0 if exited else None,
                    },
                    "reason": "production P08 candidate process receipt",
                }
                source_receipt = canonical_json_bytes(observation_body).decode()
                return control.control.record_observation(
                    access,
                    control.control_module.ExecutionObservation.model_validate(
                        {
                            **observation_body,
                            "source_receipt": source_receipt,
                            "source_digest": sha256(
                                source_receipt.encode()
                            ).hexdigest(),
                        }
                    ),
                )

            workspace = tmp_path / "workspace"
            workspace.mkdir()
            (workspace / "version.txt").write_bytes(b"fixture-version=17\n")
            receipt_root = tmp_path / "receiver-inbox"
            registry = scheduler.registry
            ledger = ledger_module.AdmissionLedger(control.uow)
            sessions = sessions_module.SessionRepository(
                control.uow,
                artifacts=control.store,
                registry=registry,
            )
            control.control.sessions = sessions
            inputs = inputs_module.InputService(
                control.uow,
                sessions=sessions,
                registry=registry,
            )
            approvals = approvals_module.ApprovalService(
                control.uow,
                sessions=sessions,
                registry=registry,
            )
            approval_token = control.provider.issue(
                subject="operator-fixture",
                tenant_id=OWNER[0],
                roles=["operator"],
            )
            approval_client = RecordedTestClient(
                create_app(
                    token_verifier=control.verifier,
                    routers=[approvals_http.create_approval_router(approvals)],
                ),
                audit_path=audit_directory / "approval-http.jsonl",
            )
            tool_admission = tool_module.ToolAdmission(
                control.uow,
                registry=registry,
                ledger=ledger,
                approvals=approvals,
            )
            executor = tool_module.WorkspaceReadExecutor(
                root=workspace,
                receipt_root=receipt_root,
                admission=tool_admission,
                receiver_id=RECEIVER,
                environment_ref=ENVIRONMENT,
            )
            evidence = import_module(
                "wuji_core.evidence.observations"
            ).EvidenceService(control.uow, control.store)
            tool_gate = tool_module.ToolGate(
                tool_admission,
                registry=registry,
                ledger=ledger,
                artifacts=control.store,
                evidence=evidence,
                executors={"workspace-reader-fixture": executor},
                collector_accesses={
                    "workspace-reader-fixture": access(
                        "collector-fixture", role="collector"
                    )
                },
            )
            model_gate = model_module.ModelGate(
                model_module.ModelAdmission(
                    control.uow,
                    registry=registry,
                    ledger=ledger,
                ),
                registry=registry,
                ledger=ledger,
                key_resolver=SyntheticTaskKeyResolver(),
                transport=model_module.HttpxModelTransport(upstream.client),
                tool_capabilities=tool_module.ToolCapabilityResolver(tool_gate),
            )
            verifier = TokenVerifier(
                public_key_pem=scheduler.keys.public_pem,
                issuer=ISSUER,
                audience=AUDIENCE,
            )
            app = create_app(
                token_verifier=verifier,
                routers=[
                    model_http.create_model_router(model_gate),
                    tool_http.create_tool_router(tool_gate),
                ],
            )
            gate_server = LocalAsgiServer(
                app,
                audit_directory / "platform-gate-http.jsonl",
            )

            def child_execute(target, *, expect_input=False):
                from support.m2 import (
                    NodeBridgeSupervisor,
                    _context_builder,
                    _receiver_credential,
                )
                from wuji_core.execution.dispatch_outbox import SupervisorHttpTransport
                from wuji_core.execution.runtime_dispatcher import (
                    build_runtime_controller,
                )
                from wuji_core.http import JsonBoundaryLimits

                worker = worker_credential(scheduler, target)
                receiver_credential = _receiver_credential(
                    scheduler,
                    audit_directory,
                )
                controller_server = LocalAsgiServer(
                    None,
                    audit_directory
                    / ("p08-controller-" + target.identity.agent_run_id + ".jsonl"),
                )
                receiver = {
                    "receiver_id": RECEIVER,
                    "runtime_attempt": target.identity.runtime_attempt.root,
                    "environment_ref": ENVIRONMENT,
                    "pod_uid": POD_UID,
                }
                node = NodeBridgeSupervisor(
                    directory=tmp_path / ("p08-node-" + target.identity.agent_run_id),
                    assignment=target,
                    receiver=receiver,
                    receiver_token=receiver_credential.token,
                    controller_origin=controller_server.url,
                    audit_path=audit_directory
                    / ("p08-node-" + target.identity.agent_run_id + ".jsonl"),
                )

                def audit_supervisor_http(record):
                    with node.audit_path.open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps(record, sort_keys=True) + "\n")

                transport = SupervisorHttpTransport(
                    node.url,
                    authorization=lambda: receiver_credential.token,
                    timeout=10,
                    max_response_bytes=1_048_576,
                    audit=audit_supervisor_http,
                )

                def host_factory(worker_access):
                    return host_module.PlatformWorkerHost(
                        uow=control.uow,
                        registry=registry,
                        access=worker_access,
                        artifacts=control.store,
                        committer=control.committer,
                        profiles=tuple(profiles.values()),
                        lock_digest=lock_digest,
                        sessions=sessions,
                        inputs=inputs,
                        receiver_access=lambda _assignment: receiver_credential.access,
                    )

                def retained_host_factory(receiver_access, retained_result):
                    return host_module.PlatformWorkerHost(
                        uow=control.uow,
                        registry=registry,
                        access=receiver_access,
                        artifacts=control.store,
                        committer=control.committer,
                        profiles=tuple(profiles.values()),
                        lock_digest=lock_digest,
                        retained_result=retained_result,
                    )

                controller = build_runtime_controller(
                    control.uow,
                    access=receiver_credential.access,
                    authorized_task_ids=(TASK,),
                    work_kinds=("explore",),
                    credentials=scheduler.issuer,
                    registry=registry,
                    control=control.control,
                    supervisor_transport=transport,
                    host_factory=host_factory,
                    retained_host_factory=retained_host_factory,
                    session_transport=True,
                    context_builder=_context_builder,
                    ledger=control.view,
                    child_config={
                        "public_key_pem": scheduler.keys.public_pem.decode("utf-8"),
                        "issuer": ISSUER,
                        "audience": AUDIENCE,
                        "host_origin": controller_server.url,
                        "model_gate_url": gate_server.url + "/internal/v2/model",
                        "tool_gate_url": gate_server.url + "/internal/v2/tool-calls",
                        "wait_timeout_seconds": 20,
                        "transport_timeout_seconds": 10,
                        "max_transport_bytes": 1_048_576,
                    },
                    journal_path=tmp_path
                    / ("p08-runtime-" + target.identity.agent_run_id + ".sqlite3"),
                    spool_directory=tmp_path
                    / ("p08-intake-" + target.identity.agent_run_id),
                    approval_service=approvals,
                    json_limits=JsonBoundaryLimits(max_body_bytes=1_048_576),
                )
                controller_server.app = controller.app
                try:
                    deliveries = controller.dispatcher.deliver_pending(limit=1)
                    if len(deliveries) != 1:
                        raise AssertionError("one current P08 child assignment required")
                    started = deliveries[0]
                    controller.dispatcher.reconcile(started.run)
                    worker_directory = node.worker_directory()
                    launch_directory = worker_directory.parent
                    deadline = time.monotonic() + 20
                    while time.monotonic() < deadline:
                        session_published = list(
                            worker_directory.glob(
                                "p08-publish-session-response-*.json"
                            )
                        )
                        input_registered = list(
                            worker_directory.glob(
                                "p08-register-input-response-*.json"
                            )
                        )
                        if (worker_directory / "sdk-request.json").is_file() and (
                            bool(session_published)
                            and (
                                bool(input_registered)
                                if expect_input
                                else (worker_directory / "result-request.json").is_file()
                            )
                        ):
                            break
                        time.sleep(0.05)
                    worker_files = tuple(
                        sorted(
                            str(path.relative_to(worker_directory))
                            for path in worker_directory.rglob("*")
                            if path.is_file()
                        )
                    )
                    stderr_path = launch_directory / "stderr.log"
                    worker_stderr = (
                        stderr_path.read_text(encoding="utf-8")
                        if stderr_path.is_file()
                        else ""
                    )
                    session_receipt = None
                    input_receipt = None
                    published_responses = list(
                        worker_directory.glob(
                            "p08-publish-session-response-*.json"
                        )
                    )
                    if len(published_responses) == 1:
                        session_receipt = controller.session_codec.decode_receipt(
                            strict_json_loads(published_responses[0].read_bytes())
                        )
                    input_responses = list(
                        worker_directory.glob(
                            "p08-register-input-response-*.json"
                        )
                    )
                    if len(input_responses) == 1:
                        input_receipt = controller.session_codec.decode_input_receipt(
                            strict_json_loads(input_responses[0].read_bytes())
                        )
                    exited = None
                    query_deadline = time.monotonic() + 10
                    while time.monotonic() < query_deadline:
                        response = node.query()
                        if response.status_code == 200 and response.json()["state"] == "exited":
                            exited = response.json()
                            break
                        time.sleep(0.05)
                    if exited is None:
                        raise AssertionError("P08 child did not publish an exit receipt")
                    final = controller.dispatcher.reconcile(started.run)
                    return SimpleNamespace(
                        assignment=target,
                        credential=worker,
                        started=started,
                        exited=exited,
                        final=final,
                        worker_directory=worker_directory,
                        worker_files=worker_files,
                        worker_stderr=worker_stderr,
                        session_receipt=session_receipt,
                        input_receipt=input_receipt,
                    )
                finally:
                    controller.close()
                    node.close()
                    controller_server.close()

            def runtime_for(target):
                target_credential = worker_credential(scheduler, target)
                record_process(target, "started")
                target_snapshot = SnapshotRepository(control.uow).get(
                    TASK,
                    target_credential.access,
                    target.snapshot_id,
                )
                target_context = build_context_bundle(
                    [],
                    target_snapshot.refs,
                    snapshot_id=target_snapshot.snapshot_id,
                    limits=ContextLimits(max_records=128, max_bytes=65_536),
                )
                target_host = host_module.PlatformWorkerHost(
                    uow=control.uow,
                    registry=registry,
                    access=target_credential.access,
                    artifacts=control.store,
                    committer=control.committer,
                    profiles=(profile_snapshot,),
                    lock_digest=lock_digest,
                    sessions=sessions,
                    inputs=inputs,
                    receiver_access=lambda _assignment: RECEIVER_ACCESS,
                )
                target_runtime = runtime_module.MafRuntime(
                    host=target_host,
                    context=target_context,
                    run_credential=target_credential.token,
                    token_verifier=verifier,
                    model_gate_url=gate_server.url + "/internal/v2/model",
                    tool_gate_url=gate_server.url + "/internal/v2/tool-calls",
                )
                return SimpleNamespace(
                    assignment=target,
                    credential=target_credential,
                    snapshot=target_snapshot,
                    context=target_context,
                    host=target_host,
                    runtime=target_runtime,
                )

            initial = None if initial_child else runtime_for(assignment)
            credential = None if initial is None else initial.credential
            snapshot = None if initial is None else initial.snapshot
            context = None if initial is None else initial.context
            host = None if initial is None else initial.host
            runtime = None if initial is None else initial.runtime
            yield SimpleNamespace(**locals())
    finally:
        if approval_client is not None:
            approval_client.close()
        if gate_server is not None:
            gate_server.close()
        upstream.close()
