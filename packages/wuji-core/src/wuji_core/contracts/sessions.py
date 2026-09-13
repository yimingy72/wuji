"""Internal P08 boundaries. SDK objects stay exclusively in the Worker package.

Export models allow missing platform receipts; SessionRepository must complete
and verify them before publication. None is never evidence of a settled action.
"""

from typing import Annotated, Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

from wuji_core.contracts.envelopes import BlobRef
from wuji_core.contracts.execution import SessionManifest
from wuji_core.contracts.knowledge import KnowledgeRef


Text = Annotated[StrictStr, Field(min_length=1, max_length=256)]
Digest = Annotated[StrictStr, Field(pattern=r"^[a-f0-9]{64}$")]
Revision = Annotated[StrictStr, Field(pattern=r"^(0|[1-9][0-9]*)$")]
Count = Annotated[StrictInt, Field(ge=0)]
Positive = Annotated[StrictInt, Field(gt=0)]
NATIVE_REJECTION_TEXT_CORE_1_18_0 = (
    "Error: Tool call invocation was rejected by user."
)


def native_rejection_content(provider_call_id: str) -> dict[str, Any]:
    """Canonical public Content observed for a rejected call in core 1.18.0."""

    return {
        "type": "function_result",
        "call_id": provider_call_id,
        "result": NATIVE_REJECTION_TEXT_CORE_1_18_0,
        "items": [
            {
                "type": "text",
                "text": NATIVE_REJECTION_TEXT_CORE_1_18_0,
                "additional_properties": {},
            }
        ],
        "additional_properties": {},
    }


class SessionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SessionLimits(SessionModel):
    max_objects: Positive
    max_reference_depth: Positive
    max_object_bytes: Positive
    max_total_bytes: Positive
    max_messages: Positive
    max_pending_approvals: Positive


class SessionCompatibility(SessionModel):
    profile_snapshot: dict[str, Any]
    client_snapshot: dict[str, Any]
    runtime_snapshot: dict[str, Any]
    framework_snapshot: dict[str, Any]
    lock_digest: Digest
    capability_ref: Text
    capability_digest: Digest
    validation_status: Literal["mechanism_candidate", "verified"]


class MessagePosition(SessionModel):
    message_index: Count
    content_index: Count
    message_digest: Digest
    content_digest: Digest
    native_message_id: Text | None = None


class NativeCallBinding(SessionModel):
    model_attempt_id: Text
    message_id: Text
    provider_call_id: Annotated[StrictStr, Field(min_length=1, max_length=1024)]
    sdk_content_id: Text
    sdk_approval_id: Text | None = None
    tool_definition_ref: Text
    native_arguments: Annotated[StrictStr, Field(max_length=16777216)]
    arguments_digest: Digest
    position: MessagePosition | None = None
    tool_call_id: Text | None = None
    provider_response_ref: BlobRef | None = None
    arguments_ref: BlobRef | None = None

    @model_validator(mode="after")
    def occurrence(self):
        if self.sdk_approval_id is not None and self.sdk_approval_id != self.sdk_content_id:
            raise ValueError("native approval and function occurrence must agree")
        return self


class ModelFrontierEntry(SessionModel):
    model_attempt_id: Text
    positions: tuple[MessagePosition, ...]
    request_digest: Digest | None = None
    request_messages: tuple[dict[str, Any], ...] = ()
    request_messages_digest: Digest | None = None
    predecessor_positions: tuple[MessagePosition, ...] = ()
    response_digest: Digest | None = None
    response_ref: BlobRef | None = None


class ToolFrontierEntry(SessionModel):
    tool_call_id: Text
    tool_attempt_id: Text
    positions: tuple[MessagePosition, ...]
    receipt: dict[str, Any]
    receipt_digest: Digest | None = None


class RejectedCallFrontierEntry(SessionModel):
    approval_ref: Text
    decision_version: Revision
    call_binding: NativeCallBinding
    result_position: MessagePosition
    result_content: dict[str, Any]
    result_digest: Digest

    @model_validator(mode="after")
    def native_shape(self):
        if self.result_content != native_rejection_content(
            self.call_binding.provider_call_id
        ):
            raise ValueError("rejected call requires the fixed native SDK result")
        return self


