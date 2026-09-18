from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys

import httpx


ROOT = Path(__file__).resolve().parents[2]
HELPER_SPEC = importlib.util.spec_from_file_location(
    "a3_gateway_test_helpers", ROOT / "tests/vnext/test_web_gateway.py"
)
helpers = importlib.util.module_from_spec(HELPER_SPEC)
sys.modules[HELPER_SPEC.name] = helpers
HELPER_SPEC.loader.exec_module(helpers)

gateway_module = helpers.gateway_module
FakeClient = helpers.FakeClient
FakeResponse = helpers.FakeResponse
FakeStreamResponse = helpers.FakeStreamResponse
settings = helpers.settings
_login = helpers._login


def test_local_entry_exchange_is_not_origin_only_and_logout_revokes_session(tmp_path):
    config, _public = settings(tmp_path)
    app = gateway_module.create_gateway(config, client=FakeClient(FakeResponse(200, b"{}")))

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:44180"
        ) as client:
            origin = {"Origin": "http://127.0.0.1:44180"}
            origin_only = await client.post("/auth/login", headers=origin)
            bearer_attempt = await client.post(
                "/auth/login",
                headers={
                    **origin,
                    gateway_module.LOCAL_ACCESS_HEADER: "b" * 32,
                    "Authorization": "Bearer browser-made",
                },
            )
            login = await client.post(
                "/auth/login",
                headers={
                    **origin,
                    gateway_module.LOCAL_ACCESS_HEADER: "b" * 32,
                },
            )
            cookie = login.headers["set-cookie"].split(";", 1)[0]
            session = await client.get("/auth/session")
            logout = await client.post("/auth/logout", headers=origin)
            revoked = await client.get("/auth/session", headers={"Cookie": cookie})
            second_exchange = await client.post(
                "/auth/login",
                headers={
                    **origin,
                    gateway_module.LOCAL_ACCESS_HEADER: "b" * 32,
                },
            )
            relogin_session = await client.get("/auth/session")
            return origin_only, bearer_attempt, login, session, logout, revoked, second_exchange, relogin_session

    origin_only, bearer_attempt, login, session, logout, revoked, second_exchange, relogin_session = asyncio.run(run())
    assert origin_only.status_code == 401
    assert bearer_attempt.status_code == 400
    assert login.status_code == 200
    assert login.json()["mode"] == "local_single_operator"
    assert login.json()["subject"] == "operator"
    assert "Authorization" not in login.text
    assert "bbbb" not in login.text
    assert session.status_code == 200
    assert session.json()["initial_task_id"] == "task-fixture"
    assert logout.status_code == 204
    assert revoked.status_code == 401
    assert second_exchange.status_code == 200
    assert relogin_session.status_code == 200


def test_c01_c03_routes_are_multi_task_but_project_is_only_an_ingress_constraint(tmp_path):
    config, _public = settings(tmp_path)
    fake = FakeClient(FakeResponse(200, b"{}"))
    app = gateway_module.create_gateway(config, client=fake)

    command = b'{"schema_version":"wuji.api.v2","command":"start","expected_version":"1","reason":"explicit start"}'

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:44180"
        ) as client:
            await _login(client)
            reads = await asyncio.gather(
                client.get("/api/v2/tasks?project_id=project-fixture&limit=20"),
                client.get("/api/v2/projects/project-fixture/task-options"),
                client.get("/api/v2/tasks/task-a"),
                client.get("/api/v2/tasks/task-b/readiness"),
                client.get("/api/v2/tasks/task-b/launch"),
            )
            command_response = await client.post(
                "/api/v2/tasks/task-b/commands",
                headers={
                    "Origin": "http://127.0.0.1:44180",
                    "Content-Type": "application/json",
                    "Idempotency-Key": "start-task-b-1",
                },
                content=command,
            )
            wrong_project = await client.get(
                "/api/v2/tasks?project_id=other-project&limit=20"
            )
            return reads, command_response, wrong_project

    reads, command_response, wrong_project = asyncio.run(run())
    assert all(response.status_code == 200 for response in reads)
    assert command_response.status_code == 200
    assert wrong_project.status_code == 404
    forwarded_urls = [url for url, _headers in fake.requests]
    assert any(url.endswith("/api/v2/tasks/task-a") for url in forwarded_urls)
    assert any(url.endswith("/api/v2/tasks/task-b/readiness") for url in forwarded_urls)
    assert any(url.endswith("/api/v2/tasks/task-b/launch") for url in forwarded_urls)
    assert any(
        url.endswith("/api/v2/tasks/task-b/commands")
        for _method, url, _headers, _body in fake.request_bodies
    )


