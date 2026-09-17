"""P12 product entry: an authorized actor drives the epoch and reads the report.

This module must not become a second completion authority. It composes the
existing canonical pieces and nothing else:

- ``CompletionService.precheck`` reads persisted work, run and judgment state;
- ``CompletionService.propose``/``close`` write the platform-authored decision
  through ``prepare_completion_*``, which the P05 state machine then consumes;
- ``ReportService.freeze`` stores the delivered bytes once per epoch.

An ``operator`` that already holds ``can_control`` on that exact Task may act:
the UnitOfWork treats that as a control capability, the decision bytes stay
platform-authored, and no caller-supplied review is ever accepted. The caller
chooses only *intent* (a close trigger and a result outcome); readiness and
settlement are read from the database.
"""

from dataclasses import dataclass
from hashlib import sha256

from wuji_core.contracts.execution import CloseTrigger, ResultOutcome
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError

ACTOR_ROLES = frozenset({"operator", "controller", "reconciler"})
ACTIONS = ("quiesce", "close")
"""``user_cancel`` is deliberately absent: cancelling has its own command route."""

CLOSE_TRIGGERS = tuple(
    item.value for item in CloseTrigger if item.value != "user_cancel"
)
RESULT_OUTCOMES = tuple(item.value for item in ResultOutcome)
MAX_IDEMPOTENCY_KEY = 200


@dataclass(frozen=True)
class CompletionOutcome:
    """One product action's bounded result; never carries raw Task bytes."""

    disposition: str
    task_id: str
    observed_state: str
    desired_state: str
    control_version: int
    completion_epoch_id: str | None
    close_trigger: str | None
    result_outcome: str | None
    review: dict
    report: dict | None

    @property
    def status_code(self) -> int:
        return 200 if self.disposition == "closed" else 202

    def document(self) -> dict:
        return {
            "disposition": self.disposition,
            "task_id": self.task_id,
            "observed_state": self.observed_state,
            "desired_state": self.desired_state,
            "control_version": self.control_version,
            "completion_epoch_id": self.completion_epoch_id,
            "close_trigger": self.close_trigger,
            "result_outcome": self.result_outcome,
            "review": self.review,
            "report": self.report,
        }


