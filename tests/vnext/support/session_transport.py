"""Literal P08 Session transport fixtures; no Host or persistence substitute."""

from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from types import SimpleNamespace

from wuji_core.contracts.envelopes import BlobRef
from wuji_core.contracts.envelopes import WorkerAssignment
from wuji_core.contracts.execution import SessionManifest
from wuji_core.contracts.sessions import (
    BoundaryObject,
    BoundaryObjects,
    DeliveryReceipt,
    HistoryRoot,
    HumanInput,
    InputPayload,
    InputReceipt,
    MemoryManifestRoot,
    NativeApprovalObservation,
    OperationFrontier,
    PublishedHistoryRoot,
    PublishedMemoryManifestRoot,
    PublishedProviderStateRoot,
    PublishedSession,
    ProviderStateRoot,
    SessionCompatibility,
    SessionLimits,
    SessionReceipt,
    StagedSessionObjects,
)
from wuji_core.http import canonical_json_bytes


BOUNDARY_BYTES = b"\xff\x00\x01"
BOUNDARY_BASE64 = "/wAB"
BOUNDARY_DIGEST = "942e1e2a66a427b6551732f758bc314f22b9cdec9365a3425c9184de299392b5"


def compatibility(profile_snapshot=None):
    body = {
        "profile_snapshot": (
            {"ref": "session-profile", "revision": "1"}
            if profile_snapshot is None
            else profile_snapshot
        ),
        "client_snapshot": {"price": Decimal("1.250")},
        "runtime_snapshot": {"ref": "runtime-v1"},
        "framework_snapshot": {"agent_framework_core": "1.18.0"},
        "lock_digest": "a" * 64,
        "capability_ref": "session-capability-v1",
        "capability_digest": "b" * 64,
    }
    if "validation_status" in SessionCompatibility.model_fields:
        body["validation_status"] = "mechanism_candidate"
    return SessionCompatibility.model_validate(body)


def boundary_objects():
    fixed_compatibility = compatibility()
    scope = {
        "session_id": "session-p08",
        "session_lineage": "run:first-p08",
        "work_item_id": "work-p08",
        "compatibility": fixed_compatibility,
    }
    history = HistoryRoot(
        **scope,
        snapshot_id="snapshot-p08",
        read_set=(),
        message_end=1,
        messages=({"role": "user", "contents": [{"type": "text", "text": "fixed"}]},),
        frontier=OperationFrontier(),
    )
    provider = ProviderStateRoot(
        **scope,
        session_state={"provider_decimal": Decimal("1.250")},
        pending_contents=(),
        call_bindings=(),
    )
    memory = MemoryManifestRoot(**scope, enabled=False)
    return BoundaryObjects(
        history=history,
        provider_state=provider,
        memory=memory,
        objects=(
            BoundaryObject(
                key="provider-raw",
                data=BOUNDARY_BYTES,
                media_type="application/octet-stream",
            ),
        ),
    )


def _blob(name, body):
    return BlobRef(
        id=name,
        version="1",
        sha256=sha256(body).hexdigest(),
    )


def _ref_key(ref):
    return ref.id + "@" + ref.version.root


