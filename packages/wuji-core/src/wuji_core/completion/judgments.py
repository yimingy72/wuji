"""P12 Goal judgments recorded from sealed, exactly-referenced evidence.

A judgment is an assessment: only an ``assessor`` principal with ``can_assess``
may write one, the cited artifacts must exist, be sealed and be readable at the
declared level, and the receipt keeps exactly the references and digests that
were checked. The current pointer moves only forward, so evidence about a
superseded revision is recorded without silently defining the Goal (AC-034,
AC-051, AC-053).
"""

from dataclasses import dataclass
from hashlib import sha256

from wuji_core.completion import platform_errors
from wuji_core.contracts.envelopes import BlobRef
from wuji_core.http import canonical_json_bytes
from wuji_core.persistence.uow import DomainError, row

STATUSES = ("met", "not_met", "unknown", "not_applicable")
APPLICABILITIES = ("current", "stale", "disputed", "retracted")


@dataclass(frozen=True)
class JudgmentReceipt:
    judgment_id: str
    criterion_id: str
    revision: str
    status: str
    applicability: str
    method: str
    evidence: tuple[dict, ...]
    access_level: int
    recorded_at: str


class JudgmentService:
    """Write accepted Goal judgments; never accepts a model's own claim."""

    def __init__(self, uow, *, artifacts):
        if not callable(getattr(artifacts, "record", None)) or not callable(
            getattr(artifacts, "checked_bytes", None)
        ):
            raise ValueError("the real artifact store is required")
        self.uow = uow
        self.artifacts = artifacts

    def _authorize(self, tx):
        if (
            "assessor" not in tx.access.principal.roles
            or "agent" in tx.access.principal.roles
            or not tx.permissions["can_assess"]
        ):
            raise DomainError("FORBIDDEN_ASSESSOR", 403)

    def record(
        self,
        access,
        task_id,
        *,
        criterion_id,
        revision,
        judgment_id,
        status,
        applicability="current",
        method,
        evidence_refs,
        definition_json,
    ) -> JudgmentReceipt:
        if status not in STATUSES or applicability not in APPLICABILITIES:
            raise DomainError("INVALID_SCHEMA", 422)
        if not isinstance(evidence_refs, (list, tuple)) or not evidence_refs:
            # A judgment without evidence is an assertion, not an assessment.
            raise DomainError("INVALID_REFERENCE", 422)
        if not isinstance(method, str) or not 1 <= len(method) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        if not isinstance(definition_json, str) or not 2 <= len(definition_json) <= 65536:
            raise DomainError("INVALID_SCHEMA", 422)
        refs = tuple(BlobRef.model_validate(ref) for ref in evidence_refs)
        level = 0
        checked = []
        with self.uow.transaction(access, task_id, capability="assess") as tx:
            self._authorize(tx)
            for ref in refs:
                record = self.artifacts.record(tx, ref)
                if record is None or record["state"] != "sealed":
                    raise DomainError("INVALID_REFERENCE", 422)
                body = self.artifacts.checked_bytes(record)
                checked.append(
                    {
                        "ref": ref.model_dump(mode="json"),
                        "digest": sha256(body).hexdigest(),
                        "access_level": int(record["access_level"]),
                    }
                )
                level = max(level, int(record["access_level"]))
            if level > tx.permissions["clearance"]:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        # The receipt is a pure function of the checked inputs: re-running the
        # same judgment must replay the stored row instead of colliding on a
        # fresh timestamp.
        receipt = JudgmentReceipt(
            judgment_id=judgment_id,
            criterion_id=criterion_id,
            revision=str(revision),
            status=status,
            applicability=applicability,
            method=method,
            evidence=tuple(checked),
            access_level=level,
            recorded_at="",
        )
        source = canonical_json_bytes(receipt.__dict__).decode()
        with self.uow.transaction(access, task_id, capability="assess") as tx:
            self._authorize(tx)
            with platform_errors():
                stored = tx.connection.execute(
                    "SELECT vnext.record_criterion_judgment(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        *tx.owner,
                        criterion_id,
                        revision,
                        judgment_id,
                        status,
                        applicability,
                        method,
                        definition_json,
                        source,
                        level,
                    ),
                ).fetchone()
        if stored is None or stored[0] != judgment_id:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        return receipt

    def current(self, access, task_id, criterion_id):
        """The judgment the Goal would read today, for operator inspection."""

        with self.uow.transaction(access, task_id, capability="read") as tx:
            record = row(
                tx.connection.execute(
                    "SELECT j.judgment_id,j.status,j.applicability,c.revision"
                    " FROM vnext.goal_criterion c"
                    " JOIN vnext.criterion_judgment j ON"
                    " (j.tenant_id,j.project_id,j.task_id,j.judgment_id)="
                    " (c.tenant_id,c.project_id,c.task_id,c.current_judgment_id)"
                    " WHERE c.tenant_id=%s AND c.project_id=%s AND c.task_id=%s"
                    " AND c.criterion_id=%s ORDER BY c.revision DESC LIMIT 1",
                    (*tx.owner, criterion_id),
                )
            )
        return record
