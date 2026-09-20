"""Internal hosted Worker ports backed by P03/P04/P06, without MAF types.

This composition is not an execution-control or Supervisor endpoint. The caller
supplies authenticated Run access; all execution prerequisites already exist.
"""

from contextlib import contextmanager
from hashlib import sha256
from threading import Lock

from pydantic import ValidationError

from wuji_core.admission.common import current_run
from wuji_core.admission.ledger import AdmissionLedger, tool_receipt
from wuji_core.contracts.envelopes import AgentPayload, BlobRef, ResultEnvelope, WorkerAssignment
from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.evidence.artifacts import bound_run
from wuji_core.execution.retained_results import (
    RetainedResultAuthority,
    RetainedResultKey,
)
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.snapshots import SnapshotRepository
from wuji_core.persistence.uow import DomainError, row


def _key(ref):
    return ref.entity_type.value, ref.id, ref.revision.root


def _profile_tools_valid(work_kind, refs):
    return bool(refs) or work_kind in {"reason", "report"}


class PlatformWorkerHost:
    def __init__(self, *, uow, registry, access, artifacts, committer, profiles, lock_digest,
                 sessions=None, inputs=None, receiver_access=None, retained_result=None):
        if retained_result is not None and not isinstance(retained_result, RetainedResultKey):
            raise ValueError("invalid retained result binding")
        self.uow, self.registry, self.access = uow, registry, access
        self.artifacts, self.committer = artifacts, committer
        self.sessions, self.inputs, self.receiver_access = sessions, inputs, receiver_access
        self.retained_result = retained_result
        self.retained_authority = RetainedResultAuthority(uow)
        self.lock_digest = lock_digest
        self.profiles = {}
        for published in profiles:
            snapshot = strict_json_loads(canonical_json_bytes(published))
            body = snapshot["body"]
            if snapshot["ref"] in self.profiles or snapshot["digest"] != sha256(canonical_json_bytes(body)).hexdigest() or snapshot["ref"] != body["ref"] or snapshot["revision"] != body["revision"] or body["lock_digest"] != lock_digest:
                raise ValueError("invalid deployment harness snapshot")
            self.profiles[snapshot["ref"]] = snapshot
        self._submit_lock = Lock()
        self._archive_lock = Lock()

    def resolve(self, assignment, context, *, verified_principal):
        assignment = WorkerAssignment.model_validate(assignment)
        if verified_principal != self.access.principal:
            raise DomainError("STALE_EXECUTION", 409)
        binding = self.registry.binding(self.access)
        if binding.identity != assignment.identity or context.snapshot_id != assignment.snapshot_id:
            raise DomainError("STALE_EXECUTION", 409)
        with self.uow.transaction(self.access, assignment.identity.task_id, capability="model_request") as tx:
            config = self.registry.config(tx)
            _run, work = current_run(tx, config)
            definition = strict_json_loads(tx.task["definition_json"])
            try:
                snapshot = definition["worker_profiles"][assignment.work_kind.value]
                trusted = self.profiles[snapshot["ref"]]
                selected_refs = {r.root for r in assignment.profile_refs}
                tool_refs = tuple(r.root for r in assignment.tool_definition_refs)
                if (
                    canonical_json_bytes(snapshot) != canonical_json_bytes(trusted)
                    or trusted["body"]["work_kind"] != work["kind"]
                    or work["kind"] != assignment.work_kind.value
                    or trusted["ref"] not in selected_refs
                    or selected_refs - {trusted["ref"], config.model.ref, config.runtime.ref}
                    or trusted["body"]["lock_digest"] != config.runtime.lock_digest
                    or config.runtime.lock_digest != self.lock_digest
                    or tuple(trusted["body"]["tool_definition_refs"]) != tool_refs
                    or not _profile_tools_valid(work["kind"], tool_refs)
                    or assignment.limits != config.runtime.limits
                ):
                    raise ValueError("assignment changed frozen harness configuration")
            except (KeyError, TypeError, ValueError) as error:
                raise DomainError("CAPABILITY_UNAVAILABLE", 503) from error
            allowed = set(config.allowed_tool_refs) & set(config.runtime.allowed_tool_refs) & set(binding.allowed_tool_refs)
            if not set(tool_refs) <= allowed:
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            tools = [self.registry.tool(tx, ref).model_dump(mode="json") for ref in tool_refs]
            if len({tool["name"] for tool in tools}) != len(tools):
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            resolved = {
                "profile": trusted, "client_model": config.model.client_model,
                "limits": assignment.limits.model_dump(mode="json"),
                "request_timeout_seconds": config.runtime.total_timeout_seconds,
                "tools": tools, "session_lineage": binding.session_lineage,
            }
            memory_files = None
            memory_inputs = ()
            session_limits = None
            if trusted["body"].get("schema_version") == "wuji.harness.session.v1":
                if self.sessions is None or self.inputs is None or not callable(self.receiver_access):
                    raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                capability = self.registry.session_capability(tx, trusted)
                resolved.update(session_compatibility=capability["compatibility"].model_dump(mode="python"),
                    session_limits=capability["limits"].model_dump(mode="python"), delivery_id=None)
                session_limits = capability["limits"]
                memory_files = {}
                if assignment.session_manifest_ref is not None:
                    recovery = self.sessions.validate_recovery_in_transaction(tx, work, assignment=assignment)
                    if not recovery.resumable:
                        raise DomainError(recovery.reason_code or "STALE_EXECUTION", 409)
                    published = self.sessions._load_in_transaction(tx, work)
                    memory_files = {f.path: published.object_bytes[f.ref.id + "@" + f.ref.version.root] for f in published.memory.files}
                    delivery = tx.connection.execute("SELECT d.delivery_id FROM vnext.input_delivery d JOIN vnext.input_request i USING(tenant_id,project_id,task_id,input_request_id) WHERE d.tenant_id=%s AND d.project_id=%s AND d.task_id=%s AND d.input_request_id=%s AND d.manifest_ref=%s AND i.status='resolved'", (*tx.owner, work["input_request_id"], recovery.manifest_ref)).fetchone()
                    resolved["delivery_id"] = delivery[0] if delivery else None
                else:
                    memory_inputs = tuple(trusted["body"].get("memory_inputs", ()))
        snapshots = SnapshotRepository(self.uow)
        manifest = snapshots.get(assignment.identity.task_id, self.access, assignment.snapshot_id)
        snapshot_records = {}
        for ref in context.read_set:
            if ref not in manifest.refs:
                raise DomainError("INVALID_REFERENCE", 422)
            snapshot_records[_key(ref)] = snapshots.read_ref(
                assignment.identity.task_id,
                self.access,
                assignment.snapshot_id,
                ref,
            )
        if memory_files is not None and assignment.session_manifest_ref is None:
            for item in memory_inputs:
                try:
                    reference = KnowledgeRef.model_validate(item["ref"])
                    path = item["path"]
                    record = snapshot_records[_key(reference)]
                    body = self.artifacts.checked_bytes(record)
                    body.decode("utf-8")
                    if (
                        reference.entity_type.value != "artifact"
                        or record["state"] != "sealed"
                        or not record["media_type"].startswith("text/")
                        or path in memory_files
                    ):
                        raise ValueError("invalid fixed memory input")
                    memory_files[path] = body
                except (KeyError, TypeError, UnicodeDecodeError, ValueError) as error:
                    raise DomainError("INVALID_REFERENCE", 422) from error
            if (
                len(memory_files) > session_limits.max_objects
                or any(
                    len(body) > session_limits.max_object_bytes
                    for body in memory_files.values()
                )
                or sum(map(len, memory_files.values()))
                > session_limits.max_total_bytes
            ):
                raise DomainError("LIMIT_BLOCKED", 429)
        resolved = strict_json_loads(canonical_json_bytes(resolved))
        if memory_files is not None:
            # Internal bytes map. Only B2's generated transport may encode it.
            resolved["memory_files"] = memory_files
        return resolved

    def _session_assignment(self, assignment):
        assignment = WorkerAssignment.model_validate(assignment)
        binding = self.registry.binding(self.access)
        if binding.identity != assignment.identity or self.sessions is None or self.inputs is None:
            raise DomainError("STALE_EXECUTION", 409)
        return assignment

    def stage_session(self, assignment, objects):
        assignment = self._session_assignment(assignment)
        return self.sessions.stage_objects(self.access, assignment, objects)

    def publish_session(self, assignment, manifest, *, expected_revision):
        assignment = self._session_assignment(assignment)
        if not callable(self.receiver_access):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        return self.sessions.publish(self.receiver_access(assignment), assignment, manifest,
            expected_revision=expected_revision)

    def load_session(self, assignment, *, manifest_ref):
        assignment = self._session_assignment(assignment)
        if assignment.session_manifest_ref is None or assignment.session_manifest_ref.root != manifest_ref:
            raise DomainError("INVALID_REFERENCE", 422)
        with self.uow.transaction(self.access, assignment.identity.task_id, capability="tool_request") as tx:
            _, work = current_run(tx, self.registry.config(tx))
            check = self.sessions.validate_recovery_in_transaction(tx, work, assignment=assignment)
            if not check.resumable:
                raise DomainError(check.reason_code or "STALE_EXECUTION", 409)
            published = self.sessions._load_in_transaction(tx, work)
            return published.model_copy(update={"recovery_check": check})

    def register_input(self, assignment, observation):
        assignment = self._session_assignment(assignment)
        if not callable(self.receiver_access):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        return self.inputs.register_native(self.receiver_access(assignment), assignment, observation)

    def load_delivery(self, assignment, *, delivery_id):
        assignment = self._session_assignment(assignment)
        return self.inputs.load_delivery(self.access, assignment, delivery_id=delivery_id)

    def acknowledge_delivery(self, assignment, *, delivery_id, payload_digest):
        assignment = self._session_assignment(assignment)
        return self.inputs.acknowledge_delivery(self.access, assignment,
            delivery_id=delivery_id, payload_digest=payload_digest)

    @contextmanager
    def _result_transaction(self, assignment):
        if self.retained_result is None:
            with self.uow.transaction(
                self.access,
                assignment.identity.task_id,
                capability="model_output",
            ) as tx:
                yield tx
            return
        if self.retained_result != RetainedResultKey.from_assignment(assignment):
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        with self.retained_authority.transaction(
            self.access, assignment
        ) as (tx, _run, _key, _disposition):
            yield tx

    def _bound_result(self, tx, assignment):
        if self.retained_result is None:
            return bound_run(
                tx, assignment.identity.agent_run_id, assignment.identity
            )
        if tx.retained_result is None:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN", 403)
        return row(
            tx.connection.execute(
                """SELECT * FROM vnext.agent_run WHERE tenant_id=%s
                AND project_id=%s AND task_id=%s AND agent_run_id=%s""",
                (*tx.owner, assignment.identity.agent_run_id),
            )
        )

    def _writer(self, assignment):
        with self._result_transaction(assignment) as tx:
            run = self._bound_result(tx, assignment)
            if run is None:
                raise DomainError("STALE_EXECUTION", 403)
            return (
                tx.permissions["clearance"]
                if self.retained_result is None
                else tx.retained_result["access_level"]
            )

    def _stage(self, assignment, data, media_type):
        level = self._writer(assignment)
        if self.retained_result is None:
            ref = self.artifacts.stage_model_output(
                self.access, assignment.identity.task_id, assignment.identity.agent_run_id,
                data, media_type, access_level=level,
            )
            return self.artifacts.seal(self.access, assignment.identity.task_id, ref)
        ref = self.artifacts.stage_retained_output(
            self.access, assignment.identity.task_id, assignment.identity.agent_run_id,
            data, media_type, retained=self.retained_result, access_level=level,
        )
        return self.artifacts.seal_retained(
            self.access, assignment.identity.task_id, ref,
            retained=self.retained_result,
        )

    @staticmethod
    def _operation_digest(assignment):
        return sha256(canonical_json_bytes({
            "identity": assignment.identity.model_dump(mode="json"),
            "operation_id": assignment.operation_id,
        })).hexdigest()

    def _publish(self, assignment, publication_id, kind, refs):
        records = []
        with self._result_transaction(assignment) as tx:
            self._bound_result(tx, assignment)
            allowed_writers = {self.access.principal.subject}
            if self.retained_result is not None:
                allowed_writers.add(tx.retained_result["source_writer_subject"])
            for ref in refs:
                record = self.artifacts.record(tx, ref)
                if (
                    record["state"] != "sealed"
                    or record["provenance"] != "model_output"
                    or record["agent_run_id"] != assignment.identity.agent_run_id
                    or record["writer_subject"] not in allowed_writers
                ):
                    raise DomainError("INVALID_REFERENCE", 422)
                records.append(record)
            level = max(record["access_level"] for record in records)
            published = row(tx.connection.execute(
                "SELECT kind,access_level FROM vnext.publication WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND publication_id=%s",
                (*tx.owner, publication_id),
            ))
            if published is None:
                tx.connection.execute(
                    "INSERT INTO vnext.publication(tenant_id,project_id,task_id,publication_id,kind,access_level) VALUES(%s,%s,%s,%s,%s,%s)",
                    (*tx.owner, publication_id, kind, level),
                )
            elif published["kind"] != kind or published["access_level"] < level:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            for record in records:
                tx.connection.execute(
                    """INSERT INTO vnext.publication_ref(tenant_id,project_id,task_id,
                    publication_id,artifact_id,artifact_revision,access_level)
                    VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (
                        *tx.owner,
                        publication_id,
                        record["entity_id"],
                        record["revision"],
                        level,
                    ),
                )

    def _published_artifacts(self, assignment, publication_id):
        with self._result_transaction(assignment) as tx:
            self._bound_result(tx, assignment)
            cursor = tx.connection.execute(
                """SELECT a.* FROM vnext.publication_ref p JOIN vnext.artifact a
                ON (a.tenant_id,a.project_id,a.task_id,a.entity_id,a.revision)=
                   (p.tenant_id,p.project_id,p.task_id,p.artifact_id,p.artifact_revision)
                WHERE p.tenant_id=%s AND p.project_id=%s AND p.task_id=%s
                AND p.publication_id=%s ORDER BY a.media_type,a.entity_id""",
                (*tx.owner, publication_id),
            )
            columns = [column.name for column in cursor.description]
            return [dict(zip(columns, values)) for values in cursor.fetchall()]

    @staticmethod
    def _blob_ref(record):
        return BlobRef.model_validate({
            "id": record["entity_id"],
            "version": str(record["revision"]),
            "sha256": record["sha256"],
        })

    def archive_sdk(self, assignment, body: bytes):
        assignment = WorkerAssignment.model_validate(assignment)
        if not isinstance(body, bytes) or len(body) > assignment.limits.max_total_output_bytes:
            raise DomainError("LIMIT_BLOCKED", 422)
        publication_id = "maf-sdk:" + self._operation_digest(assignment)
        with self._archive_lock:
            existing = self._published_artifacts(assignment, publication_id)
            if existing:
                if len(existing) != 1 or existing[0]["media_type"] != "application/x-ndjson":
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                record = existing[0]
                if self.artifacts.checked_bytes(record) != body:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                return self._blob_ref(record)
            ref = self._stage(assignment, body, "application/x-ndjson")
            self._publish(
                assignment, publication_id, "worker_sdk_archive", (ref,)
            )
            return ref

    def _tool_binding(self, assignment, receipts):
        refs = set()
        records = []
        seen = set()
        ledger = AdmissionLedger(self.uow)
        for supplied in receipts:
            actual = (
                ledger.tool_call(self.access, supplied.tool_call_id)
                if self.retained_result is None
                else None
            )
            transaction = (
                self.uow.transaction(self.access, assignment.identity.task_id)
                if self.retained_result is None
                else self._result_transaction(assignment)
            )
            with transaction as tx:
                if self.retained_result is not None:
                    call_record = row(tx.connection.execute(
                        """SELECT * FROM vnext.tool_call WHERE tenant_id=%s
                        AND project_id=%s AND task_id=%s AND tool_call_id=%s
                        AND access_level<=%s""",
                        (*tx.owner, supplied.tool_call_id, tx.permissions["clearance"]),
                    ))
                    if call_record is None:
                        raise DomainError("INVALID_REFERENCE", 422)
                    actual = tool_receipt(tx, call_record)
                if actual != supplied or actual.tool_call_id in seen:
                    raise DomainError("INVALID_REFERENCE", 422)
                seen.add(actual.tool_call_id)
                call = row(tx.connection.execute(
                    "SELECT a.agent_run_id,c.work_item_id,c.session_lineage FROM vnext.tool_attempt a JOIN vnext.tool_call c USING(tenant_id,project_id,task_id,tool_call_id) WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s AND a.tool_attempt_id=%s",
                    (*tx.owner, actual.tool_attempt_id.root if actual.tool_attempt_id else None),
                ))
                if call is None or call["work_item_id"] != assignment.identity.work_item_id:
                    raise DomainError("INVALID_REFERENCE", 422)
                if call["agent_run_id"] != assignment.identity.agent_run_id:
                    if self.sessions is None or assignment.session_manifest_ref is None:
                        raise DomainError("INVALID_REFERENCE", 422)
                    holder = tx.connection.execute("SELECT 1 FROM vnext.session_holder WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND manifest_ref=%s AND session_lineage=%s", (*tx.owner, assignment.identity.agent_run_id, assignment.session_manifest_ref.root, call["session_lineage"])).fetchone()
                    if not holder:
                        raise DomainError("INVALID_REFERENCE", 422)
                    work = row(tx.connection.execute("SELECT * FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s", (*tx.owner, assignment.identity.work_item_id)))
                    prior = self.sessions._load_in_transaction(tx, work)
                    if not any(e.tool_call_id == actual.tool_call_id and e.tool_attempt_id == actual.tool_attempt_id.root for e in prior.history.frontier.tool_entries):
                        raise DomainError("INVALID_REFERENCE", 422)
            evidence = actual.evidence_receipt
            if (
                actual.status.value != "complete"
                or actual.tool_attempt_id is None
                or actual.result_ref is None
                or evidence is None
                or evidence.status.value != "accepted"
                or evidence.observation_ref is None
            ):
                raise DomainError("INVALID_REFERENCE", 422)
            refs.add(_key(evidence.observation_ref))
            refs.update(("artifact", r.id, r.version.root) for r in evidence.artifact_refs)
            records.append({
                "tool_call_id": actual.tool_call_id,
                "operation_id": actual.operation_id,
                "tool_attempt_id": actual.tool_attempt_id.root,
                "receipt_digest": sha256(canonical_json_bytes(actual.model_dump(mode="python"))).hexdigest(),
                "observation_ref": evidence.observation_ref.model_dump(mode="json"),
                "artifact_refs": [ref.model_dump(mode="json") for ref in evidence.artifact_refs],
                "result_ref": actual.result_ref.model_dump(mode="json"),
            })
        return records, refs

    @staticmethod
    def _context_binding(context):
        rendered = strict_json_loads(context.text)
        return {
            "schema_version": rendered["schema_version"],
            "snapshot_id": context.snapshot_id,
            "input_digest": context.input_digest,
            "text_digest": sha256(context.text.encode()).hexdigest(),
            "read_set": [ref.model_dump(mode="json") for ref in context.read_set],
            "record_refs": [ref.model_dump(mode="json") for ref in context.record_refs],
            "relations_digest": sha256(canonical_json_bytes(rendered["relations"])).hexdigest(),
        }

    def _result_binding(self, assignment, submission_id, raw_ref, raw_output,
                        sdk_ref, sdk_output, context, tool_binding):
        return {
            "schema_version": "wuji.maf-result-binding.v1",
            "submission_id": submission_id,
            "identity": assignment.identity.model_dump(mode="json"),
            "operation_id": assignment.operation_id,
            "raw_output": {
                "ref": raw_ref.model_dump(mode="json"),
                "sha256": sha256(raw_output).hexdigest(),
                "size_bytes": len(raw_output),
            },
            "sdk_output": {
                "ref": sdk_ref.model_dump(mode="json"),
                "sha256": sha256(sdk_output).hexdigest(),
                "size_bytes": len(sdk_output),
            },
            "context": self._context_binding(context),
            "tool_receipts": tool_binding,
        }

    def submit_result(self, assignment, *, raw_output, context, tool_receipts, sdk_output):
        """Seal raw bytes before parsing; replay never re-enters an Agent/tool loop."""
        assignment = WorkerAssignment.model_validate(assignment)
        if context.snapshot_id != assignment.snapshot_id or not isinstance(raw_output, bytes) or not isinstance(sdk_output, bytes):
            raise DomainError("INVALID_SCHEMA", 422)
        if len(raw_output) > assignment.limits.max_single_output_bytes or len(sdk_output) > assignment.limits.max_total_output_bytes:
            raise DomainError("LIMIT_BLOCKED", 422)
        submission_id = "maf-m1:" + self._operation_digest(assignment)
        # One host owns one active Run in M1. This only serializes local sink calls;
        # P04 remains the durable idempotency authority, not this lock or a cache.
        with self._submit_lock:
            self._writer(assignment)
            with self._result_transaction(assignment) as tx:
                source_writer = (
                    None
                    if self.retained_result is None
                    else tx.retained_result["source_writer_subject"]
                )
                saved = row(tx.connection.execute(
                    "SELECT envelope_json,writer_subject FROM vnext.result_submission WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND submission_id=%s",
                    (*tx.owner, submission_id),
                ))
            if saved is not None:
                envelope = ResultEnvelope.model_validate(strict_json_loads(saved["envelope_json"]))
                if saved["writer_subject"] not in {
                    self.access.principal.subject, source_writer,
                } or envelope.identity != assignment.identity or envelope.raw_output_digest.root != sha256(raw_output).hexdigest() or envelope.snapshot_id != context.snapshot_id or envelope.read_set != list(context.read_set):
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                published = self._published_artifacts(
                    assignment, "result:" + submission_id
                )
                allowed_writers = {self.access.principal.subject}
                if source_writer is not None:
                    allowed_writers.add(source_writer)
                raw_records = [
                    record
                    for record in published
                    if self._blob_ref(record) == envelope.raw_output_ref
                ]
                sdk_records = [r for r in published if r["media_type"] == "application/x-ndjson"]
                binding_records = [r for r in published if r["media_type"] == "application/vnd.wuji.maf-result-binding+json"]
                if (
                    len(raw_records) != 1
                    or len(sdk_records) > 1
                    or len(binding_records) > 1
                    or any(
                        record["state"] != "sealed"
                        or record["provenance"] != "model_output"
                        or record["agent_run_id"]
                        != assignment.identity.agent_run_id
                        or record["writer_subject"] not in allowed_writers
                        or record["media_type"] not in {
                            "text/plain; charset=utf-8",
                            "application/x-ndjson",
                            "application/vnd.wuji.maf-result-binding+json",
                        }
                        for record in published
                    )
                    or self.artifacts.checked_bytes(raw_records[0]) != raw_output
                ):
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                repair_refs = []
                if sdk_records:
                    sdk_record = sdk_records[0]
                elif self.retained_result is not None:
                    archived = self._published_artifacts(
                        assignment,
                        "maf-sdk:" + self._operation_digest(assignment),
                    )
                    if (
                        len(archived) != 1
                        or archived[0]["media_type"] != "application/x-ndjson"
                        or archived[0]["state"] != "sealed"
                        or archived[0]["provenance"] != "model_output"
                        or archived[0]["agent_run_id"]
                        != assignment.identity.agent_run_id
                        or archived[0]["writer_subject"] not in allowed_writers
                    ):
                        raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                    sdk_record = archived[0]
                    repair_refs.append(self._blob_ref(sdk_record))
                else:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                if self.artifacts.checked_bytes(sdk_record) != sdk_output:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                tool_binding, _tool_refs = self._tool_binding(
                    assignment, tool_receipts
                )
                expected = self._result_binding(
                    assignment, submission_id, envelope.raw_output_ref, raw_output,
                    self._blob_ref(sdk_record), sdk_output, context, tool_binding,
                )
                expected_bytes = canonical_json_bytes(expected)
                if binding_records:
                    if self.artifacts.checked_bytes(binding_records[0]) != expected_bytes:
                        raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                elif self.retained_result is not None:
                    repair_refs.append(
                        self._stage(
                            assignment,
                            expected_bytes,
                            "application/vnd.wuji.maf-result-binding+json",
                        )
                    )
                else:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                if repair_refs:
                    self._publish(
                        assignment,
                        "result:" + submission_id,
                        "result_submission",
                        tuple(repair_refs),
                    )
                repaired = self._published_artifacts(
                    assignment, "result:" + submission_id
                )
                if (
                    len(repaired) != 3
                    or len([r for r in repaired if self._blob_ref(r) == envelope.raw_output_ref]) != 1
                    or len([r for r in repaired if r["media_type"] == "application/x-ndjson"]) != 1
                    or len([r for r in repaired if r["media_type"] == "application/vnd.wuji.maf-result-binding+json"]) != 1
                ):
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                if self.retained_result is None:
                    return self.committer.lookup(
                        self.access, assignment.identity.task_id, submission_id
                    )
                return self.committer.reconcile_retained(
                    self.access, assignment.identity.task_id, submission_id,
                    retained=self.retained_result,
                )

            tool_binding, tool_refs = self._tool_binding(
                assignment, tool_receipts
            )
            raw_ref = self._stage(assignment, raw_output, "text/plain; charset=utf-8")
            sdk_ref = self.archive_sdk(assignment, sdk_output)
            observed = {_key(ref) for ref in context.read_set}
            observed.update(tool_refs)
            try:
                payload = AgentPayload.model_validate(strict_json_loads(raw_output))
            except (ValueError, ValidationError):
                payload = None  # P04 owns rejection of the untouched invalid bytes.
            invalid_reference = False
            if payload is not None:
                for proposal in [*payload.claims, *payload.intent_proposals]:
                    if any(
                        isinstance(ref.root, KnowledgeRef)
                        and _key(ref.root) not in observed
                        for ref in proposal.basis_refs
                    ):
                        invalid_reference = True
                        break
                    revises = getattr(proposal, "revises", None)
                    if revises is not None and _key(revises) not in observed:
                        invalid_reference = True
                        break
            initial_reason = (
                assignment.work_kind.value == "reason"
                and not context.read_set
                and not tool_refs
                and payload is not None
                and not payload.claims
            )
            result_policy = None
            if initial_reason and any(
                proposal.basis_refs for proposal in payload.intent_proposals
            ):
                result_policy = "initial_reason_empty_basis"
            elif invalid_reference:
                result_policy = "reject_invalid_reference"
            elif assignment.work_kind.value == "reason" and payload is not None:
                supported = {"claim", "observation"}
                needs_filter = any(
                    isinstance(ref.root, KnowledgeRef)
                    and ref.root.entity_type.value not in supported
                    for proposal in payload.intent_proposals
                    for ref in proposal.basis_refs
                )
                keeps_basis = all(
                    not proposal.basis_refs
                    or any(
                        not isinstance(ref.root, KnowledgeRef)
                        or ref.root.entity_type.value in supported
                        for ref in proposal.basis_refs
                    )
                    for proposal in payload.intent_proposals
                )
                if needs_filter and keeps_basis:
                    result_policy = "reason_intent_supported_basis"
            if (
                result_policy is None
                and assignment.work_kind.value == "explore"
                and not tool_binding
            ):
                result_policy = "reject_missing_tool_evidence"
            envelope = ResultEnvelope.model_validate({
                "schema_version": "wuji.result-envelope.v2", "submission_id": submission_id,
                "identity": assignment.identity.model_dump(mode="json"),
                "snapshot_id": context.snapshot_id,
                "read_set": [ref.model_dump(mode="json") for ref in context.read_set],
                "raw_output_ref": raw_ref.model_dump(mode="json"),
                "raw_output_digest": raw_ref.sha256.root,
                "payload": None, "producer_version": "wuji-maf-worker/0.1.0:maf-core/1.18.0",
            })
            binding = self._result_binding(
                assignment, submission_id, raw_ref, raw_output, sdk_ref,
                sdk_output, context, tool_binding,
            )
            binding_ref = self._stage(
                assignment, canonical_json_bytes(binding),
                "application/vnd.wuji.maf-result-binding+json",
            )
            if self.retained_result is None:
                self.committer.receive(self.access, envelope)
            else:
                self.committer.receive_retained(
                    self.access, envelope, retained=self.retained_result
                )
            self._publish(
                assignment,
                "result:" + submission_id,
                "result_submission",
                (sdk_ref, binding_ref),
            )
            if self.retained_result is None:
                return self.committer.reconcile(
                    self.access,
                    assignment.identity.task_id,
                    submission_id,
                    result_policy=result_policy,
                )
            return self.committer.reconcile_retained(
                self.access, assignment.identity.task_id, submission_id,
                retained=self.retained_result,
                result_policy=result_policy,
            )
