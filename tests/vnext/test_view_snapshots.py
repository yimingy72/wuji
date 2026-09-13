from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from inspect import Parameter, signature
from pathlib import Path

import pytest
import yaml

from support.p03 import access
from support.p09 import explore_assignment
from support.p13 import (
    BASE,
    add_reader,
    headers,
    projection_case,
    revise_claim,
    scheduled_projection_case,
    set_actor_clearance,
    set_reader_access,
    supported_claim,
    topology,
)
from wuji_core.http.topology import create_topology_router
from wuji_core.blackboard.fact_view import FactLedger
from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.persistence.schema import migrate
from wuji_core.persistence.snapshots import SnapshotRepository
from wuji_core.persistence.uow import DomainError
from wuji_core.projection.snapshots import ProjectionRepository


P13_HEAD = "vnext_0012_p13_projection"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _shape(callable_object) -> tuple[tuple[str, Parameter], ...]:
    return tuple(signature(callable_object).parameters.items())


def test_projection_repository_has_the_frozen_assembly_shape() -> None:
    parameters = _shape(ProjectionRepository)

    assert tuple(name for name, _ in parameters) == (
        "uow",
        "snapshots",
        "ledger",
        "ttl_seconds",
        "max_records",
        "history_page_size",
    )
    assert parameters[0][1].kind is Parameter.POSITIONAL_OR_KEYWORD
    assert all(item.kind is Parameter.KEYWORD_ONLY for _, item in parameters[1:])
    assert tuple(item.default for _, item in parameters[1:]) == (
        None,
        None,
        3600,
        5000,
        100,
    )


def test_projection_repository_has_the_frozen_read_method_shapes() -> None:
    assert tuple(signature(ProjectionRepository.create_in_transaction).parameters) == (
        "self",
        "tx",
        "query",
    )
    assert tuple(signature(ProjectionRepository.topology).parameters) == (
        "self",
        "task_id",
        "access",
        "query",
    )
    assert tuple(signature(ProjectionRepository.record).parameters) == (
        "self",
        "task_id",
        "access",
        "ref",
        "snapshot_id",
    )
    assert tuple(signature(ProjectionRepository.history).parameters) == (
        "self",
        "task_id",
        "access",
        "cursor",
    )


def test_topology_router_factory_accepts_only_the_projection_service() -> None:
    assert tuple(signature(create_topology_router).parameters) == ("projection",)