def published_session():
    fixed_compatibility = compatibility()
    scope = {
        "session_id": "session-p08",
        "session_lineage": "run:first-p08",
        "work_item_id": "work-p08",
        "compatibility": fixed_compatibility,
    }
    history = PublishedHistoryRoot(
        **scope,
        snapshot_id="snapshot-p08",
        read_set=(),
        message_end=1,
        messages=({"role": "user", "contents": [{"type": "text", "text": "fixed"}]},),
        frontier=OperationFrontier(),
    )
    provider = PublishedProviderStateRoot(
        **scope,
        session_state={"provider_decimal": Decimal("1.250")},
        pending_contents=(),
        call_bindings=(),
    )
    memory = PublishedMemoryManifestRoot(**scope, enabled=False)
    history_bytes = canonical_json_bytes(history.model_dump(mode="python"))
    provider_bytes = canonical_json_bytes(provider.model_dump(mode="python"))
    memory_bytes = canonical_json_bytes(memory.model_dump(mode="python"))
    raw_bytes = BOUNDARY_BYTES
    refs = (
        _blob("history-root", history_bytes),
        _blob("provider-root", provider_bytes),
        _blob("memory-root", memory_bytes),
        _blob("provider-raw", raw_bytes),
    )
    saved_at = datetime(2026, 9, 13, 8, 30, tzinfo=timezone.utc)
    manifest = SessionManifest.model_validate(
        {
            "session_id": "session-p08",
            "work_item_id": "work-p08",
            "checkpoint_revision": "1",
            "owner_run_id": "run-p08",
            "run_epoch": "1",
            "history_root": refs[0],
            "message_end": "1",
            "provider_state_ref": refs[1],
            "memory_manifest_ref": refs[2],
            "pending_operation_refs": [],
            "lock_digest": "a" * 64,
            "recovery_class": "settled_boundary",
            "saved_at": saved_at,
        }
    )
    manifest_digest = sha256(
        canonical_json_bytes(manifest.model_dump(mode="json"))
    ).hexdigest()
    return PublishedSession(
        receipt=SessionReceipt(
            session_id="session-p08",
            manifest_ref="manifest-p08-1",
            checkpoint_revision="1",
            manifest_digest=manifest_digest,
            publication_id="publication-p08-1",
            published_at=saved_at,
        ),
        manifest=manifest,
        history=history,
        provider_state=provider,
        memory=memory,
        object_refs=refs,
        object_bytes={
            _ref_key(refs[0]): history_bytes,
            _ref_key(refs[1]): provider_bytes,
            _ref_key(refs[2]): memory_bytes,
            _ref_key(refs[3]): raw_bytes,
        },
    )


def simple_session_values():
    published = published_session()
    staged = StagedSessionObjects(
        history_root=published.manifest.history_root,
        provider_state_ref=published.manifest.provider_state_ref,
        memory_manifest_ref=published.manifest.memory_manifest_ref,
        object_refs=published.object_refs,
        lease_owner="lease-p08",
        history=published.history,
        provider_state=published.provider_state,
        memory=published.memory,
    )
    observed_at = datetime(2026, 9, 13, 8, 30, tzinfo=timezone.utc)
    return {
        "staged": staged,
        "receipt": published.receipt,
        "compatibility": compatibility(),
        "observation": NativeApprovalObservation(
            manifest_ref=published.receipt.manifest_ref,
            contents=({"type": "function_approval_request", "amount": Decimal("1.250")},),
            call_bindings=(),
            observed_at=observed_at,
        ),
        "input_receipt": InputReceipt(
            input_request_id="input-p08",
            work_item_id="work-p08",
            manifest_ref=published.receipt.manifest_ref,
            status="pending",
            approval_refs=("approval-p08",),
            source_receipt_id="source-p08",
        ),
        "human_input": HumanInput(
            delivery_id="delivery-p08",
            input_request_id="input-p08",
            manifest_ref=published.receipt.manifest_ref,
            payload_digest="c" * 64,
            payload=InputPayload(kind="question", text="fixed answer"),
        ),
        "delivery_receipt": DeliveryReceipt(
            delivery_id="delivery-p08",
            input_request_id="input-p08",
            status="delivered",
            payload_digest="c" * 64,
            receiving_run_id="run-p08",
        ),
    }


def session_limits():
    return SessionLimits(
        max_objects=32,
        max_reference_depth=8,
        max_object_bytes=16_384,
        max_total_bytes=65_536,
        max_messages=128,
        max_pending_approvals=8,
    )


