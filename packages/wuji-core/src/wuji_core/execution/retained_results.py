"""Receiver-bound authority for exact bytes retained by a registered Worker."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256

from wuji_core.contracts.envelopes import RunIdentity, WorkerAssignment
from wuji_core.http import canonical_json_bytes
from wuji_core.persistence.uow import DomainError, row
from wuji_core.scheduling.credentials import worker_subject


@dataclass(frozen=True)
class RetainedResultKey:
    agent_run_id: str
    operation_id: str
    assignment_digest: str

    @classmethod
    def from_assignment(cls, assignment) -> "RetainedResultKey":
        assignment = WorkerAssignment.model_validate(assignment)
        return cls(
            agent_run_id=assignment.identity.agent_run_id,
            operation_id=assignment.operation_id,
            assignment_digest=sha256(
                canonical_json_bytes(assignment.model_dump(mode="json"))
            ).hexdigest(),
        )

    def document(self) -> dict[str, str]:
        return {
            "agent_run_id": self.agent_run_id,
            "operation_id": self.operation_id,
            "assignment_digest": self.assignment_digest,
        }


def bound_retained_run(
    tx,
    key: RetainedResultKey,
    identity: RunIdentity | None = None,
):
    """Recheck the exact SQL-opened receiver/source binding in this transaction."""
    if (
        tx.purpose != "retained_result"
        or not isinstance(key, RetainedResultKey)
        or not isinstance(tx.retained_result, dict)
        or tx.retained_result.get("disposition")
        not in {"accepted", "historical_only"}
    ):
        raise DomainError("NOT_FOUND_OR_FORBIDDEN", 403)
    selected = tx.connection.execute(
        """SELECT current_setting('wuji.retained_run',true),
        current_setting('wuji.retained_assignment_digest',true)"""
    ).fetchone()
    source_writer = tx.retained_result.get("source_writer_subject")
    if (
        selected != (key.agent_run_id, key.assignment_digest)
        or source_writer != worker_subject(key.agent_run_id)
        or source_writer == tx.access.principal.subject
        or type(tx.retained_result.get("access_level")) is not int
        or tx.retained_result["access_level"] > tx.permissions["clearance"]
    ):
        raise DomainError("NOT_FOUND_OR_FORBIDDEN", 403)
    record = row(
        tx.connection.execute(
            """SELECT a.*,w.agent_subject,
            w.can_settle AS binding_can_settle
            FROM vnext.agent_run a JOIN vnext.run_writer w
              USING(tenant_id,project_id,task_id,agent_run_id)
            WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s
              AND a.agent_run_id=%s AND a.start_operation_id=%s
              AND w.subject=%s AND NOT w.revoked AND NOT w.can_settle""",
            (
                *tx.owner,
                key.agent_run_id,
                key.operation_id,
                source_writer,
            ),
        )
    )
    if record is None:
        raise DomainError("NOT_FOUND_OR_FORBIDDEN", 403)
    if identity is not None:
        identity = RunIdentity.model_validate(identity)
        if any(
            str(record[field]) != str(value)
            for field, value in identity.model_dump(mode="json").items()
        ):
            raise DomainError("STALE_EXECUTION", 403)
    return record


class RetainedResultAuthority:
    """Open only the migration-registered receiver binding for one Assignment."""

    def __init__(self, uow):
        self.uow = uow

    @contextmanager
    def transaction(self, access, assignment):
        assignment = WorkerAssignment.model_validate(assignment)
        key = RetainedResultKey.from_assignment(assignment)
        with self.uow.transaction(
            access,
            assignment.identity.task_id,
            capability="retained_result",
            retained_result=key.document(),
        ) as tx:
            run = bound_retained_run(tx, key, assignment.identity)
            yield tx, run, key, tx.retained_result["disposition"]


class RetainedResultService:
    """Route retained bytes to the same PlatformWorkerHost result implementation."""

    def __init__(self, host_factory):
        if not callable(host_factory):
            raise ValueError("retained PlatformWorkerHost factory required")
        self.host_factory = host_factory

    def _host(self, access, assignment):
        key = RetainedResultKey.from_assignment(assignment)
        host = self.host_factory(access, key)
        if host.access.principal != access.principal or host.retained_result != key:
            raise DomainError("STALE_EXECUTION", 409)
        return host

    def archive_sdk(self, access, assignment, body):
        return self._host(access, assignment).archive_sdk(assignment, body)

    def submit_result(self, access, assignment, **values):
        return self._host(access, assignment).submit_result(assignment, **values)
