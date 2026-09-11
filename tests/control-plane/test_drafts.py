"""D01–D04: real migrations, sessions, runtime roles and the saved-draft API."""
import asyncio
from pathlib import Path
from uuid import uuid4

import jsonschema
import psycopg
import pytest
import yaml


def validate_response(response, name):
    assert response.status_code == 200, response.text
    contract = yaml.safe_load((Path(__file__).resolve().parents[2] / "packages/contracts/openapi.yaml").read_text())
    schema = {"$ref": f"#/components/schemas/{name}", "components": contract["components"]}
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(response.json())
    return response.json()


def test_five_incomplete_scenarios_restore_without_tasks(draft_case):
    async def scenario():
        async with draft_case.client() as (client, app):
            assert await app.state.runtime.authority.ready()
            session = await client.get("/api/v1/session")
            assert session.status_code == 200
            assert session.json()["user_id"] == draft_case.users["owner"]
            for kind in ("ctf", "web_single", "comprehensive", "exercise", "code_audit"):
                draft_id = str(uuid4())
                saved = validate_response(await client.put(draft_case.path(draft_id), json={
                    "expected_version": 0, "content": {"scenario": kind}}), "SavedTaskDraft")
                assert saved["version"] == 1
                assert saved["content"]["model_profile_version_id"] is None
                assert saved["content"]["name"] == ""
                assert (await client.get(draft_case.path(draft_id))).json() == saved
            page = validate_response(await client.get(draft_case.path()), "SavedTaskDraftPage")
            assert len(page["items"]) == 5 and page["next_cursor"] is None
            tasks = await client.get(f"/api/v1/projects/{draft_case.project}/tasks")
            assert tasks.status_code == 200 and tasks.json()["items"] == []
        with draft_case.database.connect() as connection:
            for table in ("tasks", "command_receipts", "task_events", "authorization_records"):
                assert connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    asyncio.run(scenario())


def test_normalized_replay_versions_and_cursor_pagination(draft_case):
    async def scenario():
        async with draft_case.client() as (client, _):
            draft_id = str(uuid4())
            body = {"expected_version": 0, "content": {"scenario": "web_single", "name": "  Web  ",
                    "entry_url": "HTTP://EXAMPLE.COM:80/path", "budget_usd": "2.500000"}}
            first = validate_response(await client.put(draft_case.path(draft_id), json=body), "SavedTaskDraft")
            assert first["content"]["name"] == "Web"
            assert first["content"]["entry_url"] == "http://example.com/path"
            assert first["content"]["budget_usd"] == "2.5"
            body["content"] = first["content"]
            assert (await client.put(draft_case.path(draft_id), json=body)).json() == first
            changed = {"expected_version": 1, "content": {**first["content"], "name": "Revised"}}
            second = validate_response(await client.put(draft_case.path(draft_id), json=changed), "SavedTaskDraft")
            assert second["version"] == 2
            assert (await client.put(draft_case.path(draft_id), json=changed)).json() == second
            conflict = await client.put(draft_case.path(draft_id), json=body)
            assert conflict.status_code == 409 and conflict.json()["code"] == "VERSION_CONFLICT"
            ids = {draft_id}
            for _ in range(2):
                new_id = str(uuid4())
                ids.add(new_id)
                assert (await client.put(draft_case.path(new_id), json={"expected_version": 0,
                    "content": {"scenario": "ctf"}})).status_code == 200
            page = validate_response(await client.get(draft_case.path(), params={"limit": 2}), "SavedTaskDraftPage")
            cursor = page["next_cursor"]
            assert cursor and len(page["items"]) == 2
            tail = validate_response(await client.get(draft_case.path(), params={"limit": 2, "cursor": cursor}), "SavedTaskDraftPage")
            assert tail["next_cursor"] is None and len(tail["items"]) == 1
            assert {row["id"] for row in page["items"] + tail["items"]} == ids
            assert (await client.get(f"/api/v1/projects/{draft_case.project}/tasks",
                                     params={"limit": 2, "cursor": cursor})).status_code == 422
            assert (await client.get(draft_case.path(project=draft_case.second_project),
                                     params={"limit": 2, "cursor": cursor})).status_code == 422
    asyncio.run(scenario())


