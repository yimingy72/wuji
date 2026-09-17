"""P12 precheck: may this Task start closing, judged from persisted state.

The review never binds itself to the Run that proposes completion. It opens a
read-only transaction for the caller and reads only persisted work, run and
criterion state, so

- a Reason whose Run already exited and settled is not an active dependency
  (AC-047), and
- required work that is still open cannot be frozen behind a quiescing epoch
  (AC-048).

``propose`` then writes the canonical P05 decision through the platform-owned
producer; ``apply`` hands that receipt to the existing P05 state machine.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Literal
from uuid import uuid4

from wuji_core.completion import platform_errors
from wuji_core.completion.criteria import GoalCoverage, read_coverage
from wuji_core.contracts.execution import CloseTrigger, ResultOutcome
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError

TERMINAL_WORK = frozenset({"done", "failed", "cancelled"})
# An operator that already holds can_control on that exact Task may drive the
# epoch: the decision bytes stay platform-authored and P05 still consumes them.
CONTROL_ROLES = frozenset({"controller", "reconciler", "operator"})


@dataclass(frozen=True)
class CompletionReview:
    decision: Literal["wait", "ready", "blocked"]
    reasons: tuple[str, ...]
    coverage: GoalCoverage
    open_work: tuple[str, ...]
    unsettled_runs: tuple[str, ...]

    @property
    def can_propose(self) -> bool:
        return self.decision == "ready"

    def receipt(self):
        """Canonical, bounded decision source; never carries raw Task bytes."""

        return {
            "decision": self.decision,
            "reasons": list(self.reasons),
            "open_work": list(self.open_work),
            "unsettled_runs": list(self.unsettled_runs),
            "criteria": [
                {
                    "criterion_id": item.criterion_id,
                    "revision": item.revision,
                    "required": item.required,
                    "status": item.status,
                    "applicability": item.applicability,
                }
                for item in self.coverage.criteria
            ],
        }


@dataclass(frozen=True)
class CompletionProposal:
    receipt_id: str
    epoch_id: str
    deadline: datetime
    close_trigger: str


class CompletionService:
    """P12 completion reviews over the existing P05 control state machine."""

    def __init__(self, uow, *, control):
        if getattr(control, "uow", None) is not uow or not callable(
            getattr(control, "apply_completion", None)
        ):
            raise ValueError("the P05 ControlService over the same UnitOfWork is required")
        self.uow = uow
        self.control = control

    def review_in_transaction(self, tx) -> CompletionReview:
        """Read one review from the caller's transaction, never a new one.

        Completion commands must run this *after* they hold the Task write lock:
        only then does "what I verified" equal "what I am about to freeze". A
        read-only preview uses it too, but a preview never authorizes a command.
        """

        definition = strict_json_loads(tx.task["definition_json"])
        coverage = read_coverage(tx, definition)
        rows = tx.connection.execute(
            "SELECT work_item_id,state FROM vnext.work_item"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
            tx.owner,
        ).fetchall()
        open_work = tuple(
            sorted(row[0] for row in rows if row[1] not in TERMINAL_WORK)
        )
        unsettled = tx.connection.execute(
            "SELECT agent_run_id FROM vnext.agent_run WHERE tenant_id=%s"
            " AND project_id=%s AND task_id=%s AND process_state<>'exited'"
            " ORDER BY agent_run_id",
            tx.owner,
        ).fetchall()
        unsettled_runs = tuple(row[0] for row in unsettled)

        reasons = []
        decision = "ready"
        invalidated = coverage.invalidated()
        if invalidated:
            # A stale/disputed judgment must be re-evaluated before closing: the
            # platform never treats an invalidated decision as support (AC-050).
            decision = "blocked"
            reasons.append("criteria_invalidated")
        if open_work:
            decision = "wait" if decision != "blocked" else decision
            reasons.append("required_work_open")
        if unsettled_runs:
            decision = "wait" if decision != "blocked" else decision
            reasons.append("runs_unsettled")
        if not coverage.satisfied:
            if decision != "blocked":
                decision = "wait"
            reasons.append("criteria_unmet")
        return CompletionReview(
            decision=decision,
            reasons=tuple(reasons),
            coverage=coverage,
            open_work=open_work,
            unsettled_runs=unsettled_runs,
        )

    def precheck(self, access, task_id) -> CompletionReview:
        """Read-only preview: it shows, it never authorizes."""

        with self.uow.transaction(access, task_id, capability="read") as tx:
            return self.review_in_transaction(tx)

    def propose(
        self,
        access,
        task_id,
        *,
        receipt_key,
        close_trigger=None,
        deadline_seconds=900,
        expected_review_digest=None,
    ) -> CompletionProposal:
        """Write the canonical quiescing decision; never close anything here."""

        if (
            not CONTROL_ROLES.intersection(access.principal.roles)
            or "agent" in access.principal.roles
        ):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        if not isinstance(receipt_key, str) or not 1 <= len(receipt_key) <= 256:
            raise ValueError("a bounded receipt key is required")
        if type(deadline_seconds) is not int or not 60 <= deadline_seconds <= 86400:
            raise ValueError("a bounded quiescing deadline is required")
        trigger = CloseTrigger(close_trigger or "goal_satisfied").value
        moment = datetime.now(timezone.utc)
        deadline = moment + timedelta(seconds=deadline_seconds)
        # The review is recomputed *inside* the control transaction. That lock is
        # the serialization boundary every writer of work, judgment or run state
        # already takes, so a preview that went stale in between cannot be bound
        # to the newer version (R01).
        with self.uow.transaction(access, task_id, capability="control") as tx:
            review = self.review_in_transaction(tx)
            self._require_expected_basis(review, expected_review_digest)
            if not review.can_propose:
                raise DomainError("completion_precheck_incomplete", 409)
            source = canonical_json_bytes(review.receipt()).decode()
            with platform_errors():
                receipt_id = tx.connection.execute(
                    "SELECT vnext.prepare_completion_quiesce(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        *tx.owner,
                        receipt_key,
                        str(uuid4()),
                        tx.task["control_version"],
                        tx.task["board_revision"],
                        deadline,
                        trigger,
                        source,
                    ),
                ).fetchone()[0]
            stored = self._stored_decision(tx, receipt_id)
        return CompletionProposal(
            receipt_id=receipt_id,
            epoch_id=stored["epoch_id"],
            deadline=stored["deadline"],
            close_trigger=stored["close_trigger"],
        )

    def close(
        self,
        access,
        task_id,
        *,
        receipt_key,
        epoch_id,
        close_trigger,
        result_outcome,
        deadline_seconds=900,
        expected_review_digest=None,
    ) -> CompletionProposal:
        """Write the closing decision of the Task's own completion epoch.

        The trigger and the outcome are two independent fields: a budget-exhausted
        close can still carry a partial result (AC-052).
        """

        if (
            not CONTROL_ROLES.intersection(access.principal.roles)
            or "agent" in access.principal.roles
        ):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        if not isinstance(receipt_key, str) or not 1 <= len(receipt_key) <= 256:
            raise ValueError("a bounded receipt key is required")
        if type(deadline_seconds) is not int or not 60 <= deadline_seconds <= 86400:
            raise ValueError("a bounded closing deadline is required")
        trigger = CloseTrigger(close_trigger).value
        outcome = ResultOutcome(result_outcome).value
        moment = datetime.now(timezone.utc)
        deadline = moment + timedelta(seconds=deadline_seconds)
        with self.uow.transaction(access, task_id, capability="control") as tx:
            review = self.review_in_transaction(tx)
            self._require_expected_basis(review, expected_review_digest)
            # A Goal-satisfied close may only follow a complete review. A *forced*
            # close (budget, time, no progress, operator) exists precisely to end
            # a Task whose work cannot finish: the review is recorded in the
            # receipt and P05 cancels whatever is still open (AC-052).
            if not review.can_propose and trigger == "goal_satisfied":
                raise DomainError("completion_precheck_incomplete", 409)
            source = canonical_json_bytes(
                {
                    "decision": "close",
                    "review": review.receipt(),
                    "close_trigger": trigger,
                    "result_outcome": outcome,
                    "epoch_id": epoch_id,
                }
            ).decode()
            with platform_errors():
                receipt_id = tx.connection.execute(
                    "SELECT vnext.prepare_completion_close(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        *tx.owner,
                        receipt_key,
                        epoch_id,
                        tx.task["control_version"],
                        tx.task["board_revision"],
                        deadline,
                        trigger,
                        outcome,
                        source,
                    ),
                ).fetchone()[0]
            stored = self._stored_decision(tx, receipt_id)
        return CompletionProposal(
            receipt_id=receipt_id,
            epoch_id=stored["epoch_id"],
            deadline=stored["deadline"],
            close_trigger=stored["close_trigger"],
        )

    def apply(self, access, task_id, receipt_id):
        """Consume the proposal, but only while its original basis still holds.

        P05 owns the state change; this service adds the one check P05 cannot
        make: the persisted review is recomputed inside the same control
        transaction, so a decision whose evidence moved is refused instead of
        being re-wrapped in the newer values.
        """

        return self.control.apply_completion(
            access, task_id, receipt_id, basis_check=self.basis_check
        )

    def basis_check(self, tx, decision):
        """Recompute the review under the write lock and compare exact bytes."""

        source = strict_json_loads(decision["source_receipt_json"])
        recorded = source.get("review") if decision["action"] == "close" else source
        if not isinstance(recorded, dict):
            raise DomainError("STALE_VERSION", 409)
        current = self.review_in_transaction(tx).receipt()
        if canonical_json_bytes(recorded) != canonical_json_bytes(current):
            raise DomainError("STALE_VERSION", 409)

    @staticmethod
    def _require_expected_basis(review, expected_review_digest):
        if expected_review_digest is None:
            return
        current = sha256(canonical_json_bytes(review.receipt())).hexdigest()
        if current != expected_review_digest:
            raise DomainError("STALE_VERSION", 409)

    @staticmethod
    def _stored_decision(tx, receipt_id):
        stored = tx.connection.execute(
            "SELECT epoch_id,deadline,close_trigger FROM vnext.completion_decision"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND receipt_id=%s",
            (*tx.owner, receipt_id),
        ).fetchone()
        if stored is None:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        return {"epoch_id": stored[0], "deadline": stored[1], "close_trigger": stored[2]}

    @staticmethod
    def receipt_digest(review: CompletionReview) -> str:
        return sha256(canonical_json_bytes(review.receipt())).hexdigest()
