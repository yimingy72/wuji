"""The canonical WorkDependency DAG and its three distinct predicates."""

import psycopg

from wuji_core.contracts.execution import WorkDependency
from wuji_core.http.json_boundary import strict_json_loads
from wuji_core.persistence.uow import DomainError, row


def intent_record(tx, work):
    if not work["intent_id"]:
        return None
    return row(
        tx.connection.execute(
            "SELECT * FROM vnext.intent_revision WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND entity_id=%s AND revision=%s",
            (*tx.owner, work["intent_id"], work["intent_revision"]),
        )
    )


def intent_current(tx, work):
    if not work["intent_id"]:
        return True
    intent = intent_record(tx, work)
    if not intent or intent["acceptance_state"] != "admitted":
        return False
    if any(
        value.startswith("stale_input:")
        for value in strict_json_loads(intent["limitations_json"])
    ):
        return False
    from wuji_core.blackboard.fact_view import inputs_current
    from wuji_core.contracts.knowledge import KnowledgeRef

    try:
        return inputs_current(
            tx,
            [
                KnowledgeRef.model_validate(r)
                for r in strict_json_loads(intent["basis_json"])
            ],
        )
    except DomainError:
        return False


def result_accepted(tx, run_id):
    if not run_id:
        return False
    value = row(
        tx.connection.execute(
            """SELECT s.envelope_json,r.receipt_json FROM vnext.agent_run a
        JOIN vnext.result_submission s ON (s.tenant_id,s.project_id,s.task_id,s.agent_run_id,s.submission_id)=(a.tenant_id,a.project_id,a.task_id,a.agent_run_id,a.result_submission_id)
        JOIN vnext.result_receipt r ON (r.tenant_id,r.project_id,r.task_id,r.submission_id)=(s.tenant_id,s.project_id,s.task_id,s.submission_id)
        WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s AND a.agent_run_id=%s AND a.result_state='accepted'""",
            (*tx.owner, run_id),
        )
    )
    if not value:
        return False
    receipt = strict_json_loads(value["receipt_json"])
    if receipt["status"] != "accepted" or any(
        c.get("code") == "STALE_INPUT" for c in receipt["components"]
    ):
        return False
    # Fixed read_set remains subject to P04's authoritative current-visibility/freshness boundary.
    from wuji_core.blackboard.fact_view import inputs_current
    from wuji_core.contracts.knowledge import KnowledgeRef

    refs = strict_json_loads(value["envelope_json"])["read_set"]
    try:
        return inputs_current(tx, [KnowledgeRef.model_validate(r) for r in refs])
    except DomainError:
        return False


def dependencies_satisfied(tx, work_id):
    cursor = tx.connection.execute(
        "SELECT * FROM vnext.work_dependency WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s ORDER BY predecessor_id",
        (*tx.owner, work_id),
    )
    deps = []
    while (dep := row(cursor)) is not None:
        deps.append(dep)
    for dep in deps:
        previous = row(
            tx.connection.execute(
                "SELECT state,current_run_id FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
                (*tx.owner, dep["predecessor_id"]),
            )
        )
        if not previous:
            return False
        condition = dep["condition"]
        if condition == "settled":
            if previous["state"] not in {"done", "failed", "cancelled"}:
                return False
        elif previous["state"] in {"failed", "cancelled"}:
            return False
        elif condition == "accepted_result":
            if previous["state"] != "done" or not result_accepted(
                tx, previous["current_run_id"]
            ):
                return False
        else:
            judgment = row(
                tx.connection.execute(
                    """SELECT j.* FROM vnext.goal_criterion c JOIN vnext.criterion_judgment j ON
                (j.tenant_id,j.project_id,j.task_id,j.judgment_id,j.criterion_id,j.criterion_revision)=
                (c.tenant_id,c.project_id,c.task_id,c.current_judgment_id,c.criterion_id,c.revision)
                WHERE c.tenant_id=%s AND c.project_id=%s AND c.task_id=%s AND c.criterion_id=%s AND c.revision=%s""",
                    (*tx.owner, dep["criterion_id"], dep["criterion_revision"]),
                )
            )
            if (
                not judgment
                or judgment["status"] != "met"
                or judgment["applicability"] != "current"
            ):
                return False
    return True


class DependencyService:
    def __init__(self, uow):
        self.uow = uow

    def add(self, access, task_id, work_id, dependency):
        dependency = WorkDependency.model_validate(dependency)
        try:
            with self.uow.transaction(access, task_id, capability="control") as tx:
                work = row(
                    tx.connection.execute(
                        "SELECT state FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s FOR UPDATE",
                        (*tx.owner, work_id),
                    )
                )
                if not work or work["state"] not in {"ready", "blocked", "suspended"}:
                    raise DomainError("STALE_EXECUTION", 409)
                tx.add_dependency(
                    work_id,
                    dependency.predecessor_work_id,
                    dependency.condition.value,
                    criterion=dependency.criterion_ref,
                )
                if work["state"] in {"ready", "blocked"}:
                    state = (
                        "ready" if dependencies_satisfied(tx, work_id) else "blocked"
                    )
                    tx.connection.execute(
                        "UPDATE vnext.work_item SET state=%s,revision=revision+1,blocked_reason=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
                        (
                            state,
                            None if state == "ready" else "dependency_unsatisfied",
                            *tx.owner,
                            work_id,
                        ),
                    )
        except psycopg.IntegrityError as error:
            raise DomainError("INVALID_REFERENCE", 422) from error

    def satisfied(self, access, task_id, work_id):
        with self.uow.transaction(access, task_id) as tx:
            return dependencies_satisfied(tx, work_id)