def test_route_and_json_negative_controls_are_bounded_and_do_not_forward(tmp_path):
    config, _public = settings(tmp_path)
    fake = FakeClient(FakeResponse(200, b"{}"))
    app = gateway_module.create_gateway(config, client=fake)
    duplicate = b'{"schema_version":"wuji.api.v2","command":"start","expected_version":"1","reason":"a","reason":"b"}'
    oversized = b"{" + b"a" * 70_000

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:44180"
        ) as client:
            await _login(client)
            duplicate_json = await client.post(
                "/api/v2/tasks/task-a/commands",
                headers={
                    "Origin": "http://127.0.0.1:44180",
                    "Content-Type": "application/json",
                    "Idempotency-Key": "duplicate-json-1",
                },
                content=duplicate,
            )
            oversized_json = await client.post(
                "/api/v2/tasks/task-a/commands",
                headers={
                    "Origin": "http://127.0.0.1:44180",
                    "Content-Type": "application/json",
                    "Idempotency-Key": "oversized-json-1",
                },
                content=oversized,
            )
            duplicate_query = await client.get(
                "/api/v2/tasks/task-a/topology?mode=live&mode=history"
            )
            encoded_path = await client.get("/api/v2/tasks/task%2Fa/topology")
            internal = await client.get("/internal/v2/tool-calls/call-1/material")
            auth_header = await client.get(
                "/api/v2/tasks/task-a", headers={"Authorization": "Bearer browser"}
            )
            missing_origin = await client.post(
                "/api/v2/tasks/task-a/commands",
                headers={
                    "Content-Type": "application/json",
                    "Idempotency-Key": "no-origin-1",
                },
                content=b'{"schema_version":"wuji.api.v2","command":"start","expected_version":"1","reason":"x"}',
            )
            return duplicate_json, oversized_json, duplicate_query, encoded_path, internal, auth_header, missing_origin

    responses = asyncio.run(run())
    assert [response.status_code for response in responses] == [422, 422, 422, 400, 404, 400, 403]
    assert fake.request_bodies == []
    assert fake.requests == []


def test_public_material_and_artifact_content_are_bounded_and_internal_material_is_not_exposed(tmp_path):
    config, _public = settings(tmp_path)
    fake = FakeClient(
        FakeResponse(
            200,
            b'{"schema_version":"wuji.model-material.v2","status":"omitted","source":null,"representation":null,"omission_reason":"source_unavailable"}',
            {"content-type": "application/json"},
        )
    )
    app = gateway_module.create_gateway(config, client=fake)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:44180"
        ) as client:
            await _login(client)
            material = await client.get(
                "/api/v2/tasks/task-b/artifacts/artifact-1/material?version=1"
            )
            content = await client.get(
                "/api/v2/artifacts/artifact-1/content?version=1"
            )
            internal = await client.get(
                "/internal/v2/tool-calls/call-1/material?representation=wuji.model-material.v2"
            )
            return material, content, internal

    material, content, internal = asyncio.run(run())
    assert material.status_code == 200
    assert content.status_code == 200
    assert content.headers["content-disposition"].startswith("attachment;")
    assert internal.status_code == 404
    assert all("/internal/" not in url for url, _headers in fake.requests)


def test_lost_mutation_response_is_operation_unknown_without_replay(tmp_path):
    config, _public = settings(tmp_path)

    class LostClient(FakeClient):
        def __init__(self):
            super().__init__(FakeResponse(200, b"{}"))
            self.send_count = 0

        async def send(self, request, *, stream: bool = False, timeout=None):
            self.send_count += 1
            raise httpx.ReadError("connection closed after request")

    fake = LostClient()
    app = gateway_module.create_gateway(config, client=fake)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:44180"
        ) as client:
            await _login(client)
            return await client.post(
                "/api/v2/tasks/task-a/commands",
                headers={
                    "Origin": "http://127.0.0.1:44180",
                    "Content-Type": "application/json",
                    "Idempotency-Key": "same-key-after-502",
                },
                content=b'{"schema_version":"wuji.api.v2","command":"start","expected_version":"1","reason":"x"}',
            )

    response = asyncio.run(run())
    assert response.status_code == 502
    assert response.json()["code"] == "OPERATION_UNKNOWN"
    assert fake.send_count == 1


def test_view_ledger_binds_session_and_task_and_logout_does_not_cancel_worker(tmp_path):
    config, _public = settings(tmp_path)
    topology = FakeResponse(200, b'{"view_id":"view-a","snapshot_id":"snap-a"}')
    stream = FakeStreamResponse(200, [b"event: view\ndata: {\"view_id\":\"view-a\"}\n\n"])
    fake_a = FakeClient(topology, stream_response=stream)
    app_a = gateway_module.create_gateway(config, client=fake_a)
    fake_b = FakeClient(topology, stream_response=stream)
    app_b = gateway_module.create_gateway(config, client=fake_b)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_a), base_url="http://127.0.0.1:44180"
        ) as client_a, httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_b), base_url="http://127.0.0.1:44180"
        ) as client_b:
            await _login(client_a)
            await _login(client_b)
            await client_a.get("/api/v2/tasks/task-a/topology")
            allowed = await client_a.get("/api/v2/views/view-a/events")
            foreign_session = await client_b.get("/api/v2/views/view-a/events")
            await client_a.post(
                "/auth/logout", headers={"Origin": "http://127.0.0.1:44180"}
            )
            after_logout = await client_a.get("/api/v2/views/view-a/events")
            return allowed, foreign_session, after_logout

    allowed, foreign_session, after_logout = asyncio.run(run())
    assert allowed.status_code == 200
    assert foreign_session.status_code == 404
    assert after_logout.status_code == 401
    assert fake_a.streams