def _execution_limits():
    return {
        "max_work_items": 16,
        "max_reason_runs": 4,
        "max_model_requests": 8,
        "max_tool_calls": 8,
        "max_single_output_bytes": 16_384,
        "max_total_output_bytes": 65_536,
        "max_elapsed_seconds": 60,
        "max_attempts_per_work": 2,
        "repair_attempts": 1,
    }


def _tool_definition():
    return {
        "ref": "tool-p08@1",
        "revision": "1",
        "published_at": "2026-09-13T08:00:00Z",
        "name": "read_workspace",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["path"],
            "properties": {"path": {"type": "string"}},
        },
        "executor_ref": "executor-p08@1",
        "approval_required": True,
        "allowed_target_kinds": ["workspace_read"],
    }


def m1_resolved():
    body = {
        "ref": "m1-profile",
        "revision": "1",
        "work_kind": "explore",
        "instructions": "fixed",
        "tool_definition_refs": ["tool-p08@1"],
        "lock_digest": "a" * 64,
        "max_context_records": 16,
        "max_context_bytes": 16_384,
        "max_output_tokens": 2_048,
        "capabilities": {
            name: False
            for name in (
                "todo",
                "mode",
                "file_memory",
                "file_access",
                "skills",
                "shell",
                "web_search",
                "background_agents",
                "outer_loop",
                "auto_approval",
                "compaction",
                "restoration",
                "mcp",
            )
        },
    }
    return {
        "profile": {
            "ref": body["ref"],
            "revision": body["revision"],
            "digest": sha256(canonical_json_bytes(body)).hexdigest(),
            "body": body,
        },
        "client_model": "fixture-model",
        "limits": _execution_limits(),
        "request_timeout_seconds": 10.0,
        "tools": [_tool_definition()],
        "session_lineage": "run:first-p08",
    }


def session_resolved():
    value = m1_resolved()
    body = dict(value["profile"]["body"])
    body.update(
        schema_version="wuji.harness.session.v1",
        history_source_id="history_p08",
        memory_mode="pinned_context",
        memory_source_id="memory_p08",
        session_limits=session_limits().model_dump(mode="python"),
        max_context_window_tokens=8_192,
        compaction_enabled=False,
    )
    body["ref"] = "session-profile"
    body["capabilities"] = {
        **{
            name: False
            for name in (
                "todo",
                "mode",
                "file_memory",
                "file_access",
                "skills",
                "shell",
                "web_search",
                "background_agents",
                "outer_loop",
                "auto_approval",
                "compaction",
                "mcp",
            )
        },
        "restoration": True,
        "native_approval": True,
        "versioned_memory": True,
    }
    profile = {
        "ref": body["ref"],
        "revision": body["revision"],
        "digest": sha256(canonical_json_bytes(body)).hexdigest(),
        "body": body,
    }
    value["profile"] = profile
    value.update(
        session_compatibility=compatibility(profile).model_dump(mode="python"),
        session_limits=session_limits().model_dump(mode="python"),
        delivery_id="delivery-p08",
        memory_files={"notes.txt": b"fixed memory"},
    )
    return value


def assignment():
    return WorkerAssignment.model_validate(
        {
            "schema_version": "wuji.assignment.v2",
            "operation_id": "start-p08-child",
            "identity": {
                "tenant_id": "tenant-p08",
                "project_id": "project-p08",
                "task_id": "task-p08",
                "work_item_id": "work-p08",
                "agent_run_id": "run-p08",
                "execution_epoch": "1",
                "run_epoch": "1",
                "runtime_attempt": "1",
                "receiver_id": "receiver-p08",
            },
            "work_kind": "explore",
            "snapshot_id": "snapshot-p08",
            "profile_refs": ["session-profile"],
            "session_manifest_ref": "manifest-p08-1",
            "tool_definition_refs": ["tool-p08@1"],
            "limits": _execution_limits(),
            "resume_reason": "approved input",
        }
    )


