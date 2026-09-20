"""Raw-first result admission and recoverable, atomic component publication."""

from hashlib import sha256
from pydantic import ValidationError
import psycopg

from wuji_core.contracts.envelopes import ResultEnvelope, ResultReceipt, AgentPayload
from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.evidence.artifacts import bound_run, run_disposition
from wuji_core.execution.retained_results import (
    RetainedResultKey,
    bound_retained_run,
)
from wuji_core.persistence.uow import DomainError, row, json_text
from wuji_core.persistence.snapshots import SnapshotRepository
from wuji_core.http.json_boundary import (
    strict_json_loads,
    canonical_json_bytes,
    InvalidJsonDocument,
)
from wuji_core.blackboard.relations import actor, resolve, batch_order
from wuji_core.blackboard.claims import receipt
from wuji_core.blackboard.fact_view import inputs_current
from wuji_core.blackboard.result_state import project_submission


class ResultCommitter:
    def __init__(self, uow, artifacts, claims):
        self.uow, self.artifacts, self.claims = uow, artifacts, claims

    def _transaction(self, access, task_id, retained):
        if retained is None:
            return self.uow.transaction(access, task_id, capability="model_output")
        return self.uow.transaction(
            access,
            task_id,
            capability="retained_result",
            retained_result=retained.document(),
        )

    @staticmethod
    def _bound(tx, run_id, identity, retained):
        if retained is None:
            run = bound_run(tx, run_id, identity)
            return run, run_disposition(tx, run)
        run = bound_retained_run(tx, retained, identity)
        if run["agent_run_id"] != run_id:
            raise DomainError("STALE_EXECUTION", 403)
        return run, tx.retained_result["disposition"]

    def receive(self, access, envelope):
        return self._receive(access, envelope, retained=None)

    def receive_retained(self, access, envelope, *, retained: RetainedResultKey):
        if not isinstance(retained, RetainedResultKey):
            raise DomainError("INVALID_REFERENCE", 422)
        return self._receive(access, envelope, retained=retained)

    def _receive(self, access, envelope, *, retained):
        """Durable phase one. This port never runs an Agent or a tool."""
        envelope = ResultEnvelope.model_validate(envelope)
        task_id = envelope.identity.task_id
        canonical = json_text(envelope.model_dump(mode="python"))
        digest = sha256(canonical.encode()).hexdigest()
        with self._transaction(access, task_id, retained) as tx:
            run, _disposition = self._bound(
                tx, envelope.identity.agent_run_id, envelope.identity, retained
            )
            artifact = self.artifacts.record(tx, envelope.raw_output_ref)
            if (
                artifact["state"] != "sealed"
                or artifact["provenance"] != "model_output"
                or artifact["agent_run_id"] != run["agent_run_id"]
                or artifact["writer_subject"] != access.principal.subject
                or artifact["sha256"] != envelope.raw_output_digest.root
            ):
                raise DomainError("INVALID_REFERENCE", 422)
        self.artifacts.checked_bytes(artifact)
        with self._transaction(access, task_id, retained) as tx:
            run, _disposition = self._bound(
                tx, envelope.identity.agent_run_id, envelope.identity, retained
            )
            artifact = self.artifacts.record(tx, envelope.raw_output_ref, lock=True)
            old = row(
                tx.connection.execute(
                    "SELECT * FROM vnext.result_submission WHERE tenant_id=%s AND task_id=%s AND submission_id=%s",
                    (tx.owner[0], task_id, envelope.submission_id),
                )
            )
            if old:
                if old["input_digest"] != digest:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                return ResultReceipt.model_validate(
                    strict_json_loads(old["received_receipt_json"])
                )
            received = ResultReceipt.model_validate(
                dict(
                    submission_id=envelope.submission_id,
                    status="received",
                    components=[],
                    request_id=access.request_id,
                    code=None,
                )
            )
            tx.connection.execute(
                """INSERT INTO vnext.result_submission(tenant_id,project_id,task_id,submission_id,
                agent_run_id,writer_subject,input_digest,envelope_json,received_receipt_json,artifact_id,artifact_revision,access_level)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    *tx.owner,
                    envelope.submission_id,
                    run["agent_run_id"],
                    access.principal.subject,
                    digest,
                    canonical,
                    json_text(received.model_dump(mode="python")),
                    artifact["entity_id"],
                    artifact["revision"],
                    artifact["access_level"],
                ),
            )
            project_submission(tx, run["agent_run_id"], envelope.submission_id)
            publication = "result:" + envelope.submission_id
            tx.connection.execute(
                "INSERT INTO vnext.publication(tenant_id,project_id,task_id,publication_id,kind,access_level) VALUES(%s,%s,%s,%s,'result_submission',%s)",
                (*tx.owner, publication, artifact["access_level"]),
            )
            tx.connection.execute(
                """INSERT INTO vnext.publication_ref(tenant_id,project_id,task_id,publication_id,
                artifact_id,artifact_revision,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                (
                    *tx.owner,
                    publication,
                    artifact["entity_id"],
                    artifact["revision"],
                    artifact["access_level"],
                ),
            )
            return received

    def submit(self, access, envelope):
        envelope = ResultEnvelope.model_validate(envelope)
        self.receive(access, envelope)
        return self.reconcile(access, envelope.identity.task_id, envelope.submission_id)

    def submit_retained(self, access, envelope, *, retained: RetainedResultKey):
        envelope = ResultEnvelope.model_validate(envelope)
        self.receive_retained(access, envelope, retained=retained)
        return self.reconcile_retained(
            access,
            envelope.identity.task_id,
            envelope.submission_id,
            retained=retained,
        )

    def lookup(self, access, task_id, submission_id):
        return self._lookup(access, task_id, submission_id, retained=None)

    def lookup_retained(
        self, access, task_id, submission_id, *, retained: RetainedResultKey
    ):
        return self._lookup(access, task_id, submission_id, retained=retained)

    def _lookup(self, access, task_id, submission_id, *, retained):
        with self._transaction(access, task_id, retained) as tx:
            submission = self._submission(tx, submission_id)
            self._bound(tx, submission["agent_run_id"], None, retained)
            final = self._final(tx, submission_id)
            return final or ResultReceipt.model_validate(
                strict_json_loads(submission["received_receipt_json"])
            )

    def _submission(self, tx, submission_id):
        value = row(
            tx.connection.execute(
                "SELECT * FROM vnext.result_submission WHERE tenant_id=%s AND task_id=%s AND submission_id=%s",
                (tx.owner[0], tx.owner[2], submission_id),
            )
        )
        allowed_writers = {tx.access.principal.subject}
        if tx.purpose == "retained_result" and tx.retained_result:
            allowed_writers.add(tx.retained_result["source_writer_subject"])
        if value is None or value["writer_subject"] not in allowed_writers:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        return value

    def _final(self, tx, submission_id):
        value = tx.connection.execute(
            "SELECT receipt_json FROM vnext.result_receipt WHERE tenant_id=%s AND task_id=%s AND submission_id=%s",
            (tx.owner[0], tx.owner[2], submission_id),
        ).fetchone()
        return (
            ResultReceipt.model_validate(strict_json_loads(value[0])) if value else None
        )

    def reconcile(self, access, task_id, submission_id, *, result_policy=None):
        return self._reconcile(
            access,
            task_id,
            submission_id,
            retained=None,
            result_policy=result_policy,
        )

    def reconcile_retained(
        self,
        access,
        task_id,
        submission_id,
        *,
        retained: RetainedResultKey,
        result_policy=None,
    ):
        return self._reconcile(
            access,
            task_id,
            submission_id,
            retained=retained,
            result_policy=result_policy,
        )

    def _reconcile(
        self, access, task_id, submission_id, *, retained, result_policy=None
    ):
        if result_policy not in {
            None,
            "reject_invalid_reference",
            "initial_reason_empty_basis",
            "reason_intent_supported_basis",
        }:
            raise ValueError("unsupported prevalidated result policy")
        with self._transaction(access, task_id, retained) as tx:
            submission = self._submission(tx, submission_id)
            envelope = ResultEnvelope.model_validate(
                strict_json_loads(submission["envelope_json"])
            )
            self._bound(
                tx, envelope.identity.agent_run_id, envelope.identity, retained
            )
            final = self._final(tx, submission_id)
            if final:
                return final
            artifact = self.artifacts.record(tx, envelope.raw_output_ref)
        # Read immutable raw bytes and validate structure outside the publishing transaction.
        payload = None
        parse_code = None
        try:
            parsed = strict_json_loads(
                self.artifacts.checked_bytes(artifact).decode("utf-8")
            )
            if envelope.payload is not None and canonical_json_bytes(
                [parsed]
            ) != canonical_json_bytes([envelope.payload]):
                raise ValueError("payload differs from sealed output")
            payload = AgentPayload.model_validate(parsed)
        except (ValueError, ValidationError, InvalidJsonDocument, DomainError):
            parse_code = "INVALID_SCHEMA"
        if payload is not None:
            if result_policy == "initial_reason_empty_basis":
                payload = payload.model_copy(
                    update={
                        "intent_proposals": [
                            proposal.model_copy(update={"basis_refs": []})
                            for proposal in payload.intent_proposals
                        ]
                    }
                )
            elif result_policy == "reason_intent_supported_basis":
                payload = payload.model_copy(
                    update={
                        "intent_proposals": [
                            proposal.model_copy(
                                update={
                                    "basis_refs": [
                                        ref
                                        for ref in proposal.basis_refs
                                        if not isinstance(ref.root, KnowledgeRef)
                                        or ref.root.entity_type.value
                                        in {"claim", "observation"}
                                    ]
                                }
                            )
                            for proposal in payload.intent_proposals
                        ]
                    }
                )
        with self._transaction(access, task_id, retained) as tx:
            submission = self._submission(tx, submission_id)
            run, disposition = self._bound(
                tx, envelope.identity.agent_run_id, envelope.identity, retained
            )
            final = self._final(tx, submission_id)
            if final:
                return final
            components = []
            level = submission["access_level"]
            code = (
                "INVALID_REFERENCE"
                if result_policy == "reject_invalid_reference"
                else parse_code
            )
            if not code:
                try:
                    manifest = SnapshotRepository(self.uow)._get(
                        tx, envelope.snapshot_id
                    )
                    for ref in envelope.read_set:
                        if ref not in manifest.refs:
                            raise DomainError("INVALID_REFERENCE", 422)
                        resolve(tx, ref)
                    stale = not inputs_current(tx, envelope.read_set)
                except DomainError as error:
                    code = error.code
                    stale = False
                if not code and disposition != "historical_only":
                    who = actor(tx, run["agent_subject"])
                    entries = [("claim", p) for p in payload.claims] + [
                        ("intent", p) for p in payload.intent_proposals
                    ]
                    ordered, _invalid = batch_order(entries)
                    local = {}
                    receipts = {}
                    for kind, p in ordered:
                        try:
                            # Component savepoint rolls back its domain + registry + relations together.
                            with tx.connection.transaction():
                                item, item_level = self.claims.append(
                                    tx,
                                    p,
                                    kind=kind,
                                    who=who,
                                    local=local,
                                    run_id=run["agent_run_id"],
                                    stale=stale,
                                )
                            local[p.client_ref] = item.canonical_ref
                            receipts[p.client_ref] = item
                            level = max(level, item_level)
                        except DomainError as error:
                            receipts[p.client_ref] = receipt(
                                p.client_ref, access.request_id, code=error.code
                            )
                        except psycopg.IntegrityError:
                            receipts[p.client_ref] = receipt(
                                p.client_ref,
                                access.request_id,
                                code="INVALID_REFERENCE",
                            )
                    components = [
                        receipts.get(p.client_ref)
                        or receipt(
                            p.client_ref, access.request_id, code="INVALID_REFERENCE"
                        )
                        for _, p in entries
                    ]
            status = "rejected" if code else disposition
            final = ResultReceipt.model_validate(
                dict(
                    submission_id=submission_id,
                    status=status,
                    components=components,
                    request_id=access.request_id,
                    code=code,
                )
            )
            tx.connection.execute(
                "INSERT INTO vnext.result_receipt(tenant_id,project_id,task_id,submission_id,receipt_json,access_level) VALUES(%s,%s,%s,%s,%s,%s)",
                (
                    *tx.owner,
                    submission_id,
                    json_text(final.model_dump(mode="python")),
                    level,
                ),
            )
            project_submission(tx, run["agent_run_id"], submission_id)
            tx.semantic_event(
                "result_committed", final.model_dump(mode="python"), access_level=level
            )
            return final
