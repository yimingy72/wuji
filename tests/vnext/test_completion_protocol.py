"""P12 completion precheck over the real P05 control state machine.

Nothing here claims a Task can be *closed*: this slice decides whether a
completion epoch may start, writes that canonical decision, and lets the
existing P05 state machine consume it.
"""

from __future__ import annotations

import pytest

from support.p03 import access
from test_work_state_guards import (
    OPERATOR,
    OWNER,
    OBSERVER,
    TASK,
    control_case,
    observe,
    prepared_run,
    process,
)
from wuji_core.completion.judgments import JudgmentService
from wuji_core.completion.precheck import CompletionService
from wuji_core.persistence.uow import DomainError

CONTROLLER = access("completion-fixture", role="controller")


def completion(case) -> CompletionService:
    return CompletionService(case.uow, control=case.control)


def judgments(case) -> JudgmentService:
    return JudgmentService(case.uow, artifacts=case.store)


ASSESSOR = access("assessor-fixture", role="assessor")


def allow_assessor(case, *, can_assess=True, clearance=1):
    with case.env.migration_connection() as connection:
        connection.execute(
            "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,"
            "can_assess,clearance) VALUES(%s,%s,%s,'assessor-fixture',true,%s,%s)"
            " ON CONFLICT (tenant_id,project_id,task_id,subject) DO UPDATE SET can_assess=EXCLUDED.can_assess",
            (*OWNER, can_assess, clearance),
        )


def finish_work(case, *, state="done"):
    """Terminal Work plus a real exited Run; no fixture may fake Goal support."""

    with case.env.migration_connection() as connection:
        connection.execute(
            "UPDATE vnext.work_item SET state=%s,terminal_reason='fixture'"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
            (state, *OWNER),
        )
    observe(case, "exited", process=process(exited=True))
    with case.env.migration_connection() as connection:
        connection.execute(
            "UPDATE vnext.agent_run SET stop_kind='exited',result_state='accepted' WHERE agent_run_id='run-fixture'"
        )


def judge(case, *, status, applicability="current", criterion="version", revision=1):
    with case.env.migration_connection() as connection:
        connection.execute(
            "INSERT INTO vnext.goal_criterion(tenant_id,project_id,task_id,criterion_id,revision,definition_json)"
            " VALUES(%s,%s,%s,%s,%s,'{\"fixture\":true}') ON CONFLICT DO NOTHING",
            (*OWNER, criterion, revision),
        )
        judgment_id = "judgment-" + criterion + "-" + status + "-" + applicability
        connection.execute(
            "INSERT INTO vnext.criterion_judgment(tenant_id,project_id,task_id,judgment_id,criterion_id,"
            "criterion_revision,status,applicability,source_receipt_json,access_level)"
            " VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'{\"fixture\":\"prerequisite\"}',1)"
            " ON CONFLICT DO NOTHING",
            (*OWNER, judgment_id, criterion, revision, status, applicability),
        )
        connection.execute(
            "UPDATE vnext.goal_criterion SET current_judgment_id=%s"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND criterion_id=%s AND revision=%s",
            (judgment_id, *OWNER, criterion, revision),
        )


WORKER = access("worker-fixture", role="worker")


def sealed_evidence(case, body=b"fixture-version=17\n"):
    """Stage and seal one real artifact the judgment can cite."""

    staged = case.store.stage_model_output(
        WORKER, TASK, "run-fixture", body, "application/json", access_level=1
    )
    case.store.seal(WORKER, TASK, staged)
    return staged