class OperationFrontier(SessionModel):
    model_entries: tuple[ModelFrontierEntry, ...] = ()
    tool_entries: tuple[ToolFrontierEntry, ...] = ()
    pending_approvals: tuple[NativeCallBinding, ...] = ()
    rejected_calls: tuple[RejectedCallFrontierEntry, ...] = ()
    archived_history_refs: tuple[BlobRef, ...] = ()


class SessionRoot(SessionModel):
    session_id: Text
    session_lineage: Text
    work_item_id: Text
    compatibility: SessionCompatibility
    object_refs: tuple[BlobRef, ...] = ()


class HistoryRoot(SessionRoot):
    schema_version: Literal["wuji.session.history.v1"] = "wuji.session.history.v1"
    snapshot_id: Text
    read_set: tuple[KnowledgeRef, ...]
    message_end: Count
    messages: tuple[dict[str, Any], ...]
    frontier: OperationFrontier

    @model_validator(mode="after")
    def end(self):
        if self.message_end != len(self.messages):
            raise ValueError("message_end must delimit the complete saved history")
        return self


class ProviderStateRoot(SessionRoot):
    schema_version: Literal["wuji.session.provider.v1"] = "wuji.session.provider.v1"
    session_state: dict[str, Any]
    pending_contents: tuple[dict[str, Any], ...]
    call_bindings: tuple[NativeCallBinding, ...]


class MemoryFile(SessionModel):
    path: Annotated[StrictStr, Field(min_length=1, max_length=1024)]
    ref: BlobRef | None = None
    object_key: Text | None = None

    @model_validator(mode="after")
    def relative_file(self):
        if self.path.startswith("/") or "\\" in self.path or any(ord(c) < 32 for c in self.path) or any(p in {"", ".", ".."} for p in self.path.split("/")):
            raise ValueError("memory file must have a confined logical path")
        if (self.ref is None) == (self.object_key is None):
            raise ValueError("memory file needs exactly one fixed ref or export object key")
        return self


class MemoryManifestRoot(SessionRoot):
    schema_version: Literal["wuji.session.memory.v1"] = "wuji.session.memory.v1"
    enabled: bool
    files: tuple[MemoryFile, ...] = ()
    state_refs: tuple[BlobRef, ...] = ()

    @model_validator(mode="after")
    def empty_when_disabled(self):
        if not self.enabled and (self.files or self.state_refs or self.object_refs):
            raise ValueError("disabled memory must have an actual empty manifest")
        if len({f.path for f in self.files}) != len(self.files):
            raise ValueError("duplicate memory paths")
        return self


class BoundaryObject(SessionModel):
    key: Text
    data: bytes
    media_type: Annotated[StrictStr, Field(min_length=1, max_length=256)]
    object_refs: tuple[BlobRef, ...] = ()


class BoundaryObjects(SessionModel):
    history: HistoryRoot
    provider_state: ProviderStateRoot
    memory: MemoryManifestRoot
    objects: tuple[BoundaryObject, ...] = ()


def require_published_call(binding):
    if any(value is None for value in (
        binding.position, binding.tool_call_id,
        binding.provider_response_ref, binding.arguments_ref,
    )):
        raise ValueError("published call lacks observed identity or durable original bytes")


class PublishedHistoryRoot(HistoryRoot):
    @model_validator(mode="after")
    def complete_frontier(self):
        for entry in self.frontier.model_entries:
            if not entry.positions or not entry.request_messages or any(
                value is None
                for value in (
                    entry.request_digest,
                    entry.request_messages_digest,
                    entry.response_digest,
                    entry.response_ref,
                )
            ):
                raise ValueError("published model frontier requires platform response evidence")
        for entry in self.frontier.tool_entries:
            if not entry.positions or entry.receipt_digest is None:
                raise ValueError("published tool frontier requires durable receipt and message")
        for call in self.frontier.pending_approvals:
            require_published_call(call)
        for rejected in self.frontier.rejected_calls:
            require_published_call(rejected.call_binding)
        return self


