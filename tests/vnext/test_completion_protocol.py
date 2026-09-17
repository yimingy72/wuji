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
from wuji_core.completion.reports import ReportService
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
            "UPDATE vnext.agent_run SET stop_kind='exited',result_state='accepted'"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id='run-fixture'",
            OWNER,
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


def test_proposing_requires_control_over_this_exact_task(
    db_environment, tmp_path, audit_directory
):
    """P12-E: the role is not enough; can_control is read from this Task."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        prepared_run(case, state="leased")
        finish_work(case)
        judge(case, status="met")
        service = completion(case)
        assert service.precheck(OBSERVER, TASK).decision == "ready"
        # observer-fixture holds can_observe, never can_control, on this Task.
        with pytest.raises(DomainError) as refused:
            service.propose(OBSERVER, TASK, receipt_key="completion-fixture")
        assert refused.value.code == "NOT_FOUND_OR_FORBIDDEN"
        # operator-fixture does hold can_control, so the product action is allowed.
        proposal = service.propose(OPERATOR, TASK, receipt_key="completion-fixture")
        assert proposal.close_trigger == "goal_satisfied"


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


def ready_task(case):
    """Drive one case to an open completion epoch (quiescing)."""

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
    return service, proposal


def test_quiescing_refuses_new_work_but_still_accepts_the_open_runs_receipts(
    db_environment, tmp_path, audit_directory
):
    """AC-049: freeze new actions, keep collecting receipts and settlements."""

    from wuji_core.contracts.execution import can_transition_work  # noqa: F401
    from wuji_core.execution.states import task_can_run

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
        assert task["observed_state"] == "quiescing"

        # New starts are refused by the platform's own predicate.
        assert task_can_run(task) is False
        assert not case.control.dispatchable(OBSERVER, TASK, "work-b")

        # The in-flight Run's own exit observation still lands.
        observe(case, "exited", process=process(exited=True))
        with case.env.migration_connection() as connection:
            run = connection.execute(
                "SELECT process_state,stop_kind FROM vnext.agent_run"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id='run-fixture'",
                OWNER,
            ).fetchone()
        assert run == ("exited", "exited")

        # A result submission for that same Run is still accepted while the Task
        # is frozen: the table's own policy asks for model_output authority and
        # scope, not for a running Task.
        staged = case.store.stage_model_output(
            WORKER, TASK, "run-fixture", b'{"schema_version":"wuji.agent-payload.v2"}',
            "application/json", access_level=1,
        )
        case.store.seal(WORKER, TASK, staged)
        with case.uow.transaction(WORKER, TASK, capability="model_output") as tx:
            tx.connection.execute(
                "INSERT INTO vnext.result_submission(tenant_id,project_id,task_id,submission_id,"
                "agent_run_id,writer_subject,input_digest,envelope_json,status,received_receipt_json,"
                "artifact_id,artifact_revision,access_level)"
                " VALUES(%s,%s,%s,'submission-frozen','run-fixture','worker-fixture',%s,"
                "'{\"fixture\":true}','received','{\"status\":\"received\"}',%s,%s,1)",
                (*OWNER, "a" * 64, staged.id, staged.version.root),
            )
            tx.connection.execute(
                "INSERT INTO vnext.result_receipt(tenant_id,project_id,task_id,submission_id,"
                "receipt_json,access_level) VALUES(%s,%s,%s,'submission-frozen',"
                "'{\"status\":\"accepted\"}',1)",
                (*OWNER,),
            )
            # The Run's own writer still projects its accepted result while the
            # Task is frozen.
            state = tx.connection.execute(
                "SELECT vnext.project_run_result(%s,%s,%s,'run-fixture','submission-frozen')",
                OWNER,
            ).fetchone()[0]
        assert state == "accepted"
        assert case.control.read_task(OBSERVER, TASK)["observed_state"] == "quiescing"


def test_close_after_settlement_separates_trigger_from_outcome(
    db_environment, tmp_path, audit_directory
):
    """AC-052: a budget-exhausted close keeps its partial result."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        service, proposal = ready_task(case)
        observe(case, "exited", process=process(exited=True))
        with case.env.migration_connection() as connection:
            connection.execute(
                "UPDATE vnext.agent_run SET stop_kind='exited'"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id='run-fixture'",
                OWNER,
            )
            # The Run's own operation set is a settlement prerequisite, not part
            # of this decision: a real Run publishes it through its credential.
            connection.execute(
                "INSERT INTO vnext.run_operation_settlement(tenant_id,project_id,task_id,agent_run_id,"
                "status,source_receipt_json) VALUES(%s,%s,%s,'run-fixture','settled','{\"fixture\":true}')"
                " ON CONFLICT DO NOTHING",
                (*OWNER,),
            )

        # Work re-derived after the freeze is unfinished; it must be cancelled
        # under the closing trigger rather than marked done.
        with case.env.migration_connection() as connection:
            connection.execute(
                "INSERT INTO vnext.work_item(tenant_id,project_id,task_id,work_item_id)"
                " VALUES(%s,%s,%s,'work-late') ON CONFLICT DO NOTHING",
                OWNER,
            )
        # A Goal-satisfied close is refused while work is open; the forced close
        # below is the bounded path that cancels it.
        with pytest.raises(DomainError) as premature:
            service.close(
                CONTROLLER, TASK, receipt_key="completion-goal", epoch_id=proposal.epoch_id,
                close_trigger="goal_satisfied", result_outcome="complete",
                deadline_seconds=600,
            )
        assert premature.value.code == "completion_precheck_incomplete"

        closing = service.close(
            CONTROLLER, TASK, receipt_key="completion-close", epoch_id=proposal.epoch_id,
            close_trigger="budget_exhausted", result_outcome="partial", deadline_seconds=600,
        )
        service.apply(CONTROLLER, TASK, closing.receipt_id)
        task = case.control.read_task(OBSERVER, TASK)
        assert task["observed_state"] == "closed"
        assert task["close_trigger"] == "budget_exhausted"
        assert task["result_outcome"] == "partial"
        assert task["execution_allowed"] is False

        with case.env.migration_connection() as connection:
            done_work = connection.execute(
                "SELECT state FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s"
                " AND task_id=%s AND work_item_id='work-fixture'",
                OWNER,
            ).fetchone()
            late_work = connection.execute(
                "SELECT state,desired_state,terminal_reason FROM vnext.work_item"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id='work-late'",
                OWNER,
            ).fetchone()
        # Finished work is untouched; unfinished work is cancelled, never done.
        assert done_work == ("done",)
        assert late_work[0] == "cancelled" and late_work[1] == "cancel"
        assert late_work[2] == "budget_exhausted"


