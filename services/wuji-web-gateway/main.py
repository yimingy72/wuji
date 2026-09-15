"""Same-origin browser session adapter for the local vNext workbench."""

from __future__ import annotations

import argparse
import base64
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import ssl
import time
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from joserfc import jwt
from joserfc.jwk import RSAKey
from pydantic import BaseModel, ConfigDict, Field, model_validator

from wuji_core.http import canonical_json_bytes, strict_json_loads


COOKIE_NAME = "wuji_vnext_session"
NO_STORE = {"Cache-Control": "no-store"}
_READ_PATH = re.compile(
    r"^/api/v2/tasks/([^/]+)/(?:topology|snapshots|records/[^/]+/[^/]+)$"
)


class GatewaySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["wuji.web-gateway.v1"]
    api_base_url: str
    ca_file: str
    signing_key_file: str
    session_key_file: str
    issuer: str
    audience: str
    subject: str
    tenant_id: str
    project_id: str
    task_id: str
    roles: list[str] = Field(min_length=1, max_length=16)
    display_name: str = Field(min_length=1, max_length=128)
    allowed_origins: list[str] = Field(min_length=1, max_length=8)
    session_ttl_seconds: int = Field(default=1800, ge=300, le=7200)
    max_response_bytes: int = Field(default=2_097_152, ge=1024, le=8_388_608)
    secure_cookie: bool = False

    @model_validator(mode="after")
    def validate_boundary(self):
        api = urlsplit(self.api_base_url)
        if api.scheme != "https" or not api.hostname or api.path not in {"", "/"}:
            raise ValueError("gateway API origin must be an HTTPS origin")
        for path in (self.ca_file, self.signing_key_file, self.session_key_file):
            if not Path(path).is_absolute():
                raise ValueError("gateway file paths must be absolute")
        if len(set(self.roles)) != len(self.roles) or any(not role for role in self.roles):
            raise ValueError("gateway roles must be unique nonempty strings")
        origins = []
        for value in self.allowed_origins:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
            ):
                raise ValueError("allowed browser origins must be exact origins")
            origins.append(value.rstrip("/"))
        self.api_base_url = self.api_base_url.rstrip("/")
        self.allowed_origins = list(dict.fromkeys(origins))
        return self


def _read(path: str, maximum: int) -> bytes:
    with Path(path).open("rb") as stream:
        value = stream.read(maximum + 1)
    if not value or len(value) > maximum:
        raise ValueError("gateway secret/config file is empty or exceeds its bound")
    return value


def load_settings(path: str | None = None) -> GatewaySettings:
    source = path or os.environ.get(
        "WUJI_WEB_GATEWAY_CONFIG", "/config/web-gateway.json"
    )
    return GatewaySettings.model_validate(strict_json_loads(_read(source, 65_536)))


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    if not value or len(value) > 4096:
        raise ValueError("invalid session component")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class SessionCodec:
    def __init__(self, key: bytes, *, ttl_seconds: int) -> None:
        if len(key) < 32:
            raise ValueError("browser session key must be at least 32 bytes")
        self._key = key
        self._ttl_seconds = ttl_seconds

    def issue(self) -> tuple[str, dict[str, object]]:
        now = int(time.time())
        payload = {
            "sid": secrets.token_urlsafe(24),
            "iat": now,
            "exp": now + self._ttl_seconds,
        }
        body = canonical_json_bytes(payload)
        signature = hmac.digest(self._key, body, hashlib.sha256)
        return f"{_b64encode(body)}.{_b64encode(signature)}", payload

    def verify(self, token: str | None) -> dict[str, object] | None:
        if token is None or token.count(".") != 1:
            return None
        encoded, signed = token.split(".", 1)
        try:
            body = _b64decode(encoded)
            signature = _b64decode(signed)
            if not hmac.compare_digest(
                signature, hmac.digest(self._key, body, hashlib.sha256)
            ):
                return None
            payload = strict_json_loads(body)
        except (ValueError, TypeError):
            return None
        if not isinstance(payload, dict) or set(payload) != {"sid", "iat", "exp"}:
            return None
        if (
            not isinstance(payload["sid"], str)
            or not payload["sid"]
            or type(payload["iat"]) is not int
            or type(payload["exp"]) is not int
            or payload["iat"] > int(time.time()) + 5
            or payload["exp"] <= int(time.time())
            or payload["exp"] - payload["iat"] != self._ttl_seconds
        ):
            return None
        return payload


