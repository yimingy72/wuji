"""Capture is a stored observation of bytes, never an automatic FactAssessment."""

from datetime import datetime, timezone
import hashlib
from uuid import uuid4

from wuji_core.contracts.envelopes import CaptureEnvelope, EvidenceReceipt
from wuji_core.contracts.knowledge import ObservationRecord
from wuji_core.evidence.artifacts import (
    require_collector,
    bound_attempt,
    capture_disposition,
)
from wuji_core.http.json_boundary import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text, row


class EvidenceService:
    def __init__(self, uow, artifacts):
        self.uow, self.artifacts = uow, artifacts

    def ingest(
        self, authenticated_collector, envelope: CaptureEnvelope, *, original_json=None
    ):
        access = authenticated_collector
        require_collector(access)
        source = (
            strict_json_loads(original_json)
            if original_json is not None
            else envelope.model_dump(mode="json")
        )
        if CaptureEnvelope.model_validate(source) != envelope:
            raise DomainError("INVALID_SCHEMA", 422)
        serialized = canonical_json_bytes(source)
        digest = hashlib.sha256(serialized).hexdigest()
        identity = envelope.identity
        if identity.tenant_id != access.principal.tenant_id:
            raise DomainError("FORBIDDEN_COLLECTOR", 403)
        with self.uow.transaction(
            access, identity.task_id, capability="evidence"
        ) as tx:
            attempt = bound_attempt(tx, envelope.tool_attempt_id)
            expected = {
                **dict(zip(("tenant_id", "project_id", "task_id"), tx.owner)),
                **{
                    key: str(attempt[key])
                    for key in (
                        "work_item_id",
                        "agent_run_id",
                        "receiver_id",
                        "execution_epoch",
                        "run_epoch",
                        "runtime_attempt",
                    )
                },
            }
            if (
                identity.model_dump(mode="json") != expected
                or attempt["tool_call_id"] != envelope.tool_call_id
            ):
                raise DomainError("FORBIDDEN_COLLECTOR", 403)
            # Current read and stored collector binding checked before returning old data.
            previous = row(
                tx.connection.execute(
                    "SELECT * FROM vnext.evidence_receipt WHERE tenant_id=%s AND task_id=%s AND operation_kind='evidence_ingest' AND capture_id=%s",
                    (tx.owner[0], tx.owner[2], envelope.capture_id),
                )
            )
            if previous:
                if previous["input_digest"] != digest:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                return EvidenceReceipt.model_validate(
                    strict_json_loads(previous["receipt_json"])
                )
            disposition = capture_disposition(tx, attempt)
            if (
                envelope.evidence_origin.value != attempt["evidence_origin"]
                or envelope.capture_layer != attempt["capture_layer"]
            ):
                raise DomainError("INVALID_REFERENCE", 422)
            records = {}
            for ref in sorted(
                envelope.artifact_refs, key=lambda ref: (ref.id, int(ref.version.root))
            ):
                key = (ref.id, ref.version.root)
                if key in records:
                    raise DomainError("INVALID_REFERENCE", 422)
                record = self.artifacts.record(tx, ref, lock=True)
                if (
                    record["state"] != "sealed"
                    or record["provenance"] != "capture"
                    or record["tool_attempt_id"] != envelope.tool_attempt_id
                    or record["environment_ref"] != attempt["environment_ref"]
                    or record["capture_layer"] != envelope.capture_layer
                    or record["evidence_origin"] != envelope.evidence_origin.value
                    or not all(
                        condition in [c.root for c in envelope.conditions]
                        for condition in strict_json_loads(record["conditions_json"])
                    )
                ):
                    raise DomainError("INVALID_REFERENCE", 422)
                self.artifacts.checked_bytes(record)
                records[key] = record
            completeness_values = {
                record["completeness"] for record in records.values()
            }
            required_completeness = (
                "partial"
                if "partial" in completeness_values
                else "unknown" if "unknown" in completeness_values else "complete"
            )
            if envelope.completeness.value != required_completeness:
                raise DomainError("INVALID_REFERENCE", 422)
            level = max(record["access_level"] for record in records.values())
            observation_id = str(uuid4())
            received_at = datetime.now(timezone.utc)
            observation = ObservationRecord.model_validate(
                {
                    "observation_id": observation_id,
                    "revision": "1",
                    "task_id": identity.task_id,
                    "capture_id": envelope.capture_id,
                    "tool_attempt_id": envelope.tool_attempt_id,
                    "collector_ref": access.principal.subject,
                    "artifact_refs": [
                        r.model_dump(mode="json") for r in envelope.artifact_refs
                    ],
                    "capture_layer": envelope.capture_layer,
                    "observed_at": envelope.observed_at,
                    "received_at": received_at,
                    "environment_ref": attempt["environment_ref"],
                    "conditions": [c.root for c in envelope.conditions],
                    "completeness": envelope.completeness.value,
                    "evidence_origin": envelope.evidence_origin.value,
                }
            )
            tx.connection.execute(
                """INSERT INTO vnext.observation(tenant_id,project_id,task_id,entity_id,revision,
                capture_id,tool_attempt_id,collector_ref,capture_layer,observed_at,received_at,environment_ref,
                conditions_json,completeness,evidence_origin,access_level) VALUES (%s,%s,%s,%s,1,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    *tx.owner,
                    observation_id,
                    envelope.capture_id,
                    envelope.tool_attempt_id,
                    access.principal.subject,
                    observation.capture_layer,
                    observation.observed_at,
                    received_at,
                    observation.environment_ref,
                    json_text([c.root for c in envelope.conditions]),
                    observation.completeness.value,
                    observation.evidence_origin.value,
                    level,
                ),
            )
            tx.connection.execute(
                "INSERT INTO vnext.publication(tenant_id,project_id,task_id,publication_id,kind,access_level) VALUES (%s,%s,%s,%s,'observation',%s)",
                (*tx.owner, observation_id, level),
            )
            for ordinal, ref in enumerate(envelope.artifact_refs):
                tx.connection.execute(
                    "INSERT INTO vnext.observation_artifact(tenant_id,project_id,task_id,observation_id,observation_revision,ordinal,artifact_id,artifact_revision,access_level) VALUES (%s,%s,%s,%s,1,%s,%s,%s,%s)",
                    (
                        *tx.owner,
                        observation_id,
                        ordinal,
                        ref.id,
                        ref.version.root,
                        level,
                    ),
                )
                tx.connection.execute(
                    "INSERT INTO vnext.publication_ref(tenant_id,project_id,task_id,publication_id,artifact_id,artifact_revision,access_level) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (*tx.owner, observation_id, ref.id, ref.version.root, level),
                )
                tx.connection.execute(
                    "DELETE FROM vnext.artifact_lease WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND artifact_id=%s AND artifact_revision=%s AND lease_owner='staging'",
                    (*tx.owner, ref.id, ref.version.root),
                )
            receipt = EvidenceReceipt.model_validate(
                {
                    "capture_id": envelope.capture_id,
                    "status": disposition,
                    "observation_ref": {
                        "entity_type": "observation",
                        "id": observation_id,
                        "revision": "1",
                    },
                    "artifact_refs": [
                        r.model_dump(mode="json") for r in envelope.artifact_refs
                    ],
                    "request_id": access.request_id,
                }
            )
            tx.connection.execute(
                """INSERT INTO vnext.evidence_receipt(tenant_id,project_id,task_id,capture_id,input_digest,original_envelope,status,observation_id,observation_revision,receipt_json,access_level)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,1,%s,%s)""",
                (
                    *tx.owner,
                    envelope.capture_id,
                    digest,
                    serialized.decode("utf-8"),
                    disposition,
                    observation_id,
                    json_text(receipt.model_dump(mode="json")),
                    level,
                ),
            )
            tx.semantic_event(
                "evidence_ingested",
                {
                    "capture_id": envelope.capture_id,
                    "observation_ref": receipt.observation_ref.model_dump(mode="json"),
                    "status": disposition,
                },
                observations=1,
                access_level=level,
            )
            return receipt
