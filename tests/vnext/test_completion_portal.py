"""P12-E product entry: the operator drives the epoch and reads the report.

Real PostgreSQL, the real P12 services and the signed HTTP boundary. Nothing
here lets a caller supply its own review, and nothing marks a Task closed
without a platform-authored decision being consumed by P05.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from support.http_capture import RecordedTestClient
from test_completion_protocol import (
    ASSESSOR,
    allow_assessor,
    completion,
    finish_work,
    judgments,
    sealed_evidence,
)
from test_work_state_guards import OPERATOR, OWNER, TASK, control_case, prepared_run
from wuji_core.completion.portal import TaskCompletionPortal
from wuji_core.completion.reports import ReportService
from wuji_core.http import create_app
from wuji_core.http.completion import create_completion_router
from wuji_core.persistence.uow import DomainError


def portal(case) -> TaskCompletionPortal:
    return TaskCompletionPortal(
        case.uow,
        completion=completion(case),
        reports=ReportService(case.uow, artifacts=case.store),
    )


def settle_operations(case):
    """The Run's own operation set: a settlement prerequisite, not this test's claim."""

    with case.env.migration_connection() as connection:
        connection.execute(
            "INSERT INTO vnext.run_operation_settlement(tenant_id,project_id,task_id,agent_run_id,"
            "status,source_receipt_json) VALUES(%s,%s,%s,'run-fixture','settled','{\"fixture\":true}')"
            " ON CONFLICT DO NOTHING",
            OWNER,
        )


def ready_goal(case):
    """Sealed evidence plus a met judgment: the Goal is supported by facts."""

    prepared_run(case, state="leased")
    finish_work(case)
    settle_operations(case)
    allow_assessor(case)
    sealed = sealed_evidence(case)
    judgments(case).record(
        ASSESSOR,
        TASK,
        criterion_id="version",
        revision=1,
        judgment_id="judgment-portal",
        status="met",
        method="deterministic",
        evidence_refs=[sealed.model_dump(mode="json")],
        definition_json='{"fixture":true}',
    )
    return sealed


def report_commits(case, report_id=None):
    with case.env.migration_connection() as connection:
        if report_id is None:
            return connection.execute(
                "SELECT count(*) FROM vnext.report_commit WHERE tenant_id=%s AND project_id=%s"
                " AND task_id=%s",
                OWNER,
            ).fetchone()[0]
        return connection.execute(
            "SELECT body_digest,dispute_state FROM vnext.report_commit WHERE tenant_id=%s"
            " AND project_id=%s AND task_id=%s AND report_id=%s",
            (*OWNER, report_id),
        ).fetchone()


def test_the_operator_opens_the_epoch_closes_and_gets_a_frozen_report(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        service = portal(case)

        view = service.review(OPERATOR, TASK)
        assert view["review"]["decision"] == "ready", view["review"]["reasons"]
        assert view["report"] is None
        assert view["completion_epoch_id"] is None

        opened = service.submit(
            OPERATOR, TASK, action="quiesce", close_trigger="goal_satisfied",
            result_outcome="complete", idempotency_key="portal-quiesce",
        )
        assert opened.disposition == "quiescing" and opened.status_code == 202
        assert opened.completion_epoch_id
        assert opened.report is None

        # A replay of the same intent and the same review reuses the epoch instead
        # of writing a second decision.
        replay_open = service.submit(
            OPERATOR, TASK, action="quiesce", close_trigger="goal_satisfied",
            result_outcome="complete", idempotency_key="portal-quiesce",
        )
        assert replay_open.completion_epoch_id == opened.completion_epoch_id
        with case.env.migration_connection() as connection:
            quiesce_decisions = connection.execute(
                "SELECT count(*) FROM vnext.completion_decision WHERE tenant_id=%s"
                " AND project_id=%s AND task_id=%s AND action='quiesce'",
                OWNER,
            ).fetchone()[0]
        assert quiesce_decisions == 1

        closed = service.submit(
            OPERATOR, TASK, action="close", close_trigger="goal_satisfied",
            result_outcome="complete", idempotency_key="portal-close",
        )
        assert closed.disposition == "closed" and closed.status_code == 200
        assert closed.observed_state == "closed"
        assert closed.close_trigger == "goal_satisfied"
        assert closed.result_outcome == "complete"
        assert closed.report is not None
        assert closed.report["report_id"] == "report:" + opened.completion_epoch_id
        assert closed.report["dispute_state"] == "clear"

        stored = service.read_report(OPERATOR, TASK, closed.report["report_id"])
        assert stored["body_digest"] == closed.report["body_digest"]
        assert stored["body"]["task_id"] == TASK
        assert stored["body"]["close_trigger"] == "goal_satisfied"
        assert stored["body"]["result_outcome"] == "complete"
        assert stored["amendments"] == []

        # A later retry converges on the bytes that were frozen first.
        again = service.submit(
            OPERATOR, TASK, action="close", close_trigger="goal_satisfied",
            result_outcome="complete", idempotency_key="portal-close-retry",
        )
        assert again.report["body_digest"] == closed.report["body_digest"]
        assert report_commits(case, closed.report["report_id"]) == (
            closed.report["body_digest"],
            "clear",
        )
        assert report_commits(case) == 1

        # The review now reports the frozen commit; the Task stays closed.
        after = service.review(OPERATOR, TASK)
        assert after["observed_state"] == "closed"
        assert after["report"]["report_id"] == closed.report["report_id"]
        assert after["report"]["dispute_state"] == "clear"


def test_close_before_the_epoch_is_refused_without_a_decision(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        service = portal(case)
        with pytest.raises(DomainError) as refused:
            service.submit(
                OPERATOR, TASK, action="close", close_trigger="goal_satisfied",
                result_outcome="complete", idempotency_key="portal-close-early",
            )
        assert refused.value.code == "completion_epoch_absent"
        with case.env.migration_connection() as connection:
            decisions = connection.execute(
                "SELECT count(*) FROM vnext.completion_decision WHERE tenant_id=%s"
                " AND project_id=%s AND task_id=%s",
                OWNER,
            ).fetchone()[0]
        assert decisions == 0
        assert report_commits(case) == 0


def test_an_unfinished_goal_cannot_open_an_epoch_through_the_product_entry(
    db_environment, tmp_path, audit_directory
):
    """AC-048: unfinished work is never frozen behind a quiescing epoch."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        prepared_run(case, state="leased")
        finish_work(case)
        settle_operations(case)
        service = portal(case)
        view = service.review(OPERATOR, TASK)
        assert view["review"]["decision"] == "wait"
        assert "criteria_unmet" in view["review"]["reasons"]

        with pytest.raises(DomainError) as refused:
            service.submit(
                OPERATOR, TASK, action="quiesce", close_trigger="goal_satisfied",
                result_outcome="complete", idempotency_key="portal-unmet",
            )
        assert refused.value.code == "completion_precheck_incomplete"
        after = service.review(OPERATOR, TASK)
        assert after["observed_state"] == "running"
        assert after["completion_epoch_id"] is None
        assert report_commits(case) == 0