class BrowserGateway:
    def __init__(self, settings: GatewaySettings, *, client=None) -> None:
        self.settings = settings
        self.sessions = SessionCodec(
            _read(settings.session_key_file, 4096),
            ttl_seconds=settings.session_ttl_seconds,
        )
        self._signing_key = RSAKey.import_key(
            _read(settings.signing_key_file, 65_536)
        )
        self._owned_client = client is None
        self.client = client or httpx.AsyncClient(
            verify=ssl.create_default_context(cafile=settings.ca_file),
            timeout=httpx.Timeout(10.0),
            trust_env=False,
            follow_redirects=False,
        )

    async def close(self) -> None:
        if self._owned_client:
            await self.client.aclose()

    def session(self, request: Request) -> dict[str, object] | None:
        return self.sessions.verify(request.cookies.get(COOKIE_NAME))

    def require_origin(self, request: Request) -> None:
        origin = request.headers.get("origin", "").rstrip("/")
        if origin not in self.settings.allowed_origins:
            raise PermissionError("browser origin is not allowed")

    def public_session(self, payload: dict[str, object]) -> dict[str, object]:
        expires = datetime.fromtimestamp(int(payload["exp"]), timezone.utc)
        return {
            "authenticated": True,
            "display_name": self.settings.display_name,
            "tenant_id": self.settings.tenant_id,
            "project_id": self.settings.project_id,
            "task_id": self.settings.task_id,
            "expires_at": expires.isoformat().replace("+00:00", "Z"),
        }

    def internal_bearer(self, payload: dict[str, object]) -> str:
        now = int(time.time())
        claims = {
            "iss": self.settings.issuer,
            "aud": self.settings.audience,
            "sub": self.settings.subject,
            "tenant_id": self.settings.tenant_id,
            "roles": self.settings.roles,
            "iat": now,
            "nbf": now - 1,
            "exp": now + 60,
            "jti": str(uuid4()),
        }
        return jwt.encode(
            {"alg": "RS256", "kid": "web-session-adapter"},
            claims,
            self._signing_key,
            algorithms=["RS256"],
        )

    def allowed_read(self, path: str) -> bool:
        matched = _READ_PATH.fullmatch(path)
        return matched is not None and matched.group(1) == self.settings.task_id


def _problem(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        headers=NO_STORE,
        content={
            "code": code,
            "message": message,
            "request_id": str(uuid4()),
            "retryable": status >= 500,
            "details": {},
        },
    )


def create_gateway(settings: GatewaySettings, *, client=None) -> FastAPI:
    gateway = BrowserGateway(settings, client=client)

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        try:
            yield
        finally:
            await gateway.close()

    app = FastAPI(
        title="Wuji local browser session adapter",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.gateway = gateway

    @app.get("/healthz")
    async def health() -> Response:
        return Response("ok\n", media_type="text/plain")

    @app.get("/auth/session")
    async def session(request: Request) -> Response:
        payload = gateway.session(request)
        if payload is None:
            return _problem(401, "UNAUTHENTICATED", "Browser session is not active.")
        return JSONResponse(gateway.public_session(payload), headers=NO_STORE)

    @app.post("/auth/login")
    async def login(request: Request) -> Response:
        try:
            gateway.require_origin(request)
        except PermissionError:
            return _problem(403, "FORBIDDEN", "Browser origin is not allowed.")
        token, payload = gateway.sessions.issue()
        response = JSONResponse(gateway.public_session(payload), headers=NO_STORE)
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=settings.session_ttl_seconds,
            path="/",
            httponly=True,
            secure=settings.secure_cookie,
            samesite="strict",
        )
        return response

    @app.post("/auth/logout")
    async def logout(request: Request) -> Response:
        try:
            gateway.require_origin(request)
        except PermissionError:
            return _problem(403, "FORBIDDEN", "Browser origin is not allowed.")
        response = Response(status_code=204, headers=NO_STORE)
        response.delete_cookie(
            COOKIE_NAME,
            path="/",
            httponly=True,
            secure=settings.secure_cookie,
            samesite="strict",
        )
        return response

    @app.get("/api/v2/{rest:path}")
    async def proxy_read(request: Request, rest: str) -> Response:
        payload = gateway.session(request)
        if payload is None:
            return _problem(401, "UNAUTHENTICATED", "Browser session is not active.")
        path = "/api/v2/" + rest
        if not gateway.allowed_read(path):
            return _problem(404, "NOT_FOUND_OR_FORBIDDEN", "Resource is unavailable.")
        if len(request.url.query) > 8192:
            return _problem(422, "INVALID_SCHEMA", "Query exceeds its bound.")
        url = gateway.settings.api_base_url + path
        if request.url.query:
            url += "?" + request.url.query
        try:
            upstream = await gateway.client.get(
                url,
                headers={
                    "Authorization": "Bearer " + gateway.internal_bearer(payload),
                    "Accept": "application/json",
                },
            )
        except (httpx.HTTPError, OSError, TimeoutError):
            return _problem(503, "CAPABILITY_UNAVAILABLE", "Topology service is unavailable.")
        content = upstream.content
        if len(content) > gateway.settings.max_response_bytes:
            return _problem(503, "CAPABILITY_UNAVAILABLE", "Topology response exceeds its bound.")
        if upstream.status_code in {401, 403}:
            return _problem(503, "CAPABILITY_UNAVAILABLE", "Browser identity could not be mapped.")
        headers = {"Cache-Control": "no-store"}
        for name in ("content-type", "x-request-id"):
            value = upstream.headers.get(name)
            if value:
                headers[name] = value
        return Response(content, status_code=upstream.status_code, headers=headers)

    return app


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    uvicorn.run(
        create_gateway(load_settings(args.config)),
        host=args.host,
        port=args.port,
        access_log=False,
    )


if __name__ == "__main__":
    main()
