from datetime import UTC, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import psycopg
import pytest

from support.p09 import (
    OWNER,
    SCHEDULER,
    TASK,
    explore_assignment,
    migrate_p06_head_then_current,
    publish_additional_intent,
    scheduler_case,
    signed_sibling_worker,
    worker_credential,
)
from test_work_state_guards import OPERATOR, command, control_case
from wuji_core.admission.registry import revoke_run_credential
from wuji_core.contracts.execution import WorkDependency
from wuji_core.execution.dependencies import DependencyService
from wuji_core.http import strict_json_loads
from wuji_core.persistence.snapshots import SnapshotRepository
from wuji_core.persistence.uow import DomainError, json_text
from wuji_core.scheduling.claims import SchedulerOwnership, WorkRepository
from wuji_core.scheduling.policy import (
    Candidate,
    ProgressSummary,
    SchedulerPolicy,
    SchedulingSnapshot,
    WorkKey,
)
from wuji_core.scheduling.triggers import TriggerRepository
from wuji_core.scheduling.waiters import WaitPredicate, WaiterRepository


def test_policy_continues_tenant_rotation_after_persisted_cursor() -> None:
    now = datetime(2026, 9, 13, 6, 0, tzinfo=UTC)
    snapshot = SchedulingSnapshot(
        candidates=(
            Candidate(
                tenant_id="tenant-a",
                task_id="task-a",
                work_item_id="work-a",
                kind="explore",
                priority=0,
                ready_since=now,
            ),
            Candidate(
                tenant_id="tenant-b",
                task_id="task-b",
                work_item_id="work-b",
                kind="explore",
                priority=0,
                ready_since=now,
            ),
        ),
        now=now,
        tenant_cursor="tenant-a",
        limit=1,
    )

    selected = SchedulerPolicy().select(snapshot)

    assert [
        (proposal.tenant_id, proposal.task_id, proposal.work_item_id)
        for proposal in selected
    ] == [("tenant-b", "task-b", "work-b")]


def test_policy_continues_task_rotation_inside_a_tenant() -> None:
    now = datetime(2026, 9, 13, 6, 0, tzinfo=UTC)
    snapshot = SchedulingSnapshot(
        candidates=(
            Candidate(
                tenant_id="tenant-a",
                task_id="task-a",
                work_item_id="work-a",
                kind="explore",
                priority=0,
                ready_since=now,
            ),
            Candidate(
                tenant_id="tenant-a",
                task_id="task-b",
                work_item_id="work-b",
                kind="explore",
                priority=0,
                ready_since=now,
            ),
        ),
        now=now,
        task_cursors=(("tenant-a", "task-a"),),
        limit=1,
    )

    selected = SchedulerPolicy().select(snapshot)

    assert [proposal.work_item_id for proposal in selected] == ["work-b"]


def test_policy_result_is_independent_of_candidate_query_order() -> None:
    now = datetime(2026, 9, 13, 6, 0, tzinfo=UTC)
    tenant_a = Candidate(
        tenant_id="tenant-a",
        task_id="task-a",
        work_item_id="work-a",
        kind="explore",
        priority=0,
        ready_since=now,
    )
    tenant_b = Candidate(
        tenant_id="tenant-b",
        task_id="task-b",
        work_item_id="work-b",
        kind="explore",
        priority=0,
        ready_since=now,
    )

    policy = SchedulerPolicy()
    forward = policy.select(
        SchedulingSnapshot(candidates=(tenant_a, tenant_b), now=now)
    )
    reverse = policy.select(
        SchedulingSnapshot(candidates=(tenant_b, tenant_a), now=now)
    )

    assert [proposal.work_item_id for proposal in forward] == ["work-a", "work-b"]
    assert reverse == forward


def test_policy_aging_prevents_old_low_priority_work_from_starving() -> None:
    now = datetime(2026, 9, 13, 6, 0, tzinfo=UTC)
    snapshot = SchedulingSnapshot(
        candidates=(
            Candidate(
                tenant_id="tenant-a",
                task_id="task-a",
                work_item_id="new-high-priority",
                kind="explore",
                priority=10,
                ready_since=now,
            ),
            Candidate(
                tenant_id="tenant-a",
                task_id="task-a",
                work_item_id="old-low-priority",
                kind="explore",
                priority=-10,
                ready_since=now - timedelta(minutes=21),
            ),
        ),
        now=now,
        limit=1,
        aging_seconds=60,
    )

    selected = SchedulerPolicy().select(snapshot)

    assert [proposal.work_item_id for proposal in selected] == ["old-low-priority"]


