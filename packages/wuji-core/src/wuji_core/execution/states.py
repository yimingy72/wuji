"""S05 predicates over server-observed state; never infer exit from output."""

from wuji_core.contracts.execution import WorkState, can_transition_work
from wuji_core.persistence.uow import DomainError

TERMINAL = frozenset({"done", "failed", "cancelled"})
ACTIVE = frozenset({"leased", "running", "stopping", "reconciling"})


def can_settle_done(result_accepted, process_exited, operations_settled) -> bool:
    return bool(result_accepted and process_exited and operations_settled)


def require_transition(current, target):
    if current != target and not can_transition_work(
        WorkState(current), WorkState(target)
    ):
        raise DomainError("STALE_EXECUTION", 409)


def task_can_run(task):
    return bool(
        task["activated_at"]
        and task["execution_allowed"]
        and task["desired_state"] == "run"
        and task["observed_state"] == "running"
        and task["completion_epoch_id"] is None
    )
