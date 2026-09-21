"""Published predicates over canonical same-Task records, under the Task lock."""

from dataclasses import asdict, dataclass
from hashlib import sha256
from uuid import uuid4

from wuji_core.blackboard.relations import resolve
from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.execution.dependencies import result_accepted
from wuji_core.http.json_boundary import canonical_json_bytes
from wuji_core.persistence.uow import DomainError, row
from wuji_core.scheduling.triggers import _bump, require_admission, rows


@dataclass(frozen=True)
class WaitPredicate:
    kind: str
    ref_id: str
    revision: str | None = None
    predecessor_id: str | None = None

    def __post_init__(self):
        if (
            self.kind
            not in {
                "work_settled.v1",
                "work_accepted_result.v1",
                "criterion_satisfied.v1",
                "input_resolved.v1",
            }
            or not isinstance(self.ref_id, str)
            or not self.ref_id
        ):
            raise DomainError("unsupported_wait_predicate", 422)
        if self.kind == "criterion_satisfied.v1":
            if (
                not self.predecessor_id
                or not isinstance(self.revision, str)
                or not self.revision.isdecimal()
                or str(int(self.revision)) != self.revision
            ):
                raise DomainError("INVALID_REFERENCE", 422)
        elif self.revision is not None or self.predecessor_id is not None:
            raise DomainError("INVALID_REFERENCE", 422)