def test_policy_does_not_select_an_ineligible_snapshot_candidate() -> None:
    now = datetime(2026, 9, 13, 6, 0, tzinfo=UTC)
    snapshot = SchedulingSnapshot(
        candidates=(
            Candidate(
                tenant_id="tenant-a",
                task_id="task-a",
                work_item_id="ineligible-work",
                kind="explore",
                priority=10,
                ready_since=now - timedelta(days=1),
                eligible=False,
            ),
            Candidate(
                tenant_id="tenant-b",
                task_id="task-b",
                work_item_id="eligible-work",
                kind="explore",
                priority=0,
                ready_since=now,
            ),
        ),
        now=now,
        limit=2,
    )

    selected = SchedulerPolicy().select(snapshot)

    assert [proposal.work_item_id for proposal in selected] == ["eligible-work"]


def test_policy_control_work_bonus_is_bounded_by_waiting_age() -> None:
    now = datetime(2026, 9, 13, 6, 0, tzinfo=UTC)
    reason = Candidate(
        tenant_id="tenant-a",
        task_id="task-a",
        work_item_id="reason-work",
        kind="reason",
        priority=0,
        ready_since=now,
    )
    fresh_explore = Candidate(
        tenant_id="tenant-a",
        task_id="task-a",
        work_item_id="explore-work",
        kind="explore",
        priority=0,
        ready_since=now,
    )
    old_explore = Candidate(
        tenant_id="tenant-a",
        task_id="task-a",
        work_item_id="explore-work",
        kind="explore",
        priority=0,
        ready_since=now - timedelta(minutes=4),
    )

    policy = SchedulerPolicy()
    fresh_selection = policy.select(
        SchedulingSnapshot(
            candidates=(fresh_explore, reason),
            now=now,
            limit=1,
            aging_seconds=60,
        )
    )
    aged_selection = policy.select(
        SchedulingSnapshot(
            candidates=(old_explore, reason),
            now=now,
            limit=1,
            aging_seconds=60,
        )
    )

    assert [proposal.work_item_id for proposal in fresh_selection] == ["reason-work"]
    assert [proposal.work_item_id for proposal in aged_selection] == ["explore-work"]


@pytest.mark.parametrize("priority", [-11, 11])
def test_candidate_rejects_priority_outside_the_published_bounds(
    priority: int,
) -> None:
    with pytest.raises(ValueError):
        Candidate(
            tenant_id="tenant-a",
            task_id="task-a",
            work_item_id="work-a",
            kind="explore",
            priority=priority,
            ready_since=datetime(2026, 9, 13, 6, 0, tzinfo=UTC),
        )


def test_progress_depends_on_platform_derived_counters() -> None:
    assert ProgressSummary().made_progress is False
    assert ProgressSummary(new_material=1).made_progress is True
    assert ProgressSummary(resolved_blockers=1).made_progress is True
    assert ProgressSummary(new_problem_classes=1).made_progress is False
    assert (
        ProgressSummary(new_problem_classes=1, classification="known").made_progress
        is True
    )


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("problem_id", "problem-2"),
        ("intent_id", "intent-2"),
        ("intent_revision", "2"),
        ("method_ref", "method-v2"),
        ("profile_digest", "b" * 64),
        ("basis", (("claim", "claim-1", "2"),)),
        ("environment_ref", "environment-v2"),
        ("output_contract", "agent-payload-v2"),
    ],
)
def test_work_key_digest_keeps_every_exact_identity_dimension(
    field: str, changed: object
) -> None:
    values: dict[str, object] = {
        "problem_id": "problem-1",
        "intent_id": "intent-1",
        "intent_revision": "1",
        "method_ref": "method-v1",
        "profile_digest": "a" * 64,
        "basis": (("claim", "claim-1", "1"),),
        "environment_ref": "environment-v1",
        "output_contract": "agent-payload-v1",
    }
    original = WorkKey(**values).digest()

    values[field] = changed

    assert WorkKey(**values).digest() != original