class TaskCompletionPortal:
    """Operator-facing composition of the P12 decisions and the frozen report."""

    def __init__(self, uow, *, completion, reports):
        if (
            getattr(completion, "uow", None) is not uow
            or getattr(reports, "uow", None) is not uow
        ):
            raise ValueError(
                "the P12 completion and report services over the same UnitOfWork are required"
            )
        self.uow = uow
        self.completion = completion
        self.reports = reports

    # ---- reads ----------------------------------------------------------
    def review(self, access, task_id) -> dict:
        """The observable completion state plus the frozen report, if any."""

        state = self._state(access, task_id)
        return {
            "task_id": state["task_id"],
            "observed_state": state["observed_state"],
            "desired_state": state["desired_state"],
            "control_version": state["control_version"],
            "completion_epoch_id": state["completion_epoch_id"],
            "close_trigger": state["close_trigger"],
            "result_outcome": state["result_outcome"],
            "review": state["review"],
            "report": self._report_summary(self._latest_report(access, task_id)),
        }

    def read_report(self, access, task_id, report_id) -> dict | None:
        """The frozen body plus its dispute records, for authorized readers."""

        if not isinstance(report_id, str) or not 1 <= len(report_id) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        stored = self.reports.read(access, task_id, report_id)
        if stored is None:
            return None
        return {
            "report_id": report_id,
            "task_id": task_id,
            "epoch_id": stored["epoch_id"],
            "close_trigger": stored["close_trigger"],
            "result_outcome": stored["result_outcome"],
            "body": strict_json_loads(stored["body"]),
            "body_digest": stored["body_digest"],
            "dispute_state": stored["dispute_state"],
            "amendments": [
                {
                    "amendment_id": item[0],
                    "reason": item[1],
                    "authority": item[2],
                    "source_receipt": strict_json_loads(item[3]),
                }
                for item in stored["amendments"]
            ],
        }

    # ---- the product action ---------------------------------------------
    def submit(
        self,
        access,
        task_id,
        *,
        action,
        close_trigger,
        result_outcome,
        deadline_seconds=900,
        idempotency_key,
    ) -> CompletionOutcome:
        """Open the completion epoch and/or close the Task, then freeze the report."""

        self._authorize(access, idempotency_key, action, close_trigger, result_outcome,
                        deadline_seconds)
        state = self._state(access, task_id)
        if state["observed_state"] == "closed":
            # Closing already happened (possibly through the platform runner or an
            # earlier retry); the only remaining product step is the frozen report.
            return self._closed(access, state, idempotency_key)
        if action == "quiesce":
            if state["completion_epoch_id"] is None:
                proposal = self.completion.propose(
                    access,
                    task_id,
                    receipt_key=self._quiesce_key(idempotency_key, state, close_trigger),
                    close_trigger=close_trigger,
                    deadline_seconds=deadline_seconds,
                )
                self.completion.apply(access, task_id, proposal.receipt_id)
            return CompletionOutcome(
                **self._state_fields(self._state(access, task_id)),
                disposition="quiescing",
                report=None,
            )
        if state["completion_epoch_id"] is None:
            # A close decision is only meaningful inside an open epoch: the P05
            # producer refuses anything else, so the product says so up front.
            raise DomainError("completion_epoch_absent", 409)
        if close_trigger == "goal_satisfied" and state["review"]["decision"] != "ready":
            raise DomainError("completion_precheck_incomplete", 409)
        if state["review"]["unsettled_runs"]:
            # P05 refuses the close while a Run's operations are unsettled. Refuse
            # before writing a decision that could never be consumed.
            raise DomainError("completion_epoch_unsettled", 409)
        proposal = self.completion.close(
            access,
            task_id,
            receipt_key=self._close_key(idempotency_key, state, close_trigger, result_outcome),
            epoch_id=state["completion_epoch_id"],
            close_trigger=close_trigger,
            result_outcome=result_outcome,
            deadline_seconds=deadline_seconds,
        )
        self.completion.apply(access, task_id, proposal.receipt_id)
        return self._closed(access, self._state(access, task_id), idempotency_key)

    # ---- internals -------------------------------------------------------
    @staticmethod
    def _state_fields(state) -> dict:
        return {
            "task_id": state["task_id"],
            "observed_state": state["observed_state"],
            "desired_state": state["desired_state"],
            "control_version": state["control_version"],
            "completion_epoch_id": state["completion_epoch_id"],
            "close_trigger": state["close_trigger"],
            "result_outcome": state["result_outcome"],
            "review": state["review"],
        }

    def _closed(self, access, state, idempotency_key) -> CompletionOutcome:
        if state["observed_state"] != "closed" or not state["completion_epoch_id"]:
            raise DomainError("completion_not_closed", 409)
        report = self._ensure_report(access, state)
        return CompletionOutcome(
            **self._state_fields(state),
            disposition="closed",
            report=report,
        )

    def _authorize(self, access, idempotency_key, action, close_trigger,
                   result_outcome, deadline_seconds) -> None:
        if (
            "agent" in access.principal.roles
            or not ACTOR_ROLES.intersection(access.principal.roles)
        ):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= MAX_IDEMPOTENCY_KEY:
            raise DomainError("INVALID_SCHEMA", 422)
        if action not in ACTIONS:
            raise DomainError("INVALID_SCHEMA", 422)
        if close_trigger not in CLOSE_TRIGGERS or result_outcome not in RESULT_OUTCOMES:
            raise DomainError("INVALID_SCHEMA", 422)
        if type(deadline_seconds) is not int or not 60 <= deadline_seconds <= 86400:
            raise DomainError("INVALID_SCHEMA", 422)

    def _state(self, access, task_id) -> dict:
        if not isinstance(task_id, str) or not 1 <= len(task_id) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        review = self.completion.precheck(access, task_id)
        with self.uow.transaction(access, task_id, capability="read") as tx:
            task = tx.task
            values = {
                "task_id": task["task_id"],
                "observed_state": task["observed_state"],
                "desired_state": task["desired_state"],
                "control_version": int(task["control_version"]),
                "board_revision": int(task["board_revision"]),
                "completion_epoch_id": task["completion_epoch_id"],
                "close_trigger": task["close_trigger"],
                "result_outcome": task["result_outcome"],
            }
        return {**values, "review": review.receipt()}

    def _report_row(self, access, task_id, report_id):
        with self.uow.transaction(access, task_id, capability="read") as tx:
            return tx.connection.execute(
                "SELECT report_id,body_digest,dispute_state,close_trigger,result_outcome,epoch_id,created_at"
                " FROM vnext.report_commit WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND report_id=%s",
                (*tx.owner, report_id),
            ).fetchone()

    def _latest_report(self, access, task_id):
        with self.uow.transaction(access, task_id, capability="read") as tx:
            return tx.connection.execute(
                "SELECT report_id,body_digest,dispute_state,close_trigger,result_outcome,epoch_id,created_at"
                " FROM vnext.report_commit WHERE tenant_id=%s AND project_id=%s AND task_id=%s"
                " ORDER BY created_at DESC,report_id DESC LIMIT 1",
                tx.owner,
            ).fetchone()

    @staticmethod
    def _report_summary(found) -> dict | None:
        if found is None:
            return None
        return {
            "report_id": found[0],
            "body_digest": found[1],
            "dispute_state": found[2],
            "close_trigger": found[3],
            "result_outcome": found[4],
            "epoch_id": found[5],
            "created_at": found[6].isoformat().replace("+00:00", "Z"),
        }

    def _ensure_report(self, access, state) -> dict:
        """Freeze the delivered report once per closed epoch, then return it."""

        report_key = "report:" + state["completion_epoch_id"]
        stored = self.reports.read(access, state["task_id"], report_key)
        if stored is None:
            try:
                self.reports.freeze(
                    access,
                    state["task_id"],
                    report_key=report_key,
                    epoch_id=state["completion_epoch_id"],
                )
            except DomainError as error:
                # The epoch already carries frozen bytes that differ from what the
                # persisted facts compose now (a late result landed in between).
                # The frozen report stays authoritative and is returned unchanged.
                if error.code != "INPUT_DIGEST_CONFLICT":
                    raise
        found = self._report_row(access, state["task_id"], report_key)
        summary = self._report_summary(found)
        if summary is None:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        return summary

    @staticmethod
    def _quiesce_key(idempotency_key, state, close_trigger) -> str:
        """Deterministic per (caller key, review): a replay is byte-identical."""

        material = canonical_json_bytes(
            {
                "idempotency_key": idempotency_key,
                "action": "quiesce",
                "close_trigger": close_trigger,
                "review": state["review"],
            }
        )
        return "quiesce:" + sha256(material).hexdigest()

    @staticmethod
    def _close_key(idempotency_key, state, close_trigger, result_outcome) -> str:
        """Bind the decision key to the exact versions the decision will cite."""

        material = canonical_json_bytes(
            {
                "idempotency_key": idempotency_key,
                "action": "close",
                "epoch_id": state["completion_epoch_id"],
                "control_version": state["control_version"],
                "board_revision": state["board_revision"],
                "close_trigger": close_trigger,
                "result_outcome": result_outcome,
                "review": state["review"],
            }
        )
        return "close:" + sha256(material).hexdigest()
