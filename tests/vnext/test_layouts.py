from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from support.http_capture import RecordedTestClient
from support.p13 import BASE, OWNER, add_reader, projection_case, set_reader_access
from wuji_core.http import create_app
from wuji_core.http.layouts import create_layout_router
from wuji_core.persistence.schema import migrate
from wuji_core.projection.layouts import LayoutRepository


LIVE = BASE + "/layouts/knowledge-live"
HISTORY = BASE + "/layouts/knowledge-history"


@contextmanager
def layout_case(environment, tmp_path, audit_directory):
    with projection_case(environment, tmp_path, audit_directory) as projection:
        layouts = LayoutRepository(projection.knowledge.uow)
        client = RecordedTestClient(
            create_app(
                token_verifier=projection.knowledge.verifier,
                routers=[create_layout_router(layouts)],
            ),
            audit_path=audit_directory / "layout-http-exchanges.jsonl",
        )
        try:
            yield SimpleNamespace(
                **vars(projection),
                layouts=layouts,
                layout_client=client,
            )
        finally:
            client.close()


def auth(case, token: str | None = None) -> dict[str, str]:
    return {
        "Authorization": "Bearer " + (token or case.knowledge.tokens.reader),
    }


def patch(*, mode: str = "follow_latest", entries=None, viewport=None) -> dict:
    return {
        "schema_version": "wuji.api.v2",
        "selection_mode": mode,
        "entries": entries or [],
        "viewport": viewport or {"x": 0, "y": 0, "zoom": 0.82},
    }


def origin_entry():
    return {
        "anchor": {"entity_type": "origin", "id": TASK, "revision": None},
        "x": 120,
        "y": 240,
        "pinned": False,
    }


TASK = OWNER[2]