def test_scheduler_main_flow_uses_real_pg_and_minimal_signed_run_identity(
    db_environment, tmp_path, audit_directory
) -> None:
    with scheduler_case(db_environment, tmp_path, audit_directory) as case:
        receipt = case.scheduler.tick(limit=2)
        assignment = explore_assignment(receipt)
        credential = worker_credential(case, assignment)

        assert {item.work_kind.value for item in receipt.assignments} == {
            "explore",
            "reason",
        }
        assert receipt.blocked == ()
        assert credential.principal.subject == (
            "run.worker:" + assignment.identity.agent_run_id
        )
        assert credential.principal.token_id == credential.binding.token_id
        assert credential.principal.roles == frozenset({"worker"})

        manifest = case.snapshots.get(TASK, credential.access, assignment.snapshot_id)
        assert case.intent_ref in manifest.refs
        assert case.claim_ref in manifest.refs
        assert (
            case.snapshots.read_ref(
                TASK, credential.access, assignment.snapshot_id, case.intent_ref
            )["entity_id"]
            == case.intent_ref.id
        )

        with case.control.env.migration_connection() as connection:
            worker = connection.execute(
                """SELECT can_read,can_write,can_model_output,can_control,can_observe,
                can_admit,can_capture,can_settle,can_assess,can_gc,clearance
                FROM vnext.task_access WHERE tenant_id=%s AND project_id=%s
                AND task_id=%s AND subject=%s""",
                (*OWNER, credential.principal.subject),
            ).fetchone()
            run = connection.execute(
                "SELECT process_state FROM vnext.agent_run WHERE agent_run_id=%s",
                (assignment.identity.agent_run_id,),
            ).fetchone()
            ciphertext, payloads = (
                connection.execute(
                    "SELECT ciphertext FROM vnext.scheduler_credential WHERE credential_ref=%s",
                    (credential.credential_ref,),
                ).fetchone()[0],
                connection.execute(
                    "SELECT payload_json FROM vnext.outbox WHERE kind='run.dispatch_requested'"
                ).fetchall(),
            )

        assert worker == (
            True,
            True,
            True,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            1,
        )
        assert run == ("registered",)
        assert credential.token.encode("utf-8") not in bytes(ciphertext)
        assert all(credential.token not in payload for (payload,) in payloads)


def test_scheduler_snapshot_reader_requires_bound_jti_and_unrevoked_run(
    db_environment, tmp_path, audit_directory
) -> None:
    with scheduler_case(db_environment, tmp_path, audit_directory) as case:
        assignment = explore_assignment(case.scheduler.tick(limit=2))
        credential = worker_credential(case, assignment)

        assert (
            case.snapshots.get(
                TASK, credential.access, assignment.snapshot_id
            ).snapshot_id
            == assignment.snapshot_id
        )

        sibling = signed_sibling_worker(case, subject=credential.principal.subject)
        with pytest.raises(DomainError, match="NOT_FOUND_OR_FORBIDDEN"):
            case.snapshots.get(TASK, sibling, assignment.snapshot_id)

        with case.control.env.migration_connection() as connection:
            revoke_run_credential(
                connection,
                tenant_id=OWNER[0],
                subject=credential.principal.subject,
                token_id=credential.principal.token_id,
            )
        with pytest.raises(DomainError, match="NOT_FOUND_OR_FORBIDDEN"):
            case.snapshots.get(TASK, credential.access, assignment.snapshot_id)

        assert (
            case.snapshots.get(
                TASK, case.scheduler_access, assignment.snapshot_id
            ).snapshot_id
            == assignment.snapshot_id
        )


def test_scheduler_blocks_when_narrow_snapshot_omits_required_work_inputs(
    db_environment, tmp_path, audit_directory
) -> None:
    with scheduler_case(
        db_environment,
        tmp_path,
        audit_directory,
        template_clearance=0,
        input_access_level=1,
    ) as case:
        receipt = case.scheduler.tick(limit=2)

        assert {item.work_kind.value for item in receipt.assignments} == {"reason"}
        assert any(
            work_id and code == "required_snapshot_input_unavailable"
            for _task_id, work_id, code in receipt.blocked
        )
        with case.control.env.migration_connection() as connection:
            explore = connection.execute(
                """SELECT w.state,w.current_run_id,w.blocked_reason
                FROM vnext.work_item w JOIN vnext.scheduler_work s
                USING(tenant_id,project_id,task_id,work_item_id)
                WHERE s.intent_id=%s""",
                (case.intent_ref.id,),
            ).fetchone()
            created = connection.execute(
                """SELECT count(*) FROM vnext.agent_run a JOIN vnext.work_item w
                USING(tenant_id,project_id,task_id,work_item_id)
                WHERE w.intent_id=%s""",
                (case.intent_ref.id,),
            ).fetchone()[0]
        assert explore == (
            "blocked",
            None,
            "required_snapshot_input_unavailable",
        )
        assert created == 0


