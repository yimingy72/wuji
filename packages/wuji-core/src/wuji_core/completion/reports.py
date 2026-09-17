"""P12 report commits: frozen bytes, and late counter-evidence as amendments.

The report body is composed from persisted facts at freeze time and stored with
the digest the platform computed. A later amendment cites sealed evidence,
appends one dispute record and flips the commit's dispute state; it never
touches the frozen body, never reopens the Task and never creates ready work
(AC-053).
"""

from dataclasses import dataclass

from wuji_core.completion import platform_errors
from wuji_core.contracts.envelopes import BlobRef
from wuji_core.http import canonical_json_bytes
from wuji_core.persistence.uow import DomainError

CONTROL_ROLES = frozenset({"controller", "reconciler"})
REPORT_SCHEMA = "wuji.report.v1"


@dataclass(frozen=True)
class ReportReceipt:
    report_id: str
    body_digest: str
    dispute_state: str
    close_trigger: str
    result_outcome: str


@dataclass(frozen=True)
class AmendmentReceipt:
    amendment_id: str
    report_id: str
    authority: str
    evidence: tuple[dict, ...]
    access_level: int


class ReportService:
    """Freeze what was delivered, then keep later evidence honest."""

    def __init__(self, uow, *, artifacts):
        if not callable(getattr(artifacts, "record", None)) or not callable(
            getattr(artifacts, "checked_bytes", None)
        ):
            raise ValueError("the real artifact store is required")
        self.uow = uow
        self.artifacts = artifacts

    def _compose_body(self, tx, *, task, epoch_id):
        criteria = [
            {
                "criterion_id": row[0],
                "revision": str(row[1]),
                "status": row[2] or "missing",
                "applicability": row[3] or "missing",
            }
            for row in tx.connection.execute(
                "SELECT c.criterion_id,c.revision,j.status,j.applicability"
                " FROM vnext.goal_criterion c"
                " LEFT JOIN vnext.criterion_judgment j ON"
                " (j.tenant_id,j.project_id,j.task_id,j.judgment_id)="
                " (c.tenant_id,c.project_id,c.task_id,c.current_judgment_id)"
                " WHERE c.tenant_id=%s AND c.project_id=%s AND c.task_id=%s"
                " ORDER BY c.criterion_id,c.revision",
                tx.owner,
            ).fetchall()
        ]
        work = [
            {"kind": row[0], "state": row[1], "terminal_reason": row[2]}
            for row in tx.connection.execute(
                "SELECT kind,state,terminal_reason FROM vnext.work_item"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s ORDER BY kind,work_item_id",
                tx.owner,
            ).fetchall()
        ]
        runs = [
            {
                "agent_run_id": row[0],
                "process_state": row[1],
                "stop_kind": row[2],
                "result_state": row[3],
            }
            for row in tx.connection.execute(
                "SELECT agent_run_id,process_state,stop_kind,result_state FROM vnext.agent_run"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s ORDER BY agent_run_id",
                tx.owner,
            ).fetchall()
        ]
        return canonical_json_bytes(
            {
                "schema_version": REPORT_SCHEMA,
                "task_id": tx.owner[2],
                "epoch_id": epoch_id,
                "close_trigger": task["close_trigger"],
                "result_outcome": task["result_outcome"],
                "criteria": criteria,
                "work_items": work,
                "runs": runs,
            }
        ).decode()

    def freeze(self, access, task_id, *, report_key, epoch_id) -> ReportReceipt:
        """Compose and freeze the delivered report; only after the close."""

        if (
            not CONTROL_ROLES.intersection(access.principal.roles)
            or "agent" in access.principal.roles
        ):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        if not isinstance(report_key, str) or not 1 <= len(report_key) <= 256:
            raise ValueError("a bounded report key is required")
        if not isinstance(epoch_id, str) or not 1 <= len(epoch_id) <= 256:
            raise ValueError("the closed epoch is required")
        with self.uow.transaction(access, task_id, capability="control") as tx:
            task = tx.task
            if task["observed_state"] != "closed" or task["completion_epoch_id"] != epoch_id:
                raise DomainError("completion_not_closed", 409)
            body = self._compose_body(tx, task=task, epoch_id=epoch_id)
            with platform_errors():
                stored = tx.connection.execute(
                    "SELECT vnext.freeze_report_commit(%s,%s,%s,%s,%s,%s,%s)",
                    (*tx.owner, report_key, epoch_id, body, tx.permissions["clearance"]),
                ).fetchone()[0]
            row = tx.connection.execute(
                "SELECT body_digest,dispute_state,close_trigger,result_outcome FROM vnext.report_commit"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND report_id=%s",
                (*tx.owner, stored),
            ).fetchone()
        return ReportReceipt(
            report_id=stored,
            body_digest=row[0],
            dispute_state=row[1],
            close_trigger=row[2],
            result_outcome=row[3],
        )

    def amend(
        self,
        access,
        task_id,
        *,
        report_key,
        amendment_key,
        reason,
        evidence_refs,
    ) -> AmendmentReceipt:
        """Append late counter-evidence; the frozen body never changes."""

        if "assessor" in access.principal.roles and "agent" not in access.principal.roles:
            authority, capability = "assessor", "assess"
        elif CONTROL_ROLES.intersection(access.principal.roles) and "agent" not in access.principal.roles:
            authority, capability = "controller", "control"
        else:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        if not isinstance(reason, str) or not 1 <= len(reason) <= 2048:
            raise DomainError("INVALID_SCHEMA", 422)
        if not isinstance(evidence_refs, (list, tuple)) or not evidence_refs:
            raise DomainError("INVALID_REFERENCE", 422)
        refs = tuple(BlobRef.model_validate(ref) for ref in evidence_refs)
        level = 0
        checked = []
        with self.uow.transaction(access, task_id, capability=capability) as tx:
            for ref in refs:
                record = self.artifacts.record(tx, ref)
                if record is None or record["state"] != "sealed":
                    raise DomainError("INVALID_REFERENCE", 422)
                body = self.artifacts.checked_bytes(record)
                from hashlib import sha256

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
        source = canonical_json_bytes(
            {
                "amendment_id": amendment_key,
                "report_id": report_key,
                "reason": reason,
                "authority": authority,
                "evidence": checked,
                "access_level": level,
            }
        ).decode()
        with self.uow.transaction(access, task_id, capability=capability) as tx:
            with platform_errors():
                stored = tx.connection.execute(
                    "SELECT vnext.amend_report_commit(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        *tx.owner,
                        report_key,
                        amendment_key,
                        reason,
                        canonical_json_bytes({"evidence": checked}).decode(),
                        source,
                        authority,
                        level,
                    ),
                ).fetchone()[0]
        return AmendmentReceipt(
            amendment_id=stored,
            report_id=report_key,
            authority=authority,
            evidence=tuple(checked),
            access_level=level,
        )

    def read(self, access, task_id, report_key):
        """The frozen body plus its dispute records, for operator inspection."""

        with self.uow.transaction(access, task_id, capability="read") as tx:
            commit = tx.connection.execute(
                "SELECT body_json,body_digest,dispute_state,close_trigger,result_outcome,epoch_id"
                " FROM vnext.report_commit"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND report_id=%s",
                (*tx.owner, report_key),
            ).fetchone()
            if commit is None:
                return None
            amendments = tx.connection.execute(
                "SELECT amendment_id,reason,authority,source_receipt_json FROM vnext.report_amendment"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND report_id=%s"
                " ORDER BY amendment_id",
                (*tx.owner, report_key),
            ).fetchall()
        return {
            "body": commit[0],
            "body_digest": commit[1],
            "dispute_state": commit[2],
            "close_trigger": commit[3],
            "result_outcome": commit[4],
            "epoch_id": commit[5],
            "amendments": tuple(amendments),
        }
