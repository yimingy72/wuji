from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
import sys

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from joserfc import jwt
from joserfc.jwk import RSAKey


ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "vnext_web_gateway", ROOT / "services/wuji-web-gateway/main.py"
)
gateway_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = gateway_module
_spec.loader.exec_module(gateway_module)


class FakeResponse:
    def __init__(self, status_code: int, content: bytes, headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {"content-type": "application/json"}
        self.closed = False

    async def aiter_raw(self):
        yield self.content

    async def aclose(self) -> None:
        self.closed = True


class FakeStreamResponse:
    """The subset of an httpx streaming response the SSE relay consumes."""

    def __init__(self, status_code: int, chunks, headers=None):
        self.status_code = status_code
        self.chunks = list(chunks)
        self.headers = headers or {"content-type": "text/event-stream"}
        self.closed = False

    async def aread(self) -> bytes:
        return b"".join(self.chunks)

    async def aiter_raw(self):
        for chunk in self.chunks:
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


class FakeClient:
    def __init__(self, response: FakeResponse, *, stream_response=None):
        self.response = response
        self.stream_response = stream_response or FakeStreamResponse(
            200, [b"event: view\ndata: {}\n\n"]
        )
        self.requests: list[tuple[str, dict[str, str]]] = []
        self.request_bodies: list[tuple[str, str, dict[str, str], bytes]] = []
        self.streams: list[tuple[str, dict[str, str]]] = []

    async def get(self, url: str, *, headers: dict[str, str]):
        self.requests.append((url, dict(headers)))
        return self.response

    def build_request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        content: bytes | None = None,
    ):
        self.streams.append((url, dict(headers)))
        return (method, url, dict(headers), content)

    async def send(self, request, *, stream: bool = False, timeout=None):
        method, url, headers, content = request
        if "/api/v2/views/" in url and url.endswith("/events"):
            return self.stream_response
        self.requests.append((url, dict(headers)))
        if method != "GET":
            self.request_bodies.append((method, url, dict(headers), content or b""))
        return self.response

    async def request(self, method: str, url: str, *, headers: dict[str, str], content: bytes):
        self.requests.append((url, dict(headers)))
        self.request_bodies.append((method, url, dict(headers), content))
        return self.response


def settings(tmp_path: Path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    signing = tmp_path / "identity.key"
    session = tmp_path / "session.key"
    access = tmp_path / "local-access.token"
    ca = tmp_path / "ca.crt"
    signing.write_bytes(private)
    session.write_bytes(b"s" * 32)
    access.write_bytes(b"b" * 32)
    ca.write_text("unused with injected client")
    return gateway_module.GatewaySettings.model_validate(
        {
            "schema_version": "wuji.web-gateway.v2",
            "mode": "local_single_operator",
            "api_base_url": "https://api.wuji-vnext-test.svc:8443",
            "ca_file": str(ca),
            "signing_key_file": str(signing),
            "session_key_file": str(session),
            "local_access_token_file": str(access),
            "issuer": "https://identity.wuji-vnext-test.invalid",
            "audience": "wuji-vnext-deployment",
            "subject": "operator",
            "tenant_id": "tenant-fixture",
            "project_id": "project-fixture",
            "task_id": "task-fixture",
            "roles": ["operator"],
            "display_name": "Local test operator",
            "allowed_origins": ["http://127.0.0.1:44180"],
            "session_ttl_seconds": 1800,
            "secure_cookie": False,
        }
    ), public


def test_browser_login_uses_an_httponly_same_site_cookie(tmp_path):
    config, _public = settings(tmp_path)
    fake = FakeClient(FakeResponse(200, b"{}"))
    app = gateway_module.create_gateway(config, client=fake)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:44180"
        ) as client:
            anonymous = await client.get("/auth/session")
            forbidden = await client.post(
                "/auth/login", headers={"Origin": "http://not-the-workbench.invalid"}
            )
            login = await client.post(
                "/auth/login",
                headers={
                    "Origin": "http://127.0.0.1:44180",
                    gateway_module.LOCAL_ACCESS_HEADER: "b" * 32,
                },
            )
            current = await client.get("/auth/session")
            logout = await client.post(
                "/auth/logout", headers={"Origin": "http://127.0.0.1:44180"}
            )
            after_logout = await client.get("/auth/session")
            return anonymous, forbidden, login, current, logout, after_logout

    anonymous, forbidden, login, current, logout, after_logout = asyncio.run(run())
    assert anonymous.status_code == 401
    assert forbidden.status_code == 403
    assert login.status_code == 200
    cookie = login.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert "Authorization" not in login.text
    assert current.json() == {
        "authenticated": True,
        "mode": "local_single_operator",
        "subject": "operator",
        "display_name": "Local test operator",
        "tenant_id": "tenant-fixture",
        "project_id": "project-fixture",
        "initial_task_id": "task-fixture",
        "expires_at": current.json()["expires_at"],
    }
    assert logout.status_code == 204
    assert after_logout.status_code == 401