def test_a_judgment_must_cite_sealed_evidence_and_then_supports_the_goal(
    db_environment, tmp_path, audit_directory
):
    """AC-051 first half: only persisted, evidence-backed judgments count."""

    from wuji_core.contracts.envelopes import BlobRef

    with control_case(db_environment, tmp_path, audit_directory) as case:
        prepared_run(case, state="leased")
        finish_work(case)
        allow_assessor(case)
        service = judgments(case)

        # A judgment without evidence is an assertion, not an assessment.
        with pytest.raises(DomainError) as refused:
            service.record(
                ASSESSOR, TASK, criterion_id="version", revision=1,
                judgment_id="judgment-a", status="met", method="deterministic",
                evidence_refs=[], definition_json='{"fixture":true}',
            )
        assert refused.value.code == "INVALID_REFERENCE"

        # Evidence that was never sealed cannot support a Goal either.
        unsealed = case.store.stage_model_output(
            WORKER, TASK, "run-fixture", b"fixture-version=18\n", "application/json",
            access_level=1,
        )
        with pytest.raises(DomainError) as unsealed_refused:
            service.record(
                ASSESSOR, TASK, criterion_id="version", revision=1,
                judgment_id="judgment-a", status="met", method="deterministic",
                evidence_refs=[unsealed.model_dump(mode="json")],
                definition_json='{"fixture":true}',
            )
        assert unsealed_refused.value.code == "INVALID_REFERENCE"

        sealed = sealed_evidence(case)
        receipt = service.record(
            ASSESSOR, TASK, criterion_id="version", revision=1,
            judgment_id="judgment-a", status="met", method="deterministic",
            evidence_refs=[sealed.model_dump(mode="json")],
            definition_json='{"fixture":true}',
        )
        assert receipt.status == "met" and receipt.applicability == "current"
        assert receipt.evidence and receipt.evidence[0]["digest"]

        # The receipt is replayable: the same judgment returns the same row.
        assert service.record(
            ASSESSOR, TASK, criterion_id="version", revision=1,
            judgment_id="judgment-a", status="met", method="deterministic",
            evidence_refs=[sealed.model_dump(mode="json")],
            definition_json='{"fixture":true}',
        ) == receipt

        review = completion(case).precheck(OBSERVER, TASK)
        assert review.decision == "ready", review.reasons
        assert review.coverage.satisfied


def test_late_counter_evidence_on_a_superseded_revision_is_recorded_but_not_current(
    db_environment, tmp_path, audit_directory
):
    """AC-053/AC-034: history keeps the late finding; the Goal does not turn."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        prepared_run(case, state="leased")
        finish_work(case)
        allow_assessor(case)
        service = judgments(case)
        sealed = sealed_evidence(case)

        with case.env.migration_connection() as connection:
            connection.execute(
                "INSERT INTO vnext.goal_criterion(tenant_id,project_id,task_id,criterion_id,revision,definition_json)"
                " VALUES(%s,%s,%s,'version',2,'{\"fixture\":\"v2\"}') ON CONFLICT DO NOTHING",
                (*OWNER,),
            )

        late = service.record(
            ASSESSOR, TASK, criterion_id="version", revision=1,
            judgment_id="judgment-late", status="not_met", applicability="disputed",
            method="deterministic", evidence_refs=[sealed.model_dump(mode="json")],
            definition_json='{"fixture":true}',
        )
        assert late.applicability == "disputed"

        current = service.current(ASSESSOR, TASK, "version")
        # The superseded revision was judged, but revision 2 is the latest one and
        # carries no judgment, so the Goal still has no support.
        assert current is None
        review = completion(case).precheck(OBSERVER, TASK)
        assert not review.coverage.satisfied
        assert review.decision == "wait"


def test_only_an_assessor_may_record_a_judgment(db_environment, tmp_path, audit_directory):
    with control_case(db_environment, tmp_path, audit_directory) as case:
        prepared_run(case, state="leased")
        sealed = sealed_evidence(case)
        with pytest.raises(DomainError) as refused:
            judgments(case).record(
                CONTROLLER, TASK, criterion_id="version", revision=1,
                judgment_id="judgment-a", status="met", method="deterministic",
                evidence_refs=[sealed.model_dump(mode="json")],
                definition_json='{"fixture":true}',
            )
        # The UnitOfWork refuses the assessment capability for a principal
        # without an assessor role/permission before the service's own check.
        assert refused.value.code in {"FORBIDDEN_ASSESSOR", "NOT_FOUND_OR_FORBIDDEN"}


def test_the_closing_decision_keeps_trigger_and_outcome_independent(
    db_environment, tmp_path, audit_directory
):
    """AC-052: budget_exhausted may still carry a partial result."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        prepared_run(case, state="leased")
        finish_work(case)
        allow_assessor(case)
        sealed = sealed_evidence(case)
        judgments(case).record(
            ASSESSOR, TASK, criterion_id="version", revision=1,
            judgment_id="judgment-a", status="met", method="deterministic",
            evidence_refs=[sealed.model_dump(mode="json")],
            definition_json='{"fixture":true}',
        )
        service = completion(case)
        proposal = service.propose(
            CONTROLLER, TASK, receipt_key="completion-open", deadline_seconds=600
        )
        service.apply(CONTROLLER, TASK, proposal.receipt_id)
        task = case.control.read_task(OBSERVER, TASK)
        assert task["completion_epoch_id"] == proposal.epoch_id

        closing = service.close(
            CONTROLLER, TASK, receipt_key="completion-close",
            epoch_id=proposal.epoch_id, close_trigger="budget_exhausted",
            result_outcome="partial", deadline_seconds=600,
        )
        with case.env.migration_connection() as connection:
            stored = connection.execute(
                "SELECT action,close_trigger,result_outcome FROM vnext.completion_decision"
                " WHERE receipt_id=%s", (closing.receipt_id,),
            ).fetchone()
        assert stored == ("close", "budget_exhausted", "partial")