class FixedIntake:
    def __init__(self):
        self.saved = {}

    def save(self, fixed_assignment, name, value):
        key = (fixed_assignment.operation_id, name)
        previous = self.saved.get(key)
        if previous is not None and previous != value:
            raise AssertionError("a retained request key accepted different content")
        self.saved[key] = value


class FixedPlatformHost:
    def __init__(self):
        self.values = simple_session_values()
        self.boundary = boundary_objects()
        self.published = published_session()

    def stage_session(self, fixed_assignment, objects):
        if fixed_assignment != assignment() or objects != self.boundary:
            raise AssertionError("stage did not preserve assignment/boundary")
        return self.values["staged"]

    def publish_session(self, fixed_assignment, manifest, *, expected_revision):
        if (
            fixed_assignment != assignment()
            or manifest != self.published.manifest
            or expected_revision != "0"
        ):
            raise AssertionError("publish did not preserve manifest revision binding")
        return self.values["receipt"]

    def load_session(self, fixed_assignment, *, manifest_ref):
        if fixed_assignment != assignment() or manifest_ref != "manifest-p08-1":
            raise AssertionError("load did not preserve the opaque manifest ref")
        return self.published

    def register_input(self, fixed_assignment, observation):
        if fixed_assignment != assignment() or observation != self.values["observation"]:
            raise AssertionError("register did not preserve the native observation")
        return self.values["input_receipt"]

    def load_delivery(self, fixed_assignment, *, delivery_id):
        if fixed_assignment != assignment() or delivery_id != "delivery-p08":
            raise AssertionError("delivery load changed its persisted id")
        return self.values["human_input"]

    def acknowledge_delivery(
        self, fixed_assignment, *, delivery_id, payload_digest
    ):
        if (
            fixed_assignment != assignment()
            or delivery_id != "delivery-p08"
            or payload_digest != "c" * 64
        ):
            raise AssertionError("delivery ack changed its persisted binding")
        return self.values["delivery_receipt"]


class FixedWorkerBridge:
    def __init__(self):
        self.assignment = assignment()
        self.host = FixedPlatformHost()
        self.intake = FixedIntake()

    def current_worker_host(self, _access, fixed_assignment):
        if fixed_assignment != self.assignment:
            raise AssertionError("Session bridge bypassed the fixed assignment")
        return self.host


def session_host_bridge():
    from wuji_core.execution.session_bridge import SessionHostBridge

    worker_bridge = FixedWorkerBridge()
    codec = session_transport_codec()
    return SessionHostBridge(worker_bridge, codec=codec), worker_bridge, codec