def closed_task(case):
    """A real closed Task with one settled Run, ready for a report freeze."""

    service, proposal = ready_task(case)
    observe(case, "exited", process=process(exited=True))
    with case.env.migration_connection() as connection:
        connection.execute(
            "UPDATE vnext.agent_run SET stop_kind='exited'"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id='run-fixture'",
            OWNER,
        )
        connection.execute(
            "INSERT INTO vnext.run_operation_settlement(tenant_id,project_id,task_id,agent_run_id,"
            "status,source_receipt_json) VALUES(%s,%s,%s,'run-fixture','settled','{\"fixture\":true}')"
            " ON CONFLICT DO NOTHING",
            (*OWNER,),
        )
    closing = service.close(
        CONTROLLER, TASK, receipt_key="completion-close", epoch_id=proposal.epoch_id,
        close_trigger="goal_satisfied", result_outcome="complete", deadline_seconds=600,
    )
    service.apply(CONTROLLER, TASK, closing.receipt_id)
    return service, proposal


def test_the_report_freezes_after_close_and_never_rewrites(
    db_environment, tmp_path, audit_directory
):
    """AC-053 first half: immutable bytes with a server-side digest."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        _service, proposal = closed_task(case)
        reports = ReportService(case.uow, artifacts=case.store)

        # A report can only freeze after the Task closed on that epoch.
        with pytest.raises(DomainError) as early:
            reports.freeze(CONTROLLER, TASK, report_key="report-a", epoch_id="epoch-other")
        assert early.value.code == "completion_not_closed"

        receipt = reports.freeze(
            CONTROLLER, TASK, report_key="report-a", epoch_id=proposal.epoch_id
        )
        assert receipt.dispute_state == "clear"
        assert receipt.close_trigger == "goal_satisfied"
        assert receipt.result_outcome == "complete"
        body = reports.read(CONTROLLER, TASK, "report-a")
        from hashlib import sha256

        assert sha256(body["body"].encode()).hexdigest() == body["body_digest"]
        assert '"schema_version":"wuji.report.v1"' in body["body"]

        # The same key with the same composed body replays; a different body for
        # the same key is refused instead of rewriting the delivered report.
        assert reports.freeze(
            CONTROLLER, TASK, report_key="report-a", epoch_id=proposal.epoch_id
        ).body_digest == receipt.body_digest
        with case.env.migration_connection() as connection:
            connection.execute(
                "UPDATE vnext.report_commit SET body_json=%s WHERE report_id='report-a'",
                ('{"forged":true}',),
            )
        with pytest.raises(DomainError) as forged:
            reports.freeze(
                CONTROLLER, TASK, report_key="report-a", epoch_id=proposal.epoch_id
            )
        assert forged.value.code == "INPUT_DIGEST_CONFLICT"


def test_late_counter_evidence_is_appended_and_marks_the_report_disputed(
    db_environment, tmp_path, audit_directory
):
    """AC-053 second half: the frozen body stands, the dispute is visible."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        _service, proposal = closed_task(case)
        reports = ReportService(case.uow, artifacts=case.store)
        receipt = reports.freeze(
            CONTROLLER, TASK, report_key="report-a", epoch_id=proposal.epoch_id
        )
        before = reports.read(CONTROLLER, TASK, "report-a")
        allow_assessor(case)
        sealed = sealed_evidence(case, b'{"counter_evidence":"older call was not settled"}')

        # An amendment without sealed evidence is an assertion, not evidence.
        with pytest.raises(DomainError) as unsealed:
            reports.amend(
                ASSESSOR, TASK, report_key="report-a", amendment_key="amendment-a",
                reason="late counter-evidence", evidence_refs=[],
            )
        assert unsealed.value.code == "INVALID_REFERENCE"

        amendment = reports.amend(
            ASSESSOR, TASK, report_key="report-a", amendment_key="amendment-a",
            reason="late counter-evidence about an old call",
            evidence_refs=[sealed.model_dump(mode="json")],
        )
        assert amendment.authority == "assessor" and amendment.evidence

        after = reports.read(CONTROLLER, TASK, "report-a")
        assert after["body"] == before["body"]
        assert after["body_digest"] == before["body_digest"] == receipt.body_digest
        assert after["dispute_state"] == "disputed"
        assert [row[0] for row in after["amendments"]] == ["amendment-a"]

        # The Task stays closed, no work was reopened, and nothing became ready.
        task = case.control.read_task(OBSERVER, TASK)
        assert task["observed_state"] == "closed"
        with case.env.migration_connection() as connection:
            work = connection.execute(
                "SELECT count(*) FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s"
                " AND task_id=%s AND state='ready'",
                OWNER,
            ).fetchone()
        assert work == (0,)


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