def test_required_work_prevents_early_quiesce(db_environment, tmp_path, audit_directory):
    """AC-048 with the plan's representative check: open work returns wait."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        prepared_run(case, state="leased")
        service = completion(case)

        review = service.precheck(OBSERVER, TASK)
        assert review.decision == "wait"
        assert "required_work_open" in review.reasons
        assert "work-fixture" in review.open_work
        assert case.control.read_task(OBSERVER, TASK)["observed_state"] == "running"

        with pytest.raises(DomainError) as refused:
            service.propose(CONTROLLER, TASK, receipt_key="completion-fixture")
        assert refused.value.code == "completion_precheck_incomplete"

        # Nothing was frozen by the refused proposal.
        task = case.control.read_task(OBSERVER, TASK)
        assert task["completion_epoch_id"] is None
        assert task["observed_state"] == "running"


def test_precheck_does_not_wait_for_a_settled_reason_run(
    db_environment, tmp_path, audit_directory
):
    """AC-047: an exited, judged Reason is not an active dependency."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        prepared_run(case, state="leased")
        finish_work(case)
        judge(case, status="met")
        service = completion(case)

        review = service.precheck(OBSERVER, TASK)
        assert review.decision == "ready", review.reasons
        assert review.open_work == ()
        assert review.unsettled_runs == ()
        assert review.coverage.satisfied

        proposal = service.propose(
            CONTROLLER,
            TASK,
            receipt_key="completion-fixture",
            deadline_seconds=600,
        )
        assert proposal.close_trigger == "goal_satisfied"
        # Replaying the same key returns the same canonical receipt.
        replay = service.propose(
            CONTROLLER,
            TASK,
            receipt_key="completion-fixture",
            deadline_seconds=600,
        )
        assert replay.receipt_id == proposal.receipt_id

        receipt = service.apply(CONTROLLER, TASK, proposal.receipt_id)
        assert receipt is not None
        task = case.control.read_task(OBSERVER, TASK)
        assert task["completion_epoch_id"] == proposal.epoch_id
        assert task["observed_state"] == "quiescing"
        assert task["execution_allowed"] is False


def test_an_operator_without_the_controller_role_cannot_propose(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as case:
        prepared_run(case, state="leased")
        finish_work(case)
        judge(case, status="met")
        service = completion(case)
        assert service.precheck(OBSERVER, TASK).decision == "ready"
        with pytest.raises(DomainError) as refused:
            service.propose(OPERATOR, TASK, receipt_key="completion-fixture")
        assert refused.value.code == "NOT_FOUND_OR_FORBIDDEN"


@pytest.mark.parametrize(
    ("status", "applicability", "reason"),
    [
        ("unknown", "current", "criteria_unmet"),
        ("not_applicable", "current", "criteria_unmet"),
        ("not_met", "current", "criteria_unmet"),
        ("met", "stale", "criteria_invalidated"),
    ],
)
def test_only_a_current_met_judgment_supports_the_goal(
    db_environment, tmp_path, audit_directory, status, applicability, reason
):
    """AC-051: an empty, unknown or invalidated decision never satisfies a Goal."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        prepared_run(case, state="leased")
        finish_work(case)
        judge(case, status=status, applicability=applicability)
        review = completion(case).precheck(OBSERVER, TASK)
        assert not review.coverage.satisfied
        assert reason in review.reasons
        assert review.decision in {"wait", "blocked"}


def test_a_goal_without_required_criteria_is_never_satisfied(
    db_environment, tmp_path, audit_directory
):
    """AC-051: all(required == []) must not read as met."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        with case.env.migration_connection() as connection:
            raw = connection.execute(
                "SELECT definition_json FROM vnext.task WHERE task_id=%s", (TASK,)
            ).fetchone()[0]
        import json as _json

        document = _json.loads(raw)
        document["task"]["goal"]["criteria"] = []
        with case.env.migration_connection() as connection:
            connection.execute(
                "UPDATE vnext.task SET definition_json=%s WHERE task_id=%s",
                (_json.dumps(document, sort_keys=True), TASK),
            )
        prepared_run(case, state="leased")
        finish_work(case)
        review = completion(case).precheck(OBSERVER, TASK)
        assert review.coverage.required == ()
        assert review.coverage.satisfied is False
        assert "criteria_unmet" in review.reasons
        assert review.decision == "wait"