class WaiterRepository:
    def from_result(self, tx, wait_refs, components):
        """Current public WaitRef can identify Intent; no fake Work KnowledgeRef."""
        require_admission(tx)
        local = {
            c.local_ref: c.canonical_ref
            for c in components
            if c.canonical_ref is not None and c.code is None
        }
        result = []
        for wait in wait_refs:
            ref = wait.ref.root
            if hasattr(ref, "client_ref"):
                ref = local.get(ref.client_ref)
            if ref is None:
                raise DomainError("INVALID_REFERENCE", 422)
            ref = KnowledgeRef.model_validate(ref)
            resolve(tx, ref)
            if (
                ref.entity_type.value != "intent"
                or wait.predicate_version.root != "1"
                or wait.predicate not in {"work_settled", "work_accepted_result"}
            ):
                raise DomainError("unsupported_wait_reference", 422)
            from wuji_core.scheduling.claims import WorkRepository

            binding = WorkRepository().resolve_canonical_work(
                tx, intent_id=ref.id, intent_revision=ref.revision.root
            )
            if not binding:
                raise DomainError("wait_work_unregistered", 409)
            result.append(WaitPredicate(
                wait.predicate + ".v1", binding["canonical_work_item_id"]
            ))
        return tuple(result)

    def _evaluate(self, tx, predicate):
        if predicate.kind == "input_resolved.v1":
            value = row(
                tx.connection.execute(
                    "SELECT status FROM vnext.input_request WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND input_request_id=%s",
                    (*tx.owner, predicate.ref_id),
                )
            )
            if not value:
                return "unsatisfiable"
            if value["status"] == "resolved":
                return "satisfied"
            if value["status"] in {"cancelled", "expired"}:
                return "unsatisfiable"
            return "pending"
        work_id = (
            predicate.predecessor_id
            if predicate.kind == "criterion_satisfied.v1"
            else predicate.ref_id
        )
        work = row(
            tx.connection.execute(
                "SELECT state,current_run_id FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
                (*tx.owner, work_id),
            )
        )
        if not work:
            return "unsatisfiable"
        if predicate.kind == "work_settled.v1":
            return (
                "satisfied"
                if work["state"] in {"done", "failed", "cancelled"}
                else "pending"
            )
        if predicate.kind == "work_accepted_result.v1":
            if work["state"] == "done" and result_accepted(tx, work["current_run_id"]):
                return "satisfied"
            if work["state"] in {"done", "failed", "cancelled"}:
                return "unsatisfiable"
            return "pending"
        criterion = row(
            tx.connection.execute(
                """SELECT c.criterion_id,j.status,j.applicability FROM vnext.goal_criterion c
            LEFT JOIN vnext.criterion_judgment j ON
            (j.tenant_id,j.project_id,j.task_id,j.judgment_id,j.criterion_id,j.criterion_revision)=
            (c.tenant_id,c.project_id,c.task_id,c.current_judgment_id,c.criterion_id,c.revision)
            WHERE c.tenant_id=%s AND c.project_id=%s AND c.task_id=%s AND c.criterion_id=%s AND c.revision=%s""",
                (*tx.owner, predicate.ref_id, predicate.revision),
            )
        )
        if not criterion:
            return "unsatisfiable"
        if (
            work["state"] not in {"failed", "cancelled"}
            and criterion["status"] == "met"
            and criterion["applicability"] == "current"
        ):
            return "satisfied"
        if work["state"] in {"failed", "cancelled"}:
            return "unsatisfiable"
        return "pending"

    def register(self, tx, *, work_item_id, processing_generation, predicates):
        require_admission(tx)
        predicates = tuple(predicates)
        if not 1 <= len(predicates) <= 128 or not all(
            isinstance(p, WaitPredicate) for p in predicates
        ):
            raise DomainError("INVALID_REFERENCE", 422)
        lease = row(
            tx.connection.execute(
                "SELECT * FROM vnext.scheduler_reason_lease WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
                (*tx.owner, work_item_id),
            )
        )
        if (
            not lease
            or lease["status"] != "inflight"
            or lease["processing_generation"] != processing_generation
        ):
            raise DomainError("STALE_EXECUTION", 409)
        digest = sha256(
            canonical_json_bytes([asdict(p) for p in predicates])
        ).hexdigest()
        old = row(
            tx.connection.execute(
                "SELECT * FROM vnext.scheduler_waiter WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s AND processing_generation=%s",
                (*tx.owner, work_item_id, processing_generation),
            )
        )
        if old:
            if old["predicate_digest"] != digest:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            return old["waiter_id"]
        # Evaluate every reference before publication, without short-circuiting
        # invalid references behind a currently false earlier predicate.
        outcomes = [self._evaluate(tx, p) for p in predicates]
        waiter_id = str(uuid4())
        tx.connection.execute(
            """INSERT INTO vnext.scheduler_waiter(tenant_id,project_id,task_id,waiter_id,
            work_item_id,processing_generation,predicate_digest,status) VALUES(%s,%s,%s,%s,%s,%s,%s,'waiting')""",
            (*tx.owner, waiter_id, work_item_id, processing_generation, digest),
        )
        for ordinal, p in enumerate(predicates):
            is_work = p.kind in {"work_settled.v1", "work_accepted_result.v1"}
            is_criterion = p.kind == "criterion_satisfied.v1"
            tx.connection.execute(
                """INSERT INTO vnext.scheduler_wait_predicate(tenant_id,project_id,task_id,waiter_id,
                ordinal,kind,work_ref,criterion_id,criterion_revision,input_ref) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    *tx.owner,
                    waiter_id,
                    ordinal,
                    p.kind,
                    p.ref_id if is_work else p.predecessor_id,
                    p.ref_id if is_criterion else None,
                    p.revision,
                    p.ref_id if p.kind == "input_resolved.v1" else None,
                ),
            )
        if outcomes and all(outcome == "satisfied" for outcome in outcomes):
            self._wake(tx, waiter_id)
        elif "unsatisfiable" in outcomes:
            self._unsatisfiable(tx, waiter_id)
        return waiter_id

    def _wake(self, tx, waiter_id):
        updated = tx.connection.execute(
            "UPDATE vnext.scheduler_waiter SET status='ready' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND waiter_id=%s AND status='waiting' RETURNING waiter_id",
            (*tx.owner, waiter_id),
        ).fetchone()
        if updated:
            _bump(tx, event_key="waiter:" + waiter_id, reason="wait_satisfied")
        # No Work state, capacity or process truth is changed by a wake.

    def _unsatisfiable(self, tx, waiter_id):
        updated = tx.connection.execute(
            "UPDATE vnext.scheduler_waiter SET status='unsatisfiable' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND waiter_id=%s AND status='waiting' RETURNING waiter_id",
            (*tx.owner, waiter_id),
        ).fetchone()
        if updated:
            _bump(tx, event_key="wait-unsatisfiable:" + waiter_id,
                  reason="wait_unsatisfiable")

    def scan(self, tx):
        require_admission(tx)
        pending = rows(
            tx.connection.execute(
                "SELECT waiter_id FROM vnext.scheduler_waiter WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND status='waiting' ORDER BY waiter_id LIMIT 256",
                tx.owner,
            )
        )
        ready = []
        for value in pending:
            predicates = rows(
                tx.connection.execute(
                    "SELECT * FROM vnext.scheduler_wait_predicate WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND waiter_id=%s ORDER BY ordinal",
                    (*tx.owner, value["waiter_id"]),
                )
            )
            checks = []
            for p in predicates:
                criterion = p["kind"] == "criterion_satisfied.v1"
                predicate = WaitPredicate(
                    p["kind"],
                    p["criterion_id"] if criterion else p["input_ref"] or p["work_ref"],
                    str(p["criterion_revision"]) if criterion else None,
                    p["work_ref"] if criterion else None,
                )
                checks.append(self._evaluate(tx, predicate))
            if checks and all(check == "satisfied" for check in checks):
                self._wake(tx, value["waiter_id"])
                ready.append(value["waiter_id"])
            elif "unsatisfiable" in checks:
                self._unsatisfiable(tx, value["waiter_id"])
                ready.append(value["waiter_id"])
        return tuple(ready)
