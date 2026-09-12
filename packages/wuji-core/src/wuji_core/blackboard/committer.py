"""Raw-first result admission and recoverable, atomic component publication."""

from hashlib import sha256
from pydantic import ValidationError
import psycopg

from wuji_core.contracts.envelopes import ResultEnvelope, ResultReceipt, AgentPayload
from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.evidence.artifacts import bound_run, run_disposition
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


class ResultCommitter:
    def __init__(self, uow, artifacts, claims):
        self.uow, self.artifacts, self.claims = uow, artifacts, claims

    def receive(self, access, envelope):
        """Durable phase one. This port never runs an Agent or a tool."""
        envelope = ResultEnvelope.model_validate(envelope)
        task_id = envelope.identity.task_id
        canonical = json_text(envelope.model_dump(mode="python"))
        digest = sha256(canonical.encode()).hexdigest()
        with self.uow.transaction(access, task_id, capability="model_output") as tx:
            run = bound_run(tx, envelope.identity.agent_run_id, envelope.identity)
            run_disposition(tx, run)
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
        with self.uow.transaction(access, task_id, capability="model_output") as tx:
            run_disposition(
                tx, bound_run(tx, envelope.identity.agent_run_id, envelope.identity)
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

    def lookup(self, access, task_id, submission_id):
        with self.uow.transaction(access, task_id, capability="model_output") as tx:
            submission = self._submission(tx, submission_id)
            bound_run(tx, submission["agent_run_id"])
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
        if value is None or value["writer_subject"] != tx.access.principal.subject:
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

    def reconcile(self, access, task_id, submission_id):
        with self.uow.transaction(access, task_id, capability="model_output") as tx:
            submission = self._submission(tx, submission_id)
            envelope = ResultEnvelope.model_validate(
                strict_json_loads(submission["envelope_json"])
            )
            bound_run(tx, envelope.identity.agent_run_id, envelope.identity)
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
        with self.uow.transaction(access, task_id, capability="model_output") as tx:
            submission = self._submission(tx, submission_id)
            run = bound_run(tx, envelope.identity.agent_run_id, envelope.identity)
            disposition = run_disposition(tx, run)
            final = self._final(tx, submission_id)
            if final:
                return final
            components = []
            level = submission["access_level"]
            code = parse_code
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
            tx.semantic_event(
                "result_committed", final.model_dump(mode="python"), access_level=level
            )
            return final