class PublishedProviderStateRoot(ProviderStateRoot):
    @model_validator(mode="after")
    def complete_calls(self):
        for call in self.call_bindings:
            require_published_call(call)
        return self


class PublishedMemoryManifestRoot(MemoryManifestRoot):
    @model_validator(mode="after")
    def fixed_files(self):
        if any(f.ref is None or f.object_key is not None for f in self.files):
            raise ValueError("published memory files require immutable refs")
        return self


class StagedSessionObjects(SessionModel):
    history_root: BlobRef
    provider_state_ref: BlobRef
    memory_manifest_ref: BlobRef
    object_refs: tuple[BlobRef, ...]
    lease_owner: Text
    history: PublishedHistoryRoot
    provider_state: PublishedProviderStateRoot
    memory: PublishedMemoryManifestRoot


class SessionReceipt(SessionModel):
    session_id: Text
    manifest_ref: Text
    checkpoint_revision: Revision
    manifest_digest: Digest
    publication_id: Text
    published_at: AwareDatetime
    status: Literal["published"] = "published"


class RecoveryCheck(SessionModel):
    resumable: bool
    reason_code: Text | None = None
    manifest_ref: Text | None = None
    session_id: Text | None = None
    checkpoint_revision: Revision | None = None
    session_lineage: Text | None = None
    owner_run_id: Text | None = None
    frontier_digest: Digest | None = None


class PublishedSession(SessionModel):
    receipt: SessionReceipt
    manifest: SessionManifest
    history: PublishedHistoryRoot
    provider_state: PublishedProviderStateRoot
    memory: PublishedMemoryManifestRoot
    object_refs: tuple[BlobRef, ...]
    # Exact bytes for all refs, keyed by '<id>@<version>'. Never mutable paths.
    object_bytes: dict[str, bytes] = Field(default_factory=dict)
    recovery_check: RecoveryCheck | None = None


class NativeApprovalObservation(SessionModel):
    manifest_ref: Text
    contents: tuple[dict[str, Any], ...]
    call_bindings: tuple[NativeCallBinding, ...]
    # Worker observation time is optional provenance, never Host intake time.
    observed_at: AwareDatetime | None = None


class InputReceipt(SessionModel):
    input_request_id: Text
    work_item_id: Text
    manifest_ref: Text
    status: Literal["pending", "resolved", "revoked"]
    approval_refs: tuple[str, ...]
    source_receipt_id: Text


class ApprovalDeliveryDecision(SessionModel):
    approval_ref: Text
    decision_version: Revision
    decision: Literal["approve", "reject"]
    pending_content: dict[str, Any]
    call_binding: NativeCallBinding


class InputPayload(SessionModel):
    kind: Literal["approval", "question"]
    decisions: tuple[ApprovalDeliveryDecision, ...] = ()
    text: Annotated[StrictStr, Field(min_length=1, max_length=32768)] | None = None

    @model_validator(mode="after")
    def shape(self):
        if self.kind == "approval" and (not self.decisions or self.text is not None):
            raise ValueError("approval delivery requires persisted decisions only")
        if self.kind == "question" and (self.decisions or self.text is None):
            raise ValueError("question delivery requires persisted text only")
        return self


class HumanInput(SessionModel):
    delivery_id: Text
    input_request_id: Text
    manifest_ref: Text
    payload_digest: Digest
    payload: InputPayload


class DeliveryReceipt(SessionModel):
    delivery_id: Text
    input_request_id: Text
    status: Literal["pending", "delivered"]
    payload_digest: Digest
    receiving_run_id: Text | None = None


class ApprovalReceipt(SessionModel):
    approval_ref: Text
    version: Revision
    decision: Literal["approve", "reject"] | None
    decision_status: Literal["pending", "decided", "consumed"]
    execution_block_reason: Text | None = None
    tool_call_id: Text
    tool_attempt_id: Text | None = None


class ApprovalBinding(SessionModel):
    approval_ref: Text
    decision_version: Revision
    tool_call_id: Text
    tool_attempt_id: Text | None = None
    replay: bool = False
