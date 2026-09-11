"""Five minimal D2 API/real PostgreSQL checks with native-shaped HTTP substitutes."""
import asyncio
from uuid import uuid4

import psycopg
import pytest

BASE = "https://synthetic-model.example/v1"
SECRET = "synthetic-upstream-key-D2-only"


def service_body():
    return {"name": "Synthetic service", "config": {"protocol": "openai", "base_url": BASE}, "api_key": SECRET}


def profile_body(service_id, priced=True):
    config = {"service_version_id": service_id, "model_id": "synthetic-chat", "context_window": 4096,
              "max_output_tokens": 256, "timeout_seconds": 30}
    if priced:
        config["pricing"] = {"source": "synthetic fixture", "input_per_million": "1.25",
            "output_per_million": "2.5", "cache_mode": "standard_input"}
    return {"name": "Synthetic profile", "config": config}


def ok(response):
    assert response.status_code == 200, response.text
    assert SECRET not in response.text
    return response.json()


async def post(client, path, body, key=None):
    return await client.post(path, json=body, headers={"Idempotency-Key": key or str(uuid4())})


async def save(client, case, kind, body, definition=None):
    segment = "model-services" if kind == "service" else "model-profiles"
    path = case.path(segment + (f"/{definition}/versions" if definition else ""))
    operation = ok(await post(client, path, body))
    assert operation["state"] == "succeeded"
    return ok(await client.get(case.path(f"model-{kind}-versions/{operation['version_id']}")))


async def check(client, case, version):
    result = ok(await post(client, case.path(f"model-profile-versions/{version['id']}/checks"), {}))
    assert result["state"] == "succeeded"
    assert result["result"]["usage"] is None and result["result"]["cost_usd"] is None
    return result


async def command(client, case, version, action, key=None):
    return await post(client, case.path(f"model-profile-versions/{version['id']}/commands"),
                      {"action": action, "expected_version": version["state_revision"]}, key)


def test_m01_admin_permissions_cross_tenant_revocation_and_rls(model_case):
    case, draft = model_case, model_case.draft
    async def scenario():
        async with case.client("peer") as (client, _):
            assert ok(await client.get("/api/v1/tenants"))["items"][0]["permissions"] == []
            assert (await client.get(case.path("model-services"))).status_code == 403
            assert (await post(client, case.path("model-services"), service_body())).status_code == 403
        case.grant()
        case.grant("outsider")
        with draft.database.connect() as connection:
            connection.execute("UPDATE project_memberships SET enabled=false WHERE user_id=%s", (draft.users["owner"],))
        async with case.client() as (client, _):
            assert set(ok(await client.get("/api/v1/tenants"))["items"][0]["permissions"]) == {"model.config.read", "model.config.write"}
            version = await save(client, case, "service", service_body())
            assert (await client.get(f"/api/v1/projects/{draft.project}/model-profiles")).status_code == 404
            assert (await client.get(case.path("model-services", draft.other_tenant))).status_code == 403
        async with case.client("outsider") as (client, _):
            assert (await client.get(case.path(f"model-service-versions/{version['id']}", draft.other_tenant))).status_code == 404
        with draft.database.connect("project") as connection:
            connection.execute("SELECT set_config('app.user_id',%s,true),set_config('app.tenant_id',%s,true)",
                               (draft.users["peer"], draft.tenant))
            assert connection.execute("SELECT count(*) FROM model_versions").fetchone()[0] == 0
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                connection.execute("UPDATE tenant_admin_grants SET enabled=true")
        with draft.database.connect("auth") as connection:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                connection.execute("SELECT * FROM model_versions")
        case.grant(enabled=False)
        async with case.client() as (client, _):
            assert (await client.get(case.path(f"model-service-versions/{version['id']}"))).status_code == 403
        assert case.native.count("POST", "/credentials") == 1
    asyncio.run(scenario())


def test_m02_service_versions_replay_pagination_and_secret_absence(model_case):
    case = model_case
    case.grant()
    async def scenario():
        async with case.client() as (client, _):
            key = str(uuid4())
            first = ok(await post(client, case.path("model-services"), service_body(), key))
            assert first["state"] == "succeeded"
            assert ok(await post(client, case.path("model-services"), service_body(), key)) == first
            version = ok(await client.get(case.path(f"model-service-versions/{first['version_id']}")))
            second = await save(client, case, "service", {**service_body(), "name": "Second version"}, version["definition_id"])
            assert version["number"] == 1 and second["number"] == 2
            path = case.path(f"model-services/{version['definition_id']}/versions")
            page = ok(await client.get(path, params={"limit": 1}))
            tail = ok(await client.get(path, params={"limit": 1, "cursor": page["next_cursor"]}))
            assert {page["items"][0]["id"], tail["items"][0]["id"]} == {version["id"], second["id"]}
            assert tail["next_cursor"] is None
            assert (await client.get(case.path("model-services"), params={"limit": 1, "cursor": page["next_cursor"]})).status_code == 422
            assert case.native.count("POST", "/credentials") == 2
        with case.draft.database.connect() as connection:
            for table in ("model_definitions", "model_versions", "model_operations"):
                rows = connection.execute(f"SELECT row_to_json(t)::text FROM {table} t WHERE tenant_id=%s", (case.draft.tenant,)).fetchall()
                assert rows and all(SECRET not in row[0] and 'api_key' not in row[0] for row in rows)
    asyncio.run(scenario())