def test_a_forced_close_keeps_trigger_and_outcome_through_the_product_entry(
    db_environment, tmp_path, audit_directory
):
    """AC-052: once the epoch exists, a forced close keeps its own fields."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        service = portal(case)
        opened = service.submit(
            OPERATOR, TASK, action="quiesce", close_trigger="goal_satisfied",
            result_outcome="complete", idempotency_key="portal-quiesce",
        )
        assert opened.disposition == "quiescing"

        # A later revision of the criterion has no judgment yet, so the Goal is
        # no longer supported; a goal_satisfied close is refused while the forced
        # one is the bounded way to end the Task.
        with case.env.migration_connection() as connection:
            connection.execute(
                "INSERT INTO vnext.goal_criterion(tenant_id,project_id,task_id,criterion_id,"
                "revision,definition_json) VALUES(%s,%s,%s,'version',2,'{\"fixture\":\"v2\"}')"
                " ON CONFLICT DO NOTHING",
                OWNER,
            )
        blocked = service.review(OPERATOR, TASK)
        assert blocked["review"]["decision"] == "wait"

        with pytest.raises(DomainError) as goal_refused:
            service.submit(
                OPERATOR, TASK, action="close", close_trigger="goal_satisfied",
                result_outcome="complete", idempotency_key="portal-forced-goal",
            )
        assert goal_refused.value.code == "completion_precheck_incomplete"

        closed = service.submit(
            OPERATOR, TASK, action="close", close_trigger="operator_finish",
            result_outcome="partial", idempotency_key="portal-forced-close",
        )
        assert closed.disposition == "closed"
        assert closed.close_trigger == "operator_finish"
        assert closed.result_outcome == "partial"
        body = service.read_report(OPERATOR, TASK, closed.report["report_id"])["body"]
        # The unmet revision is frozen as missing; a forced close never rewrites it.
        assert [item["status"] for item in body["criteria"]] == ["met", "missing"]
        assert body["close_trigger"] == "operator_finish"
        assert body["result_outcome"] == "partial"


def test_only_an_actor_with_control_over_this_task_may_drive_completion(
    db_environment, tmp_path, audit_directory
):
    from support.p03 import access

    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        service = portal(case)
        # A reader has no control capability on this Task; the UnitOfWork refuses
        # before any decision could be written.
        for subject, role in [("reader-fixture", "reader"), ("observer-fixture", "controller")]:
            with pytest.raises(DomainError) as refused:
                service.submit(
                    access(subject, role=role), TASK, action="quiesce",
                    close_trigger="goal_satisfied", result_outcome="complete",
                    idempotency_key="portal-refused",
                )
            assert refused.value.code == "NOT_FOUND_OR_FORBIDDEN"
        # The browser identity carries both roles for agent work; it is excluded
        # from the product actor set on purpose.
        with pytest.raises(DomainError) as agent:
            service.submit(
                access("agent-fixture", role="operator"), TASK, action="quiesce",
                close_trigger="goal_satisfied", result_outcome="complete",
                idempotency_key="portal-refused",
            )
        assert agent.value.code == "NOT_FOUND_OR_FORBIDDEN"
        with case.env.migration_connection() as connection:
            decisions = connection.execute(
                "SELECT count(*) FROM vnext.completion_decision WHERE tenant_id=%s"
                " AND project_id=%s AND task_id=%s",
                OWNER,
            ).fetchone()[0]
        assert decisions == 0


def test_the_signed_http_routes_return_the_closed_task_and_its_report(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        token = case.provider.issue(
            subject="operator-fixture", tenant_id=OWNER[0], roles=["operator"]
        )
        client = RecordedTestClient(
            create_app(
                token_verifier=case.verifier,
                routers=[create_completion_router(portal(case))],
            ),
            audit_path=audit_directory / "completion-portal-http.jsonl",
        )
        headers = {"Authorization": "Bearer " + token}
        try:
            review = client.get(
                f"/api/v2/tasks/{TASK}/completion", headers=headers
            )
            assert review.status_code == 200, review.text
            assert review.json()["review"]["decision"] == "ready"
            # Revisions travel as decimal strings on the wire.
            assert review.json()["control_version"].isdigit()
            assert review.json()["report"] is None

            # Closing before an epoch exists is a bounded refusal, not a 500:
            # the public envelope only carries the frozen ErrorCode enum.
            early = client.post(
                f"/api/v2/tasks/{TASK}/completion",
                json={
                    "action": "close",
                    "close_trigger": "goal_satisfied",
                    "result_outcome": "complete",
                },
                headers={**headers, "Idempotency-Key": str(uuid4())},
            )
            assert early.status_code == 409, early.text
            assert early.json()["code"] == "COMPLETION_EPOCH_ABSENT"

            opened = client.post(
                f"/api/v2/tasks/{TASK}/completion",
                json={
                    "action": "quiesce",
                    "close_trigger": "goal_satisfied",
                    "result_outcome": "complete",
                },
                headers={**headers, "Idempotency-Key": str(uuid4())},
            )
            assert opened.status_code == 202, opened.text
            assert opened.json()["disposition"] == "quiescing"
            assert opened.json()["completion_epoch_id"]

            closed = client.post(
                f"/api/v2/tasks/{TASK}/completion",
                json={
                    "action": "close",
                    "close_trigger": "goal_satisfied",
                    "result_outcome": "complete",
                    "deadline_seconds": 600,
                },
                headers={**headers, "Idempotency-Key": str(uuid4())},
            )
            assert closed.status_code == 200, closed.text
            document = closed.json()
            assert document["disposition"] == "closed"
            assert document["observed_state"] == "closed"
            assert document["report"]["dispute_state"] == "clear"

            fetched = client.get(
                f"/api/v2/tasks/{TASK}/reports/{document['report']['report_id']}",
                headers=headers,
            )
            assert fetched.status_code == 200, fetched.text
            assert fetched.json()["body_digest"] == document["report"]["body_digest"]
            assert fetched.json()["body"]["task_id"] == TASK
            assert fetched.json()["amendments"] == []

            missing = client.get(
                f"/api/v2/tasks/{TASK}/reports/report-absent", headers=headers
            )
            assert missing.status_code == 404

            # A caller without the control permission is refused by the service,
            # not by a route-level guess.
            assert client.post(
                f"/api/v2/tasks/{TASK}/completion",
                json={
                    "action": "quiesce",
                    "close_trigger": "goal_satisfied",
                    "result_outcome": "complete",
                },
                headers={
                    "Authorization": "Bearer " + case.tokens.reader,
                    "Idempotency-Key": str(uuid4()),
                },
            ).status_code == 404
        finally:
            client.close()
