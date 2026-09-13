"""Internal hosted Worker ports backed by P03/P04/P06, without MAF types.

This composition is not an execution-control or Supervisor endpoint. The caller
supplies authenticated Run access; all execution prerequisites already exist.
"""

from hashlib import sha256
from threading import Lock

from pydantic import ValidationError

from wuji_core.admission.common import current_run
from wuji_core.admission.ledger import AdmissionLedger
from wuji_core.contracts.envelopes import AgentPayload, ResultEnvelope, WorkerAssignment
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

    def resolve(self, assignment, context):
        assignment = WorkerAssignment.model_validate(assignment)
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

    def archive_sdk(self, assignment, body: bytes):
        return self._stage(assignment, body, "application/x-ndjson")

    def _tool_basis(self, assignment, receipts):
        refs = set()
        ledger = AdmissionLedger(self.uow)
        for receipt in receipts:
            actual = ledger.tool_call(self.access, receipt.tool_call_id)
            if actual != receipt:
                raise DomainError("INVALID_REFERENCE", 422)
            with self.uow.transaction(self.access, assignment.identity.task_id) as tx:
                call = row(tx.connection.execute(
                    "SELECT agent_run_id FROM vnext.tool_attempt WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s",
                    (*tx.owner, receipt.tool_attempt_id.root if receipt.tool_attempt_id else None),
                ))
                if call is None or call["agent_run_id"] != assignment.identity.agent_run_id:
                    raise DomainError("INVALID_REFERENCE", 422)
            evidence = actual.evidence_receipt
            if actual.status.value != "complete" or evidence is None or evidence.status.value != "accepted" or evidence.observation_ref is None:
                raise DomainError("INVALID_REFERENCE", 422)
            refs.add(_key(evidence.observation_ref))
            refs.update(("artifact", r.id, r.version.root) for r in evidence.artifact_refs)
        return refs

    def submit_result(self, assignment, *, raw_output, context, tool_receipts, sdk_output):
        """Seal raw bytes before parsing; replay never re-enters an Agent/tool loop."""
        assignment = WorkerAssignment.model_validate(assignment)
        if context.snapshot_id != assignment.snapshot_id or not isinstance(raw_output, bytes) or not isinstance(sdk_output, bytes):
            raise DomainError("INVALID_SCHEMA", 422)
        if len(raw_output) > assignment.limits.max_single_output_bytes or len(sdk_output) > assignment.limits.max_total_output_bytes:
            raise DomainError("LIMIT_BLOCKED", 422)
        submission_id = "maf-m1:" + sha256(canonical_json_bytes({
            "identity": assignment.identity.model_dump(mode="json"),
            "operation_id": assignment.operation_id,
        })).hexdigest()
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
                return self.committer.submit(self.access, envelope)

            raw_ref = self._stage(assignment, raw_output, "text/plain; charset=utf-8")
            self.archive_sdk(assignment, sdk_output)
            observed = {_key(ref) for ref in context.read_set}
            observed.update(self._tool_basis(assignment, tool_receipts))
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
            return self.committer.submit(self.access, envelope)
