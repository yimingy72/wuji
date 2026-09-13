"""M2 real P09/P10/controller/child integration support."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import signal
import subprocess
import time
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import httpx
from joserfc import jwt
from joserfc.jwk import RSAKey

from support.m1 import LocalAsgiServer, NativeSseModel
from support.p03 import access
from support.p06 import ENVIRONMENT, RECEIVER, SyntheticTaskKeyResolver
from support.p09 import (
    AUDIENCE,
    ISSUER,
    OWNER,
    POD_UID,
    TASK,
    explore_assignment,
    scheduler_case,
    worker_credential,
)
from wuji_core.admission.ledger import AdmissionLedger
from wuji_core.admission.models import HttpxModelTransport, ModelAdmission, ModelGate
from wuji_core.admission.registry import revoke_run_credential
from wuji_core.admission.tools import (
    ToolAdmission,
    ToolCapabilityResolver,
    ToolGate,
    WorkspaceReadExecutor,
)
from wuji_core.evidence.observations import EvidenceService
from wuji_core.execution.dispatch_outbox import SupervisorHttpTransport
from wuji_core.execution.runtime_dispatcher import build_runtime_controller
from wuji_core.http import JsonBoundaryLimits, canonical_json_bytes, create_app
from wuji_core.http.auth import TokenVerifier
from wuji_core.http.model_gate import create_model_router
from wuji_core.http.tool_gate import create_tool_router
from wuji_core.persistence.uow import AccessContext
from wuji_core.worker_host import PlatformWorkerHost
from wuji_maf_worker.context import ContextLimits, ContextRelation, build_context_bundle
from wuji_core.contracts.knowledge import KnowledgeRef

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
NODE_HOST = Path(__file__).with_name("m2_supervisor_host.mjs")


def worker_host_bridge_type():
    """Return the production bridge type without a test bridge substitute."""

    try:
        module = import_module("wuji_core.execution.worker_bridge")
    except ModuleNotFoundError as error:
        raise AssertionError(
            "M2 WorkerHostBridge production module is absent"
        ) from error
    bridge_type = getattr(module, "WorkerHostBridge", None)
    if bridge_type is None:
        raise AssertionError("M2 WorkerHostBridge production interface is absent")
    return bridge_type


def bridge_wire_types():
    """Load only OpenAPI-generated bridge DTOs from the contract source."""

    generated = import_module("wuji_core.contracts.generated")
    names = (
        "ReceiverBridgeGrant",
        "ReceiverBridgeRequest",
        "WorkerArchiveRequest",
        "WorkerBootstrap",
        "WorkerBridgeRequest",
        "WorkerContext",
        "WorkerReceiver",
        "WorkerResolvedContext",
        "WorkerStartPermission",
        "WorkerSubmitRequest",
    )
    missing = [name for name in names if not hasattr(generated, name)]
    if missing:
        raise AssertionError(
            "M2 generated bridge DTOs are absent: " + ", ".join(missing)
        )
    return {name: getattr(generated, name) for name in names}


def assignment_body() -> dict[str, object]:
    return {
        "schema_version": "wuji.assignment.v2",
        "operation_id": "start-m2-child",
        "identity": {
            "tenant_id": "tenant-fixture",
            "project_id": "project-fixture",
            "task_id": "task-fixture",
            "work_item_id": "work-fixture",
            "agent_run_id": "run-fixture",
            "execution_epoch": "1",
            "run_epoch": "1",
            "runtime_attempt": "1",
            "receiver_id": "receiver-fixture",
        },
        "work_kind": "explore",
        "snapshot_id": "snapshot-m2-child",
        "profile_refs": ["harness.explore.m1.v1"],
        "session_manifest_ref": None,
        "tool_definition_refs": ["fixture-reader-v1"],
        "limits": {
            "max_work_items": 4,
            "max_reason_runs": 2,
            "max_model_requests": 4,
            "max_tool_calls": 2,
            "max_single_output_bytes": 4096,
            "max_total_output_bytes": 65536,
            "max_elapsed_seconds": 300,
            "max_attempts_per_work": 3,
            "repair_attempts": 1,
        },
        "resume_reason": None,
    }


def receiver_body() -> dict[str, str]:
    return {
        "receiver_id": "receiver-fixture",
        "runtime_attempt": "1",
        "environment_ref": "environment-fixture",
        "pod_uid": "pod-fixture",
    }


class MappedModelClient:
    """Map the published fixture hostname to an actual localhost SSE peer."""

    def __init__(self, target: str) -> None:
        self.target = target
        self.requested_urls: list[str] = []

    @asynccontextmanager
    async def stream(self, method: str, url: str, **kwargs):
        if url != "https://model.fixture.invalid/v1":
            raise AssertionError("P09 published model endpoint changed")
        self.requested_urls.append(url)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0), trust_env=False, follow_redirects=False
        ) as client:
            async with client.stream(method, self.target, **kwargs) as response:
                yield response


class RejectFirstWorkerSubmit:
    """Fail before controller intake once; retained child bytes must reconcile."""

    def __init__(self, app) -> None:
        self.app = app
        self.rejections = 0

    async def __call__(self, scope, receive, send) -> None:
        if (
            scope["type"] == "http"
            and scope["path"] == "/internal/v2/worker-host/submit-result"
            and self.rejections == 0
        ):
            self.rejections += 1
            body = canonical_json_bytes(
                {
                    "code": "CAPABILITY_UNAVAILABLE",
                    "message": "synthetic controller intake interruption",
                    "request_id": "m2-submit-interruption",
                    "retryable": False,
                    "details": {},
                }
            )
            await send(
                {
                    "type": "http.response.start",
                    "status": 503,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("ascii")),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)


def _receiver_credential(case, audit_directory: Path):
    now = int(datetime.now(UTC).timestamp())
    token = jwt.encode(
        {"alg": "RS256", "kid": "p09-test-key"},
        {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": "observer-fixture",
            "tenant_id": "tenant-fixture",
            "roles": ["controller"],
            "iat": now,
            "nbf": now,
            "exp": now + 300,
            "jti": "m2-receiver-token-id",
        },
        RSAKey.import_key(case.keys.private_pem),
        algorithms=["RS256"],
    )
    verifier = TokenVerifier(
        public_key_pem=case.keys.public_pem, issuer=ISSUER, audience=AUDIENCE
    )
    principal = verifier.verify(token)
    audit_directory.joinpath("m2-receiver-identity.json").write_bytes(
        canonical_json_bytes(
            {
                "subject": principal.subject,
                "tenant_id": principal.tenant_id,
                "roles": sorted(principal.roles),
                "token_id": principal.token_id,
            }
        )
    )
    return SimpleNamespace(
        token=token,
        verifier=verifier,
        principal=principal,
        access=AccessContext(principal, "m2-receiver"),
    )


def _context_builder(
    *, records, read_set, snapshot_id, max_records, max_bytes, relations
):
    return build_context_bundle(
        records,
        read_set,
        snapshot_id=snapshot_id,
        limits=ContextLimits(max_records=max_records, max_bytes=max_bytes),
        relations=tuple(
            ContextRelation(
                source=KnowledgeRef.model_validate(item["source"]),
                target=KnowledgeRef.model_validate(item["target"]),
                relation=item["relation"],
            )
            for item in relations
        ),
    )


class NodeBridgeSupervisor:
    def __init__(
        self,
        *,
        directory: Path,
        assignment,
        receiver: dict[str, str],
        receiver_token: str,
        controller_origin: str,
        audit_path: Path,
    ) -> None:
        self.directory = directory
        self.directory.mkdir(mode=0o700)
        self.assignment = assignment
        self.receiver = receiver
        self.token = receiver_token
        self.audit_path = audit_path
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path = self.directory / "config.json"
        self.ready_path = self.directory / "ready.json"
        python = REPOSITORY_ROOT / "packages/maf-worker/.venv/bin/python"
        python_path = os.pathsep.join(
            [
                str(REPOSITORY_ROOT / "packages/maf-worker/src"),
                str(REPOSITORY_ROOT / "packages/wuji-core/src"),
            ]
        )
        config = {
            "controllerOrigin": controller_origin,
            "receiverToken": receiver_token,
            "receiver": receiver,
            "timeoutMs": 10_000,
            "maxTransportBytes": 1_048_576,
            "inboxDir": str(self.directory / "inbox"),
            "profileId": assignment.profile_refs[0].root,
            "pythonExecutable": str(python),
            "cwd": str(REPOSITORY_ROOT),
            "env": {
                "PATH": str(python.parent),
                "PYTHONPATH": python_path,
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            "readyFile": str(self.ready_path),
        }
        self.config_path.write_bytes(canonical_json_bytes(config))
        self.config_path.chmod(0o600)
        self.process = subprocess.Popen(
            [str(REPOSITORY_ROOT / "work/toolchain/bin/node"), str(NODE_HOST)],
            cwd=REPOSITORY_ROOT,
            env={"WUJI_M2_SUPERVISOR_CONFIG": str(self.config_path)},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.ready_path.exists():
                self.ready = json.loads(self.ready_path.read_text())
                self.url = f"http://{self.ready['host']}:{self.ready['port']}"
                break
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                raise AssertionError(f"M2 Node host exited: {stdout} {stderr}")
            time.sleep(0.01)
        else:
            raise AssertionError("M2 Node host did not publish its address")
        self.client = httpx.Client(timeout=10, trust_env=False, follow_redirects=False)

    def _request(self, method: str, path: str, body=None):
        headers = {
            "Authorization": "Bearer " + self.token,
            "Accept": "application/json",
        }
        content = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            content = canonical_json_bytes(body)
        response = self.client.request(
            method, self.url + path, headers=headers, content=content
        )
        record = {
            "request": {
                "method": method,
                "url": self.url + path,
                "headers": {
                    **headers,
                    "Authorization": "Bearer [REDACTED RECEIVER CREDENTIAL]",
                },
                "body_base64": base64.b64encode(content or b"").decode("ascii"),
            },
            "response": {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body_base64": base64.b64encode(response.content).decode("ascii"),
            },
        }
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
        return response

    def start(self):
        return self._request(
            "PUT",
            "/operations/" + self.assignment.operation_id,
            {
                "assignment": self.assignment.model_dump(mode="json"),
                "profile_id": self.assignment.profile_refs[0].root,
            },
        )

    def query(self):
        return self._request("GET", "/operations/" + self.assignment.operation_id)

    def worker_directory(self) -> Path:
        launches = list((self.directory / "inbox/launches").glob("*/worker"))
        if len(launches) != 1:
            raise AssertionError("M2 expected exactly one Supervisor launch")
        return launches[0]

    def close(self) -> None:
        self.client.close()
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)


@contextmanager
def m2_case(
    environment,
    tmp_path: Path,
    audit_directory: Path,
    *,
    reject_first_submit: bool = True,
    revoke_worker_on_result_write: bool = False,
):
    upstream = NativeSseModel(audit_directory / "m2-model-upstream-http.jsonl")
    gate_server = None
    controller_server = None
    node = None
    runtime = None
    try:
        with scheduler_case(environment, tmp_path, audit_directory) as scheduled:
            # P09's deployment fixture explicitly grants this receiver; M2 only
            # verifies the prerequisite and never self-grants settlement power.
            with environment.migration_connection() as connection:
                receiver_acl = connection.execute(
                    """SELECT can_read,can_observe,can_settle,can_write,
                    can_model_output FROM vnext.task_access
                    WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                    AND subject='observer-fixture'""",
                    OWNER,
                ).fetchone()
            if receiver_acl != (True, True, True, False, False):
                raise AssertionError("P09 receiver settlement ACL was not provisioned")
            assignment = explore_assignment(scheduled.scheduler.tick(limit=2))
            worker = worker_credential(scheduled, assignment)
            worker_write_state = {"revocations": 0}
            receiver_credential = _receiver_credential(scheduled, audit_directory)
            receiver = {
                "receiver_id": RECEIVER,
                "runtime_attempt": assignment.identity.runtime_attempt.root,
                "environment_ref": ENVIRONMENT,
                "pod_uid": POD_UID,
            }
            workspace = tmp_path / "m2-workspace"
            workspace.mkdir()
            expected_output = b"fixture-version=17\n"
            (workspace / "version.txt").write_bytes(expected_output)
            registry = scheduled.registry
            ledger = AdmissionLedger(scheduled.control.uow)
            tool_admission = ToolAdmission(
                scheduled.control.uow, registry=registry, ledger=ledger
            )
            executor = WorkspaceReadExecutor(
                root=workspace,
                receipt_root=tmp_path / "m2-receiver-inbox",
                admission=tool_admission,
                receiver_id=RECEIVER,
                environment_ref=ENVIRONMENT,
            )
            evidence = EvidenceService(scheduled.control.uow, scheduled.control.store)
            tool_gate = ToolGate(
                tool_admission,
                registry=registry,
                ledger=ledger,
                artifacts=scheduled.control.store,
                evidence=evidence,
                executors={"workspace-reader-fixture": executor},
                collector_accesses={
                    "workspace-reader-fixture": access(
                        "collector-fixture", role="collector"
                    )
                },
            )
            mapped_model = MappedModelClient(upstream.url)
            model_gate = ModelGate(
                ModelAdmission(scheduled.control.uow, registry=registry, ledger=ledger),
                registry=registry,
                ledger=ledger,
                key_resolver=SyntheticTaskKeyResolver(),
                transport=HttpxModelTransport(mapped_model),
                tool_capabilities=ToolCapabilityResolver(tool_gate),
            )
            gate_server = LocalAsgiServer(
                create_app(
                    token_verifier=receiver_credential.verifier,
                    routers=[
                        create_model_router(model_gate),
                        create_tool_router(tool_gate),
                    ],
                ),
                audit_directory / "m2-platform-gates-http.jsonl",
            )
            controller_server = LocalAsgiServer(
                None, audit_directory / "m2-controller-http.jsonl"
            )

            def host_factory(worker_access):
                if (
                    revoke_worker_on_result_write
                    and runtime is not None
                    and runtime.bridge.intake.read(assignment, "result") is not None
                    and worker_write_state["revocations"] == 0
                ):
                    with environment.migration_connection() as connection:
                        revoke_run_credential(
                            connection,
                            tenant_id=worker.principal.tenant_id,
                            subject=worker.principal.subject,
                            token_id=worker.principal.token_id,
                        )
                    worker_write_state["revocations"] += 1
                return PlatformWorkerHost(
                    uow=scheduled.control.uow,
                    registry=registry,
                    access=worker_access,
                    artifacts=scheduled.control.store,
                    committer=scheduled.control.committer,
                    profiles=tuple(scheduled.profiles.values()),
                    lock_digest=scheduled.control.scheduler_config.runtime.lock_digest,
                )

            def retained_host_factory(receiver_access, retained_result):
                return PlatformWorkerHost(
                    uow=scheduled.control.uow,
                    registry=registry,
                    access=receiver_access,
                    artifacts=scheduled.control.store,
                    committer=scheduled.control.committer,
                    profiles=tuple(scheduled.profiles.values()),
                    lock_digest=scheduled.control.scheduler_config.runtime.lock_digest,
                    retained_result=retained_result,
                )

            node = NodeBridgeSupervisor(
                directory=tmp_path / "m2-node",
                assignment=assignment,
                receiver=receiver,
                receiver_token=receiver_credential.token,
                controller_origin=controller_server.url,
                audit_path=audit_directory / "m2-node-http.jsonl",
            )
            transport = SupervisorHttpTransport(
                node.url,
                authorization=lambda: receiver_credential.token,
                timeout=10,
                max_response_bytes=1_048_576,
            )
            runtime = build_runtime_controller(
                scheduled.control.uow,
                access=receiver_credential.access,
                authorized_task_ids=(TASK,),
                credentials=scheduled.issuer,
                registry=registry,
                control=scheduled.control.control,
                supervisor_transport=transport,
                host_factory=host_factory,
                retained_host_factory=retained_host_factory,
                context_builder=_context_builder,
                ledger=scheduled.control.view,
                child_config={
                    "public_key_pem": scheduled.keys.public_pem.decode("utf-8"),
                    "issuer": ISSUER,
                    "audience": AUDIENCE,
                    "host_origin": controller_server.url,
                    "model_gate_url": gate_server.url + "/internal/v2/model",
                    "tool_gate_url": gate_server.url + "/internal/v2/tool-calls",
                    "wait_timeout_seconds": 20,
                    "transport_timeout_seconds": 10,
                    "max_transport_bytes": 1_048_576,
                },
                journal_path=tmp_path / "m2-runtime/dispatch.sqlite3",
                spool_directory=tmp_path / "m2-controller-intake",
                json_limits=JsonBoundaryLimits(max_body_bytes=1_048_576),
            )
            bridge = runtime.bridge
            reconciler = runtime.reconciler
            dispatcher = runtime.dispatcher
            if reject_first_submit:
                controller_fault = RejectFirstWorkerSubmit(runtime.app)
                controller_server.app = controller_fault
            else:
                controller_fault = SimpleNamespace(rejections=0)
                controller_server.app = runtime.app
            yield SimpleNamespace(**locals())
    finally:
        if runtime is not None:
            runtime.close()
        if node is not None:
            node.close()
        if controller_server is not None:
            controller_server.close()
        if gate_server is not None:
            gate_server.close()
        upstream.close()
