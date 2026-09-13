"""Immutable, fully pinned native boundaries over the canonical P03/P05/P06 rows."""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from wuji_core.admission.common import current_run, digest
from wuji_core.contracts.envelopes import BlobRef, WorkerAssignment
from wuji_core.contracts.execution import SessionManifest
from wuji_core.contracts.sessions import (
    BoundaryObjects, InputPayload, MessagePosition, ModelFrontierEntry,
    NativeCallBinding,
    OperationFrontier,
    PublishedHistoryRoot, PublishedMemoryManifestRoot, PublishedProviderStateRoot,
    PublishedSession, RecoveryCheck, SessionReceipt, StagedSessionObjects,
    native_rejection_content,
)
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.http.json_boundary import InvalidJsonDocument
from wuji_core.persistence.uow import DomainError, json_text, row


SESSION_OBJECT_ROLES = {
    "dependency",
    "archive",
    "model_response",
    "native_arguments",
    "history_root",
    "provider_root",
    "memory_root",
}


def rows(cursor):
    names = [c.name for c in cursor.description]
    return [dict(zip(names, value)) for value in cursor.fetchall()]


def ref_key(ref):
    return ref.id + "@" + ref.version.root


def document(value):
    if isinstance(value, (SessionManifest, SessionReceipt)):
        return value.model_dump(mode="json")
    return value.model_dump(mode="python") if hasattr(value, "model_dump") else value


def equal(left, right):
    return canonical_json_bytes(document(left)) == canonical_json_bytes(document(right))


def unique_refs(refs):
    found = {}
    for ref in refs:
        ref = BlobRef.model_validate(ref)
        previous = found.get(ref_key(ref))
        if previous is not None and previous != ref:
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        found[ref_key(ref)] = ref
    return tuple(found[key] for key in sorted(found))


def work_row(tx, work_id, *, lock=True):
    result = row(tx.connection.execute(
        "SELECT * FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s"
        + (" FOR UPDATE" if lock else ""), (*tx.owner, work_id),
    ))
    if result is None:
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")
    return result


def check_position(history, position):
    if position is None or position.message_index >= history.message_end:
        raise DomainError("INVALID_REFERENCE", 422)
    message = history.messages[position.message_index]
    contents = message.get("contents", [])
    if (position.content_index >= len(contents)
            or digest(message) != position.message_digest
            or digest(contents[position.content_index]) != position.content_digest
            or (position.native_message_id is not None and message.get("message_id") != position.native_message_id)):
        raise DomainError("INPUT_DIGEST_CONFLICT", 409)
    return contents[position.content_index]


def content_versions(history, position, archives):
    current = check_position(history, position)
    message = history.messages[position.message_index]
    versions = [current]
    for original in archives:
        same_message = bool(message.get("message_id")) and original.get("message_id") == message["message_id"]
        for index, content in enumerate(original.get("contents", [])):
            same_content = bool(current.get("id")) and content.get("id") == current["id"]
            if (same_content or (same_message and index == position.content_index)) and content.get("type") == current.get("type"):
                if current.get("call_id") != content.get("call_id"):
                    continue
                versions.append(content)
    return versions


def request_predecessor_positions(history, request_messages):
    """Map provider-wire operation messages to unique earlier native positions."""

    positions = {}
    for request in request_messages:
        expected = []
        if request.get("role") == "assistant":
            for call in request.get("tool_calls", []):
                expected.append(("function_call", call.get("id"), call.get("function")))
        elif request.get("role") == "tool":
            expected.append(("function_result", request.get("tool_call_id"), request.get("content")))
        for kind, call_id, wire in expected:
            matches = []
            for message_index, message in enumerate(history.messages):
                for content_index, content in enumerate(message.get("contents", [])):
                    native = content.get("function_call", content)
                    if native.get("call_id") != call_id or native.get("type") != kind:
                        continue
                    if kind == "function_call":
                        arguments = native.get("arguments")
                        if not isinstance(arguments, str):
                            arguments = canonical_json_bytes(arguments).decode()
                        if not isinstance(wire, dict) or wire.get("name") != native.get("name") or wire.get("arguments") != arguments:
                            continue
                    else:
                        result = native.get("result")
                        if isinstance(result, str):
                            try:
                                result = strict_json_loads(result)
                            except (InvalidJsonDocument, ValueError):
                                pass
                        supplied = wire
                        if isinstance(supplied, str):
                            try:
                                supplied = strict_json_loads(supplied)
                            except (InvalidJsonDocument, ValueError):
                                pass
                        if result != supplied:
                            continue
                    matches.append((
                        content.get("type") != kind,
                        message_index,
                        content_index,
                    ))
            if matches:
                matches.sort()
                matches = [match for match in matches if match[0] == matches[0][0]]
            if len(matches) != 1:
                raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
            _wrapped, message_index, content_index = matches[0]
            position = MessagePosition(
                message_index=message_index,
                content_index=content_index,
                message_digest=digest(history.messages[message_index]),
                content_digest=digest(
                    history.messages[message_index]["contents"][content_index]
                ),
                native_message_id=history.messages[message_index].get("message_id"),
            )
            positions[(message_index, content_index)] = position
    return tuple(positions[key] for key in sorted(positions))


def provider_messages(body, content_type):
    """Read stored native protocol bytes. This is no SDK loop or synthetic reply."""
    if "text/event-stream" not in (content_type or ""):
        data = strict_json_loads(body)
        return {c["index"]: c["message"] for c in data.get("choices", [])}
    messages, done = {}, False
    for frame in body.replace(b"\r\n", b"\n").split(b"\n\n"):
        payload = b"\n".join(line[5:].lstrip(b" ") for line in frame.split(b"\n") if line.startswith(b"data:"))
        if not payload:
            continue
        if payload == b"[DONE]":
            done = True
            continue
        if done:
            raise DomainError("INVALID_REFERENCE", 422)
        parsed = strict_json_loads(payload)
        for choice in parsed.get("choices", []):
            item = messages.setdefault(choice["index"], {"content": "", "tool_calls": {}})
            delta = choice.get("delta", {})
            if delta.get("content") is not None:
                item["content"] += delta["content"]
            for call in delta.get("tool_calls", []):
                target = item["tool_calls"].setdefault(call["index"], {"id": "", "function": {"name": "", "arguments": ""}})
                if call.get("id"):
                    if target["id"] and target["id"] != call["id"]:
                        raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                    target["id"] = call["id"]
                for name in ("name", "arguments"):
                    if call.get("function", {}).get(name):
                        target["function"][name] += call["function"][name]
    if not done:
        raise DomainError("OPERATION_UNKNOWN", 409)
    return {k: {**v, "tool_calls": list(v["tool_calls"].values())} for k, v in messages.items()}