def test_owner_viewer_project_isolation_and_runtime_rls(draft_case):
    async def scenario():
        draft_id = str(uuid4())
        body = {"expected_version": 0, "content": {"scenario": "ctf"}}
        async with draft_case.client() as (client, _):
            assert (await client.put(draft_case.path(draft_id), json=body)).status_code == 200
            project = await client.get(f"/api/v1/projects/{draft_case.project}")
            assert {"task.draft.read", "task.draft.write"} <= set(project.json()["permissions"])
            assert (await client.get(draft_case.path(draft_id, draft_case.second_project))).status_code == 404
        for user in ("peer", "outsider"):
            async with draft_case.client(user) as (client, _):
                assert (await client.get(draft_case.path(draft_id))).status_code == 404
                assert (await client.put(draft_case.path(draft_id), json=body)).status_code == 404
                listing = await client.get(draft_case.path())
                if user == "peer":
                    assert listing.status_code == 200 and listing.json()["items"] == []
                else:
                    assert listing.status_code == 404
        with draft_case.database.connect("project") as connection:
            assert connection.execute("SELECT count(*) FROM task_drafts").fetchone()[0] == 0
            for user, tenant, project in (("owner", draft_case.tenant, draft_case.project),
                                          ("peer", draft_case.tenant, draft_case.project),
                                          ("owner", draft_case.tenant, draft_case.second_project),
                                          ("outsider", draft_case.other_tenant, draft_case.other_project)):
                connection.execute("SELECT set_config('app.user_id', %s, true), set_config('app.tenant_id', %s, true), "
                                   "set_config('app.project_id', %s, true)", (draft_case.users[user], tenant, project))
                count = connection.execute("SELECT count(*) FROM task_drafts WHERE id = %s", (draft_id,)).fetchone()[0]
                assert count == int(user == "owner" and project == draft_case.project)
        with draft_case.database.connect("auth") as connection:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                connection.execute("SELECT * FROM task_drafts")
        with draft_case.database.connect("project") as connection:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                connection.execute("UPDATE task_drafts SET user_id = %s WHERE id = %s",
                                   (draft_case.users["peer"], draft_id))
        with draft_case.database.connect() as connection:
            connection.execute("UPDATE project_memberships SET role = 'viewer' WHERE user_id = %s", (draft_case.users["owner"],))
            connection.execute("UPDATE users SET permissions_version = permissions_version + 1 WHERE id = %s", (draft_case.users["owner"],))
        async with draft_case.client() as (client, _):
            assert (await client.get(draft_case.path(draft_id))).status_code == 200
            assert (await client.put(draft_case.path(draft_id), json=body)).status_code == 403
            project = (await client.get(f"/api/v1/projects/{draft_case.project}")).json()
            assert "task.draft.read" in project["permissions"] and "task.draft.write" not in project["permissions"]
        with draft_case.database.connect("project") as connection:
            connection.execute("SELECT set_config('app.user_id', %s, true), set_config('app.tenant_id', %s, true), "
                               "set_config('app.project_id', %s, true)",
                               (draft_case.users["owner"], draft_case.tenant, draft_case.project))
            assert connection.execute("UPDATE task_drafts SET version = version + 1 WHERE id = %s", (draft_id,)).rowcount == 0
        with draft_case.database.connect() as connection:
            connection.execute("UPDATE project_memberships SET enabled = false WHERE user_id = %s", (draft_case.users["owner"],))
        async with draft_case.client() as (client, _):
            assert (await client.get(draft_case.path(draft_id))).status_code == 404
    asyncio.run(scenario())


def test_session_write_guards_and_fresh_permission_version(draft_case, monkeypatch):
    async def scenario():
        draft_id = str(uuid4())
        body = {"expected_version": 0, "content": {"scenario": "ctf"}}
        async with draft_case.client() as (client, app):
            for header in ("Origin", "X-CSRF-Token"):
                value = client.headers.pop(header)
                assert (await client.put(draft_case.path(draft_id), json=body)).status_code == 403
                client.headers[header] = value
            assert (await client.put(draft_case.path(draft_id), json=body,
                                     headers={"Origin": "https://untrusted.example"})).status_code == 403
            original = app.state.runtime.authority.authenticate
            async def change_after_authentication(raw_token):
                session = await original(raw_token)
                with draft_case.database.connect() as connection:
                    connection.execute("UPDATE users SET permissions_version = permissions_version + 1 WHERE id = %s", (draft_case.users["owner"],))
                return session
            monkeypatch.setattr(app.state.runtime.authority, "authenticate", change_after_authentication)
            conflict = await client.put(draft_case.path(draft_id), json=body)
            assert conflict.status_code == 409 and conflict.json()["code"] == "VERSION_CONFLICT"
            monkeypatch.setattr(app.state.runtime.authority, "authenticate", original)
            assert (await client.put(draft_case.path(draft_id), json=body)).status_code == 200
            client.cookies.clear()
            assert (await client.get(draft_case.path(draft_id))).status_code == 401
    asyncio.run(scenario())


def test_invalid_draft_input_is_rejected_without_storage(draft_case):
    async def scenario():
        invalid = [
            {"scenario": "web_single", "entry_url": "https://user:password@example.com"},
            {"scenario": "web_single", "entry_url": "https://example.com/#fragment"},
            {"scenario": "ctf", "budget_usd": "0"},
            {"scenario": "ctf", "challenge": "invalid\x00text"},
            {"scenario": "ctf", "budget_usd": 1.5},
            {"scenario": "ctf", "budget_usd": "1.0000001"},
            {"scenario": "web_single", "password": "not-accepted"},
            {"scenario": "ctf", "assets": []},
            {"scenario": "code_audit", "repository_url": "https://example.com/repo", "source_reference_id": str(uuid4())},
            {"scenario": "comprehensive", "assets": ["x"] * 101},
            {"scenario": "comprehensive", "assets": ["界" * 2048] * 20},
        ]
        async with draft_case.client() as (client, _):
            for content in invalid:
                result = await client.put(draft_case.path(str(uuid4())), json={"expected_version": 0, "content": content})
                assert result.status_code == 422, result.text
            page = validate_response(await client.get(draft_case.path()), "SavedTaskDraftPage")
            assert page["items"] == []
    asyncio.run(scenario())