@pytest.mark.parametrize("purpose", ["model_request", "tool_request"])
def test_run_request_cannot_create_scheduler_identity(
    db_environment, tmp_path, audit_directory, purpose: str
) -> None:
    with scheduler_case(db_environment, tmp_path, audit_directory) as case:
        assignment = explore_assignment(case.scheduler.tick(limit=2))
        credential = worker_credential(case, assignment)
        body = json_text(credential.binding.model_dump(mode="json"))

        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with case.control.uow.transaction(
                credential.access, TASK, capability=purpose
            ) as tx:
                tx.connection.execute(
                    "SELECT vnext.bind_scheduler_credential(%s,%s,%s,%s,%s)",
                    (*OWNER, credential.credential_ref, body),
                ).fetchone()


def test_same_transaction_snapshot_uses_goal_criterion_ref(
    db_environment, tmp_path, audit_directory
) -> None:
    with control_case(db_environment, tmp_path, audit_directory) as case:
        command(case, "start")
        with case.env.migration_connection() as connection:
            connection.execute(
                """INSERT INTO vnext.goal_criterion(
                tenant_id,project_id,task_id,criterion_id,revision,definition_json)
                VALUES(%s,%s,%s,'criterion-p09',1,'{}')""",
                OWNER,
            )
        DependencyService(case.uow).add(
            OPERATOR,
            TASK,
            "work-b",
            WorkDependency.model_validate(
                {
                    "predecessor_work_id": "work-fixture",
                    "condition": "criterion_satisfied",
                    "criterion_ref": {
                        "criterion_id": "criterion-p09",
                        "revision": "1",
                    },
                }
            ),
        )

        with case.uow.transaction(SCHEDULER, TASK, capability="admit") as tx:
            manifest = SnapshotRepository(case.uow).create_in_transaction(tx)

        dependency = next(
            item for item in manifest.dependencies if item["work_item_id"] == "work-b"
        )
        assert dependency["criterion_ref"] == {
            "criterion_id": "criterion-p09",
            "revision": "1",
        }


def test_late_domain_event_advances_generation_without_consuming_inflight_reason(
    db_environment, tmp_path, audit_directory
) -> None:
    with scheduler_case(db_environment, tmp_path, audit_directory) as case:
        case.scheduler.tick(limit=2)
        with case.control.env.migration_connection() as connection:
            lease = connection.execute("""SELECT work_item_id,processing_generation FROM
                vnext.scheduler_reason_lease WHERE status='inflight'""").fetchone()
        late_intent = publish_additional_intent(case, "late-generation")
        with case.control.env.migration_connection() as connection:
            event_seq = connection.execute(
                """SELECT event_seq FROM vnext.outbox WHERE kind='intent_shared'
                AND payload_json::jsonb->'canonical_ref'->>'id'=%s""",
                (late_intent.id,),
            ).fetchone()[0]

        with case.control.uow.transaction(SCHEDULER, TASK, capability="admit") as tx:
            repository = TriggerRepository()
            generation = repository.record(tx, event_seq=event_seq)
            after = repository.read(tx)
            duplicate = repository.record(tx, event_seq=event_seq)
            deduplicated = repository.read(tx)

        assert generation == duplicate
        assert generation > lease[1]
        assert after.pending_generation == generation
        assert after.consumed_generation < generation
        assert after.inflight_reason_work_id == lease[0]
        assert deduplicated == after


@pytest.mark.parametrize("condition_first", [True, False])
def test_wait_registration_handles_condition_before_or_after_registration(
    db_environment, tmp_path, audit_directory, condition_first: bool
) -> None:
    with scheduler_case(db_environment, tmp_path, audit_directory) as case:
        reason = next(
            item
            for item in case.scheduler.tick(limit=2).assignments
            if item.work_kind.value == "reason"
        )
        with case.control.env.migration_connection() as connection:
            processing_generation = connection.execute(
                """SELECT processing_generation FROM vnext.scheduler_reason_lease
                WHERE work_item_id=%s""",
                (reason.identity.work_item_id,),
            ).fetchone()[0]

        if condition_first:
            command(case.control, "cancel", work="work-b")
        with case.control.uow.transaction(SCHEDULER, TASK, capability="admit") as tx:
            waiters = WaiterRepository()
            waiter_id = waiters.register(
                tx,
                work_item_id=reason.identity.work_item_id,
                processing_generation=processing_generation,
                predicates=(WaitPredicate("work_settled.v1", "work-b"),),
            )
            initial = tx.connection.execute(
                "SELECT status FROM vnext.scheduler_waiter WHERE waiter_id=%s",
                (waiter_id,),
            ).fetchone()[0]

        if not condition_first:
            command(case.control, "cancel", work="work-b")
            with case.control.uow.transaction(
                SCHEDULER, TASK, capability="admit"
            ) as tx:
                assert WaiterRepository().scan(tx) == (waiter_id,)
                initial = tx.connection.execute(
                    "SELECT status FROM vnext.scheduler_waiter WHERE waiter_id=%s",
                    (waiter_id,),
                ).fetchone()[0]

        with case.control.env.migration_connection() as connection:
            active_reservations = connection.execute(
                """SELECT count(*) FROM vnext.capacity_reservation
                WHERE agent_run_id=%s AND state<>'released'""",
                (reason.identity.agent_run_id,),
            ).fetchone()[0]
        assert initial == "ready"
        assert active_reservations == 3


