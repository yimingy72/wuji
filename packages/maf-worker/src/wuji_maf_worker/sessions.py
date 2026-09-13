"""Complete native boundaries, with publication and recovery authority at Wuji."""

from dataclasses import dataclass
from hashlib import sha256

from agent_framework import AgentSession, Content

from wuji_core.contracts.sessions import (
    BoundaryObject, BoundaryObjects, MemoryFile, MemoryManifestRoot,
    ModelFrontierEntry, NativeCallBinding, OperationFrontier, ProviderStateRoot,
    PublishedSession, RejectedCallFrontierEntry, SessionCompatibility,
    SessionLimits, ToolFrontierEntry, native_rejection_content,
)
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_maf_worker.approvals import extract_approval_requests, validate_pending
from wuji_maf_worker.history import VersionedMemoryStore, digest, locate_content


def _ref_key(ref):
    body = ref.model_dump(mode="json")
    return body["id"] + "@" + body["version"]


def _position(messages, message_index, content_index):
    from wuji_core.contracts.sessions import MessagePosition

    message = messages[message_index]
    return MessagePosition(
        message_index=message_index, content_index=content_index,
        message_digest=digest(message),
        content_digest=digest(message["contents"][content_index]),
        native_message_id=message.get("message_id"),
    )


def _positions(observed, messages):
    """Relate actual archived messages to the native annotated working history."""
    found = {}
    for source in observed:
        for index, message in enumerate(messages):
            same_id = source.get("message_id") and source.get("message_id") == message.get("message_id")
            same_contents = {
                item.get("id") for item in source.get("contents", []) if item.get("id")
            } & {item.get("id") for item in message.get("contents", []) if item.get("id")}
            if same_id or same_contents or digest(source) == digest(message):
                for offset, _ in enumerate(message.get("contents", [])):
                    found[(index, offset)] = _position(messages, index, offset)
    if not found:
        raise ValueError("an observed model response has no fixed native history position")
    return tuple(found[key] for key in sorted(found))


def _rejected_entry(history, binding, *, approval_ref, decision_version):
    expected = native_rejection_content(binding.provider_call_id)
    matches = []
    for index, message in enumerate(history.messages):
        if message.get("role") != "tool":
            continue
        for offset, content in enumerate(message.get("contents", [])):
            if content == expected:
                matches.append((index, offset, content))
    if len(matches) != 1:
        raise ValueError("native rejection result is missing or ambiguous")
    index, offset, content = matches[0]
    return RejectedCallFrontierEntry(
        approval_ref=approval_ref,
        decision_version=decision_version,
        call_binding=binding,
        result_position=_position(history.messages, index, offset),
        result_content=content,
        result_digest=digest(content),
    )


@dataclass(frozen=True)
class RestoredNativeSession:
    """Local public SDK objects, never a substitute for a PublishedSession DTO."""

    session: AgentSession
    pending_contents: tuple
    call_bindings: tuple
    history: object
    memory: VersionedMemoryStore | None
    published: PublishedSession


