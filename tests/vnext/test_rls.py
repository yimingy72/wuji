"""P03: real nonowner RLS, typed composite references and transactional DAG."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import psycopg
import pytest

from support.p03 import (
    access,
    claim,
    control_access,
    prepared,
    seed_capacity,
    seed_control_actor,
)


def test_rls_uses_nonowner_role_and_resets_request_scope(db_environment):
    with prepared(db_environment) as uow:
        with uow.transaction(access(), "task-fixture", capability="write") as tx:
            tx.connection.execute("SHOW server_version").fetchone()
            identity = tx.connection.execute(
                "SELECT current_user, r.rolsuper, r.rolbypassrls, c.relowner::regrole::text FROM pg_roles r, pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE r.rolname=current_user AND c.relname='claim_revision' AND n.nspname='vnext'"
            ).fetchone()
            assert identity == (
                db_environment.application_role,
                False,
                False,
                db_environment.migration_role,
            )
            claim(tx)
            assert tx.connection.execute(
                "SELECT task_id FROM vnext.task"
            ).fetchall() == [("task-fixture",)]
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with tx.connection.transaction():
                    tx.connection.execute(
                        "INSERT INTO vnext.claim_revision(tenant_id,project_id,task_id,entity_id,revision,kind,assertion_role,text,producer_kind,producer_ref) VALUES ('tenant-other','project-other','task-other','forged',1,'hypothesis','hypothesis','x','agent','agent-fixture')"
                    )
        with db_environment.additional_app_connection() as raw:
            assert (
                raw.execute("SELECT count(*) FROM vnext.claim_revision").fetchone()[0]
                == 0
            )
        with uow.transaction(access(tenant="tenant-other"), "task-other") as tx:
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.claim_revision"
                ).fetchone()[0]
                == 0
            )


def test_registry_requires_real_domain_and_rolls_back_event(db_environment):
    with prepared(db_environment) as uow:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with uow.transaction(access(), "task-fixture", capability="write") as tx:
                claim(tx)
                tx.semantic_event("claim_appended", {"id": "claim-1"})
                tx.connection.execute(
                    "INSERT INTO vnext.entity_revision_registry(tenant_id,project_id,task_id,entity_type,entity_id,revision) VALUES (%s,%s,%s,'claim','phantom',1)",
                    tx.owner,
                )
        with uow.transaction(access(), "task-fixture") as tx:
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.claim_revision"
                ).fetchone()[0]
                == 0
            )
            assert tx.connection.execute(
                "SELECT board_revision,event_seq FROM vnext.task"
            ).fetchone() == (0, 0)
            assert (
                tx.connection.execute("SELECT count(*) FROM vnext.outbox").fetchone()[0]
                == 0
            )
        with uow.transaction(access(), "task-fixture", capability="write") as tx:
            claim(tx)
            tx.semantic_event("claim_appended", {"id": "claim-1"})
        with uow.transaction(access(), "task-fixture") as tx:
            assert tx.connection.execute(
                "SELECT entity_type,entity_id,revision FROM vnext.entity_revision_registry"
            ).fetchall() == [("claim", "claim-1", 1)]
            assert tx.connection.execute(
                "SELECT board_revision,event_seq FROM vnext.task"
            ).fetchone() == (1, 1)


@pytest.mark.parametrize(
    "target",
    [("claim", "missing", 1), ("observation", "claim-1", 1), ("claim", "claim-1", 2)],
)
def test_composite_refs_reject_missing_type_or_revision(db_environment, target):
    with prepared(db_environment) as uow:
        with uow.transaction(access(), "task-fixture", capability="write") as tx:
            claim(tx)
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with uow.transaction(access(), "task-fixture", capability="write") as tx:
                tx.connection.execute(
                    "INSERT INTO vnext.entity_relation(tenant_id,project_id,task_id,source_type,source_id,source_revision,relation,target_type,target_id,target_revision) VALUES (%s,%s,%s,'claim','claim-1',1,'cites',%s,%s,%s)",
                    (*tx.owner, *target),
                )


def test_same_tenant_other_project_task_cannot_supply_a_reference(db_environment):
    with prepared(db_environment) as uow:
        with uow.transaction(access(), "task-sibling", capability="write") as tx:
            claim(tx, "sibling-claim")
        with uow.transaction(access(), "task-fixture", capability="write") as tx:
            claim(tx)
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with uow.transaction(access(), "task-fixture", capability="write") as tx:
                tx.connection.execute(
                    "INSERT INTO vnext.entity_relation(tenant_id,project_id,task_id,source_type,source_id,source_revision,relation,target_type,target_id,target_revision) VALUES (%s,%s,%s,'claim','claim-1',1,'cites','claim','sibling-claim',1)",
                    tx.owner,
                )


def test_immutable_claim_and_agent_assessment_boundary(db_environment):
    with prepared(db_environment) as uow:
        with uow.transaction(access(), "task-fixture", capability="write") as tx:
            claim(tx)
        with uow.transaction(
            access("agent-fixture", role="agent"), "task-fixture", capability="write"
        ) as tx:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with tx.connection.transaction():
                    tx.connection.execute(
                        "UPDATE vnext.claim_revision SET text='replacement'"
                    )
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with tx.connection.transaction():
                    tx.connection.execute(
                        "INSERT INTO vnext.assessment(tenant_id,project_id,task_id,assessment_id,claim_id,claim_revision,method_kind,method_version,reviewer_ref,reason) VALUES (%s,%s,%s,'fake','claim-1',1,'deterministic','v1','agent-fixture','self-certification')",
                        tx.owner,
                    )


def test_two_connections_cannot_commit_dependency_cycle(db_environment):
    with prepared(db_environment) as uow:
        with db_environment.migration_connection() as m:
            seed_control_actor(m)
            seed_capacity(m)
        barrier = Barrier(2)

        def insert(source, target):
            barrier.wait(timeout=5)
            try:
                with uow.transaction(
                    control_access(), "task-fixture", capability="control"
                ) as tx:
                    tx.add_dependency(source, target, "settled")
                return "committed"
            except psycopg.errors.CheckViolation:
                return "cycle_rejected"

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(insert, "work-fixture", "work-b")
            second = pool.submit(insert, "work-b", "work-fixture")
            assert sorted([first.result(timeout=10), second.result(timeout=10)]) == [
                "committed",
                "cycle_rejected",
            ]
        with uow.transaction(access(), "task-fixture") as tx:
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.work_dependency"
                ).fetchone()[0]
                == 1
            )


def test_agent_database_context_cannot_forge_observation(db_environment):
    with prepared(db_environment) as uow:
        with uow.transaction(
            access("agent-fixture", role="agent"), "task-fixture", capability="write"
        ) as tx:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with tx.connection.transaction():
                    tx.connection.execute(
                        "INSERT INTO vnext.observation(tenant_id,project_id,task_id,entity_id,revision,capture_id,tool_attempt_id,collector_ref,capture_layer,observed_at,received_at,environment_ref,conditions_json,completeness,evidence_origin) VALUES (%s,%s,%s,'forged',1,'forged','attempt-fixture','collector-fixture','fixture_file_bytes',clock_timestamp(),clock_timestamp(),'environment-fixture','[]','complete','fixture_capture')",
                        tx.owner,
                    )


def test_derived_claim_cannot_lower_source_visibility(db_environment):
    with prepared(db_environment) as uow:
        with uow.transaction(access(), "task-fixture", capability="write") as tx:
            claim(tx, "secret", level=1)
            claim(tx, "public", level=0)
        with pytest.raises(psycopg.errors.CheckViolation):
            with uow.transaction(access(), "task-fixture", capability="write") as tx:
                tx.connection.execute(
                    "INSERT INTO vnext.entity_relation(tenant_id,project_id,task_id,source_type,source_id,source_revision,relation,target_type,target_id,target_revision,access_level) VALUES (%s,%s,%s,'claim','public',1,'cites','claim','secret',1,0)",
                    tx.owner,
                )
        with db_environment.migration_connection() as db:
            db.execute(
                "UPDATE vnext.task_access SET clearance=0 WHERE tenant_id='tenant-fixture' AND task_id='task-fixture' AND subject='reader-fixture'"
            )
        with uow.transaction(
            access("reader-fixture", role="reader"), "task-fixture"
        ) as tx:
            assert tx.connection.execute(
                "SELECT entity_id FROM vnext.claim_revision"
            ).fetchall() == [("public",)]
