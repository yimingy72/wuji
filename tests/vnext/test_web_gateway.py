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


class FakeClient:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.requests: list[tuple[str, dict[str, str]]] = []

    async def get(self, url: str, *, headers: dict[str, str]):
        self.requests.append((url, dict(headers)))
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
    ca = tmp_path / "ca.crt"
    signing.write_bytes(private)
    session.write_bytes(b"s" * 32)
    ca.write_text("unused with injected client")
    return gateway_module.GatewaySettings.model_validate(
        {
            "schema_version": "wuji.web-gateway.v1",
            "api_base_url": "https://api.wuji-vnext-test.svc:8443",
            "ca_file": str(ca),
            "signing_key_file": str(signing),
            "session_key_file": str(session),
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
                "/auth/login", headers={"Origin": "http://127.0.0.1:44180"}
            )
            current = await client.get("/auth/session")
            return anonymous, forbidden, login, current

    anonymous, forbidden, login, current = asyncio.run(run())
    assert anonymous.status_code == 401
    assert forbidden.status_code == 403
    assert login.status_code == 200
    cookie = login.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert "Authorization" not in login.text
    assert current.json() == {
        "authenticated": True,
        "display_name": "Local test operator",
        "tenant_id": "tenant-fixture",
        "project_id": "project-fixture",
        "task_id": "task-fixture",
        "expires_at": current.json()["expires_at"],
    }


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
            await client.post(
                "/auth/login", headers={"Origin": "http://127.0.0.1:44180"}
            )
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
    assert wrong_task.status_code == 404
    assert len(fake.requests) == 1
    url, headers = fake.requests[0]
    assert url.endswith("/api/v2/tasks/task-fixture/topology?mode=live")
    scheme, bearer = headers["Authorization"].split(" ", 1)
    assert scheme == "Bearer"
    claims = jwt.decode(bearer, RSAKey.import_key(public), algorithms=["RS256"]).claims
    assert claims["sub"] == "operator"
    assert claims["tenant_id"] == "tenant-fixture"
    assert claims["roles"] == ["operator"]
    assert 0 < claims["exp"] - claims["iat"] <= 60