def test_browser_proxy_mints_short_lived_internal_identity(tmp_path):
    config, public = settings(tmp_path)
    body = json.dumps(
        {
            "view_id": "view-1",
            "snapshot_id": "snapshot-1",
            "nodes": [],
            "edges": [],
        }
    ).encode()
    fake = FakeClient(FakeResponse(200, body, {"content-type": "application/json"}))
    app = gateway_module.create_gateway(config, client=fake)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:44180"
        ) as client:
            await _login(client)
            response = await client.get(
                "/api/v2/tasks/task-fixture/topology?mode=live"
            )
            wrong_task = await client.get(
                "/api/v2/tasks/other-task/topology?mode=live"
            )
            return response, wrong_task

    response, wrong_task = asyncio.run(run())
    assert response.status_code == 200
    assert response.content == body
    assert wrong_task.status_code == 200
    assert len(fake.requests) == 2
    url, headers = fake.requests[0]
    assert url.endswith("/api/v2/tasks/task-fixture/topology?mode=live")
    scheme, bearer = headers["Authorization"].split(" ", 1)
    assert scheme == "Bearer"
    claims = jwt.decode(bearer, RSAKey.import_key(public), algorithms=["RS256"]).claims
    assert claims["sub"] == "operator"
    assert claims["tenant_id"] == "tenant-fixture"
    assert claims["roles"] == ["operator"]
    assert 0 < claims["exp"] - claims["iat"] <= 60


def test_browser_proxy_allows_only_bounded_layout_put_and_preserves_conflict(tmp_path):
    config, _public = settings(tmp_path)
    body = json.dumps({
        "schema_version": "wuji.api.v2",
        "selection_mode": "follow_latest",
        "entries": [],
        "viewport": {"x": 0, "y": 0, "zoom": 0.82},
    }).encode()
    error = json.dumps({
        "code": "STALE_VERSION",
        "message": "The request could not be completed.",
        "request_id": "upstream-request",
        "retryable": False,
        "details": {},
    }).encode()
    fake = FakeClient(FakeResponse(409, error, {"content-type": "application/json"}))
    app = gateway_module.create_gateway(config, client=fake)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:44180"
        ) as client:
            await _login(client)
            missing_origin = await client.put(
                "/api/v2/tasks/task-fixture/layouts/knowledge-live",
                headers={"Content-Type": "application/json", "If-Match": "0"},
                content=body,
            )
            conflict = await client.put(
                "/api/v2/tasks/task-fixture/layouts/knowledge-live",
                headers={
                    "Origin": "http://127.0.0.1:44180",
                    "Content-Type": "application/json",
                    "If-Match": "0",
                },
                content=body,
            )
            forbidden = await client.put(
                "/api/v2/tasks/task-fixture/commands",
                headers={
                    "Origin": "http://127.0.0.1:44180",
                    "Content-Type": "application/json",
                    "If-Match": "0",
                },
                content=body,
            )
            return missing_origin, conflict, forbidden

    missing_origin, conflict, forbidden = asyncio.run(run())
    assert missing_origin.status_code == 403
    assert conflict.status_code == 409
    assert conflict.json() == json.loads(error)
    assert forbidden.status_code == 404
    assert len(fake.request_bodies) == 1
    method, url, headers, forwarded = fake.request_bodies[0]
    assert method == "PUT"
    assert url.endswith("/api/v2/tasks/task-fixture/layouts/knowledge-live")
    assert headers["If-Match"] == "0"
    assert forwarded == body


def _login(client):
    return client.post(
        "/auth/login",
        headers={
            "Origin": "http://127.0.0.1:44180",
            gateway_module.LOCAL_ACCESS_HEADER: "b" * 32,
        },
    )