class SessionRepository:
    def __init__(self, uow, *, artifacts, registry):
        self.uow, self.artifacts, self.registry = uow, artifacts, registry

    def capability(self, tx, history):
        capability = self.registry.session_capability(tx, history.compatibility.profile_snapshot)
        if not equal(capability["compatibility"], history.compatibility):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        if (history.message_end > capability["limits"].max_messages
                or len(history.frontier.pending_approvals) > capability["limits"].max_pending_approvals):
            raise DomainError("LIMIT_BLOCKED", 429)
        return capability

    def _writer(self, access, assignment):
        binding = self.registry.binding(access)
        if binding.identity != assignment.identity or "worker" not in access.principal.roles or "agent" in access.principal.roles:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        return binding

    def receiver(self, tx, assignment):
        """Match the controller to its registered receiver; observe ACL alone is insufficient."""
        if tx.purpose != "observe":
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        stored = row(tx.connection.execute(
            "SELECT a.assignment_json,r.* FROM vnext.scheduler_assignment a JOIN vnext.agent_run r USING(tenant_id,project_id,task_id,agent_run_id) WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s AND a.operation_id=%s",
            (*tx.owner, assignment.operation_id),
        ))
        if stored is None or not equal(strict_json_loads(stored["assignment_json"]), assignment):
            raise DomainError("STALE_EXECUTION", 409)
        receiver = row(tx.connection.execute(
            "SELECT * FROM vnext.scheduler_receiver WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND receiver_id=%s AND runtime_attempt=%s AND enabled",
            (*tx.owner, assignment.identity.receiver_id, assignment.identity.runtime_attempt.root),
        ))
        if receiver is None or receiver["receiver_subject"] != tx.access.principal.subject:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        return stored

    def _model(self, tx, history, attempt_id):
        record = row(tx.connection.execute(
            "SELECT m.*,r.work_item_id FROM vnext.model_call m JOIN vnext.agent_run r USING(tenant_id,project_id,task_id,agent_run_id) WHERE m.tenant_id=%s AND m.project_id=%s AND m.task_id=%s AND m.model_attempt_id=%s AND m.access_level<=%s",
            (*tx.owner, attempt_id, tx.permissions["clearance"]),
        ))
        if record is None or record["work_item_id"] != history.work_item_id:
            raise DomainError("INVALID_REFERENCE", 422)
        if (record["inflight"] or record["local_state"] != "ended" or record["response_state"] != "complete"
                or record["send_state"] != "sent" or not record["response_available"] or record["upstream_status"] != 200):
            raise DomainError("OPERATION_UNKNOWN", 409)
        parts = tx.connection.execute(
            "SELECT ordinal,data FROM vnext.model_response_chunk WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND model_attempt_id=%s ORDER BY ordinal",
            (*tx.owner, attempt_id),
        ).fetchall()
        if not parts or [p[0] for p in parts] != list(range(len(parts))):
            raise DomainError("INVALID_REFERENCE", 422)
        body = b"".join(bytes(p[1]) for p in parts)
        if len(body) != record["retained_bytes"] or len(body) > self.artifacts.max_bytes:
            raise DomainError("LIMIT_BLOCKED", 429)
        original_request = strict_json_loads(record["request_json"])
        original_request["model"] = strict_json_loads(record["profile_json"])["model"]["client_model"]
        if digest(original_request) != record["input_digest"]:
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        return (
            record,
            body,
            provider_messages(body, record["content_type"]),
            original_request,
        )

    def _check_call(self, tx, history, binding, provider):
        if binding.message_id != "model-attempt:" + binding.model_attempt_id + ":choice:0":
            raise DomainError("INVALID_REFERENCE", 422)
        definition = self.registry.tool(tx, binding.tool_definition_ref)
        native = [c for c in provider.get(0, {}).get("tool_calls", []) if c["id"] == binding.provider_call_id]
        if (len(native) != 1 or native[0]["function"]["name"] != definition.name
                or native[0]["function"]["arguments"] != binding.native_arguments):
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        arguments = strict_json_loads(binding.native_arguments)
        if digest(arguments) != binding.arguments_digest:
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        content = check_position(history, binding.position)
        call_content = content.get("function_call") if content.get("type") == "function_approval_request" else content
        if (not isinstance(call_content, dict) or call_content.get("id") != binding.sdk_content_id
                or call_content.get("call_id") != binding.provider_call_id or call_content.get("name") != definition.name):
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        original = call_content.get("arguments")
        if isinstance(original, str):
            original = strict_json_loads(original)
        if not equal(original, arguments):
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        call = row(tx.connection.execute(
            "SELECT * FROM vnext.tool_call WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND session_lineage=%s AND message_id=%s AND provider_call_id=%s AND tool_definition_version=%s AND access_level<=%s",
            (*tx.owner, history.session_lineage, binding.message_id, binding.provider_call_id, binding.tool_definition_ref, tx.permissions["clearance"]),
        ))
        if call is None or call["work_item_id"] != history.work_item_id:
            raise DomainError("INVALID_REFERENCE", 422)
        if binding.tool_call_id is not None and call["tool_call_id"] != binding.tool_call_id:
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        request = strict_json_loads(call["request_json"])
        if (request["sdk_content_id"] != binding.sdk_content_id
                or request.get("sdk_approval_id") != binding.sdk_approval_id or not equal(request["arguments"], arguments)):
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        return call

    def _tool(self, tx, history, entry, archives=()):
        value = row(tx.connection.execute(
            "SELECT a.*,c.work_item_id,c.session_lineage,c.latest_attempt_id,c.request_json,c.status AS call_status FROM vnext.tool_attempt a JOIN vnext.tool_call c USING(tenant_id,project_id,task_id,tool_call_id) WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s AND a.tool_attempt_id=%s AND c.access_level<=%s",
            (*tx.owner, entry.tool_attempt_id, tx.permissions["clearance"]),
        ))
        if (value is None or value["tool_call_id"] != entry.tool_call_id or value["work_item_id"] != history.work_item_id
                or value["session_lineage"] != history.session_lineage or value["status"] != "complete"
                or value["call_status"] != "complete" or not value["result_receipt_json"]):
            raise DomainError("OPERATION_UNKNOWN", 409)
        receipt = strict_json_loads(value["result_receipt_json"])
        if not equal(receipt, entry.receipt) or receipt.get("evidence_receipt", {}).get("status") != "accepted":
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        matched = False
        request = strict_json_loads(value["request_json"])
        for position in entry.positions:
            content = check_position(history, position)
            if content.get("type") != "function_result" or content.get("call_id") != request["provider_call_id"]:
                continue
            for candidate in content_versions(history, position, archives):
                result = candidate.get("result")
                if isinstance(result, str):
                    try:
                        result = strict_json_loads(result)
                    except ValueError:
                        continue  # Native working-history compaction may replace it.
                if equal(result, receipt):
                    matched = True
        if not matched:
            raise DomainError("INVALID_REFERENCE", 422)
        return value, receipt

    def _stage(self, access, assignment, data, media_type, refs, role, level, lease):
        ref = self.artifacts.stage_model_output(access, assignment.identity.task_id,
            assignment.identity.agent_run_id, data, media_type, access_level=level)
        self.artifacts.seal(access, assignment.identity.task_id, ref)
        self.artifacts.acquire_lease(access, assignment.identity.task_id, ref, lease_owner=lease)
        with self.uow.transaction(access, assignment.identity.task_id, capability="model_output") as tx:
            tx.connection.execute(
                "INSERT INTO vnext.session_object(tenant_id,project_id,task_id,artifact_id,artifact_revision,agent_run_id,writer_token_id,role,refs_json,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (*tx.owner, ref.id, ref.version.root, assignment.identity.agent_run_id, access.principal.token_id, role,
                 json_text([document(r) for r in unique_refs(refs)]), level),
            )
        return ref

    def stage_objects(self, worker_access, assignment, objects):
        assignment = WorkerAssignment.model_validate(assignment)
        objects = BoundaryObjects.model_validate(objects).model_copy(deep=True)
        binding = self._writer(worker_access, assignment)
        history, provider, memory = objects.history, objects.provider_state, objects.memory
        for root in (history, provider, memory):
            if (root.work_item_id != assignment.identity.work_item_id or root.session_id != history.session_id
                    or root.session_lineage != binding.session_lineage or not equal(root.compatibility, history.compatibility)):
                raise DomainError("INVALID_REFERENCE", 422)
        if history.snapshot_id != assignment.snapshot_id or provider.session_state.get("session_id") != history.session_id:
            raise DomainError("INVALID_REFERENCE", 422)
        with self.uow.transaction(worker_access, assignment.identity.task_id, capability="tool_request") as tx:
            current_run(tx, self.registry.config(tx))
            capability = self.capability(tx, history)
            level = tx.permissions["clearance"]
            models = {}
            for entry in history.frontier.model_entries:
                if entry.model_attempt_id in models or not entry.positions:
                    raise DomainError("INVALID_REFERENCE", 422)
                record, raw, protocol, request = self._model(tx, history, entry.model_attempt_id)
                for position in entry.positions:
                    check_position(history, position)
                models[entry.model_attempt_id] = (record, raw, protocol, request)
            calls = []
            for call in provider.call_bindings:
                if call.model_attempt_id not in models:
                    raise DomainError("INVALID_REFERENCE", 422)
                value = self._check_call(tx, history, call, models[call.model_attempt_id][2])
                calls.append(call.model_copy(update={"tool_call_id": value["tool_call_id"]}))
            archive_messages = list(self._archives(tx, history))
            for obj in objects.objects:
                if obj.key == "history-archive":
                    archived = strict_json_loads(obj.data)
                    if archived.get("schema_version") != "wuji.session.history-archive.v1" or not isinstance(archived.get("messages"), list):
                        raise DomainError("INVALID_REFERENCE", 422)
                    archive_messages.extend(archived["messages"])
            tools = []
            for entry in history.frontier.tool_entries:
                _value, receipt = self._tool(tx, history, entry, archive_messages)
                if entry.receipt_digest is not None and entry.receipt_digest != digest(receipt):
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                tools.append(entry.model_copy(update={"receipt_digest": digest(receipt)}))
        limits = capability["limits"]
        if memory.enabled != (capability["memory_mode"] != "disabled"):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        lease = "session-stage:" + str(uuid4())
        refs, objects_by_key, total = [], {}, 0

        def save(data, media_type, children=(), role="dependency"):
            nonlocal total
            total += len(data)
            if len(data) > limits.max_object_bytes or total > limits.max_total_bytes or len(refs) >= limits.max_objects:
                raise DomainError("LIMIT_BLOCKED", 429)
            ref = self._stage(worker_access, assignment, data, media_type, children, role, level, lease)
            refs.append(ref)
            return ref

        archives = list(history.frontier.archived_history_refs)
        for obj in objects.objects:
            if obj.key in objects_by_key:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            if obj.key == "history-archive":
                archive = strict_json_loads(obj.data)
                if archive.get("schema_version") != "wuji.session.history-archive.v1" or not isinstance(archive.get("messages"), list):
                    raise DomainError("INVALID_REFERENCE", 422)
            ref = save(obj.data, obj.media_type, obj.object_refs, "archive" if obj.key == "history-archive" else "dependency")
            objects_by_key[obj.key] = ref
            if obj.key == "history-archive":
                archives.append(ref)
        model_entries, response_refs = [], {}
        for entry in history.frontier.model_entries:
            record, raw, _, request = models[entry.model_attempt_id]
            request_digest, response_digest = record["input_digest"], sha256(raw).hexdigest()
            if ((entry.request_digest is not None and entry.request_digest != request_digest)
                    or (entry.response_digest is not None and entry.response_digest != response_digest)):
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            response_ref = save(raw, record["content_type"], role="model_response")
            response_refs[entry.model_attempt_id] = response_ref
            request_messages = tuple(request.get("messages", ()))
            model_entries.append(entry.model_copy(update={
                "request_digest": request_digest,
                "request_messages": request_messages,
                "request_messages_digest": digest(request_messages),
                "predecessor_positions": request_predecessor_positions(
                    history, request_messages
                ),
                "response_digest": response_digest,
                "response_ref": response_ref,
            }))
        enriched_calls = []
        for call in calls:
            arguments_ref = save(call.native_arguments.encode("utf-8"), "application/json", role="native_arguments")
            enriched_calls.append(call.model_copy(update={"provider_response_ref": response_refs[call.model_attempt_id], "arguments_ref": arguments_ref}))
        observed_by_tool = {call.tool_call_id: call for call in calls}
        enriched_by_tool = {call.tool_call_id: call for call in enriched_calls}
        pending_ids = {call.sdk_content_id for call in history.frontier.pending_approvals}
        enriched_pending = tuple(c for c in enriched_calls if c.sdk_content_id in pending_ids)
        if len(enriched_pending) != len(pending_ids) or len(pending_ids) != len(history.frontier.pending_approvals):
            raise DomainError("INVALID_REFERENCE", 422)
        enriched_rejections = []
        for entry in history.frontier.rejected_calls:
            observed = observed_by_tool.get(entry.call_binding.tool_call_id)
            enriched = enriched_by_tool.get(entry.call_binding.tool_call_id)
            result = check_position(history, entry.result_position)
            if (
                observed is None
                or enriched is None
                or not equal(observed, entry.call_binding)
                or history.messages[entry.result_position.message_index].get("role") != "tool"
                or entry.result_content != result
                or entry.result_digest != digest(result)
                or result != native_rejection_content(observed.provider_call_id)
            ):
                raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
            enriched_rejections.append(
                entry.model_copy(update={"call_binding": enriched})
            )
        files = []
        for file in memory.files:
            if file.object_key is not None:
                if file.object_key not in objects_by_key:
                    raise DomainError("INVALID_REFERENCE", 422)
                files.append(file.model_copy(update={"ref": objects_by_key[file.object_key], "object_key": None}))
            else:
                files.append(file)
        memory_refs = unique_refs([*memory.object_refs, *memory.state_refs, *(f.ref for f in files)])
        memory = PublishedMemoryManifestRoot.model_validate({**document(memory), "files": files, "object_refs": memory_refs})
        provider = PublishedProviderStateRoot.model_validate({**document(provider), "call_bindings": enriched_calls,
            "object_refs": unique_refs([*provider.object_refs, *response_refs.values(), *(c.arguments_ref for c in enriched_calls)])})
        frontier = OperationFrontier(model_entries=tuple(model_entries), tool_entries=tuple(tools),
            pending_approvals=enriched_pending, rejected_calls=tuple(enriched_rejections),
            archived_history_refs=unique_refs(archives))
        evidence_refs = []
        for entry in tools:
            evidence_refs.extend(BlobRef.model_validate(r) for r in entry.receipt["evidence_receipt"]["artifact_refs"])
            evidence_refs.append(BlobRef.model_validate(entry.receipt["result_ref"]))
        history = PublishedHistoryRoot.model_validate({**document(history), "frontier": frontier,
            "object_refs": unique_refs([*history.object_refs, *refs, *archives, *evidence_refs])})
        # Recheck the complete frontier before writing immutable root bytes.
        with self.uow.transaction(worker_access, assignment.identity.task_id, capability="tool_request") as tx:
            current_run(tx, self.registry.config(tx))
            self._frontier(tx, history, provider, allow_pending=True)
        history_ref = save(canonical_json_bytes(document(history)), "application/json", history.object_refs, "history_root")
        provider_ref = save(canonical_json_bytes(document(provider)), "application/json", provider.object_refs, "provider_root")
        memory_ref = save(canonical_json_bytes(document(memory)), "application/json", memory.object_refs, "memory_root")
        with self.uow.transaction(worker_access, assignment.identity.task_id, capability="tool_request") as tx:
            current_run(tx, self.registry.config(tx))
            self._graph(
                tx,
                (history_ref, provider_ref, memory_ref),
                limits,
                work_id=assignment.identity.work_item_id,
                session_id=history.session_id,
                owner_run_id=assignment.identity.agent_run_id,
                source_subject=worker_access.principal.subject,
                source_token_id=worker_access.principal.token_id,
            )
        return StagedSessionObjects(history_root=history_ref, provider_state_ref=provider_ref,
            memory_manifest_ref=memory_ref, object_refs=unique_refs(refs), lease_owner=lease,
            history=history, provider_state=provider, memory=memory)

    def _archives(self, tx, history):
        messages = []
        total = 0
        limits = self.capability(tx, history)["limits"]
        if len(history.frontier.archived_history_refs) > limits.max_objects:
            raise DomainError("LIMIT_BLOCKED", 429)
        for ref in history.frontier.archived_history_refs:
            record = self.artifacts.record(tx, ref)
            if record["state"] != "sealed" or record["access_level"] > tx.permissions["clearance"]:
                raise DomainError("INVALID_REFERENCE", 422)
            body = self.artifacts.checked_bytes(record)
            total += len(body)
            if total > limits.max_total_bytes:
                raise DomainError("LIMIT_BLOCKED", 429)
            archive = strict_json_loads(body)
            if archive.get("schema_version") != "wuji.session.history-archive.v1" or not isinstance(archive.get("messages"), list):
                raise DomainError("INVALID_REFERENCE", 422)
            messages.extend(archive["messages"])
        return tuple(messages)

    def _frontier(self, tx, history, provider, *, allow_pending):
        archives = self._archives(tx, history)
        model_positions = set()
        expected_models = {e.model_attempt_id for e in history.frontier.model_entries}
        actual_models = {r[0] for r in tx.connection.execute(
            "SELECT m.model_attempt_id FROM vnext.model_call m JOIN vnext.agent_run r USING(tenant_id,project_id,task_id,agent_run_id) WHERE m.tenant_id=%s AND m.project_id=%s AND m.task_id=%s AND r.work_item_id=%s",
            (*tx.owner, history.work_item_id),
        ).fetchall()}
        if expected_models != actual_models or len(expected_models) != len(history.frontier.model_entries):
            raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
        for entry in history.frontier.model_entries:
            record, raw, protocol, request = self._model(tx, history, entry.model_attempt_id)
            if (entry.request_digest != record["input_digest"] or entry.response_digest != sha256(raw).hexdigest()
                    or entry.response_ref is None or entry.response_ref.sha256.root != entry.response_digest
                    or tuple(request.get("messages", ())) != entry.request_messages
                    or digest(entry.request_messages) != entry.request_messages_digest
                    or request_predecessor_positions(history, entry.request_messages) != entry.predecessor_positions):
                raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
            if entry.predecessor_positions and max(
                position.message_index for position in entry.predecessor_positions
            ) >= min(position.message_index for position in entry.positions):
                raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
            observed_text, observed_calls = [], set()
            text_options = [""]
            for position in entry.positions:
                coordinate = (position.message_index, position.content_index)
                if coordinate in model_positions:
                    raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
                model_positions.add(coordinate)
                content = check_position(history, position)
                if history.messages[position.message_index].get("role") != "assistant":
                    raise DomainError("INVALID_REFERENCE", 422)
                if content.get("type") == "text":
                    observed_text.append(content.get("text", ""))
                    variants = {item.get("text", "") for item in content_versions(history, position, archives)}
                    text_options = list({left + right for left in text_options for right in variants})
                    if len(text_options) > 128:
                        raise DomainError("LIMIT_BLOCKED", 429)
                if content.get("type") in {"function_call", "function_approval_request"}:
                    native = content.get("function_call", content)
                    observed_calls.add(native.get("call_id"))
            expected = protocol.get(0)
            if expected is None or (expected.get("content") or "") not in text_options:
                raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
            if observed_calls != {call["id"] for call in expected.get("tool_calls", [])}:
                raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
        by_id = {c.tool_call_id: c for c in provider.call_bindings}
        if None in by_id or len(by_id) != len(provider.call_bindings):
            raise DomainError("INVALID_REFERENCE", 422)
        for binding in provider.call_bindings:
            _, raw, protocol, _request = self._model(tx, history, binding.model_attempt_id)
            self._check_call(tx, history, binding, protocol)
            if (binding.arguments_ref is None or binding.arguments_ref.sha256.root != sha256(binding.native_arguments.encode()).hexdigest()
                    or binding.provider_response_ref is None or binding.provider_response_ref.sha256.root != sha256(raw).hexdigest()):
                raise DomainError("INVALID_REFERENCE", 422)
        tool_entries = {e.tool_attempt_id: e for e in history.frontier.tool_entries}
        actual_attempts = {r[0] for r in tx.connection.execute(
            "SELECT a.tool_attempt_id FROM vnext.tool_attempt a JOIN vnext.agent_run r USING(tenant_id,project_id,task_id,agent_run_id) WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s AND r.work_item_id=%s",
            (*tx.owner, history.work_item_id),
        ).fetchall()}
        if set(tool_entries) != actual_attempts or len(tool_entries) != len(history.frontier.tool_entries):
            raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
        for entry in tool_entries.values():
            _, receipt = self._tool(tx, history, entry, archives)
            if digest(receipt) != entry.receipt_digest or entry.tool_call_id not in by_id:
                raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
            evidence = receipt["evidence_receipt"]
            stored = tx.connection.execute(
                "SELECT receipt_json FROM vnext.evidence_receipt WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND capture_id=%s AND access_level<=%s",
                (*tx.owner, evidence["capture_id"], tx.permissions["clearance"]),
            ).fetchone()
            if stored is None or not equal(strict_json_loads(stored[0]), evidence):
                raise DomainError("INVALID_REFERENCE", 422)
        pending = {b.tool_call_id: b for b in history.frontier.pending_approvals}
        rejected = {e.call_binding.tool_call_id: e for e in history.frontier.rejected_calls}
        native_pending = {c.get("id"): c for c in provider.pending_contents}
        if (
            len(native_pending) != len(provider.pending_contents)
            or len(pending) != len(history.frontier.pending_approvals)
            or None in rejected
            or len(rejected) != len(history.frontier.rejected_calls)
            or set(rejected) & (set(pending) | {e.tool_call_id for e in tool_entries.values()})
        ):
            raise DomainError("INVALID_REFERENCE", 422)
        if (bool(pending) and not allow_pending) or set(native_pending) != {b.sdk_approval_id for b in pending.values()}:
            raise DomainError("INVALID_REFERENCE", 422)
        calls = rows(tx.connection.execute(
            "SELECT * FROM vnext.tool_call WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
            (*tx.owner, history.work_item_id),
        ))
        if {c["tool_call_id"] for c in calls} != set(by_id):
            raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
        for tool_call_id, entry in rejected.items():
            result = check_position(history, entry.result_position)
            approval = row(tx.connection.execute(
                """SELECT a.*,d.status AS delivery_status,d.receiving_run_id,
                d.payload_json,i.status AS input_status
                FROM vnext.approval_request a
                JOIN vnext.input_delivery d USING(tenant_id,project_id,task_id,input_request_id)
                JOIN vnext.input_request i USING(tenant_id,project_id,task_id,input_request_id)
                WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s
                  AND a.approval_ref=%s AND a.tool_call_id=%s""",
                (*tx.owner, entry.approval_ref, tool_call_id),
            ))
            if approval is None:
                raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
            payload = InputPayload.model_validate(
                strict_json_loads(approval["payload_json"])
            )
            decisions = [
                decision
                for decision in payload.decisions
                if decision.approval_ref == entry.approval_ref
            ]
            holder = tx.connection.execute(
                """SELECT 1 FROM vnext.session_holder
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                  AND agent_run_id=%s AND manifest_ref=%s AND session_lineage=%s""",
                (*tx.owner, approval["receiving_run_id"], approval["manifest_ref"],
                 history.session_lineage),
            ).fetchone()
            if (
                approval["decision"] != "reject"
                or approval["decision_status"] != "decided"
                or str(approval["version"]) != entry.decision_version
                or approval["input_status"] != "resolved"
                or approval["delivery_status"] != "delivered"
                or holder is None
                or len(decisions) != 1
                or decisions[0].decision != "reject"
                or str(decisions[0].decision_version) != entry.decision_version
                or not equal(decisions[0].call_binding, entry.call_binding)
                or not equal(strict_json_loads(approval["binding_json"]), entry.call_binding)
                or history.messages[entry.result_position.message_index].get("role") != "tool"
                or result != entry.result_content
                or digest(result) != entry.result_digest
                or result != native_rejection_content(entry.call_binding.provider_call_id)
            ):
                raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
        consumed_positions = {
            (position.message_index, position.content_index)
            for model_entry in history.frontier.model_entries
            for position in model_entry.predecessor_positions
        }
        for tool_entry in history.frontier.tool_entries:
            results = [
                position
                for position in tool_entry.positions
                if check_position(history, position).get("type") == "function_result"
            ]
            if len(results) != 1 or (
                results[0].message_index,
                results[0].content_index,
            ) not in consumed_positions:
                raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
        for rejected_entry in history.frontier.rejected_calls:
            if (
                rejected_entry.result_position.message_index,
                rejected_entry.result_position.content_index,
            ) not in consumed_positions:
                raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
        for call in calls:
            binding = by_id[call["tool_call_id"]]
            if call["tool_call_id"] in pending:
                original_content = native_pending.get(binding.sdk_approval_id, {})
                at_position = check_position(history, binding.position)
                was_rejected = call["status"] == "cancelled" and tx.connection.execute(
                    "SELECT 1 FROM vnext.approval_request WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_call_id=%s AND decision='reject' AND decision_status='decided'",
                    (*tx.owner, call["tool_call_id"]),
                ).fetchone()
                if (not equal(binding, pending[call["tool_call_id"]]) or call["latest_attempt_id"] is not None
                        or (call["status"] != "pending_approval" and not was_rejected)
                        or not (equal(at_position, original_content)
                                or equal(at_position, original_content.get("function_call")))):
                    raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
            elif call["latest_attempt_id"] not in tool_entries:
                # A native rejection has no fake ToolAttempt or successful tool result.
                if (
                    call["tool_call_id"] not in rejected
                    or call["status"] != "cancelled"
                    or call["latest_attempt_id"] is not None
                ):
                    raise DomainError("SESSION_FRONTIER_MISMATCH", 409)
        source_id = history.compatibility.profile_snapshot["body"]["history_source_id"]
        saved_history = provider.session_state.get("state", {}).get(source_id, {}).get("messages")
        if saved_history is None or not equal(saved_history, history.messages):
            raise DomainError("INVALID_REFERENCE", 422)

    def _graph(self, tx, roots, limits, *, publication_id=None, work_id=None,
               session_id=None, owner_run_id=None, source_subject=None,
               source_token_id=None):
        records, bodies, seen, visiting, total = {}, {}, set(), set(), 0

        def visit(ref, depth):
            nonlocal total
            key = ref_key(ref)
            if key in visiting or depth > limits.max_reference_depth:
                raise DomainError("INVALID_REFERENCE", 422)
            if key in seen:
                if records[key]["sha256"] != ref.sha256.root:
                    raise DomainError("INVALID_REFERENCE", 422)
                return
            if len(seen) >= limits.max_objects:
                raise DomainError("LIMIT_BLOCKED", 429)
            visiting.add(key)
            record = self.artifacts.record(tx, ref)
            if record["state"] != "sealed" or record["access_level"] > tx.permissions["clearance"]:
                raise DomainError("INVALID_REFERENCE", 422)
            data = self.artifacts.checked_bytes(record)
            total += len(data)
            if len(data) > limits.max_object_bytes or total > limits.max_total_bytes:
                raise DomainError("LIMIT_BLOCKED", 429)
            metadata = row(tx.connection.execute(
                "SELECT * FROM vnext.session_object WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND artifact_id=%s AND artifact_revision=%s",
                (*tx.owner, ref.id, ref.version.root),
            ))
            if publication_id is not None:
                pin = tx.connection.execute(
                    "SELECT 1 FROM vnext.publication_ref WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND publication_id=%s AND artifact_id=%s AND artifact_revision=%s",
                    (*tx.owner, publication_id, ref.id, ref.version.root),
                ).fetchone()
                if pin is None:
                    raise DomainError("INVALID_REFERENCE", 422)
            else:
                ancestor = tx.connection.execute(
                    "SELECT 1 FROM vnext.session_manifest s JOIN vnext.publication_ref p USING(tenant_id,project_id,task_id,publication_id) WHERE s.tenant_id=%s AND s.project_id=%s AND s.task_id=%s AND s.session_id=%s AND s.work_item_id=%s AND p.artifact_id=%s AND p.artifact_revision=%s",
                    (*tx.owner, session_id, work_id, ref.id, ref.version.root),
                ).fetchone()
                evidence = tx.connection.execute(
                    "SELECT 1 FROM vnext.tool_attempt a JOIN vnext.agent_run r USING(tenant_id,project_id,task_id,agent_run_id) WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s AND a.tool_attempt_id=%s AND r.work_item_id=%s",
                    (*tx.owner, record["tool_attempt_id"], work_id),
                ).fetchone() if record["tool_attempt_id"] else None
                if not ancestor and not evidence:
                    if (
                        record["agent_run_id"] != owner_run_id
                        or record["provenance"] != "model_output"
                        or metadata is None
                        or metadata["agent_run_id"] != owner_run_id
                        or metadata["role"] not in SESSION_OBJECT_ROLES
                        or metadata["access_level"] < record["access_level"]
                        or (
                            source_subject is not None
                            and record["writer_subject"] != source_subject
                        )
                        or (
                            source_token_id is not None
                            and metadata["writer_token_id"] != source_token_id
                        )
                    ):
                        raise DomainError("INVALID_REFERENCE", 422)
                    writer = tx.connection.execute(
                        """SELECT 1 FROM vnext.run_credential credential
                        JOIN vnext.run_writer writer ON
                          (writer.tenant_id,writer.project_id,writer.task_id,
                           writer.agent_run_id,writer.subject)=
                          (credential.tenant_id,credential.project_id,credential.task_id,
                           credential.agent_run_id,credential.subject)
                        WHERE credential.tenant_id=%s AND credential.project_id=%s
                          AND credential.task_id=%s AND credential.agent_run_id=%s
                          AND credential.subject=%s AND credential.token_id=%s
                          AND NOT credential.revoked AND NOT writer.revoked
                          AND (credential.document_json::jsonb->>'expires_at')::timestamptz
                              >clock_timestamp()""",
                        (*tx.owner, owner_run_id, record["writer_subject"],
                         metadata["writer_token_id"]),
                    ).fetchone()
                    if writer is None:
                        raise DomainError("STALE_EXECUTION", 409)
            children = () if metadata is None else tuple(BlobRef.model_validate(r) for r in strict_json_loads(metadata["refs_json"]))
            records[key], bodies[key] = record, data
            seen.add(key)
            for child in sorted(children, key=ref_key):
                visit(child, depth + 1)
            visiting.remove(key)

        for root in sorted(roots, key=ref_key):
            visit(root, 0)
        return records, bodies

    def _load_in_transaction(self, tx, work, *, revision=None):
        revision = work["session_revision"] if revision is None else revision
        value = row(tx.connection.execute(
            "SELECT * FROM vnext.session_manifest WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND session_id=%s AND revision=%s AND work_item_id=%s AND access_level<=%s",
            (*tx.owner, work["session_id"], revision, work["work_item_id"], tx.permissions["clearance"]),
        ))
        if value is None or not value["manifest_ref"]:
            raise DomainError("SESSION_NOT_PUBLISHED", 409)
        manifest = SessionManifest.model_validate(strict_json_loads(value["manifest_json"]))
        if (manifest.session_id != work["session_id"] or manifest.work_item_id != work["work_item_id"]
                or manifest.owner_run_id != value["owner_run_id"]
                or manifest.checkpoint_revision.root != str(value["revision"]) or digest(document(manifest)) != value["manifest_digest"]):
            raise DomainError("INVALID_REFERENCE", 422)
        roots = (manifest.history_root, manifest.provider_state_ref, manifest.memory_manifest_ref)
        provisional = self.artifacts.record(tx, manifest.history_root)
        history = PublishedHistoryRoot.model_validate(strict_json_loads(self.artifacts.checked_bytes(provisional)))
        capability = self.capability(tx, history)
        records, bodies = self._graph(tx, roots, capability["limits"], publication_id=value["publication_id"])
        history = PublishedHistoryRoot.model_validate(strict_json_loads(bodies[ref_key(manifest.history_root)]))
        provider = PublishedProviderStateRoot.model_validate(strict_json_loads(bodies[ref_key(manifest.provider_state_ref)]))
        memory = PublishedMemoryManifestRoot.model_validate(strict_json_loads(bodies[ref_key(manifest.memory_manifest_ref)]))
        self._root_agreement(manifest, history, provider, memory, capability, records)
        if history.session_lineage != value["session_lineage"] or digest(document(history.frontier)) != value["frontier_digest"]:
            raise DomainError("INVALID_REFERENCE", 422)
        receipt = SessionReceipt(session_id=manifest.session_id, manifest_ref=value["manifest_ref"],
            checkpoint_revision=str(value["revision"]), manifest_digest=value["manifest_digest"],
            publication_id=value["publication_id"], published_at=value["published_at"])
        return PublishedSession(receipt=receipt, manifest=manifest, history=history,
            provider_state=provider, memory=memory, object_refs=tuple(BlobRef.model_validate({
                "id": r["entity_id"], "version": str(r["revision"]), "sha256": r["sha256"],
            }) for r in records.values()), object_bytes=bodies)

    def _root_agreement(self, manifest, history, provider, memory, capability, records):
        for root in (history, provider, memory):
            if (root.session_id != manifest.session_id or root.work_item_id != manifest.work_item_id
                    or root.session_lineage != history.session_lineage or not equal(root.compatibility, history.compatibility)):
                raise DomainError("INVALID_REFERENCE", 422)

        if (manifest.message_end.root != str(history.message_end) or manifest.lock_digest.root != history.compatibility.lock_digest
                or memory.enabled != (capability["memory_mode"] != "disabled")
                or manifest.recovery_class.value not in capability["recovery_classes"]):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        pending = {r.root for r in manifest.pending_operation_refs}
        if pending != {b.tool_call_id for b in history.frontier.pending_approvals}:
            raise DomainError("INVALID_REFERENCE", 422)
        if (manifest.recovery_class.value == "approval_boundary") != bool(provider.pending_contents):
            raise DomainError("INVALID_REFERENCE", 422)
        explicit = [*history.object_refs, *provider.object_refs, *memory.object_refs,
            *memory.state_refs, *(f.ref for f in memory.files), *history.frontier.archived_history_refs,
            *(e.response_ref for e in history.frontier.model_entries),
            *(c.provider_response_ref for c in provider.call_bindings), *(c.arguments_ref for c in provider.call_bindings)]
        for ref in explicit:
            if ref is None or ref_key(ref) not in records or records[ref_key(ref)]["sha256"] != ref.sha256.root:
                raise DomainError("INVALID_REFERENCE", 422)

    def require_current_root_writer(self, tx, manifest):
        for ref in (manifest.history_root, manifest.provider_state_ref, manifest.memory_manifest_ref):
            actual = tx.connection.execute(
                "SELECT 1 FROM vnext.session_object o JOIN vnext.run_credential c ON (c.tenant_id,c.project_id,c.task_id,c.agent_run_id,c.token_id)=(o.tenant_id,o.project_id,o.task_id,o.agent_run_id,o.writer_token_id) JOIN vnext.run_writer w ON (w.tenant_id,w.project_id,w.task_id,w.agent_run_id,w.subject)=(c.tenant_id,c.project_id,c.task_id,c.agent_run_id,c.subject) WHERE o.tenant_id=%s AND o.project_id=%s AND o.task_id=%s AND o.artifact_id=%s AND o.artifact_revision=%s AND o.agent_run_id=%s AND NOT c.revoked AND NOT w.revoked AND (c.document_json::jsonb->>'expires_at')::timestamptz>clock_timestamp()",
                (*tx.owner, ref.id, ref.version.root, manifest.owner_run_id),
            ).fetchone()
            if actual is None:
                raise DomainError("STALE_EXECUTION", 409)

    def publish(self, access, assignment, manifest, *, expected_revision):
        assignment = WorkerAssignment.model_validate(assignment)
        manifest = SessionManifest.model_validate(manifest)
        if isinstance(expected_revision, bool) or str(expected_revision) != str(int(expected_revision)) or int(expected_revision) < 0:
            raise DomainError("INVALID_SCHEMA", 422)
        expected_revision = int(expected_revision)
        if (manifest.owner_run_id != assignment.identity.agent_run_id or manifest.run_epoch != assignment.identity.run_epoch
                or manifest.work_item_id != assignment.identity.work_item_id
                or int(manifest.checkpoint_revision.root) != expected_revision + 1):
            raise DomainError("STALE_EXECUTION", 409)
        with self.uow.transaction(access, assignment.identity.task_id, capability="observe") as tx:
            run = self.receiver(tx, assignment)
            work = work_row(tx, manifest.work_item_id)
            self._current_writer(tx, work, run)
            if manifest.saved_at > datetime.now(timezone.utc) or manifest.saved_at < run["started_at"]:
                raise DomainError("INVALID_REFERENCE", 422)
            old = row(tx.connection.execute(
                "SELECT * FROM vnext.session_manifest WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND session_id=%s AND revision=%s",
                (*tx.owner, manifest.session_id, manifest.checkpoint_revision.root),
            ))
            if old:
                if old["owner_run_id"] != run["agent_run_id"] or old["manifest_digest"] != digest(document(manifest)):
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                return self._load_in_transaction(tx, {**work, "session_id": manifest.session_id}, revision=old["revision"]).receipt
            if ((expected_revision == 0 and work["session_id"] is not None)
                    or (expected_revision > 0 and (work["session_id"] != manifest.session_id or work["session_revision"] != expected_revision))):
                raise DomainError("STALE_VERSION", 409)
            record = self.artifacts.record(tx, manifest.history_root)
            history = PublishedHistoryRoot.model_validate(strict_json_loads(self.artifacts.checked_bytes(record)))
            capability = self.capability(tx, history)
            if history.snapshot_id != assignment.snapshot_id:
                raise DomainError("INVALID_REFERENCE", 422)
            credential = tx.connection.execute(
                "SELECT document_json FROM vnext.run_credential WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND NOT revoked",
                (*tx.owner, run["agent_run_id"]),
            ).fetchone()
            if not credential or strict_json_loads(credential[0])["session_lineage"] != history.session_lineage:
                raise DomainError("STALE_EXECUTION", 409)
            roots = (manifest.history_root, manifest.provider_state_ref, manifest.memory_manifest_ref)
            records, bodies = self._graph(tx, roots, capability["limits"], work_id=work["work_item_id"],
                session_id=manifest.session_id, owner_run_id=run["agent_run_id"])
            for ref in roots:
                r = records[ref_key(ref)]
                if r["agent_run_id"] != run["agent_run_id"] or r["provenance"] != "model_output":
                    raise DomainError("INVALID_REFERENCE", 422)
                writer = tx.connection.execute(
                    "SELECT 1 FROM vnext.session_object o JOIN vnext.run_credential c ON (c.tenant_id,c.project_id,c.task_id,c.agent_run_id,c.token_id)=(o.tenant_id,o.project_id,o.task_id,o.agent_run_id,o.writer_token_id) JOIN vnext.run_writer w ON (w.tenant_id,w.project_id,w.task_id,w.agent_run_id,w.subject)=(c.tenant_id,c.project_id,c.task_id,c.agent_run_id,c.subject) WHERE o.tenant_id=%s AND o.project_id=%s AND o.task_id=%s AND o.artifact_id=%s AND o.artifact_revision=%s AND c.subject=%s AND NOT c.revoked AND NOT w.revoked AND (c.document_json::jsonb->>'expires_at')::timestamptz>clock_timestamp()",
                    (*tx.owner, ref.id, ref.version.root, r["writer_subject"]),
                ).fetchone()
                if writer is None:
                    raise DomainError("STALE_EXECUTION", 409)
            provider = PublishedProviderStateRoot.model_validate(strict_json_loads(bodies[ref_key(manifest.provider_state_ref)]))
            memory = PublishedMemoryManifestRoot.model_validate(strict_json_loads(bodies[ref_key(manifest.memory_manifest_ref)]))
            self._root_agreement(manifest, history, provider, memory, capability, records)
            self._frontier(tx, history, provider, allow_pending=manifest.recovery_class.value == "approval_boundary")
            level = max(r["access_level"] for r in records.values())
            publication_id, manifest_ref = "session:" + str(uuid4()), "session-checkpoint:" + str(uuid4())
            tx.connection.execute("INSERT INTO vnext.publication(tenant_id,project_id,task_id,publication_id,kind,access_level) VALUES(%s,%s,%s,%s,'session_manifest',%s)", (*tx.owner, publication_id, level))
            for r in sorted(records.values(), key=lambda r: (r["entity_id"], r["revision"])):
                tx.connection.execute("INSERT INTO vnext.publication_ref(tenant_id,project_id,task_id,publication_id,artifact_id,artifact_revision,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s)", (*tx.owner, publication_id, r["entity_id"], r["revision"], level))
            published_at = tx.connection.execute(
                "INSERT INTO vnext.session_manifest(tenant_id,project_id,task_id,session_id,revision,work_item_id,owner_run_id,manifest_json,publication_id,published_at,access_level,manifest_ref,manifest_digest,frontier_digest,session_lineage) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,clock_timestamp(),%s,%s,%s,%s,%s) RETURNING published_at",
                (*tx.owner, manifest.session_id, manifest.checkpoint_revision.root, work["work_item_id"], run["agent_run_id"], json_text(document(manifest)), publication_id, level, manifest_ref, digest(document(manifest)), digest(document(history.frontier)), history.session_lineage),
            ).fetchone()[0]
            updated = tx.connection.execute(
                "UPDATE vnext.work_item SET session_id=%s,session_revision=%s,revision=revision+1 WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s AND current_run_id=%s AND run_epoch=%s AND session_revision IS NOT DISTINCT FROM %s RETURNING work_item_id",
                (manifest.session_id, manifest.checkpoint_revision.root, *tx.owner, work["work_item_id"], run["agent_run_id"], run["run_epoch"], work["session_revision"]),
            ).fetchone()
            if not updated:
                raise DomainError("STALE_VERSION", 409)
            tx.semantic_event("session.published", {"work_item_id": work["work_item_id"], "manifest_ref": manifest_ref}, access_level=level)
            return SessionReceipt(session_id=manifest.session_id, manifest_ref=manifest_ref,
                checkpoint_revision=manifest.checkpoint_revision.root, manifest_digest=digest(document(manifest)),
                publication_id=publication_id, published_at=published_at)

    def _current_writer(self, tx, work, run):
        from wuji_core.execution.states import task_can_run
        from wuji_core.execution.dependencies import dependencies_satisfied, intent_current
        config = self.registry.config(tx)
        definition = strict_json_loads(tx.task["definition_json"])
        if (not task_can_run(tx.task) or work["current_run_id"] != run["agent_run_id"] or work["run_epoch"] != run["run_epoch"]
                or work["state"] != "running" or work["desired_state"] != "run" or not run["execution_allowed"]
                or run["process_state"] != "running" or not run["started_at"] or not run["process_identity_json"]
                or run["stop_kind"] is not None or run["execution_epoch"] != tx.task["execution_epoch"]
                or run["runtime_attempt"] != tx.task["runtime_attempt"]
                or not dependencies_satisfied(tx, work["work_item_id"]) or not intent_current(tx, work)):
            raise DomainError("STALE_EXECUTION", 409)
        now = datetime.now(timezone.utc)
        if (datetime.fromisoformat(definition["task"]["authorization_expires_at"].replace("Z", "+00:00")) <= now
                or (now - tx.task["activated_at"]).total_seconds() >= config.runtime.limits.max_elapsed_seconds
                or tx.connection.execute("SELECT 1 FROM vnext.work_suspension WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s", (*tx.owner, work["work_item_id"])).fetchone()):
            raise DomainError("STALE_EXECUTION", 409)
        if not any(pool["tier"] == "model" for pool in tx.capacity_pools):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        for pool in tx.capacity_pools:
            reservation = tx.connection.execute("SELECT state FROM vnext.capacity_reservation WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND pool_key=%s", (*tx.owner, run["agent_run_id"], pool["pool_key"])).fetchone()
            if reservation is None or reservation[0] == "released":
                raise DomainError("STALE_EXECUTION", 409)

    def load_published(self, access, task_id, session_id, *, revision=None):
        with self.uow.transaction(access, task_id, repeatable_read=True) as tx:
            work = row(tx.connection.execute("SELECT * FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND session_id=%s", (*tx.owner, session_id)))
            if work is None:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            return self._load_in_transaction(tx, work, revision=revision)

    def validate_recovery_in_transaction(self, tx, work, *, assignment=None):
        try:
            published = self._load_in_transaction(tx, work)
            manifest = published.manifest
            current = row(tx.connection.execute("SELECT * FROM vnext.agent_run WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s", (*tx.owner, work["current_run_id"])))
            if current is None:
                raise DomainError("STALE_EXECUTION", 409)
            if assignment is None:
                unsettled = tx.connection.execute("SELECT 1 FROM vnext.agent_run WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s AND stop_kind IS NULL", (*tx.owner, work["work_item_id"])).fetchone()
                if unsettled:
                    raise DomainError("OPERATION_UNKNOWN", 409)
            else:
                assignment = WorkerAssignment.model_validate(assignment)
                if (assignment.identity.agent_run_id != work["current_run_id"] or assignment.identity.run_epoch.root != str(work["run_epoch"])
                        or assignment.session_manifest_ref is None or assignment.session_manifest_ref.root != published.receipt.manifest_ref):
                    raise DomainError("STALE_EXECUTION", 409)
                holder = tx.connection.execute("SELECT 1 FROM vnext.session_holder WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND manifest_ref=%s AND session_lineage=%s", (*tx.owner, current["agent_run_id"], published.receipt.manifest_ref, published.history.session_lineage)).fetchone()
                if holder is None:
                    raise DomainError("STALE_EXECUTION", 409)
            self._frontier(tx, published.history, published.provider_state,
                allow_pending=manifest.recovery_class.value == "approval_boundary")
            return RecoveryCheck(resumable=True, manifest_ref=published.receipt.manifest_ref,
                session_id=manifest.session_id, checkpoint_revision=manifest.checkpoint_revision.root,
                session_lineage=published.history.session_lineage, owner_run_id=manifest.owner_run_id,
                frontier_digest=digest(document(published.history.frontier)))
        except (ValueError, KeyError, TypeError, DomainError) as error:
            return RecoveryCheck(resumable=False, reason_code=getattr(error, "code", "SESSION_INCOMPATIBLE"))
