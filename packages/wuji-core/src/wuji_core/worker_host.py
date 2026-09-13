"""Internal hosted Worker ports backed by P03/P04/P06, without MAF types.

This composition is not an execution-control or Supervisor endpoint. The caller
supplies authenticated Run access; all execution prerequisites already exist.
"""

from hashlib import sha256
from threading import Lock

from pydantic import ValidationError

from wuji_core.admission.common import current_run
from wuji_core.admission.ledger import AdmissionLedger
from wuji_core.contracts.envelopes import AgentPayload, BlobRef, ResultEnvelope, WorkerAssignment
from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.evidence.artifacts import bound_run
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.snapshots import SnapshotRepository
from wuji_core.persistence.uow import DomainError, row


def _key(ref):
    return ref.entity_type.value, ref.id, ref.revision.root


class PlatformWorkerHost:
    def __init__(self, *, uow, registry, access, artifacts, committer, profiles, lock_digest):
        self.uow, self.registry, self.access = uow, registry, access
        self.artifacts, self.committer = artifacts, committer
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
                    or not tool_refs
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
        snapshots = SnapshotRepository(self.uow)
        manifest = snapshots.get(assignment.identity.task_id, self.access, assignment.snapshot_id)
        for ref in context.read_set:
            if ref not in manifest.refs:
                raise DomainError("INVALID_REFERENCE", 422)
            snapshots.read_ref(assignment.identity.task_id, self.access, assignment.snapshot_id, ref)
        return strict_json_loads(canonical_json_bytes(resolved))

    def _writer(self, assignment):
        with self.uow.transaction(self.access, assignment.identity.task_id, capability="model_output") as tx:
            bound_run(tx, assignment.identity.agent_run_id, assignment.identity)
            return tx.permissions["clearance"]

    def _stage(self, assignment, data, media_type):
        level = self._writer(assignment)
        ref = self.artifacts.stage_model_output(
            self.access, assignment.identity.task_id, assignment.identity.agent_run_id,
            data, media_type, access_level=level,
        )
        return self.artifacts.seal(self.access, assignment.identity.task_id, ref)

    @staticmethod
    def _operation_digest(assignment):
        return sha256(canonical_json_bytes({
            "identity": assignment.identity.model_dump(mode="json"),
            "operation_id": assignment.operation_id,
        })).hexdigest()

    def _publish(self, assignment, publication_id, kind, refs):
        records = []
        with self.uow.transaction(
            self.access, assignment.identity.task_id, capability="model_output"
        ) as tx:
            bound_run(tx, assignment.identity.agent_run_id, assignment.identity)
            for ref in refs:
                record = self.artifacts.record(tx, ref)
                if (
                    record["state"] != "sealed"
                    or record["provenance"] != "model_output"
                    or record["agent_run_id"] != assignment.identity.agent_run_id
                    or record["writer_subject"] != self.access.principal.subject
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
        with self.uow.transaction(
            self.access, assignment.identity.task_id, capability="model_output"
        ) as tx:
            bound_run(tx, assignment.identity.agent_run_id, assignment.identity)
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
        for receipt in receipts:
            actual = ledger.tool_call(self.access, receipt.tool_call_id)
            if actual != receipt or actual.tool_call_id in seen:
                raise DomainError("INVALID_REFERENCE", 422)
            seen.add(actual.tool_call_id)
            with self.uow.transaction(self.access, assignment.identity.task_id) as tx:
                call = row(tx.connection.execute(
                    "SELECT agent_run_id FROM vnext.tool_attempt WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s",
                    (*tx.owner, receipt.tool_attempt_id.root if receipt.tool_attempt_id else None),
                ))
                if call is None or call["agent_run_id"] != assignment.identity.agent_run_id:
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
            with self.uow.transaction(self.access, assignment.identity.task_id, capability="model_output") as tx:
                saved = row(tx.connection.execute(
                    "SELECT envelope_json,writer_subject FROM vnext.result_submission WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND submission_id=%s",
                    (*tx.owner, submission_id),
                ))
            if saved is not None:
                envelope = ResultEnvelope.model_validate(strict_json_loads(saved["envelope_json"]))
                if saved["writer_subject"] != self.access.principal.subject or envelope.identity != assignment.identity or envelope.raw_output_digest.root != sha256(raw_output).hexdigest() or envelope.snapshot_id != context.snapshot_id or envelope.read_set != list(context.read_set):
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                published = self._published_artifacts(
                    assignment, "result:" + submission_id
                )
                sdk_records = [r for r in published if r["media_type"] == "application/x-ndjson"]
                binding_records = [r for r in published if r["media_type"] == "application/vnd.wuji.maf-result-binding+json"]
                if len(sdk_records) != 1 or len(binding_records) != 1:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                sdk_record, binding_record = sdk_records[0], binding_records[0]
                if self.artifacts.checked_bytes(sdk_record) != sdk_output:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                tool_binding, _tool_refs = self._tool_binding(
                    assignment, tool_receipts
                )
                expected = self._result_binding(
                    assignment, submission_id, envelope.raw_output_ref, raw_output,
                    self._blob_ref(sdk_record), sdk_output, context, tool_binding,
                )
                if self.artifacts.checked_bytes(binding_record) != canonical_json_bytes(expected):
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                return self.committer.lookup(
                    self.access, assignment.identity.task_id, submission_id
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
            if payload is not None:
                for proposal in [*payload.claims, *payload.intent_proposals]:
                    for ref in proposal.basis_refs:
                        if isinstance(ref.root, KnowledgeRef) and _key(ref.root) not in observed:
                            raise DomainError("INVALID_REFERENCE", 422)
                    revises = getattr(proposal, "revises", None)
                    if revises is not None and _key(revises) not in observed:
                        raise DomainError("INVALID_REFERENCE", 422)
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
            self.committer.receive(self.access, envelope)
            self._publish(
                assignment,
                "result:" + submission_id,
                "result_submission",
                (sdk_ref, binding_ref),
            )
            return self.committer.reconcile(
                self.access, assignment.identity.task_id, submission_id
            )
