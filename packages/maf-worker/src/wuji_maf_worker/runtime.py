"""One hosted Worker assignment, independently consuming MAF's native stream."""

import asyncio
import json
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import AsyncIterator, Protocol
from urllib.parse import urlsplit

import httpx
from agent_framework import (
    AgentSession,
    ChatMiddleware,
    FileMemoryProvider,
    InMemoryHistoryProvider,
    Message,
)
from agent_framework.exceptions import ChatClientException

from wuji_core.contracts.envelopes import RunIdentity, WorkerAssignment
from wuji_core.contracts.execution import SessionManifest
from wuji_core.contracts.sessions import (
    DeliveryReceipt, HumanInput, InputReceipt, NativeApprovalObservation,
    NativeCheckpointManifestV2, PublishedNativeSessionV2, PublishedSession,
    SessionCompatibility, SessionReceipt, StagedNativeSessionV2,
    StagedSessionObjects,
)
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.http.auth import TokenVerifier
from wuji_maf_worker.context import ContextBundle
from wuji_maf_worker.factory import ProblemHarnessProfile, SessionHarnessProfile, build_agent, parse_profile
from wuji_maf_worker.approvals import approval_response_message
from wuji_maf_worker.history import (
    BoundedWorkMemoryProvider,
    HistoryArchive,
    PinnedMemoryContextProvider,
    VersionedMemoryStore,
    WorkMemoryStore,
)
from wuji_maf_worker.sessions import NativeSessionAdapter, NativeSessionV2Adapter
from wuji_maf_worker.tools import FunctionBudget, GateFunctions, ModelCallIdentity


class ModelGateTransportError(ValueError):
    """The child could not complete a model request over its own gate transport.

    The SDK wraps every provider-side failure in ChatClientException. Only the
    transport cause is classified here: the class name is what reaches the
    bounded operator signal, and the SDK's own text stays on the private
    diagnostic channel.
    """


class ModelGateRejectedError(ValueError):
    """The model gate answered, and the SDK could not use that answer."""


# Provider transport causes the SDK re-raises as ChatClientException. The openai
# client's own transport class is matched by name so the child does not add a
# direct dependency on that package; a wrong label only changes a diagnostic.
_TRANSPORT_CAUSE_NAMES = frozenset({
    "APIConnectionError", "ConnectError", "ConnectTimeout", "PoolTimeout",
    "ReadError", "ReadTimeout", "RemoteProtocolError", "TransportError",
    "WriteError", "WriteTimeout",
})


def _model_gate_error(error):
    cause = error.__cause__
    while cause is not None:
        if isinstance(cause, (httpx.HTTPError, OSError, TimeoutError)):
            break
        if type(cause).__name__ in _TRANSPORT_CAUSE_NAMES:
            break
        cause = cause.__cause__
    if cause is None:
        return ModelGateRejectedError("the model gate refused or failed the request")
    return ModelGateTransportError(
        "the model gate transport did not complete the request"
    )


@dataclass(frozen=True)
class WorkerEvent:
    kind: str
    agent_run_id: str
    data: dict


class CheckpointBeforeModel(ChatMiddleware):
    """Publish the prior complete tool-result group before another model call."""

    def __init__(self, publish):
        self.publish = publish
        self.calls = 0

    async def process(self, context, call_next):
        if self.calls:
            if context.session is None:
                raise ValueError("problem checkpoint requires the native Session")
            await self.publish(context.session, context.messages)
        self.calls += 1
        await call_next()


async def _settled_boundary(history, session, messages):
    """Build a complete checkpoint without mutating the running Session."""
    boundary_session = AgentSession.from_dict(session.to_dict())
    state = boundary_session.state.setdefault(history.source_id, {})
    await history.save_messages(
        boundary_session.session_id,
        [message for message in messages if message.role == "tool"],
        state=state,
    )
    stored = await history.get_messages(boundary_session.session_id, state=state)
    return boundary_session, stored