class NativeSessionAdapter:
    def __init__(self, *, compatibility, limits):
        self.compatibility = SessionCompatibility.model_validate(compatibility)
        self.limits = SessionLimits.model_validate(limits)

    def _bounded(self, body):
        if len(canonical_json_bytes(body)) > self.limits.max_object_bytes:
            raise ValueError("native root exceeds the fixed object bound")

    def _frontier(self, history, bindings, receipts, pending, rejections):
        models = {}
        tools = {}
        prior_rejections = ()
        prior = getattr(history, "published", None)
        if prior is not None:
            for entry in prior.history.frontier.model_entries:
                originals = [prior.history.messages[p.message_index] for p in entry.positions]
                models[entry.model_attempt_id] = entry.model_copy(update={
                    "positions": _positions(originals, history.messages),
                })
            tools = {entry.tool_call_id: entry for entry in prior.history.frontier.tool_entries}
            prior_rejections = prior.history.frontier.rejected_calls
        for attempt, originals in history.model_observations.items():
            models[attempt] = ModelFrontierEntry(
                model_attempt_id=attempt,
                positions=_positions(
                    [m for m in originals.values() if m.get("role") == "assistant"],
                    history.messages,
                ),
            )  # Canonical Gate hashes are supplied and verified by Host.stage_session.
        by_call = {binding.tool_call_id: binding for binding in bindings if binding.tool_call_id}
        for receipt in receipts:
            body = receipt.model_dump(mode="json")
            if body["status"] != "complete" or body["tool_attempt_id"] is None:
                raise ValueError("unsettled tool result cannot enter a native boundary")
            tools[body["tool_call_id"]] = ToolFrontierEntry(
                tool_call_id=body["tool_call_id"], tool_attempt_id=body["tool_attempt_id"],
                positions=(), receipt=body, receipt_digest=digest(body),
            )
        for call_id, entry in tuple(tools.items()):
            binding = by_call.get(call_id)
            if binding is None:
                raise ValueError("durable tool receipt has no original native call mapping")
            positions = [binding.position]
            for index, message in enumerate(history.messages):
                for offset, content in enumerate(message.get("contents", [])):
                    if content.get("type") == "function_result" and content.get("call_id") == binding.provider_call_id:
                        positions.append(_position(history.messages, index, offset))
            if len(positions) != 2 or any(position is None for position in positions):
                raise ValueError("tool request/result pairing is missing or ambiguous")
            tools[call_id] = entry.model_copy(update={"positions": tuple(positions)})
        rejected = {}
        for entry in prior_rejections:
            binding = by_call.get(entry.call_binding.tool_call_id)
            if binding is None:
                raise ValueError("published rejection lost its original call binding")
            rejected[binding.tool_call_id] = _rejected_entry(
                history,
                binding,
                approval_ref=entry.approval_ref,
                decision_version=entry.decision_version,
            )
        for decision in rejections:
            binding = NativeCallBinding.model_validate(decision.call_binding)
            if (
                decision.decision != "reject"
                or binding.tool_call_id in rejected
                or binding.tool_call_id in tools
            ):
                raise ValueError("rejected call is duplicated or has an execution receipt")
            rejected[binding.tool_call_id] = _rejected_entry(
                history,
                binding,
                approval_ref=decision.approval_ref,
                decision_version=decision.decision_version,
            )
        pending_ids = {content.id for content in pending}
        return OperationFrontier(
            model_entries=tuple(models.values()), tool_entries=tuple(tools.values()),
            pending_approvals=tuple(b for b in bindings if b.sdk_approval_id in pending_ids),
            rejected_calls=tuple(rejected.values()),
            archived_history_refs=() if prior is None else prior.history.frontier.archived_history_refs,
        )

    def export_boundary(self, *, session, response, history, call_bindings,
                        tool_receipts, memory, recovery_class, observed_at,
                        rejection_decisions=()):
        if not isinstance(session, AgentSession) or recovery_class not in {"settled_boundary", "approval_boundary"}:
            raise ValueError("only observed public native boundaries can be published")
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("the actual boundary observation time must include its zone")
        bindings = tuple(NativeCallBinding.model_validate(value) for value in call_bindings)
        bindings = tuple(binding.model_copy(update={
            "position": locate_content(history.messages, binding.sdk_content_id),
        }) for binding in bindings)
        pending = extract_approval_requests(response, call_bindings=bindings)
        if (recovery_class == "approval_boundary") != bool(pending):
            raise ValueError("recovery class differs from the actual native response")
        if len(pending) > self.limits.max_pending_approvals:
            raise ValueError("native approval batch exceeds the fixed limit")
        if any(binding.tool_call_id is None for binding in bindings):
            raise ValueError("native calls must first receive a canonical ToolGate identity")
        if response.continuation_token is not None:
            raise ValueError("unfinished native continuation is not a restorable boundary")
        history.frontier = self._frontier(
            history,
            bindings,
            tool_receipts,
            pending,
            tuple(rejection_decisions),
        )
        root = history.export()
        if root.session_id != session.session_id or root.compatibility != self.compatibility:
            raise ValueError("native Session/history compatibility mismatch")
        scope = {
            "session_id": root.session_id, "session_lineage": root.session_lineage,
            "work_item_id": root.work_item_id, "compatibility": self.compatibility,
        }
        provider = ProviderStateRoot(
            **scope, session_state=session.to_dict(),
            pending_contents=tuple(content.to_dict() for content in pending),
            call_bindings=bindings,
        )
        objects = [BoundaryObject(
            key="history-archive", media_type="application/json",
            data=canonical_json_bytes({
                "schema_version": "wuji.session.history-archive.v1",
                "messages": tuple(history.observations.values()),
            }),
        )]
        files = []
        if memory is not None:
            if not isinstance(memory, VersionedMemoryStore):
                raise TypeError("memory must be a bounded publication-owned AgentFileStore")
            for path, data in memory.snapshot_files().items():
                key = "memory-" + sha256(path.encode("utf-8")).hexdigest()
                files.append(MemoryFile(path=path, object_key=key))
                objects.append(BoundaryObject(key=key, data=data, media_type="text/plain; charset=utf-8"))
        memory_root = MemoryManifestRoot(**scope, enabled=memory is not None, files=tuple(files))
        expected_memory = self.compatibility.profile_snapshot["body"]["memory_mode"] != "disabled"
        if memory_root.enabled != expected_memory:
            raise ValueError("memory does not match the fixed Session Profile")
        roots = (root, provider, memory_root)
        for value in roots:
            self._bounded(value.model_dump(mode="python"))
        total = sum(len(canonical_json_bytes(value.model_dump(mode="python"))) for value in roots)
        total += sum(len(obj.data) for obj in objects)
        if (
            len(objects) + 3 > self.limits.max_objects
            or any(len(obj.data) > self.limits.max_object_bytes for obj in objects)
            or total > self.limits.max_total_bytes
        ):
            raise ValueError("complete native export exceeds fixed object/byte bounds")
        return BoundaryObjects(history=root, provider_state=provider, memory=memory_root, objects=tuple(objects))

    def restore_boundary(self, published: PublishedSession):
        if not isinstance(published, PublishedSession):
            raise TypeError("restore requires Host.load_session's checked PublishedSession")
        check, receipt, manifest = published.recovery_check, published.receipt, published.manifest
        manifest_body = manifest.model_dump(mode="json")
        if (
            check is None or not check.resumable
            or check.manifest_ref != receipt.manifest_ref
            or check.checkpoint_revision != receipt.checkpoint_revision
            or check.session_id != receipt.session_id
            or check.session_lineage != published.history.session_lineage
            or check.frontier_digest != digest(published.history.frontier.model_dump(mode="python"))
            or manifest_body["recovery_class"] not in {"settled_boundary", "approval_boundary"}
            or manifest_body["checkpoint_revision"] != receipt.checkpoint_revision
            or manifest_body["message_end"] != str(published.history.message_end)
            or digest(manifest_body) != receipt.manifest_digest
            or manifest_body["lock_digest"] != self.compatibility.lock_digest
        ):
            raise ValueError("the published boundary lacks a matching recovery check")
        roots = (published.history, published.provider_state, published.memory)
        expected_memory = self.compatibility.profile_snapshot["body"]["memory_mode"] != "disabled"
        if published.memory.enabled != expected_memory:
            raise ValueError("published memory differs from the fixed Session Profile")
        refs = (manifest.history_root, manifest.provider_state_ref, manifest.memory_manifest_ref)
        for root, ref in zip(roots, refs, strict=True):
            body = canonical_json_bytes(root.model_dump(mode="python"))
            if (
                root.compatibility != self.compatibility
                or root.session_id != receipt.session_id
                or root.work_item_id != manifest.work_item_id
                or root.session_lineage != check.session_lineage
                or sha256(body).hexdigest() != ref.model_dump(mode="json")["sha256"]
                or published.object_bytes.get(_ref_key(ref)) != body
            ):
                raise ValueError("loaded native root is not the fixed published object")
        if len(published.object_refs) > self.limits.max_objects:
            raise ValueError("published object count exceeds the fixed limits")
        total = 0
        for ref in published.object_refs:
            data = published.object_bytes.get(_ref_key(ref))
            if data is None or sha256(data).hexdigest() != ref.model_dump(mode="json")["sha256"]:
                raise ValueError("missing or corrupt immutable Session object")
            if len(data) > self.limits.max_object_bytes:
                raise ValueError("published object exceeds the fixed byte limit")
            total += len(data)
        if total > self.limits.max_total_bytes:
            raise ValueError("published Session exceeds the total byte limit")
        session = AgentSession.from_dict(published.provider_state.session_state)
        if session.session_id != receipt.session_id:
            raise ValueError("restored SDK Session differs from its publication")
        source_id = self.compatibility.profile_snapshot["body"]["history_source_id"]
        stored = session.state.get(source_id, {}).get("messages", [])
        if canonical_json_bytes([message.to_dict() for message in stored]) != canonical_json_bytes(published.history.messages):
            raise ValueError("native provider state differs from the fixed complete history")
        pending = tuple(Content.from_dict(body) for body in published.provider_state.pending_contents)
        bindings = published.provider_state.call_bindings
        by_id = {binding.sdk_approval_id: binding for binding in bindings if binding.sdk_approval_id}
        for content in pending:
            if content.id not in by_id:
                raise ValueError("restored approval has no published original call")
            validate_pending(content, by_id[content.id])
        if {content.id for content in pending} != {b.sdk_approval_id for b in published.history.frontier.pending_approvals}:
            raise ValueError("native pending contents differ from the operation frontier")
        files = {}
        for item in published.memory.files:
            if item.ref is None or item.object_key is not None:
                raise ValueError("memory contains unpublished mutable keys")
            files[item.path] = published.object_bytes[_ref_key(item.ref)]
        memory = VersionedMemoryStore(limits=self.limits, files=files) if published.memory.enabled else None
        return RestoredNativeSession(session, pending, bindings, published.history, memory, published)