def test_work_repository_deduplicates_exact_key_and_rejects_intent_conflict(
    db_environment, tmp_path, audit_directory
) -> None:
    with scheduler_case(db_environment, tmp_path, audit_directory) as case:
        assignment = explore_assignment(case.scheduler.tick(limit=2))
        with case.control.uow.transaction(SCHEDULER, TASK, capability="admit") as tx:
            record = tx.connection.execute(
                "SELECT key_json FROM vnext.scheduler_work WHERE work_item_id=%s",
                (assignment.identity.work_item_id,),
            ).fetchone()[0]
            value = strict_json_loads(record)
            key = WorkKey(
                **{
                    **value,
                    "basis": tuple(tuple(reference) for reference in value["basis"]),
                }
            )
            same = WorkRepository().register(tx, key=key, kind="explore")
            conflict = WorkKey(
                **{
                    **value,
                    "problem_id": "different-problem",
                    "basis": tuple(tuple(reference) for reference in value["basis"]),
                }
            )
            with pytest.raises(DomainError, match="INPUT_DIGEST_CONFLICT"):
                WorkRepository().register(tx, key=conflict, kind="explore")
            count = tx.connection.execute(
                "SELECT count(*) FROM vnext.scheduler_work WHERE intent_id=%s",
                (case.intent_ref.id,),
            ).fetchone()[0]

        assert same == assignment.identity.work_item_id
        assert count == 1


def test_cumulative_work_limit_survives_another_scheduler_tick(
    db_environment, tmp_path, audit_directory
) -> None:
    with scheduler_case(
        db_environment, tmp_path, audit_directory, max_work_items=4
    ) as case:
        assert len(case.scheduler.tick(limit=2).assignments) == 2
        publish_additional_intent(case, "over-limit")

        receipt = case.scheduler.tick(limit=2)

        assert (TASK, "", "max_work_items") in receipt.blocked
        with case.control.env.migration_connection() as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext.work_item WHERE task_id=%s", (TASK,)
            ).fetchone() == (4,)


def test_dedicated_scheduler_ownership_has_one_winner_across_connections(
    db_environment, tmp_path, audit_directory
) -> None:
    with control_case(db_environment, tmp_path, audit_directory):
        with db_environment.additional_app_connection() as first_connection:
            with db_environment.additional_app_connection() as second_connection:
                barrier = Barrier(2)
                first = SchedulerOwnership(first_connection)
                second = SchedulerOwnership(second_connection)

                def acquire(ownership: SchedulerOwnership) -> bool:
                    barrier.wait()
                    return ownership.acquire()

                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(acquire, (first, second)))
                try:
                    assert sorted(results) == [False, True]
                finally:
                    first.close()
                    second.close()


def test_capacity_is_rechecked_for_each_selected_work(
    db_environment, tmp_path, audit_directory
) -> None:
    with scheduler_case(db_environment, tmp_path, audit_directory, capacity=1) as case:
        receipt = case.scheduler.tick(limit=2)

        assert len(receipt.assignments) == 1
        assert any(code == "capacity_unavailable" for _, _, code in receipt.blocked)
        with case.control.env.migration_connection() as connection:
            reservations = connection.execute(
                """SELECT pool_key,count(*) FROM vnext.capacity_reservation
                WHERE state<>'released' GROUP BY pool_key ORDER BY pool_key"""
            ).fetchall()
        assert reservations == [
            ("model:fixture-model-v1", 1),
            ("platform", 1),
            ("tenant-fixture", 1),
        ]


def test_p09_migration_upgrades_p06_head_and_reapplies_once(db_environment) -> None:
    migrate_p06_head_then_current(db_environment)