def test_layout_get_defaults_and_put_uses_personal_cas_without_domain_event(
    db_environment, tmp_path, audit_directory
):
    with layout_case(db_environment, tmp_path, audit_directory) as case:
        with db_environment.migration_connection() as connection:
            before = connection.execute(
                "SELECT board_revision,event_seq,observation_count FROM vnext.task WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                OWNER,
            ).fetchone()

        initial = case.layout_client.get(LIVE, headers=auth(case))
        assert initial.status_code == 200, initial.text
        assert initial.json() == {
            "schema_version": "wuji.api.v2",
            "view_name": "knowledge-live",
            "layout_revision": "0",
            "selection_mode": "follow_latest",
            "entries": [],
            "viewport": {"x": 0.0, "y": 0.0, "zoom": 0.82},
        }

        saved = case.layout_client.put(
            LIVE,
            headers={**auth(case), "If-Match": "0"},
            json=patch(entries=[origin_entry()], viewport={"x": -20, "y": 30, "zoom": 1.1}),
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["view_name"] == "knowledge-live"
        assert saved.json()["layout_revision"] == "1"

        restored = case.layout_client.get(LIVE, headers=auth(case))
        assert restored.status_code == 200, restored.text
        assert restored.json()["layout_revision"] == "1"
        assert restored.json()["entries"] == [origin_entry()]
        assert restored.json()["viewport"] == {"x": -20.0, "y": 30.0, "zoom": 1.1}

        stale = case.layout_client.put(
            LIVE,
            headers={**auth(case), "If-Match": "0"},
            json=patch(entries=[], viewport={"x": 0, "y": 0, "zoom": 0.82}),
        )
        assert stale.status_code == 409, stale.text
        assert stale.json()["code"] == "STALE_VERSION"

        with db_environment.migration_connection() as connection:
            after = connection.execute(
                "SELECT board_revision,event_seq,observation_count FROM vnext.task WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                OWNER,
            ).fetchone()
            stored = connection.execute(
                "SELECT layout_revision,subject,view_name FROM vnext.layout_preference"
            ).fetchall()
        assert after == before
        assert stored == [(1, "reader-fixture", "knowledge-live")]


def test_layout_isolated_by_subject_and_view_mode(db_environment, tmp_path, audit_directory):
    with layout_case(db_environment, tmp_path, audit_directory) as case:
        second_token = add_reader(case, "reader-two")
        first = case.layout_client.put(
            LIVE,
            headers={**auth(case), "If-Match": "0"},
            json=patch(entries=[origin_entry()]),
        )
        assert first.status_code == 200, first.text

        second_default = case.layout_client.get(LIVE, headers=auth(case, second_token))
        assert second_default.status_code == 200, second_default.text
        assert second_default.json()["layout_revision"] == "0"
        assert second_default.json()["entries"] == []

        second_patch = patch(
            mode="explicit_revision",
            entries=[origin_entry()],
        )
        wrong_mode = case.layout_client.put(
            HISTORY,
            headers={**auth(case, second_token), "If-Match": "0"},
            json=second_patch,
        )
        assert wrong_mode.status_code == 200, wrong_mode.text

        first_history = case.layout_client.get(HISTORY, headers=auth(case))
        assert first_history.status_code == 200, first_history.text
        assert first_history.json()["layout_revision"] == "0"
        assert first_history.json()["entries"] == []

        second_history = case.layout_client.get(HISTORY, headers=auth(case, second_token))
        assert second_history.status_code == 200, second_history.text
        assert second_history.json()["layout_revision"] == "1"


def test_layout_rejects_unknown_or_duplicate_anchors_and_invalid_json(
    db_environment, tmp_path, audit_directory
):
    with layout_case(db_environment, tmp_path, audit_directory) as case:
        unknown = case.layout_client.put(
            LIVE,
            headers={**auth(case), "If-Match": "0"},
            json=patch(
                entries=[
                    {
                        "anchor": {"entity_type": "claim", "id": "missing"},
                        "x": 1,
                        "y": 2,
                        "pinned": False,
                    }
                ]
            ),
        )
        assert unknown.status_code == 422, unknown.text
        assert unknown.json()["code"] == "INVALID_REFERENCE"

        duplicate = case.layout_client.put(
            LIVE,
            headers={**auth(case), "If-Match": "0"},
            json=patch(entries=[origin_entry(), origin_entry()]),
        )
        assert duplicate.status_code == 422, duplicate.text
        assert duplicate.json()["code"] == "INVALID_SCHEMA"

        invalid_json = case.layout_client.put(
            LIVE,
            headers={
                **auth(case),
                "If-Match": "0",
                "Content-Type": "application/json",
            },
            content=b'{"schema_version":"wuji.api.v2","schema_version":"wuji.api.v2"}',
        )
        assert invalid_json.status_code == 422, invalid_json.text
        assert invalid_json.json()["code"] == "INVALID_SCHEMA"


def test_layout_revocation_is_indistinguishable_from_absence(
    db_environment, tmp_path, audit_directory
):
    with layout_case(db_environment, tmp_path, audit_directory) as case:
        set_reader_access(case, can_read=False)
        get_response = case.layout_client.get(LIVE, headers=auth(case))
        put_response = case.layout_client.put(
            LIVE,
            headers={**auth(case), "If-Match": "0"},
            json=patch(entries=[origin_entry()]),
        )
        assert get_response.status_code == 404
        assert put_response.status_code == 404


def test_layout_migration_is_idempotent_and_is_latest_head(db_environment):
    with db_environment.migration_connection() as connection:
        migrate(connection, application_role=db_environment.application_role)
        migrate(connection, application_role=db_environment.application_role)
        assert connection.execute(
            "SELECT head FROM vnext.schema_migration ORDER BY applied_at DESC LIMIT 1"
        ).fetchone() == ("vnext_0018_p15_layout",)
        assert connection.execute(
            "SELECT to_regclass('vnext.layout_preference')"
        ).fetchone() == ("vnext.layout_preference",)