def test_m03_check_publish_selection_and_version_specific_evidence(model_case):
    case = model_case
    case.grant()
    async def scenario():
        async with case.client() as (client, _):
            service = await save(client, case, "service", service_body())
            missing = await save(client, case, "profile", profile_body(service["id"], priced=False))
            await check(client, case, missing)
            assert (await command(client, case, missing, "publish")).status_code == 409
            good = await save(client, case, "profile", profile_body(service["id"]), missing["definition_id"])
            assert (await command(client, case, good, "publish")).status_code == 409
            await check(client, case, good)
            assert ok(await command(client, case, good, "publish"))["state"] == "succeeded"
            another = await save(client, case, "profile", profile_body(service["id"]), good["definition_id"])
            assert (await command(client, case, another, "publish")).status_code == 409
            assert case.native.count("GET", "/health") == 2
        async with case.client("peer") as (client, _):
            selection = ok(await client.get(f"/api/v1/projects/{case.draft.project}/model-profiles"))
            assert [row["id"] for row in selection["items"]] == [good["id"]]
            assert (await client.get(case.path("model-profiles"))).status_code == 403
    asyncio.run(scenario())


def test_m04_unknown_create_reconciles_read_only_and_check_never_repeats(model_case):
    case = model_case
    case.grant()
    async def scenario():
        async with case.client() as (client, _):
            key = str(uuid4())
            case.native.lose_create = True
            lost = ok(await post(client, case.path("model-services"), service_body(), key))
            assert lost["state"] == "unknown"
            restored = ok(await client.get(case.path(f"model-operations/{lost['id']}")))
            assert restored["state"] == "succeeded"
            assert ok(await post(client, case.path("model-services"), service_body(), key))["id"] == lost["id"]
            assert (await post(client, case.path("model-services"), {**service_body(), "name": "Different"}, key)).status_code == 409
            assert case.native.count("POST", "/credentials") == 1
            profile = await save(client, case, "profile", profile_body(lost["version_id"]))
            case.native.lose_health = True
            check_key = str(uuid4())
            path = case.path(f"model-profile-versions/{profile['id']}/checks")
            unknown = ok(await post(client, path, {}, check_key))
            assert unknown["state"] == "unknown"
            assert ok(await post(client, path, {}, check_key))["state"] == "unknown"
            assert ok(await client.get(case.path(f"model-operations/{unknown['id']}")))["state"] == "unknown"
            assert (await command(client, case, profile, "publish")).status_code == 409
            assert case.native.count("GET", "/health") == 1
    asyncio.run(scenario())


def test_m05_retire_and_failed_native_block_remove_selection_locally(model_case):
    case = model_case
    case.grant()
    async def scenario():
        async with case.client() as (client, _):
            service = await save(client, case, "service", service_body())
            profile = await save(client, case, "profile", profile_body(service["id"]))
            await check(client, case, profile)
            ok(await command(client, case, profile, "publish"))
            path = case.path(f"model-profile-versions/{profile['id']}")
            profile = ok(await client.get(path))
            ok(await command(client, case, profile, "retire"))
            selection_path = f"/api/v1/projects/{case.draft.project}/model-profiles"
            assert ok(await client.get(selection_path))["items"] == []
            profile = ok(await client.get(path))
            assert profile["state"] == "retired"
            ok(await command(client, case, profile, "publish"))
            profile = ok(await client.get(path))
            case.native.reject_block = True
            key = str(uuid4())
            failed = ok(await command(client, case, profile, "revoke", key))
            assert failed["state"] == "failed"
            revoked = ok(await client.get(path))
            assert revoked["state"] == "revoked" and revoked["sync_state"] == "unknown"
            assert ok(await client.get(selection_path))["items"] == []
            assert ok(await command(client, case, profile, "revoke", key))["id"] == failed["id"]
            assert case.native.count("POST", "/model/block") == 1
            assert case.native.count("GET", "/health") == 1
    asyncio.run(scenario())
