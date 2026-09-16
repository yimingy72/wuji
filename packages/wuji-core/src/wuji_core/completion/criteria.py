"""Goal coverage read from persisted criterion judgments only.

A criterion counts only when a persisted ``criterion_judgment`` for the revision
the Goal currently names says ``met`` with applicability ``current``. Missing
judgments, ``unknown``, ``not_applicable`` and any non-current applicability are
all "not met": an empty required set, a model's own claim inside a request body
or a natural-language summary never satisfy a Goal (AC-051).
"""

from dataclasses import dataclass

from wuji_core.persistence.uow import DomainError, row


@dataclass(frozen=True)
class CriterionState:
    criterion_id: str
    required: bool
    revision: str | None
    status: str
    applicability: str
    judged: bool

    @property
    def satisfied(self) -> bool:
        return self.status == "met" and self.applicability == "current"


@dataclass(frozen=True)
class GoalCoverage:
    criteria: tuple[CriterionState, ...]

    @property
    def required(self) -> tuple[CriterionState, ...]:
        return tuple(item for item in self.criteria if item.required)

    @property
    def satisfied(self) -> bool:
        """An empty or all-not-applicable required set never satisfies a Goal."""

        required = self.required
        return bool(required) and all(item.satisfied for item in required)

    def unmet(self) -> tuple[CriterionState, ...]:
        return tuple(item for item in self.required if not item.satisfied)

    def invalidated(self) -> tuple[CriterionState, ...]:
        return tuple(
            item
            for item in self.required
            if item.judged and item.applicability in {"stale", "disputed", "retracted"}
        )


def declared_criteria(definition):
    """The Goal's criteria as the Task definition fixed them."""

    try:
        goal = definition["task"]["goal"]
        criteria = goal["criteria"]
    except (KeyError, TypeError) as error:
        raise DomainError("CAPABILITY_UNAVAILABLE", 503) from error
    if not isinstance(criteria, list):
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    declared = []
    for entry in criteria:
        if not isinstance(entry, dict):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        criterion_id = entry.get("criterion_id")
        required = entry.get("required")
        if not isinstance(criterion_id, str) or not criterion_id or type(required) is not bool:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        declared.append((criterion_id, required))
    return tuple(declared)


def read_coverage(tx, definition):
    """Every declared criterion with the judgment that actually exists."""

    states = []
    for criterion_id, required in declared_criteria(definition):
        current = row(
            tx.connection.execute(
                "SELECT c.revision,c.current_judgment_id,j.judgment_id,j.status,j.applicability"
                " FROM vnext.goal_criterion c"
                " LEFT JOIN vnext.criterion_judgment j ON"
                " (j.tenant_id,j.project_id,j.task_id,j.judgment_id)="
                " (c.tenant_id,c.project_id,c.task_id,c.current_judgment_id)"
                " WHERE c.tenant_id=%s AND c.project_id=%s AND c.task_id=%s AND c.criterion_id=%s"
                " ORDER BY c.revision DESC LIMIT 1",
                (*tx.owner, criterion_id),
            )
        )
        if current is None:
            # The definition fixes a required criterion that was never persisted
            # with a judgment: still unmet, and visibly judged=False.
            states.append(
                CriterionState(criterion_id, required, None, "missing", "missing", False)
            )
            continue
        revision = str(current["revision"])
        if current["judgment_id"] is None:
            states.append(
                CriterionState(criterion_id, required, revision, "missing", "missing", False)
            )
            continue
        status = str(current["status"])
        applicability = str(current["applicability"])
        if status not in {"met", "not_met", "unknown", "not_applicable"}:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        states.append(
            CriterionState(criterion_id, required, revision, status, applicability, True)
        )
    return GoalCoverage(tuple(states))