def test_openapi_declares_actual_410_responses_for_snapshot_reads() -> None:
    openapi = yaml.safe_load(
        (REPOSITORY_ROOT / "packages/contracts/openapi-v2.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert "410" in openapi["paths"]["/api/v2/tasks/{task_id}/snapshots"]["get"][
        "responses"
    ]
    assert "410" in openapi["paths"][
        "/api/v2/tasks/{task_id}/records/{record_type}/{record_id}"
    ]["get"]["responses"]


def test_p13_migration_installs_the_private_projection_schema(db_environment) -> None:
    with db_environment.migration_connection() as connection:
        migrate(connection, application_role=db_environment.application_role)

        heads = {
            item[0]
            for item in connection.execute(
                "SELECT head FROM vnext.schema_migration"
            ).fetchall()
        }
        relations = connection.execute(
            """SELECT to_regclass('vnext.projection_materialization'),
            to_regclass('vnext.projection_view'),
            to_regclass('vnext.projection_cursor')"""
        ).fetchone()
        functions = connection.execute(
            """SELECT to_regprocedure('vnext.projection_reader(text,text,text,text,integer)'),
            to_regprocedure('vnext.projection_run_origin(text,text,text,text)')"""
        ).fetchone()
        table_acl = connection.execute(
            """SELECT c.relname,c.relrowsecurity,
            has_table_privilege(%s,c.oid,'SELECT'),
            has_table_privilege(%s,c.oid,'INSERT'),
            has_table_privilege(%s,c.oid,'UPDATE'),
            has_table_privilege(%s,c.oid,'DELETE')
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='vnext' AND c.relname IN (
              'projection_materialization','projection_view','projection_cursor')
            ORDER BY c.relname""",
            (db_environment.application_role,) * 4,
        ).fetchall()
        function_acl = connection.execute(
            """SELECT p.oid::regprocedure::text,p.prosecdef,p.proconfig,
            has_function_privilege(%s,p.oid,'EXECUTE'),
            NOT EXISTS(SELECT 1 FROM aclexplode(COALESCE(
              p.proacl,acldefault('f',p.proowner))) a
              WHERE a.grantee=0 AND a.privilege_type='EXECUTE')
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname='vnext' AND p.proname IN (
              'projection_reader','projection_run_origin')
            ORDER BY p.proname""",
            (db_environment.application_role,),
        ).fetchall()

    assert P13_HEAD in heads
    assert relations == (
        "vnext.projection_materialization",
        "vnext.projection_view",
        "vnext.projection_cursor",
    )
    assert functions == (
        "vnext.projection_reader(text,text,text,text,integer)",
        "vnext.projection_run_origin(text,text,text,text)",
    )
    assert table_acl == [
        ("projection_cursor", True, True, True, False, False),
        ("projection_materialization", True, True, True, False, False),
        ("projection_view", True, True, True, False, False),
    ]
    assert function_acl == [
        (
            "vnext.projection_reader(text,text,text,text,integer)",
            False,
            ["search_path=pg_catalog"],
            True,
            True,
        ),
        (
            "vnext.projection_run_origin(text,text,text,text)",
            True,
            ["search_path=pg_catalog"],
            True,
            True,
        ),
    ]


def test_saved_pages_and_record_stay_fixed_after_a_new_claim_revision(
    db_environment, tmp_path, audit_directory
) -> None:
    with projection_case(db_environment, tmp_path, audit_directory) as case:
        claim = supported_claim(case)
        first_response = topology(case, node_limit=1, edge_limit=1)
        assert first_response.status_code == 200, first_response.text
        first = first_response.json()
        assert first["truncated"] is True
        assert first["continuation"]

        revision_two = revise_claim(case, claim, text="New unassessed revision")
        assert revision_two == {
            "entity_type": "claim",
            "id": claim.ref["id"],
            "revision": "2",
        }

        pages = [first]
        cursor = first["continuation"]
        while cursor is not None:
            response = topology(
                case,
                cursor=cursor,
                node_limit=1,
                edge_limit=1,
            )
            assert response.status_code == 200, response.text
            page = response.json()
            assert page["snapshot_id"] == first["snapshot_id"]
            assert page["view_id"] == first["view_id"]
            assert page["view_revision"] == "1"
            pages.append(page)
            cursor = page["continuation"]
            assert len(pages) < 32

        node_ids = {
            node["id"] for page in pages for node in page["nodes"]
        }
        assert f"claim:{claim.ref['id']}@1" in node_ids
        assert f"claim:{claim.ref['id']}@2" not in node_ids
        serialized = json.dumps(pages, sort_keys=True)
        assert "board_revision" not in serialized
        assert "event_seq" not in serialized

        saved_record = case.client.get(
            BASE + "/records/claim/" + claim.ref["id"],
            params={"revision": "1", "snapshot_id": first["snapshot_id"]},
            headers=headers(case),
        )
        current_record = case.client.get(
            BASE + "/records/claim/" + claim.ref["id"],
            params={"revision": "2"},
            headers=headers(case),
        )

        assert saved_record.status_code == 200, saved_record.text
        assert saved_record.json()["display_kind"] == "fact"
        assert saved_record.json()["record"]["text"] == claim.body["text"]
        assert current_record.status_code == 200, current_record.text
        assert current_record.json()["display_kind"] == "claim"
        assert current_record.json()["record"]["text"] == "New unassessed revision"


def test_opaque_cursor_is_persisted_and_bound_to_query_and_principal(
    db_environment, tmp_path, audit_directory
) -> None:
    with projection_case(db_environment, tmp_path, audit_directory) as case:
        supported_claim(case)
        first_response = topology(case, node_limit=1, edge_limit=1)
        assert first_response.status_code == 200, first_response.text
        first = first_response.json()
        handle = first["continuation"]
        assert handle and len(handle) >= 32
        assert "task-fixture" not in handle
        assert "event_seq" not in handle

        with case.environment.migration_connection() as connection:
            stored = connection.execute(
                """SELECT kind,view_id,position_json FROM vnext.projection_cursor
                WHERE handle=%s""",
                (handle,),
            ).fetchone()
        assert stored[0] == "page"
        assert stored[1] == first["view_id"]
        assert json.loads(stored[2]) == {"edge": 0, "node": 1}

        changed_query = topology(
            case,
            cursor=handle,
            node_limit=2,
            edge_limit=1,
        )
        assert changed_query.status_code == 404
        assert changed_query.json()["code"] == "NOT_FOUND_OR_FORBIDDEN"

        other_token = add_reader(case, "reader-other")
        other_principal = case.client.get(
            BASE + "/topology",
            params={
                "mode": "live",
                "cursor": handle,
                "node_limit": 1,
                "edge_limit": 1,
            },
            headers={"Authorization": "Bearer " + other_token},
        )
        assert other_principal.status_code == 404
        assert other_principal.json()["code"] == "NOT_FOUND_OR_FORBIDDEN"

        unsigned = case.client.get(
            BASE + "/topology",
            params={"mode": "live", "node_limit": 1, "edge_limit": 1},
        )
        assert unsigned.status_code == 401
        assert unsigned.json()["code"] == "UNAUTHENTICATED"


def test_current_clearance_invalidates_old_view_and_hides_private_basis(
    db_environment, tmp_path, audit_directory
) -> None:
    with projection_case(db_environment, tmp_path, audit_directory) as case:
        set_actor_clearance(
            case,
            (
                "collector-fixture",
                "agent-fixture",
                "assessor-fixture",
                "reader-fixture",
            ),
            2,
        )
        private = supported_claim(case, access_level=2)
        visible_response = topology(case, node_limit=1, edge_limit=1)
        assert visible_response.status_code == 200, visible_response.text
        visible = visible_response.json()
        assert visible["continuation"]

        set_reader_access(case, clearance=1)
        old_page = topology(
            case,
            cursor=visible["continuation"],
            node_limit=1,
            edge_limit=1,
        )
        old_record = case.client.get(
            BASE + "/records/claim/" + private.ref["id"],
            params={"revision": "1", "snapshot_id": visible["snapshot_id"]},
            headers=headers(case),
        )
        fresh_response = topology(case)

        assert old_page.status_code == 404
        assert old_page.json()["code"] == "NOT_FOUND_OR_FORBIDDEN"
        assert old_record.status_code == 410
        assert old_record.json()["code"] == "HISTORY_UNAVAILABLE"
        assert fresh_response.status_code == 200, fresh_response.text
        fresh = fresh_response.json()
        public_text = json.dumps(fresh, sort_keys=True)
        for secret in (
            private.ref["id"],
            private.observation["id"],
            private.artifact.id,
            private.body["text"],
        ):
            assert secret not in public_text
        assert fresh["allowed_actions"] == []
        assert all(node["allowed_actions"] == [] for node in fresh["nodes"])
        assert "count" not in public_text


def test_history_lists_only_saved_views_and_freezes_its_opaque_page(
    db_environment, tmp_path, audit_directory
) -> None:
    with projection_case(
        db_environment,
        tmp_path,
        audit_directory,
        history_page_size=1,
    ) as case:
        supported_claim(case)
        first = topology(case).json()
        second = topology(case).json()

        index_response = case.client.get(
            BASE + "/snapshots",
            headers=headers(case),
        )
        assert index_response.status_code == 200, index_response.text
        index = index_response.json()
        assert len(index["items"]) == 1
        assert index["opaque_cursor"]

        third = topology(case).json()
        continued_response = case.client.get(
            BASE + "/snapshots",
            params={"cursor": index["opaque_cursor"]},
            headers=headers(case),
        )
        assert continued_response.status_code == 200, continued_response.text
        continued = continued_response.json()
        frozen_ids = {
            index["items"][0]["snapshot_id"],
            continued["items"][0]["snapshot_id"],
        }
        assert frozen_ids == {first["snapshot_id"], second["snapshot_id"]}
        assert third["snapshot_id"] not in frozen_ids

        replay_response = topology(
            case,
            mode="history",
            snapshot_id=first["snapshot_id"],
            node_limit=1,
            edge_limit=1,
        )
        assert replay_response.status_code == 200, replay_response.text
        replay = replay_response.json()
        assert replay["snapshot_id"] == first["snapshot_id"]
        assert replay["view_id"] != first["view_id"]
        assert replay["allowed_actions"] == []
        assert all(node["allowed_actions"] == [] for node in replay["nodes"])
        assert replay["continuation"]

        continued_replay_response = topology(
            case,
            mode="history",
            snapshot_id=first["snapshot_id"],
            cursor=replay["continuation"],
            node_limit=1,
            edge_limit=1,
        )
        live_history_mix = topology(
            case,
            mode="live",
            snapshot_id=first["snapshot_id"],
        )
        assert continued_replay_response.status_code == 200
        continued_replay = continued_replay_response.json()
        assert continued_replay["view_id"] == replay["view_id"]
        assert continued_replay["snapshot_id"] == replay["snapshot_id"]
        assert live_history_mix.status_code == 422
        assert live_history_mix.json()["code"] == "INVALID_SCHEMA"

        unknown = topology(
            case,
            mode="history",
            snapshot_id="unknown-saved-snapshot",
        )
        missing_selection = topology(case, mode="history")
        assert unknown.status_code == 410
        assert unknown.json()["code"] == "HISTORY_UNAVAILABLE"
        assert missing_selection.status_code == 422
        assert missing_selection.json()["code"] == "INVALID_SCHEMA"


def test_topology_reads_do_not_create_execution_or_invent_unsourced_runs(
    db_environment, tmp_path, audit_directory
) -> None:
    with projection_case(db_environment, tmp_path, audit_directory) as case:
        def execution_state():
            with case.environment.migration_connection() as connection:
                task = connection.execute(
                    """SELECT desired_state,observed_state,control_version,
                    execution_epoch,runtime_attempt,event_seq,board_revision
                    FROM vnext.task WHERE tenant_id=%s AND project_id=%s
                    AND task_id=%s""",
                    ("tenant-fixture", "project-fixture", "task-fixture"),
                ).fetchone()
                counts = connection.execute(
                    """SELECT
                    (SELECT count(*) FROM vnext.agent_run),
                    (SELECT count(*) FROM vnext.scheduler_assignment),
                    (SELECT count(*) FROM vnext.run_credential),
                    (SELECT count(*) FROM vnext.outbox)"""
                ).fetchone()
            return task, counts

        before = execution_state()
        response = topology(case)
        after = execution_state()

        assert response.status_code == 200, response.text
        assert after == before
        public = response.json()
        assert not any(
            node["ref"]["entity_type"] == "agent_run"
            for node in public["nodes"]
        )
        assert "run-fixture" not in json.dumps(public, sort_keys=True)


def test_expired_view_and_snapshot_return_explicit_410_errors(
    db_environment, tmp_path, audit_directory
) -> None:
    with projection_case(
        db_environment,
        tmp_path,
        audit_directory,
        history_page_size=1,
    ) as case:
        supported_claim(case)
        first = topology(case, node_limit=1, edge_limit=1).json()
        topology(case)
        index_response = case.client.get(
            BASE + "/snapshots",
            headers=headers(case),
        )
        assert index_response.status_code == 200, index_response.text
        index_cursor = index_response.json()["opaque_cursor"]
        assert index_cursor
        with case.environment.migration_connection() as connection:
            connection.execute(
                """UPDATE vnext.projection_cursor
                SET expires_at=clock_timestamp()-interval '1 second'
                WHERE handle=ANY(%s)""",
                ([first["continuation"], index_cursor],),
            )
            connection.execute(
                """UPDATE vnext.projection_materialization
                SET created_at=clock_timestamp()-interval '2 seconds',
                    expires_at=clock_timestamp()-interval '1 second'
                WHERE snapshot_id=%s""",
                (first["snapshot_id"],),
            )

        expired_view = topology(
            case,
            cursor=first["continuation"],
            node_limit=1,
            edge_limit=1,
        )
        expired_snapshot = case.client.get(
            BASE + "/records/claim/not-present",
            params={"revision": "1", "snapshot_id": first["snapshot_id"]},
            headers=headers(case),
        )
        expired_index = case.client.get(
            BASE + "/snapshots",
            params={"cursor": index_cursor},
            headers=headers(case),
        )

        assert expired_view.status_code == 410
        assert expired_view.json()["code"] == "VIEW_EXPIRED"
        assert expired_snapshot.status_code == 410
        assert expired_snapshot.json()["code"] == "SNAPSHOT_EXPIRED"
        assert expired_index.status_code == 410
        assert expired_index.json()["code"] == "VIEW_EXPIRED"


def test_fact_ledger_reads_the_uncommitted_canonical_manifest_in_the_same_rr(
    db_environment, tmp_path, audit_directory
) -> None:
    with projection_case(db_environment, tmp_path, audit_directory) as case:
        claim = supported_claim(case)
        ref = KnowledgeRef.model_validate(claim.ref)
        snapshots = SnapshotRepository(case.knowledge.uow)
        ledger = FactLedger(case.knowledge.uow)

        with case.knowledge.uow.transaction(
            access("reader-fixture", role="reader"),
            "task-fixture",
            capability="snapshot",
            repeatable_read=True,
        ) as tx:
            manifest = snapshots.create_in_transaction(tx)
            record = ledger.read_in_transaction(tx, ref, manifest=manifest)
            forged = replace(
                manifest,
                states={**manifest.states, "claim_assessments": {}},
            )

            assert record.display_kind == "fact"
            assert record.assessment and record.assessment.eligible
            with pytest.raises(DomainError, match="CAPABILITY_UNAVAILABLE"):
                ledger.read_in_transaction(tx, ref, manifest=forged)

        foreign = snapshots.create(
            "task-sibling",
            access("reader-fixture", role="reader"),
        )
        with case.knowledge.uow.transaction(
            access("reader-fixture", role="reader"),
            "task-fixture",
            capability="snapshot",
            repeatable_read=True,
        ) as tx:
            with pytest.raises(DomainError, match="NOT_FOUND_OR_FORBIDDEN"):
                ledger.read_in_transaction(tx, ref, manifest=foreign)


def test_real_run_origin_is_safe_for_reader_and_missing_source_stays_hidden(
    db_environment, tmp_path, audit_directory
) -> None:
    with scheduled_projection_case(
        db_environment, tmp_path, audit_directory
    ) as case:
        assignment = explore_assignment(case.scheduler.scheduler.tick(limit=2))
        run_id = assignment.identity.agent_run_id
        reader = access("reader-fixture", role="reader")

        with case.scheduler.control.uow.transaction(
            reader,
            "task-fixture",
            capability="snapshot",
            repeatable_read=True,
        ) as tx:
            restricted = tx.connection.execute(
                """SELECT assignment_json,assignment_digest,credential_ref,event_seq
                FROM vnext.scheduler_assignment WHERE agent_run_id=%s""",
                (run_id,),
            ).fetchall()
            safe_cursor = tx.connection.execute(
                "SELECT * FROM vnext.projection_run_origin(%s,%s,%s,%s)",
                (*tx.owner, run_id),
            )
            safe = safe_cursor.fetchone()
            safe_fields = tuple(column.name for column in safe_cursor.description)
            cross_task = tx.connection.execute(
                "SELECT * FROM vnext.projection_run_origin(%s,%s,%s,%s)",
                (tx.owner[0], "project-other", "task-sibling", run_id),
            ).fetchone()
            unsourced = tx.connection.execute(
                "SELECT * FROM vnext.projection_run_origin(%s,%s,%s,%s)",
                (*tx.owner, "run-fixture"),
            ).fetchone()

        assert restricted == []
        assert safe is not None
        assert safe_fields == ("created_at",)
        assert cross_task is None
        assert unsourced is None

        response = case.client.get(
            BASE + "/topology",
            params={
                "mode": "live",
                "node_limit": 300,
                "edge_limit": 600,
            },
            headers={
                "Authorization": "Bearer " + case.scheduler.control.tokens.reader
            },
        )
        assert response.status_code == 200, response.text
        topology_body = response.json()
        node_ids = {node["id"] for node in topology_body["nodes"]}
        assert f"agent_run:{run_id}@1" in node_ids
        assert "agent_run:run-fixture@1" not in node_ids
        origin = next(
            node
            for node in topology_body["nodes"]
            if node["ref"]["entity_type"] == "origin"
        )
        assert not any(
            node["ref"]["entity_type"] == "goal"
            for node in topology_body["nodes"]
        )

        detail = case.client.get(
            BASE + "/records/agent_run/" + run_id,
            params={
                "revision": "1",
                "snapshot_id": topology_body["snapshot_id"],
            },
            headers={
                "Authorization": "Bearer " + case.scheduler.control.tokens.reader
            },
        )
        assert detail.status_code == 200, detail.text
        record = detail.json()["record"]
        assert datetime.fromisoformat(
            record["created_at"].replace("Z", "+00:00")
        ) == safe[0]
        origin_detail = case.client.get(
            BASE + "/records/origin/task-fixture",
            params={
                "revision": origin["ref"]["revision"],
                "snapshot_id": topology_body["snapshot_id"],
            },
            headers={
                "Authorization": "Bearer " + case.scheduler.control.tokens.reader
            },
        )
        assert origin_detail.status_code == 200, origin_detail.text
        assert origin_detail.json()["record"]["goal_revision"] == "1"
        public = json.dumps({"topology": topology_body, "record": detail.json()})
        for restricted_name in (
            "event_seq",
            "assignment_json",
            "assignment_digest",
            "credential_ref",
        ):
            assert restricted_name not in public

        with case.environment.migration_connection() as connection:
            connection.execute(
                """UPDATE vnext.task_access SET can_read=false
                WHERE tenant_id='tenant-fixture' AND project_id='project-fixture'
                AND task_id='task-fixture' AND subject='reader-fixture'"""
            )
        with case.environment.additional_app_connection() as connection:
            with connection.transaction():
                for key, value in {
                    "tenant": "tenant-fixture",
                    "project": "project-fixture",
                    "task": "task-fixture",
                    "subject": "reader-fixture",
                    "clearance": "1",
                    "snapshot": "true",
                    "admit": "false",
                    "observe": "false",
                    "request_purpose": "",
                }.items():
                    connection.execute(
                        "SELECT set_config(%s,%s,true)",
                        ("wuji." + key, value),
                    ).fetchone()
                revoked_safe = connection.execute(
                    "SELECT * FROM vnext.projection_run_origin(%s,%s,%s,%s)",
                    ("tenant-fixture", "project-fixture", "task-fixture", run_id),
                ).fetchone()
                revoked_assignment = connection.execute(
                    "SELECT assignment_json FROM vnext.scheduler_assignment"
                ).fetchall()

        assert revoked_safe is None
        assert revoked_assignment == []