class FixedRemoteSessionTransport:
    """Replace only external HTTP I/O; every request still uses generated wire."""

    def __init__(self, codec):
        self.codec = codec
        self.values = simple_session_values()
        self.published = published_session()

    def __call__(self, action, payload):
        if action == "stage-session":
            request = __import__(
                "wuji_core.contracts.generated", fromlist=["WorkerStageSessionRequest"]
            ).WorkerStageSessionRequest.model_validate(payload)
            if self.codec.decode_boundary(request.boundary) != boundary_objects():
                raise AssertionError("remote stage request changed boundary bytes")
            response = self.codec.encode_staged(self.values["staged"])
        elif action == "publish-session":
            request = __import__(
                "wuji_core.contracts.generated", fromlist=["WorkerPublishSessionRequest"]
            ).WorkerPublishSessionRequest.model_validate(payload)
            if request.manifest != self.published.manifest or request.expected_revision.root != "0":
                raise AssertionError("remote publish request changed revision/manifest")
            response = self.codec.encode_receipt(self.values["receipt"])
        elif action == "load-session":
            request = __import__(
                "wuji_core.contracts.generated", fromlist=["WorkerLoadSessionRequest"]
            ).WorkerLoadSessionRequest.model_validate(payload)
            if request.manifest_ref != "manifest-p08-1":
                raise AssertionError("remote load request changed manifest ref")
            response = self.codec.encode_published(self.published)
        elif action == "register-input":
            request = __import__(
                "wuji_core.contracts.generated", fromlist=["WorkerRegisterInputRequest"]
            ).WorkerRegisterInputRequest.model_validate(payload)
            if self.codec.decode_observation(request.observation) != self.values["observation"]:
                raise AssertionError("remote input request changed native observation")
            response = self.codec.encode_input_receipt(self.values["input_receipt"])
        elif action == "load-delivery":
            request = __import__(
                "wuji_core.contracts.generated", fromlist=["WorkerLoadDeliveryRequest"]
            ).WorkerLoadDeliveryRequest.model_validate(payload)
            if request.delivery_id != "delivery-p08":
                raise AssertionError("remote delivery request changed delivery id")
            response = self.codec.encode_human_input(self.values["human_input"])
        elif action == "acknowledge-delivery":
            request = __import__(
                "wuji_core.contracts.generated", fromlist=["WorkerAcknowledgeDeliveryRequest"]
            ).WorkerAcknowledgeDeliveryRequest.model_validate(payload)
            if request.delivery_id != "delivery-p08" or request.payload_digest.root != "c" * 64:
                raise AssertionError("remote acknowledgement changed delivery binding")
            response = self.codec.encode_delivery_receipt(self.values["delivery_receipt"])
        else:
            raise AssertionError("RemoteWorkerHost selected an unknown Session endpoint")
        if request.assignment != assignment():
            raise AssertionError("remote request changed the complete Run assignment")
        return response.model_dump(mode="python")


def remote_worker_host(directory):
    from wuji_core.contracts import generated as wire
    from wuji_maf_worker.remote_host import RemoteWorkerHost

    directory.mkdir(mode=0o700)
    codec = session_transport_codec()
    host = object.__new__(RemoteWorkerHost)
    host.receiver = wire.WorkerReceiver.model_validate(
        {
            "receiver_id": "receiver-p08",
            "runtime_attempt": "1",
            "environment_ref": "environment-p08",
            "pod_uid": "pod-p08",
        }
    )
    host._assignment = None
    host.maximum = codec.maximum
    host.directory = directory
    host.session_codec = codec
    host._request = FixedRemoteSessionTransport(codec)
    return host, codec


class FixedVerifier:
    def verify(self, credential):
        if credential != "actual-run-bearer":
            raise AssertionError("remote resolve changed the actual Run bearer")
        return "verified-worker-principal"


def remote_resolver(resolved):
    from wuji_core.contracts import generated as wire
    from wuji_maf_worker.context import ContextBundle
    from wuji_maf_worker.remote_host import RemoteWorkerHost

    codec = session_transport_codec()
    text = '{"schema_version":"wuji.context.v2"}'
    digest = sha256(text.encode()).hexdigest()
    context = ContextBundle("snapshot-p08", (), (), text, digest)
    resolved_wire = (
        wire.WorkerSessionResolvedHost.model_validate(codec.encode_resolved(resolved))
        if resolved["profile"]["body"].get("schema_version")
        else wire.WorkerResolvedHost.model_validate(resolved)
    )
    reply = SimpleNamespace(
        context=wire.WorkerContext.model_validate(
            {
                "snapshot_id": context.snapshot_id,
                "read_set": [],
                "record_refs": [],
                "text": context.text,
                "input_digest": context.input_digest,
            }
        ),
        resolved=resolved_wire,
    )
    host = object.__new__(RemoteWorkerHost)
    host._credential = "actual-run-bearer"
    host.verifier = FixedVerifier()
    host.session_codec = codec
    host._resolved = lambda fixed_assignment: reply
    return host, context


def session_transport_codec(*, maximum=65_536):
    from wuji_core.execution.session_bridge import SessionTransportCodec

    return SessionTransportCodec(max_transport_bytes=maximum)