class AgentRuntimePort(Protocol):
    def execute(self, assignment: WorkerAssignment) -> AsyncIterator[WorkerEvent]: ...
    async def cancel(self, identity: RunIdentity, reason: str): ...
    async def deliver_input(self, identity: RunIdentity, human_input): ...


class WorkerHostPort(Protocol):
    def resolve(self, assignment, context, *, verified_principal): ...
    def archive_sdk(self, assignment, body: bytes): ...
    def retain_final_output(self, assignment, *, raw_output): ...
    def submit_result(self, assignment, *, raw_output, context, tool_receipts, sdk_output): ...
    def stage_session(self, assignment, objects) -> StagedSessionObjects: ...
    def publish_session(self, assignment, manifest, *, expected_revision) -> SessionReceipt: ...
    def load_session(self, assignment, *, manifest_ref) -> PublishedSession: ...
    def register_input(self, assignment, observation) -> InputReceipt: ...
    def load_delivery(self, assignment, *, delivery_id) -> HumanInput: ...
    def acknowledge_delivery(self, assignment, *, delivery_id, payload_digest) -> DeliveryReceipt: ...
    def knowledge_list(self, assignment, *, snapshot_id, material_types, cursor, limit, native_occurrence): ...
    def knowledge_read(self, assignment, *, snapshot_id, ref, selector, native_occurrence): ...
    def knowledge_refresh(self, assignment, *, snapshot_id, native_occurrence): ...
    def knowledge_attach(self, assignment, *, deliveries, manifest_ref=None, channel=None): ...