def test_the_view_stream_is_allowed_only_after_its_task_published_it(tmp_path):
    config, _public = settings(tmp_path)
    topology = FakeResponse(
        200,
        json.dumps(
            {
                "view_id": "view-published",
                "snapshot_id": "snapshot-1",
                "view_revision": "1",
            }
        ).encode(),
    )
    fake = FakeClient(topology)
    app = gateway_module.create_gateway(config, client=fake)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:44180"
        ) as client:
            await _login(client)
            before = await client.get("/api/v2/views/view-published/events")
            published = await client.get("/api/v2/tasks/task-fixture/topology?mode=live")
            after = await client.get("/api/v2/views/view-published/events")
            unknown = await client.get("/api/v2/views/view-unknown/events")
            return before, published, after, unknown

    before, published, after, unknown = asyncio.run(run())
    # An id this adapter never published for the pinned Task is not streamable.
    assert before.status_code == 404
    assert published.status_code == 200
    assert after.status_code == 200
    assert unknown.status_code == 404
    assert fake.streams[-1][0] == "https://api.wuji-vnext-test.svc:8443/api/v2/views/view-published/events"


def test_the_view_stream_relays_batches_and_resumes_from_last_event_id(tmp_path):
    config, _public = settings(tmp_path)
    topology = FakeResponse(200, json.dumps({"view_id": "view-1"}).encode())
    stream = FakeStreamResponse(
        200,
        [b"id: cursor-1\n\nevent: view\ndata: {\"view_id\":\"view-1\"}\n\n"],
    )
    fake = FakeClient(topology, stream_response=stream)
    app = gateway_module.create_gateway(config, client=fake)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:44180"
        ) as client:
            await _login(client)
            await client.get("/api/v2/tasks/task-fixture/topology?mode=live")
            response = await client.get(
                "/api/v2/views/view-1/events",
                headers={"Last-Event-ID": "cursor-1", "Accept": "text/event-stream"},
            )
            return response

    response = asyncio.run(run())
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-accel-buffering"] == "no"
    assert "event: view" in response.text
    url, headers = fake.streams[-1]
    assert url.endswith("/api/v2/views/view-1/events")
    assert headers["Last-Event-ID"] == "cursor-1"
    assert headers["Accept"] == "text/event-stream"


def test_browser_proxy_records_a_delivery_only_for_its_own_task(tmp_path):
    config, _public = settings(tmp_path)
    body = json.dumps({
        "profile": {
            "schema_version": "wuji.delivery-profile.v1",
            "profile_id": "offline-document-v1",
            "mode": "offline",
            "requirements": [
                {
                    "role": "report_body",
                    "media_type": "application/vnd.wuji.report+json",
                    "min_count": 1,
                    "required": True,
                }
            ],
        }
    }).encode()
    fake = FakeClient(FakeResponse(200, b"{}"))
    app = gateway_module.create_gateway(config, client=fake)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:44180"
        ) as client:
            await _login(client)
            origin = {"Origin": "http://127.0.0.1:44180"}
            foreign = await client.post(
                "/api/v2/tasks/task-other/reports/report-1/deliveries",
                headers={**origin, "Content-Type": "application/json",
                         "Idempotency-Key": "delivery-key-1"},
                content=body,
            )
            missing_key = await client.post(
                "/api/v2/tasks/task-fixture/reports/report-1/deliveries",
                headers={**origin, "Content-Type": "application/json"},
                content=body,
            )
            accepted = await client.post(
                "/api/v2/tasks/task-fixture/reports/report-1/deliveries",
                headers={**origin, "Content-Type": "application/json",
                         "Idempotency-Key": "delivery-key-1"},
                content=body,
            )
            read = await client.get(
                "/api/v2/tasks/task-fixture/reports/report-1/deliveries",
                headers=origin,
            )
            read_one = await client.get(
                "/api/v2/tasks/task-fixture/reports/report-1/deliveries/delivery-1",
                headers=origin,
            )
            foreign_read = await client.get(
                "/api/v2/tasks/task-other/reports/report-1/deliveries",
                headers=origin,
            )
            return foreign, missing_key, accepted, read, read_one, foreign_read

    foreign, missing_key, accepted, read, read_one, foreign_read = asyncio.run(run())
    assert foreign.status_code == 200
    assert missing_key.status_code == 422
    assert accepted.status_code == 200
    assert read.status_code == 200
    assert read_one.status_code == 200
    assert foreign_read.status_code == 200
    assert len(fake.request_bodies) == 2
    method, url, headers, forwarded = fake.request_bodies[0]
    assert method == "POST"
    assert url.endswith("/api/v2/tasks/task-other/reports/report-1/deliveries")
    assert headers["Idempotency-Key"] == "delivery-key-1"
    assert forwarded == body
    assert fake.request_bodies[1][1].endswith(
        "/api/v2/tasks/task-fixture/reports/report-1/deliveries"
    )