class MafRuntime:
    def __init__(self, *, host: WorkerHostPort, context: ContextBundle,
                 run_credential: str, token_verifier: TokenVerifier,
                 model_gate_url: str, tool_gate_url: str, ssl_context=None):
        for url, suffix in ((model_gate_url, "/internal/v2/model"), (tool_gate_url, "/internal/v2/tool-calls")):
            parsed = urlsplit(url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path.rstrip("/") != suffix:
                raise ValueError("a deployment-owned Wuji Gate endpoint is required")
        if not run_credential or "\n" in run_credential or "\r" in run_credential:
            raise ValueError("a Run credential is required")
        if not isinstance(token_verifier, TokenVerifier):
            raise TypeError("the deployment TokenVerifier is required")
        self._host, self._context, self._credential = host, context, run_credential
        if ssl_context is not None and (
            not isinstance(ssl_context, ssl.SSLContext)
            or ssl_context.verify_mode != ssl.CERT_REQUIRED
            or not ssl_context.check_hostname
        ):
            raise ValueError("verified TLS context required")
        self._ssl_context = ssl_context
        self._token_verifier = token_verifier
        self._model_url, self._tool_url = model_gate_url, tool_gate_url
        self._assignment = None
        self._task = None
        self.result = None
        self.input_receipt = None
        self.session_receipt = None
        self.session_checkpoint_error = None
        self.delivery_receipt = None
        self._delivery = None
        self._delivery_id = None
        self._delivery_window = False
        self._delivery_lock = asyncio.Lock()
        self.raw_output = b""
        self.sdk_output = b""
        self.tool_receipts = []
        self.identity_mapping = []

    async def execute(self, assignment):
        assignment = WorkerAssignment.model_validate(assignment).model_copy(deep=True)
        if self._assignment is not None and self._assignment != assignment:
            raise ValueError("one runtime instance owns one immutable assignment")
        if self._task is None:
            self._assignment = assignment
            # Only this task owns SDK iteration. Closing an event consumer does not
            # inject cancellation into the SDK, tool request or result commit.
            self._task = asyncio.create_task(self._run(assignment))
        receipt = await asyncio.shield(self._task)
        yield WorkerEvent(
            "input_receipt" if isinstance(receipt, InputReceipt) else "result_receipt",
            assignment.identity.agent_run_id,
            receipt.model_dump(mode="json"),
        )

    async def wait(self, identity):
        self._require_identity(identity)
        return await asyncio.shield(self._task)

    def _require_identity(self, identity):
        if self._assignment is None or RunIdentity.model_validate(identity) != self._assignment.identity:
            raise ValueError("no local task for that complete Run identity")

    async def cancel(self, identity, reason):
        self._require_identity(identity)
        if not isinstance(reason, str) or not 1 <= len(reason) <= 8192:
            raise ValueError("a bounded cancellation reason is required")
        if self._task.done():
            state = "local_task_finished"
        else:
            self._task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=5)
                state = "local_task_finished"
            except asyncio.CancelledError:
                state = "local_task_cancelled"
            except TimeoutError:
                state = "local_cancel_requested"
            except Exception:
                state = "local_task_failed"
        return {"source": "worker_adapter", "state": state, "remote_state": "unknown"}

    async def deliver_input(self, identity, human_input):
        self._require_identity(identity)
        supplied = HumanInput.model_validate(human_input)
        async with self._delivery_lock:
            if supplied.delivery_id != self._delivery_id:
                raise ValueError("delivery differs from the Host's fixed assignment input")
            if self._delivery is not None:
                if supplied != self._delivery:
                    raise ValueError("delivery replay changed its persisted payload")
                return self.delivery_receipt
            if not self._delivery_window or self._assignment.session_manifest_ref is None:
                raise ValueError("input is accepted only at the fixed restored native boundary")
            loaded = HumanInput.model_validate(await asyncio.to_thread(
                self._host.load_delivery, self._assignment, delivery_id=supplied.delivery_id,
            ))
            if (
                loaded != supplied
                or loaded.manifest_ref != self._assignment.session_manifest_ref.root
                or sha256(canonical_json_bytes(loaded.payload.model_dump(mode="python"))).hexdigest() != loaded.payload_digest
            ):
                raise ValueError("delivery is not the exact persisted checkpoint payload")
            receipt = DeliveryReceipt.model_validate(await asyncio.to_thread(
                self._host.acknowledge_delivery, self._assignment,
                delivery_id=loaded.delivery_id, payload_digest=loaded.payload_digest,
            ))
            if (
                receipt.status != "delivered" or receipt.delivery_id != loaded.delivery_id
                or receipt.input_request_id != loaded.input_request_id
                or receipt.payload_digest != loaded.payload_digest
                or receipt.receiving_run_id != self._assignment.identity.agent_run_id
            ):
                raise ValueError("Host did not persist the actual delivery receipt")
            self._delivery, self.delivery_receipt = loaded, receipt
            return receipt

    async def aclose(self):
        if self._task is not None:
            await asyncio.shield(self._task)

    async def _run(self, assignment):
        verified_principal = await asyncio.to_thread(
            self._token_verifier.verify, self._credential
        )
        resolved = await asyncio.to_thread(
            self._host.resolve,
            assignment,
            self._context,
            verified_principal=verified_principal,
        )
        profile = parse_profile(resolved["profile"])
        problem_profile = isinstance(profile, ProblemHarnessProfile)
        native_v2 = problem_profile and profile.native_session
        session_profile = isinstance(profile, SessionHarnessProfile) or problem_profile
        if not session_profile and (assignment.session_manifest_ref is not None or assignment.resume_reason is not None):
            raise NotImplementedError("M1 only executes fresh work; manifest restoration is unavailable")
        if (
            self._context.snapshot_id != assignment.snapshot_id
            or sha256(self._context.text.encode()).hexdigest() != self._context.input_digest
            or len(self._context.record_refs) > profile.max_context_records
            or len(self._context.text.encode()) > profile.max_context_bytes
        ):
            raise ValueError("context does not match the frozen input/profile")
        limits = resolved["limits"]
        identity = ModelCallIdentity(
            resolved["tools"],
            max_bytes=limits["max_single_output_bytes"],
            require_initial_tool=profile.work_kind == "explore" and not problem_profile,
            capability_manifest=(
                [item.model_dump(mode="json") for item in profile.capability_manifest]
                if problem_profile else ()
            ),
        )
        self.identity_mapping = identity.mapping
        budget = (
            FunctionBudget(profile.function_limits.model_dump(mode="python"))
            if problem_profile else None
        )
        adapter = history = memory = memory_provider = work_memory_provider = restored = None
        if session_profile:
            compatibility = SessionCompatibility.model_validate(resolved["session_compatibility"])
            if (
                compatibility.profile_snapshot != resolved["profile"]
                or compatibility.lock_digest != profile.lock_digest
                or profile.session_limits.model_dump(mode="python") != resolved["session_limits"]
            ):
                raise ValueError("Host Session compatibility does not match the fixed Task Profile")
            adapter = (
                NativeSessionV2Adapter(
                    compatibility=compatibility, limits=profile.session_limits
                )
                if native_v2
                else NativeSessionAdapter(
                    compatibility=compatibility, limits=profile.session_limits
                )
            )
            history = (
                InMemoryHistoryProvider(
                    source_id=profile.history_source_id, skip_excluded=False
                )
                if native_v2
                else HistoryArchive(
                    compatibility=compatibility, limits=profile.session_limits
                )
            )
            if not native_v2:
                history.model_identity = identity
            if assignment.session_manifest_ref is not None:
                loaded = await asyncio.to_thread(
                    self._host.load_session,
                    assignment,
                    manifest_ref=assignment.session_manifest_ref.root,
                )
                published = (
                    PublishedNativeSessionV2.model_validate(loaded)
                    if native_v2
                    else PublishedSession.model_validate(loaded)
                )
                if published.receipt.manifest_ref != assignment.session_manifest_ref.root:
                    raise ValueError("restored Session differs from the assigned Work/input/lineage")
                if native_v2:
                    if (
                        published.manifest.work_item_id
                        != assignment.identity.work_item_id
                        or published.manifest.session_lineage
                        != resolved["session_lineage"]
                    ):
                        raise ValueError("restored native Session differs from its assignment")
                elif (
                    published.history.work_item_id != assignment.identity.work_item_id
                    or published.history.snapshot_id != self._context.snapshot_id
                    or published.history.read_set != self._context.read_set
                    or published.history.session_lineage != resolved["session_lineage"]
                ):
                    raise ValueError("restored Session differs from the assigned Work/input/lineage")
                restored = adapter.restore_boundary(published)
                if not native_v2:
                    history.restore_observations(published)
                identity.restore_bindings(
                    call_bindings=restored.call_bindings, pending_contents=restored.pending_contents,
                    lineage=resolved["session_lineage"],
                )
                memory = restored.memory
            else:
                if assignment.resume_reason is not None:
                    raise ValueError("a resume reason cannot create an unrelated fresh Session")
                if profile.memory_mode == "pinned_context":
                    memory = VersionedMemoryStore(limits=profile.session_limits, files=resolved["memory_files"])
                elif profile.memory_mode == "work_memory":
                    memory = WorkMemoryStore(
                        limits=profile.session_limits,
                        policy=profile.work_memory_policy.model_dump(mode="python"),
                    )
            if profile.memory_mode == "pinned_context":
                memory_provider = PinnedMemoryContextProvider(
                    source_id=profile.memory_source_id, store=memory,
                    max_context_bytes=profile.max_context_bytes - len(self._context.text.encode()),
                )
            if profile.memory_mode == "work_memory":
                if not isinstance(memory, WorkMemoryStore):
                    raise ValueError("problem memory did not restore as the bounded store")
                scope = sha256(canonical_json_bytes({
                    "task_id": assignment.identity.task_id,
                    "work_item_id": assignment.identity.work_item_id,
                    "session_lineage": resolved["session_lineage"],
                })).hexdigest()
                work_memory_provider = (
                    FileMemoryProvider(
                        memory,
                        source_id=profile.memory_source_id,
                        scope=scope,
                    )
                    if native_v2
                    else BoundedWorkMemoryProvider(
                        memory,
                        source_id=profile.memory_source_id,
                        scope=scope,
                    )
                )
        timeout = httpx.Timeout(float(resolved["request_timeout_seconds"]))
        sdk_lines = []
        retained = 0

        def retain(body):
            nonlocal retained
            retained += len(body) + 1
            if retained > limits["max_total_output_bytes"]:
                raise ValueError("SDK archive exceeds the published output limit")
            sdk_lines.append(body)

        def archive_bytes():
            rendered_context = strict_json_loads(self._context.text)
            return b"\n".join(sdk_lines + [canonical_json_bytes({
                "source": "wuji_worker_adapter", "identity_mapping": identity.mapping,
                "local_identity_mapping": identity.local_mapping,
                "tool_receipts": [r.model_dump(mode="python") for r in self.tool_receipts],
                "context": {
                    "schema_version": rendered_context["schema_version"],
                    "snapshot_id": self._context.snapshot_id,
                    "input_digest": self._context.input_digest,
                    "text_digest": sha256(self._context.text.encode()).hexdigest(),
                    "read_set": [r.model_dump(mode="json") for r in self._context.read_set],
                    "record_refs": [r.model_dump(mode="json") for r in self._context.record_refs],
                    "semantic_digest": sha256(canonical_json_bytes(rendered_context)).hexdigest(),
                },
            })]) + b"\n"

        async with httpx.AsyncClient(
            transport=httpx.AsyncHTTPTransport(retries=0, verify=self._ssl_context or True), trust_env=False,
            follow_redirects=False, timeout=timeout,
            event_hooks={"request": [identity.request], "response": [identity.response]},
        ) as model_http, httpx.AsyncClient(
            transport=httpx.AsyncHTTPTransport(retries=0, verify=self._ssl_context or True), trust_env=False,
            follow_redirects=False, timeout=timeout,
            headers={"Authorization": "Bearer " + self._credential, "Content-Type": "application/json"},
        ) as tool_http:
            functions = GateFunctions(
                definitions=resolved["tools"], identity=identity,
                lineage=resolved["session_lineage"], client=tool_http, url=self._tool_url,
                native_approval=session_profile,
                # Older frozen profiles omit this optional field and retain
                # the v1 material contract.  New profiles publish v2
                # explicitly; the Worker never upgrades a Session implicitly.
                material_representation=resolved["profile"]["body"].get(
                    "material_representation", "v1"
                ),
                budget=budget, host=self._host if problem_profile else None,
                assignment=assignment if problem_profile else None,
            )
            self.tool_receipts = functions.receipts
            current_revision = [
                0 if restored is None
                else int(restored.published.receipt.checkpoint_revision)
            ]
            attached_deliveries = set()
            initial_deliveries = []
            if problem_profile and self._context.wire is not None:
                initial_deliveries = [
                    {
                        "delivery_id": item["delivery_id"],
                        "representation_digest": item["representation_digest"],
                    }
                    for item in self._context.wire.get("initial_deliveries", ())
                ]

            async def confirm_native_handoffs(deliveries, channel):
                if not native_v2:
                    return
                pending = [
                    item for item in deliveries
                    if item["delivery_id"] not in attached_deliveries
                ]
                if not pending:
                    return
                await asyncio.to_thread(
                    self._host.knowledge_attach,
                    assignment,
                    deliveries=pending,
                    manifest_ref=None,
                    channel=channel,
                )
                attached_deliveries.update(
                    item["delivery_id"] for item in pending
                )

            async def publish_boundary(session, *, response=None, settled=False,
                                       messages=None):
                observed_at = datetime.now(timezone.utc)
                if native_v2:
                    boundary_kind = (
                        "approval_wait"
                        if any(
                            content.type == "function_approval_request"
                            for message in response.messages
                            for content in message.contents
                        )
                        else "run_return"
                    )
                    objects = adapter.export_boundary(
                        session=session,
                        response=response,
                        memory=memory,
                        session_lineage=resolved["session_lineage"],
                        work_item_id=assignment.identity.work_item_id,
                        boundary_kind=boundary_kind,
                        call_bindings=identity.export_bindings(),
                    )
                    staged = StagedNativeSessionV2.model_validate(
                        await asyncio.to_thread(
                            self._host.stage_session, assignment, objects
                        )
                    )
                    previous = current_revision[0]
                    parent = (
                        None
                        if restored is None
                        else restored.published.receipt.manifest_ref
                    )
                    publication_key = "session-publish:" + sha256(
                        canonical_json_bytes({
                            "identity": assignment.identity.model_dump(mode="json"),
                            "session_id": session.session_id,
                            "parent_manifest_ref": parent,
                            "native_state_ref": staged.native_state_ref.model_dump(mode="json"),
                            "dependency_manifest_ref": staged.dependency_manifest_ref.model_dump(mode="json"),
                            "operation_fence_ref": staged.operation_fence_ref.model_dump(mode="json"),
                        })
                    ).hexdigest()
                    manifest = NativeCheckpointManifestV2(
                        session_id=session.session_id,
                        session_lineage=resolved["session_lineage"],
                        work_item_id=assignment.identity.work_item_id,
                        checkpoint_revision=str(previous + 1),
                        parent_manifest_ref=parent,
                        producer_identity=assignment.identity,
                        profile_ref=profile.ref,
                        profile_revision=profile.revision,
                        profile_digest=profile.digest,
                        compatibility_ref=compatibility.capability_ref,
                        compatibility_digest=compatibility.capability_digest,
                        native_state_ref=staged.native_state_ref,
                        dependency_manifest_ref=staged.dependency_manifest_ref,
                        operation_fence_ref=staged.operation_fence_ref,
                        boundary_kind=boundary_kind,
                        pending_approval_refs=staged.operation_fence.pending_approval_refs,
                        access_scope_ref="task:" + assignment.identity.task_id,
                        publication_key=publication_key,
                        saved_at=observed_at,
                    )
                    receipt = SessionReceipt.model_validate(
                        await asyncio.to_thread(
                            self._host.publish_session,
                            assignment,
                            manifest,
                            expected_revision=previous,
                        )
                    )
                    if (
                        receipt.session_id != session.session_id
                        or receipt.checkpoint_revision != str(previous + 1)
                        or receipt.manifest_digest
                        != sha256(
                            canonical_json_bytes(manifest.model_dump(mode="json"))
                        ).hexdigest()
                    ):
                        raise ValueError("Host published a different native v2 boundary")
                    current_revision[0] = previous + 1
                    self.session_receipt = receipt
                    return staged, receipt
                if settled and messages is not None:
                    boundary_session, stored = await _settled_boundary(
                        history, session, messages
                    )
                else:
                    boundary_session = session
                    stored = await history.get_messages(
                        session.session_id,
                        state=session.state.get(history.source_id),
                    )
                history.observe_messages(
                    stored,
                    model_attempt_id=identity.attempt_id,
                    call_bindings=identity.export_bindings(),
                    tool_receipts=functions.receipts,
                )
                objects = (
                    adapter.export_settled_boundary(
                        session=boundary_session, messages=stored, history=history,
                        call_bindings=identity.export_bindings(),
                        tool_receipts=functions.receipts, memory=memory,
                        observed_at=observed_at,
                    )
                    if settled
                    else adapter.export_boundary(
                        session=session, response=response, history=history,
                        call_bindings=identity.export_bindings(),
                        tool_receipts=functions.receipts, memory=memory,
                        recovery_class=(
                            "approval_boundary"
                            if any(content.type == "function_approval_request"
                                   for message in response.messages for content in message.contents)
                            else "settled_boundary"
                        ),
                        observed_at=observed_at,
                        rejection_decisions=identity.rejected_decisions(),
                    )
                )
                staged = StagedSessionObjects.model_validate(await asyncio.to_thread(
                    self._host.stage_session, assignment, objects,
                ))
                recovery_class = (
                    "approval_boundary"
                    if staged.history.frontier.pending_approvals
                    else "settled_boundary"
                )
                previous = current_revision[0]
                manifest = SessionManifest.model_validate({
                    "session_id": session.session_id,
                    "work_item_id": assignment.identity.work_item_id,
                    "checkpoint_revision": str(previous + 1),
                    "owner_run_id": assignment.identity.agent_run_id,
                    "run_epoch": assignment.identity.run_epoch,
                    "history_root": staged.history_root,
                    "message_end": str(staged.history.message_end),
                    "provider_state_ref": staged.provider_state_ref,
                    "memory_manifest_ref": staged.memory_manifest_ref,
                    "pending_operation_refs": [
                        binding.tool_call_id
                        for binding in staged.history.frontier.pending_approvals
                    ],
                    "lock_digest": profile.lock_digest,
                    "recovery_class": recovery_class,
                    "saved_at": observed_at,
                })
                receipt = SessionReceipt.model_validate(await asyncio.to_thread(
                    self._host.publish_session,
                    assignment,
                    manifest,
                    expected_revision=previous,
                ))
                if (
                    receipt.session_id != session.session_id
                    or receipt.checkpoint_revision != str(previous + 1)
                    or receipt.manifest_digest
                    != sha256(canonical_json_bytes(manifest.model_dump(mode="json"))).hexdigest()
                ):
                    raise ValueError("Host published a different native boundary")
                current_revision[0] = previous + 1
                self.session_receipt = receipt
                if problem_profile:
                    deliveries = [
                        item for item in [*initial_deliveries, *functions.knowledge_deliveries]
                        if item["delivery_id"] not in attached_deliveries
                    ]
                    if deliveries:
                        await asyncio.to_thread(
                            self._host.knowledge_attach,
                            assignment,
                            deliveries=deliveries,
                            manifest_ref=receipt.manifest_ref,
                        )
                        attached_deliveries.update(
                            item["delivery_id"] for item in deliveries
                        )
                return staged, receipt

            checkpoint = (
                CheckpointBeforeModel(
                    lambda session, messages: publish_boundary(
                        session, settled=True, messages=messages
                    )
                )
                if problem_profile and not native_v2 else None
            )
            environment_tools = functions.registered_tools()
            knowledge_tools = functions.registered_knowledge_tools()
            agent, native = build_agent(
                resolved=resolved, profile=profile, model_http=model_http,
                model_gate_url=self._model_url, run_credential=self._credential,
                tools=[*environment_tools, *knowledge_tools], middleware=functions,
                response_parser=identity.parse_response,
                history=history, memory_provider=memory_provider,
                work_memory_provider=work_memory_provider,
                extra_middleware=(() if checkpoint is None else (checkpoint,)),
                environment_tool_count=len(environment_tools),
            )
            try:
                async with asyncio.timeout(limits["max_elapsed_seconds"]):
                    session = restored.session if restored is not None else agent.create_session()
                    if budget is not None:
                        budget.bind(session)
                    messages = self._context.text
                    if session_profile and not native_v2:
                        history.bind_context(
                            session_id=session.session_id, session_lineage=resolved["session_lineage"],
                            assignment=assignment, context=self._context,
                        )
                    if restored is not None:
                        self._delivery_id = resolved["delivery_id"]
                        if self._delivery_id is not None:
                            self._delivery_window = True
                            delivery = HumanInput.model_validate(await asyncio.to_thread(
                                self._host.load_delivery, assignment, delivery_id=self._delivery_id,
                            ))
                            await self.deliver_input(assignment.identity, delivery)
                            self._delivery_window = False
                            if delivery.payload.kind == "approval":
                                identity.bind_delivery(delivery)
                                original_contents = {content.id: content for content in restored.pending_contents}
                                messages = [approval_response_message(
                                    pending_content=original_contents[decision.call_binding.sdk_approval_id],
                                    decision=decision.decision,
                                ) for decision in delivery.payload.decisions]
                            else:
                                if restored.pending_contents:
                                    raise ValueError("a question answer does not resolve native approvals")
                                messages = Message(role="user", contents=delivery.payload.text)
                        elif restored.pending_contents:
                            raise ValueError("pending native approvals require persisted decisions")
                        else:
                            messages = None  # Continue the original settled Session, without duplicating its input.
                    try:
                        stream = agent.run(messages, session=session, stream=True)
                        if restored is None:
                            await confirm_native_handoffs(
                                initial_deliveries, "initial_input"
                            )
                        async for update in stream:
                            retain(update.to_json().encode())
                        final = await stream.get_final_response()
                    except ChatClientException as error:
                        # Bounded classification only: the tool-refusal path keeps
                        # its own MiddlewareFailure and code.
                        raise _model_gate_error(error) from error
                    retain(final.to_json().encode())
                    retain(canonical_json_bytes({"session": session.to_dict()}))
                    approvals = [content for message in final.messages for content in message.contents
                                 if content.type == "function_approval_request"]
                    if approvals and not session_profile:
                        raise ValueError("the frozen M1 Profile does not support native approval")
                    settled_messages = [message for message in final.messages if message.role == "assistant"]
                    if not approvals and (
                        not settled_messages or not settled_messages[-1].text
                        or any(content.type in {"function_call", "function_approval_request"}
                               for content in settled_messages[-1].contents)
                        or final.continuation_token is not None
                    ):
                        raise ValueError("SDK has no settled final assistant text")
                    if session_profile:
                        if approvals:
                            await functions.register_pending(final)
                            staged, self.session_receipt = await publish_boundary(
                                session, response=final
                            )
                        elif not native_v2:
                            staged, self.session_receipt = await publish_boundary(
                                session, response=final
                            )
                        if approvals:
                            observed_at = datetime.now(timezone.utc)
                            self.sdk_output = archive_bytes()
                            await asyncio.to_thread(self._host.archive_sdk, assignment, self.sdk_output)
                            pending_contents = (
                                staged.pending_contents
                                if native_v2
                                else staged.provider_state.pending_contents
                            )
                            pending_bindings = (
                                staged.call_bindings
                                if native_v2
                                else staged.provider_state.call_bindings
                            )
                            observation = NativeApprovalObservation(
                                manifest_ref=self.session_receipt.manifest_ref,
                                contents=pending_contents,
                                call_bindings=pending_bindings,
                                observed_at=observed_at,
                            )
                            self.input_receipt = InputReceipt.model_validate(await asyncio.to_thread(
                                self._host.register_input, assignment, observation,
                            ))
                            if (
                                self.input_receipt.work_item_id != assignment.identity.work_item_id
                                or self.input_receipt.manifest_ref != self.session_receipt.manifest_ref
                            ):
                                raise ValueError("Host input receipt differs from the native boundary")
                            return self.input_receipt
                    self.raw_output = settled_messages[-1].text.encode("utf-8")
                    self.sdk_output = archive_bytes()
                    if len(self.raw_output) > limits["max_single_output_bytes"] or len(self.sdk_output) > limits["max_total_output_bytes"]:
                        raise ValueError("final SDK output exceeds published limits")
                    if native_v2:
                        await confirm_native_handoffs(
                            functions.knowledge_deliveries, "function_result"
                        )
                        raw_ref = await asyncio.to_thread(
                            self._host.retain_final_output,
                            assignment,
                            raw_output=self.raw_output,
                        )
                        if raw_ref.sha256.root != sha256(self.raw_output).hexdigest():
                            raise ValueError("Host retained different final output bytes")
                        try:
                            _staged, self.session_receipt = await publish_boundary(
                                session, response=final
                            )
                        except Exception as error:
                            # The accepted raw/result is authoritative. A failed
                            # optional recovery point never re-runs the Agent.
                            self.session_checkpoint_error = error
                            print(json.dumps({
                                "event": "session_checkpoint_unavailable",
                                "error_class": type(error).__name__,
                                "code": getattr(error, "code", None),
                                "status": getattr(error, "status_code", None),
                            }, sort_keys=True), flush=True)
                    self.result = await asyncio.to_thread(
                        self._host.submit_result, assignment,
                        raw_output=self.raw_output, context=self._context,
                        tool_receipts=tuple(self.tool_receipts), sdk_output=self.sdk_output,
                    )
                    return self.result
            except BaseException:
                self._delivery_window = False
                self.sdk_output = archive_bytes()
                # Preserve the actual partial SDK observations if the result sink
                # did not finish. A persistence error propagates, never success.
                if sdk_lines:
                    await asyncio.to_thread(self._host.archive_sdk, assignment, self.sdk_output)
                raise
            finally:
                await native.close()
