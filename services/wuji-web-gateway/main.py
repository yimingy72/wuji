"""Bounded same-origin browser gateway for the local vNext workbench.

The gateway has two deliberately narrow local authentication modes.
``local_single_operator`` preserves the original deployment access-code flow;
``local_password`` verifies one fixed development operator from a private scrypt
credential file and persists independently revocable browser sessions in SQLite.
The browser never chooses the upstream subject, tenant, project, role, task, or bearer token.
The upstream API remains the authority for Task/RLS authorization; this
process only constrains the public entry point and the forwarded contract.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import sqlite3
import ssl
import time
from typing import Literal
from urllib.parse import parse_qsl, urlsplit
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from joserfc import jwt
from joserfc.jwk import RSAKey
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from wuji_core.contracts.generated import (
    InputAnswerCommandV1,
    LayoutPatch,
    ReportDeliveryCommand,
    TaskCommand,
    TaskCompletionCommand,
    TaskCreate,
)
from wuji_core.http import canonical_json_bytes, strict_json_loads


COOKIE_NAME = "wuji_vnext_session"
LOCAL_ACCESS_HEADER = "x-wuji-local-access"
NO_STORE = {"Cache-Control": "no-store"}
PASSWORD_SCHEMA = "wuji.local-password.v1"
PASSWORD_SCRYPT_N = 1 << 14
PASSWORD_SCRYPT_R = 8
PASSWORD_SCRYPT_P = 1
PASSWORD_SCRYPT_DKLEN = 32
_USERNAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@-]{0,127}$")
_IDENTIFIER = r"[A-Za-z0-9][A-Za-z0-9._:-]{0,255}"
_TASK_ID = _IDENTIFIER
_PROJECT_ID = _IDENTIFIER
_REPORT_ID = _IDENTIFIER
_DELIVERY_ID = _IDENTIFIER
_ARTIFACT_ID = _IDENTIFIER
_VIEW_ID = _IDENTIFIER
_RECORD_TYPE = _IDENTIFIER
_RECORD_ID = _IDENTIFIER
_CAPTURE_ID = _IDENTIFIER
_CAPTURE_PART = r"[a-z][a-z0-9_.-]{0,127}"
_MAX_DOWNLOAD_BYTES = 67_108_864


def _local_http_origin(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme == "http" and parsed.hostname in {
        "localhost", "127.0.0.1", "::1"
    }

_GET_ROUTES = (
    ("task_list", re.compile(r"^/api/v2/tasks$")),
    (
        "task_options",
        re.compile(rf"^/api/v2/projects/(?P<project_id>{_PROJECT_ID})/task-options$"),
    ),
    ("task_get", re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})$")),
    ("task_overview", re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/overview$")),
    ("command_inventory", re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/command-inventory$")),
    ("publications", re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/publications$")),
    ("capture_sessions", re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/capture-sessions$")),
    ("capture_items", re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/capture-sessions/(?P<capture_session_id>{_CAPTURE_ID})/items$")),
    ("capture_part", re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/capture-sessions/(?P<capture_session_id>{_CAPTURE_ID})/items/(?P<item_seq>[1-9][0-9]*)/parts/(?P<part>{_CAPTURE_PART})$")),
    ("task_activity", re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/activity$")),
    (
        "task_readiness",
        re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/readiness$"),
    ),
    ("task_launch", re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/launch$")),
    ("topology", re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/topology$")),
    ("exploration", re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/exploration$")),
    ("task_inputs", re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/inputs$")),
    ("snapshots", re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/snapshots$")),
    (
        "completion_get",
        re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/completion$"),
    ),
    (
        "report_get",
        re.compile(
            rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/reports/(?P<report_id>{_REPORT_ID})$"
        ),
    ),
    (
        "delivery_list",
        re.compile(
            rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/reports/(?P<report_id>{_REPORT_ID})/deliveries$"
        ),
    ),
    (
        "delivery_get",
        re.compile(
            rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/reports/(?P<report_id>{_REPORT_ID})/deliveries/(?P<delivery_id>{_DELIVERY_ID})$"
        ),
    ),
    (
        "record_get",
        re.compile(
            rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/records/(?P<record_type>{_RECORD_TYPE})/(?P<record_id>{_RECORD_ID})$"
        ),
    ),
    (
        "layout_get",
        re.compile(
            rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/layouts/(?P<view_name>knowledge-live|knowledge-history)$"
        ),
    ),
    (
        "task_material",
        re.compile(
            rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/artifacts/(?P<artifact_id>{_ARTIFACT_ID})/material$"
        ),
    ),
    (
        "artifact_content",
        re.compile(rf"^/api/v2/artifacts/(?P<artifact_id>{_ARTIFACT_ID})/content$"),
    ),
)

_POST_ROUTES = (
    ("task_create", re.compile(r"^/api/v2/tasks$")),
    (
        "task_command",
        re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/commands$"),
    ),
    (
        "completion_post",
        re.compile(rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/completion$"),
    ),
    (
        "delivery_post",
        re.compile(
            rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/reports/(?P<report_id>{_REPORT_ID})/deliveries$"
        ),
    ),
    (
        "input_answer",
        re.compile(rf"^/api/v2/inputs/(?P<input_request_id>{_IDENTIFIER})/answers$"),
    ),
)

_PUT_ROUTES = (
    (
        "layout_put",
        re.compile(
            rf"^/api/v2/tasks/(?P<task_id>{_TASK_ID})/layouts/(?P<view_name>knowledge-live|knowledge-history)$"
        ),
    ),
)
_STREAM_PATH = re.compile(rf"^/api/v2/views/(?P<view_id>{_VIEW_ID})/events$")
_IF_MATCH = re.compile(r"^(0|[1-9][0-9]*)$")
_IDEMPOTENCY_KEY = re.compile(r"^[\x21-\x7e]{1,256}$")
_SAFE_ERROR_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_MAX_QUERY_BYTES = 8192
_MAX_HEADER_BYTES = 4096
_STREAM_LIFETIME_SECONDS = 300.0


class GatewaySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["wuji.web-gateway.v2"]
    mode: Literal["local_single_operator", "local_password"]
    api_base_url: str
    ca_file: str
    signing_key_file: str
    session_key_file: str
    local_access_token_file: str | None = None
    password_credential_file: str | None = None
    session_db_file: str | None = None
    issuer: str
    audience: str
    subject: str
    tenant_id: str
    project_id: str
    # Legacy selected-task configuration is retained only as an initial UI
    # selection hint. It is never used as a Task authorization grant.
    task_id: str | None = None
    roles: list[str] = Field(min_length=1, max_length=16)
    display_name: str = Field(min_length=1, max_length=128)
    allowed_origins: list[str] = Field(min_length=1, max_length=8)
    session_ttl_seconds: int = Field(default=1800, ge=300, le=86400)
    max_request_bytes: int = Field(default=1_048_576, ge=32_768, le=8_388_608)
    # JSON responses remain bounded separately from dedicated file downloads.
    max_response_bytes: int = Field(default=2_097_152, ge=32_768, le=8_388_608)
    max_stream_bytes: int = Field(default=4_194_304, ge=32_768, le=16_777_216)
    secure_cookie: bool = False

    @model_validator(mode="after")
    def validate_boundary(self):
        api = urlsplit(self.api_base_url)
        if api.scheme != "https" or not api.hostname or api.path not in {"", "/"}:
            raise ValueError("gateway API origin must be an HTTPS origin")
        if self.mode == "local_single_operator":
            if self.local_access_token_file is None:
                raise ValueError("local access credential is required")
            mode_paths = (self.local_access_token_file,)
        else:
            if self.password_credential_file is None or self.session_db_file is None:
                raise ValueError("password credential and session database are required")
            mode_paths = (self.password_credential_file, self.session_db_file)
        for path in (self.ca_file, self.signing_key_file, self.session_key_file, *mode_paths):
            if not Path(path).is_absolute():
                raise ValueError("gateway file paths must be absolute")
        if len(set(self.roles)) != len(self.roles) or any(
            not role or any(ord(char) < 0x21 or ord(char) > 0x7E for char in role)
            for role in self.roles
        ):
            raise ValueError("gateway roles must be unique printable strings")
        if not self.subject or not self.tenant_id or not self.project_id:
            raise ValueError("gateway identity fields must be nonempty")
        if self.task_id is not None and not re.fullmatch(_TASK_ID, self.task_id):
            raise ValueError("legacy task_id is not a safe identifier")
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
        if self.mode == "local_password":
            local_http = all(_local_http_origin(origin) for origin in self.allowed_origins)
            https = all(origin.startswith("https://") for origin in self.allowed_origins)
            if not ((local_http and not self.secure_cookie) or (https and self.secure_cookie)):
                raise ValueError(
                    "local password mode requires HTTPS or an explicit loopback HTTP origin"
                )
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
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (binascii.Error, ValueError) as error:
        raise ValueError("invalid session component") from error


class SessionCodec:
    """Signed, active-session registry with explicit revocation."""

    def __init__(self, key: bytes, *, ttl_seconds: int, database_file: str | None = None) -> None:
        if len(key) < 32:
            raise ValueError("browser session key must be at least 32 bytes")
        self._key = key
        self._ttl_seconds = ttl_seconds
        self._active: dict[str, dict[str, object]] = {}
        self._database_file = database_file
        if database_file is not None:
            path = Path(database_file)
            if not path.parent.is_dir():
                raise ValueError("browser session database parent is unavailable")
            with self._database() as connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS browser_session("
                    "sid TEXT PRIMARY KEY,iat INTEGER NOT NULL,exp INTEGER NOT NULL)"
                )
            os.chmod(path, 0o600)

    @contextmanager
    def _database(self):
        if self._database_file is None:
            raise RuntimeError("persistent browser sessions are not configured")
        connection = sqlite3.connect(self._database_file, timeout=5.0)
        try:
            connection.execute("PRAGMA busy_timeout=5000")
            with connection:
                yield connection
        finally:
            connection.close()

    def _store(self, payload: dict[str, object]) -> None:
        if self._database_file is None:
            self._active[str(payload["sid"])] = payload
            return
        with self._database() as connection:
            connection.execute("DELETE FROM browser_session WHERE exp<=?", (int(time.time()),))
            connection.execute(
                "INSERT INTO browser_session(sid,iat,exp) VALUES(?,?,?)",
                (str(payload["sid"]), int(payload["iat"]), int(payload["exp"])),
            )

    def _stored(self, payload: dict[str, object]) -> bool:
        if self._database_file is None:
            return self._active.get(str(payload["sid"])) == payload
        with self._database() as connection:
            found = connection.execute(
                "SELECT iat,exp FROM browser_session WHERE sid=?",
                (str(payload["sid"]),),
            ).fetchone()
        return found == (int(payload["iat"]), int(payload["exp"]))

    def issue(self) -> tuple[str, dict[str, object]]:
        now = int(time.time())
        payload = {
            "sid": secrets.token_urlsafe(24),
            "iat": now,
            "exp": now + self._ttl_seconds,
        }
        body = canonical_json_bytes(payload)
        signature = hmac.digest(self._key, body, hashlib.sha256)
        self._store(payload)
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
            self.revoke(payload)
            return None
        if not self._stored(payload):
            return None
        return payload

    def revoke(self, payload: dict[str, object]) -> None:
        sid = payload.get("sid")
        if isinstance(sid, str):
            if self._database_file is None:
                self._active.pop(sid, None)
            else:
                with self._database() as connection:
                    connection.execute("DELETE FROM browser_session WHERE sid=?", (sid,))

    def revoke_all(self) -> list[dict[str, object]]:
        """Rotate the single local-operator session and return old bindings."""
        if self._database_file is None:
            previous = list(self._active.values())
            self._active.clear()
            return previous
        with self._database() as connection:
            previous = [
                {"sid": row[0], "iat": row[1], "exp": row[2]}
                for row in connection.execute("SELECT sid,iat,exp FROM browser_session")
            ]
            connection.execute("DELETE FROM browser_session")
        return previous


class DeploymentAccessCredential:
    """Reusable deployment-local access secret, never forwarded upstream."""

    def __init__(self, path: str) -> None:
        token = _read(path, _MAX_HEADER_BYTES).strip()
        if not 32 <= len(token) <= _MAX_HEADER_BYTES:
            raise ValueError("local access credential must be 32..4096 bytes")
        self._token = token

    def matches(self, candidate: str | None) -> bool:
        if candidate is None:
            return False
        raw = candidate.encode("utf-8", errors="strict")
        return hmac.compare_digest(raw, self._token)


class PasswordLogin(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


class PasswordCredential:
    """One fixed local operator credential with a bounded scrypt verifier."""

    def __init__(self, path: str) -> None:
        document = strict_json_loads(_read(path, 16_384))
        if not isinstance(document, dict) or set(document) != {
            "schema_version", "username", "salt", "digest"
        } or document.get("schema_version") != PASSWORD_SCHEMA:
            raise ValueError("local password credential has an invalid shape")
        username = document.get("username")
        if not isinstance(username, str) or _USERNAME.fullmatch(username) is None:
            raise ValueError("local password username is invalid")
        try:
            salt = _b64decode(document["salt"])
            digest = _b64decode(document["digest"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("local password credential encoding is invalid") from error
        if len(salt) != 16 or len(digest) != PASSWORD_SCRYPT_DKLEN:
            raise ValueError("local password credential size is invalid")
        self._username = username.encode("utf-8")
        self._salt = salt
        self._digest = digest

    def matches(self, username: str, password: str) -> bool:
        try:
            username_bytes = username.encode("utf-8")
            password_bytes = password.encode("utf-8")
        except UnicodeEncodeError:
            return False
        if not 1 <= len(password_bytes) <= 4096:
            return False
        candidate = hashlib.scrypt(
            password_bytes,
            salt=self._salt,
            n=PASSWORD_SCRYPT_N,
            r=PASSWORD_SCRYPT_R,
            p=PASSWORD_SCRYPT_P,
            dklen=PASSWORD_SCRYPT_DKLEN,
        )
        username_matches = hmac.compare_digest(username_bytes, self._username)
        password_matches = hmac.compare_digest(candidate, self._digest)
        return username_matches and password_matches


class ViewLedger:
    """Bounded bindings of (session, subject, project, task, view)."""

    def __init__(self, *, maximum: int = 128, ttl_seconds: int = 3600) -> None:
        if not 1 <= maximum <= 2048 or not 60 <= ttl_seconds <= 86400:
            raise ValueError("view ledger bounds are invalid")
        self._maximum, self._ttl_seconds = maximum, ttl_seconds
        self._entries: dict[tuple[str, str, str, str, str, str], float] = {}

    @staticmethod
    def _key(payload: dict[str, object], task_id: str, view_id: str):
        return (
            str(payload["sid"]),
            str(payload["subject"]),
            str(payload["tenant_id"]),
            str(payload["project_id"]),
            task_id,
            view_id,
        )

    def _prune(self) -> None:
        now = time.monotonic()
        self._entries = {
            key: expiry for key, expiry in self._entries.items() if expiry > now
        }

    def remember(self, payload: dict[str, object], task_id: str, view_id: str) -> None:
        self._prune()
        self._entries[self._key(payload, task_id, view_id)] = (
            time.monotonic() + self._ttl_seconds
        )
        while len(self._entries) > self._maximum:
            oldest = min(self._entries, key=self._entries.__getitem__)
            self._entries.pop(oldest, None)

    def allowed(self, payload: dict[str, object], view_id: str) -> bool:
        self._prune()
        sid = str(payload["sid"])
        return any(key[0] == sid and key[-1] == view_id for key in self._entries)

    def forget_session(self, payload: dict[str, object]) -> None:
        sid = str(payload["sid"])
        self._entries = {
            key: value for key, value in self._entries.items() if key[0] != sid
        }


def _problem(
    status: int,
    code: str,
    message: str,
    *,
    request_id: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        headers=NO_STORE,
        content={
            "code": code,
            "message": message,
            "request_id": request_id or str(uuid4()),
            "retryable": status >= 500,
            "details": {},
        },
    )


def _request_id(request: Request) -> str:
    state_id = getattr(request.state, "gateway_request_id", None)
    if isinstance(state_id, str):
        return state_id
    value = str(uuid4())
    request.state.gateway_request_id = value
    return value


def _header_values(request: Request, name: str) -> list[str]:
    wanted = name.lower().encode("ascii")
    return [
        value.decode("latin-1")
        for header, value in request.scope.get("headers", [])
        if header.lower() == wanted
    ]


def _one_header(request: Request, name: str, *, maximum: int = _MAX_HEADER_BYTES):
    values = _header_values(request, name)
    if len(values) != 1 or not 0 <= len(values[0]) <= maximum:
        return None, False
    return values[0], True


def _raw_path_is_safe(request: Request) -> bool:
    raw = request.scope.get("raw_path", b"")
    if not isinstance(raw, bytes):
        return False
    try:
        path = raw.decode("ascii")
    except UnicodeDecodeError:
        return False
    lowered = path.lower()
    return not (
        "%" in path
        or "\\" in path
        or "\x00" in path
        or "//" in path
        or "/./" in path
        or "/../" in path
        or lowered.endswith("/.")
        or lowered.endswith("/..")
    )


def _query(request: Request, allowed: set[str], required: set[str] = frozenset()):
    raw = request.scope.get("query_string", b"")
    if not isinstance(raw, bytes) or len(raw) > _MAX_QUERY_BYTES:
        return None
    if b"%25" in raw.lower():
        return None
    if not raw:
        pairs: list[tuple[str, str]] = []
    else:
        try:
            pairs = parse_qsl(
                raw.decode("ascii"),
                keep_blank_values=True,
                strict_parsing=True,
                max_num_fields=32,
            )
        except (UnicodeDecodeError, ValueError):
            return None
    values: dict[str, str] = {}
    for key, value in pairs:
        if key not in allowed or key in values or not key:
            return None
        if len(value) > _MAX_HEADER_BYTES or any(ord(char) < 0x20 for char in value):
            return None
        if "%25" in value.lower():
            return None
        values[key] = value
    if not required.issubset(values):
        return None
    return values


def _url(settings: GatewaySettings, path: str, request: Request) -> str:
    raw_query = request.scope.get("query_string", b"")
    query = raw_query.decode("ascii") if raw_query else ""
    return settings.api_base_url + path + (("?" + query) if query else "")


async def _bounded_request_body(request: Request, maximum: int) -> tuple[bytes | None, bool]:
    content_lengths = _header_values(request, "content-length")
    if len(content_lengths) > 1:
        return None, False
    content_length = content_lengths[0] if content_lengths else None
    if content_length is not None and (
        not content_length or not content_length.isdigit() or int(content_length) > maximum
    ):
        return None, False
    body = bytearray()
    try:
        async for chunk in request.stream():
            if not isinstance(chunk, bytes) or len(body) + len(chunk) > maximum:
                return None, False
            body.extend(chunk)
    except (asyncio.CancelledError, RuntimeError):
        return None, False
    return bytes(body), True


async def _bounded_response_body(response, maximum: int) -> bytes | None:
    body = bytearray()
    iterator = getattr(response, "aiter_bytes", None) or getattr(
        response, "aiter_raw", None
    )
    try:
        if iterator is None:
            content = getattr(response, "content", b"")
            if not isinstance(content, bytes) or len(content) > maximum:
                return None
            return content
        async for chunk in iterator():
            if not isinstance(chunk, bytes) or len(body) + len(chunk) > maximum:
                return None
            body.extend(chunk)
        return bytes(body)
    finally:
        close = getattr(response, "aclose", None)
        if close is not None:
            await close()


def _json_content_type(headers) -> bool:
    value = headers.get("content-type", "").split(";", 1)[0].strip().lower()
    return value == "application/json" or value.endswith("+json")


def _sanitized_upstream_error(status: int, content: bytes, *, request_id: str):
    code = (
        "CAPABILITY_UNAVAILABLE"
        if status >= 500 or status == 401
        else "NOT_FOUND_OR_FORBIDDEN"
    )
    upstream_request_id = None
    if content:
        try:
            document = strict_json_loads(content)
        except (TypeError, ValueError):
            document = None
        if isinstance(document, dict):
            candidate = document.get("code")
            if isinstance(candidate, str) and _SAFE_ERROR_CODE.fullmatch(candidate):
                code = candidate
            candidate_id = document.get("request_id")
            if isinstance(candidate_id, str) and 1 <= len(candidate_id) <= 256 and all(
                ord(char) >= 0x20 for char in candidate_id
            ):
                upstream_request_id = candidate_id
    if status >= 500 or status == 401:
        status = 503
    return _problem(
        status,
        code,
        "The request could not be completed.",
        request_id=upstream_request_id or request_id,
    )


def _upstream_response(
    status: int,
    headers,
    content: bytes,
    *,
    request_id: str,
    expect_json: bool,
    download: bool = False,
) -> Response:
    if status >= 400:
        return _sanitized_upstream_error(status, content, request_id=request_id)
    if expect_json and content:
        try:
            strict_json_loads(content)
        except (TypeError, ValueError):
            return _problem(
                503,
                "CAPABILITY_UNAVAILABLE",
                "Upstream JSON is invalid.",
                request_id=request_id,
            )
    output_headers = dict(NO_STORE)
    content_type = headers.get("content-type")
    if content_type:
        output_headers["Content-Type"] = content_type
    for name in ("digest", "x-content-type-options"):
        value = headers.get(name)
        if value and len(value) <= _MAX_HEADER_BYTES and "\r" not in value and "\n" not in value:
            output_headers[name.title()] = value
    if download:
        output_headers["Content-Disposition"] = 'attachment; filename="artifact"'
        output_headers["Content-Security-Policy"] = "default-src 'none'"
    return Response(content, status_code=status, headers=output_headers)


class BrowserGateway:
    def __init__(self, settings: GatewaySettings, *, client=None) -> None:
        self.settings = settings
        self.sessions = SessionCodec(
            _read(settings.session_key_file, 4096),
            ttl_seconds=settings.session_ttl_seconds,
            database_file=(
                settings.session_db_file if settings.mode == "local_password" else None
            ),
        )
        self.local_access = (
            DeploymentAccessCredential(settings.local_access_token_file)
            if settings.mode == "local_single_operator" and settings.local_access_token_file
            else None
        )
        self.password = (
            PasswordCredential(settings.password_credential_file)
            if settings.mode == "local_password" and settings.password_credential_file
            else None
        )
        self._signing_key = RSAKey.import_key(_read(settings.signing_key_file, 65_536))
        self._owned_client = client is None
        self.views = ViewLedger()
        self.client = client or httpx.AsyncClient(
            verify=ssl.create_default_context(cafile=settings.ca_file),
            timeout=httpx.Timeout(10.0),
            trust_env=False,
            follow_redirects=False,
        )
        self.stream_client = None if client is not None else httpx.AsyncClient(
            verify=ssl.create_default_context(cafile=settings.ca_file),
            timeout=httpx.Timeout(connect=10.0, read=45.0, write=10.0, pool=10.0),
            trust_env=False,
            follow_redirects=False,
        )

    async def close(self) -> None:
        if self._owned_client:
            await self.client.aclose()
            if self.stream_client is not None:
                await self.stream_client.aclose()

    def session(self, request: Request) -> dict[str, object] | None:
        values = _header_values(request, "cookie")
        if len(values) != 1:
            return None
        token = None
        for item in values[0].split(";"):
            name, separator, value = item.strip().partition("=")
            if separator and name == COOKIE_NAME:
                token = value
                break
        payload = self.sessions.verify(token)
        if payload is None:
            return None
        # The signed cookie only carries an opaque session id and timestamps.
        # These trusted identity fields are server-side settings, never browser
        # claims, and are added solely for the per-session ViewLedger key.
        return {
            **payload,
            "subject": self.settings.subject,
            "tenant_id": self.settings.tenant_id,
            "project_id": self.settings.project_id,
        }

    def allowed_hosts(self) -> set[str]:
        return {urlsplit(origin).netloc.lower() for origin in self.settings.allowed_origins}

    def request_boundary_ok(self, request: Request) -> bool:
        if not _raw_path_is_safe(request):
            return False
        host, present = _one_header(request, "host", maximum=256)
        return present and host.lower() in self.allowed_hosts()

    def require_origin(self, request: Request) -> None:
        values = _header_values(request, "origin")
        if len(values) != 1 or values[0].rstrip("/") not in self.settings.allowed_origins:
            raise PermissionError("browser origin is not allowed")

    def reject_browser_bearer(self, request: Request) -> bool:
        return bool(_header_values(request, "authorization"))

    def public_session(self, payload: dict[str, object]) -> dict[str, object]:
        expires = datetime.fromtimestamp(int(payload["exp"]), timezone.utc)
        return {
            "authenticated": True,
            "mode": self.settings.mode,
            "subject": self.settings.subject,
            "display_name": self.settings.display_name,
            "tenant_id": self.settings.tenant_id,
            "project_id": self.settings.project_id,
            "initial_task_id": self.settings.task_id,
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

    @staticmethod
    def _match(routes, path: str):
        for name, pattern in routes:
            matched = pattern.fullmatch(path)
            if matched is not None:
                return name, matched.groupdict()
        return None

    def get_route(self, path: str):
        return self._match(_GET_ROUTES, path)

    def post_route(self, path: str):
        return self._match(_POST_ROUTES, path)

    def put_route(self, path: str):
        return self._match(_PUT_ROUTES, path)

    def stream_route(self, path: str):
        matched = _STREAM_PATH.fullmatch(path)
        return matched.group("view_id") if matched else None

    def remember_topology(self, payload: dict[str, object], path: str, body: bytes) -> None:
        route = self.get_route(path)
        if route is None or route[0] != "topology":
            return
        try:
            document = strict_json_loads(body)
        except (TypeError, ValueError):
            return
        view_id = document.get("view_id") if isinstance(document, dict) else None
        task_id = route[1].get("task_id")
        if (
            isinstance(view_id, str)
            and re.fullmatch(_VIEW_ID, view_id)
            and isinstance(task_id, str)
        ):
            self.views.remember(payload, task_id, view_id)

    async def forward(
        self,
        request: Request,
        payload: dict[str, object],
        *,
        method: str,
        path: str,
        body: bytes | None = None,
        expect_json: bool,
        mutation: bool = False,
        download: bool = False,
    ) -> Response:
        request_id = _request_id(request)
        headers = {
            "Authorization": "Bearer " + self.internal_bearer(payload),
            "Accept": "application/json" if expect_json else "application/octet-stream",
            "X-Request-ID": request_id,
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        for name in ("idempotency-key", "if-match"):
            value, valid = _one_header(
                request, name, maximum=256 if name == "idempotency-key" else 1024
            )
            if valid and value:
                headers[name.title()] = value
        url = _url(self.settings, path, request)
        try:
            upstream_request = self.client.build_request(
                method, url, headers=headers, content=body
            )
            upstream = await self.client.send(upstream_request, stream=True)
            content = await _bounded_response_body(
                upstream,
                _MAX_DOWNLOAD_BYTES if download and not expect_json
                else self.settings.max_response_bytes,
            )
        except (httpx.HTTPError, OSError, TimeoutError):
            if mutation:
                return _problem(
                    502,
                    "OPERATION_UNKNOWN",
                    "Operation status is unknown; query the original command with the same key.",
                    request_id=request_id,
                )
            return _problem(
                503,
                "CAPABILITY_UNAVAILABLE",
                "Upstream service is unavailable.",
                request_id=request_id,
            )
        if content is None:
            return _problem(
                503,
                "CAPABILITY_UNAVAILABLE",
                "Upstream response exceeds its bound.",
                request_id=request_id,
            )
        if mutation and upstream.status_code in {502, 504}:
            return _problem(
                502,
                "OPERATION_UNKNOWN",
                "Operation status is unknown; query the original command with the same key.",
                request_id=request_id,
            )
        return _upstream_response(
            upstream.status_code,
            upstream.headers,
            content,
            request_id=request_id,
            expect_json=expect_json,
            download=download,
        )


def _query_for_route(request: Request, name: str):
    allowed = {
        "task_list": {"project_id", "limit", "cursor"},
        "task_options": set(),
        "task_get": set(),
        "task_overview": set(),
        "command_inventory": {"limit", "after"},
        "publications": {"limit", "after"},
        "capture_sessions": set(),
        "capture_items": {"after", "limit"},
        "capture_part": set(),
        "task_activity": {"limit", "cursor", "after_cursor", "importance", "category", "work_item_id"},
        "task_readiness": set(),
        "task_launch": set(),
        "topology": {"mode", "snapshot_id", "cursor", "node_limit", "edge_limit"},
        "exploration": {"mode", "snapshot_id", "cursor", "node_limit"},
        "task_inputs": set(),
        "snapshots": {"cursor"},
        "completion_get": set(),
        "report_get": set(),
        "delivery_list": set(),
        "delivery_get": set(),
        "record_get": {"revision", "snapshot_id"},
        "layout_get": set(),
        "task_material": {"version"},
        "artifact_content": {"version"},
    }[name]
    required = {"project_id"} if name == "task_list" else set()
    if name in {"task_material", "artifact_content"}:
        required = {"version"}
    if name == "record_get":
        required = {"revision"}
    return _query(request, allowed, required)


def _query_for_stream(request: Request):
    values = _query(request, {"cursor"})
    if values is None:
        return None
    last_event_values = _header_values(request, "last-event-id")
    if len(last_event_values) > 1 or (
        last_event_values and len(last_event_values[0]) > _MAX_HEADER_BYTES
    ):
        return None
    last_event_id = last_event_values[0] if last_event_values else None
    if values.get("cursor") and last_event_id:
        return None
    return values, last_event_id or None


def _model_for_post(name: str):
    return {
        "task_create": TaskCreate,
        "task_command": TaskCommand,
        "completion_post": TaskCompletionCommand,
        "delivery_post": ReportDeliveryCommand,
        "input_answer": InputAnswerCommandV1,
    }[name]


async def _validated_json(request: Request, model, maximum: int):
    content_type, content_type_present = _one_header(
        request, "content-type", maximum=256
    )
    if (
        not content_type_present
        or content_type.split(";", 1)[0].strip().lower() != "application/json"
    ):
        return None, _problem(
            422,
            "INVALID_SCHEMA",
            "Requests require application/json.",
            request_id=_request_id(request),
        )
    body, complete = await _bounded_request_body(request, maximum)
    if not complete or not body:
        return None, _problem(
            422,
            "INVALID_SCHEMA",
            "Request body exceeds its bound.",
            request_id=_request_id(request),
        )
    try:
        document = strict_json_loads(body)
        model.model_validate(document)
    except (TypeError, ValueError, ValidationError):
        return None, _problem(
            422,
            "INVALID_SCHEMA",
            "Request is not the registered strict JSON contract.",
            request_id=_request_id(request),
        )
    return body, None


def create_gateway(settings: GatewaySettings, *, client=None) -> FastAPI:
    gateway = BrowserGateway(settings, client=client)

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        try:
            yield
        finally:
            await gateway.close()

    app = FastAPI(
        title="Wuji local browser gateway",
        version="2.0.0",
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
        if not gateway.request_boundary_ok(request):
            return _problem(400, "INVALID_SCHEMA", "Gateway request boundary is invalid.")
        if gateway.reject_browser_bearer(request):
            return _problem(400, "INVALID_SCHEMA", "Use the browser session protocol.")
        payload = gateway.session(request)
        if payload is None:
            return _problem(401, "UNAUTHENTICATED", "Browser session is not active.")
        return JSONResponse(gateway.public_session(payload), headers=NO_STORE)

    @app.post("/auth/login")
    async def login(request: Request) -> Response:
        if not gateway.request_boundary_ok(request):
            return _problem(400, "INVALID_SCHEMA", "Gateway request boundary is invalid.")
        try:
            gateway.require_origin(request)
        except PermissionError:
            return _problem(403, "FORBIDDEN", "Browser origin is not allowed.")
        if gateway.reject_browser_bearer(request):
            return _problem(400, "INVALID_SCHEMA", "Use the browser session protocol.")
        if settings.mode == "local_single_operator":
            access_token, valid_header = _one_header(request, LOCAL_ACCESS_HEADER)
            body, complete = await _bounded_request_body(request, 4096)
            if (
                not valid_header
                or not complete
                or body
                or gateway.local_access is None
                or not gateway.local_access.matches(access_token)
            ):
                return _problem(
                    401,
                    "UNAUTHENTICATED",
                    "The local entry credential is invalid.",
                )
            for previous in gateway.sessions.revoke_all():
                gateway.views.forget_session(previous)
        else:
            body, error = await _validated_json(request, PasswordLogin, 4096)
            if error is not None:
                return error
            try:
                credentials = PasswordLogin.model_validate(strict_json_loads(body))
            except (TypeError, ValueError, ValidationError):
                credentials = None
            if (
                credentials is None
                or gateway.password is None
                or not gateway.password.matches(credentials.username, credentials.password)
            ):
                return _problem(
                    401,
                    "UNAUTHENTICATED",
                    "The username or password is invalid.",
                )
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
        if not gateway.request_boundary_ok(request):
            return _problem(400, "INVALID_SCHEMA", "Gateway request boundary is invalid.")
        if gateway.reject_browser_bearer(request):
            return _problem(400, "INVALID_SCHEMA", "Use the browser session protocol.")
        try:
            gateway.require_origin(request)
        except PermissionError:
            return _problem(403, "FORBIDDEN", "Browser origin is not allowed.")
        payload = gateway.session(request)
        if payload is None:
            return _problem(401, "UNAUTHENTICATED", "Browser session is not active.")
        gateway.sessions.revoke(payload)
        gateway.views.forget_session(payload)
        response = Response(status_code=204, headers=NO_STORE)
        response.delete_cookie(
            COOKIE_NAME,
            path="/",
            httponly=True,
            secure=settings.secure_cookie,
            samesite="strict",
        )
        return response

    @app.get("/api/v2/views/{view_id}/events")
    async def proxy_stream(request: Request, view_id: str) -> Response:
        if not gateway.request_boundary_ok(request):
            return _problem(400, "INVALID_SCHEMA", "Gateway request boundary is invalid.")
        payload = gateway.session(request)
        if payload is None:
            return _problem(401, "UNAUTHENTICATED", "Browser session is not active.")
        path = "/api/v2/views/" + view_id + "/events"
        if gateway.stream_route(path) is None or gateway.reject_browser_bearer(request):
            return _problem(404, "NOT_FOUND_OR_FORBIDDEN", "Resource is unavailable.")
        query = _query_for_stream(request)
        if query is None or not gateway.views.allowed(payload, view_id):
            return _problem(404, "NOT_FOUND_OR_FORBIDDEN", "Resource is unavailable.")
        _query_values, last_event_id = query
        headers = {
            "Authorization": "Bearer " + gateway.internal_bearer(payload),
            "Accept": "text/event-stream",
            "X-Request-ID": _request_id(request),
        }
        if last_event_id:
            headers["Last-Event-ID"] = last_event_id
        stream_client = gateway.stream_client or gateway.client
        try:
            upstream_request = stream_client.build_request(
                "GET", _url(settings, path, request), headers=headers
            )
            upstream = await stream_client.send(upstream_request, stream=True)
        except (httpx.HTTPError, OSError, TimeoutError):
            return _problem(
                503,
                "CAPABILITY_UNAVAILABLE",
                "View stream is unavailable.",
                request_id=_request_id(request),
            )
        if upstream.status_code != 200:
            content = await _bounded_response_body(
                upstream, gateway.settings.max_response_bytes
            )
            if content is None:
                return _problem(
                    503,
                    "CAPABILITY_UNAVAILABLE",
                    "Upstream response exceeds its bound.",
                    request_id=_request_id(request),
                )
            return _upstream_response(
                upstream.status_code,
                upstream.headers,
                content,
                request_id=_request_id(request),
                expect_json=True,
            )

        async def relay():
            total = 0
            try:
                async with asyncio.timeout(_STREAM_LIFETIME_SECONDS):
                    iterator = getattr(upstream, "aiter_raw", None) or getattr(
                        upstream, "aiter_bytes"
                    )
                    async for chunk in iterator():
                        if (
                            not isinstance(chunk, bytes)
                            or total + len(chunk) > gateway.settings.max_stream_bytes
                        ):
                            return
                        total += len(chunk)
                        yield chunk
            except TimeoutError:
                return
            finally:
                await upstream.aclose()

        return StreamingResponse(
            relay(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-store",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    @app.get("/api/v2/{rest:path}")
    async def proxy_read(request: Request, rest: str) -> Response:
        if not gateway.request_boundary_ok(request):
            return _problem(400, "INVALID_SCHEMA", "Gateway request boundary is invalid.")
        payload = gateway.session(request)
        if payload is None:
            return _problem(401, "UNAUTHENTICATED", "Browser session is not active.")
        if gateway.reject_browser_bearer(request):
            return _problem(400, "INVALID_SCHEMA", "Use the browser session protocol.")
        path = "/api/v2/" + rest
        route = gateway.get_route(path)
        if route is None:
            return _problem(404, "NOT_FOUND_OR_FORBIDDEN", "Resource is unavailable.")
        name, groups = route
        query = _query_for_route(request, name)
        if query is None:
            return _problem(422, "INVALID_SCHEMA", "Query is not the registered route contract.")
        if name in {"task_list", "task_options"}:
            project_id = query.get("project_id") or groups.get("project_id")
            if project_id != settings.project_id:
                return _problem(404, "NOT_FOUND_OR_FORBIDDEN", "Resource is unavailable.")
        if name == "topology" and query.get("mode") not in {None, "live", "history"}:
            return _problem(422, "INVALID_SCHEMA", "Unsupported topology mode.")
        if name in {"task_material", "artifact_content"} and not re.fullmatch(
            r"[0-9]+", query["version"]
        ):
            return _problem(422, "INVALID_SCHEMA", "Artifact version is invalid.")
        if name == "record_get" and not re.fullmatch(r"[1-9][0-9]*", query["revision"]):
            return _problem(422, "INVALID_SCHEMA", "Record revision is invalid.")
        response = await gateway.forward(
            request,
            payload,
            method="GET",
            path=path,
            expect_json=name not in {"artifact_content", "capture_part"},
            download=name in {"artifact_content", "capture_part"},
        )
        if name == "topology" and response.status_code == 200:
            gateway.remember_topology(payload, path, response.body)
        return response

    @app.post("/api/v2/{rest:path}")
    async def proxy_post(request: Request, rest: str) -> Response:
        if not gateway.request_boundary_ok(request):
            return _problem(400, "INVALID_SCHEMA", "Gateway request boundary is invalid.")
        payload = gateway.session(request)
        if payload is None:
            return _problem(401, "UNAUTHENTICATED", "Browser session is not active.")
        if gateway.reject_browser_bearer(request):
            return _problem(400, "INVALID_SCHEMA", "Use the browser session protocol.")
        path = "/api/v2/" + rest
        route = gateway.post_route(path)
        if route is None or _query(request, set()) is None:
            return _problem(404, "NOT_FOUND_OR_FORBIDDEN", "Resource is unavailable.")
        try:
            gateway.require_origin(request)
        except PermissionError:
            return _problem(403, "FORBIDDEN", "Browser origin is not allowed.")
        idempotency_key, valid_key = _one_header(
            request, "idempotency-key", maximum=256
        )
        if (
            not valid_key
            or not idempotency_key
            or not _IDEMPOTENCY_KEY.fullmatch(idempotency_key)
        ):
            return _problem(422, "INVALID_SCHEMA", "Idempotency-Key is required.")
        name, _groups = route
        body_limit = {
            "task_create": 1_048_576,
            "task_command": 65_536,
            "completion_post": 65_536,
            "delivery_post": 262_144,
            "input_answer": 65_536,
        }[name]
        body, error = await _validated_json(
            request,
            _model_for_post(name),
            min(body_limit, settings.max_request_bytes),
        )
        if error is not None:
            return error
        if name == "task_create":
            try:
                document = strict_json_loads(body)
            except (TypeError, ValueError):
                return _problem(422, "INVALID_SCHEMA", "Request is not strict JSON.")
            if (
                not isinstance(document, dict)
                or document.get("project_id") != settings.project_id
            ):
                return _problem(404, "NOT_FOUND_OR_FORBIDDEN", "Resource is unavailable.")
        return await gateway.forward(
            request,
            payload,
            method="POST",
            path=path,
            body=body,
            expect_json=True,
            mutation=True,
        )

    @app.put("/api/v2/{rest:path}")
    async def proxy_put(request: Request, rest: str) -> Response:
        if not gateway.request_boundary_ok(request):
            return _problem(400, "INVALID_SCHEMA", "Gateway request boundary is invalid.")
        payload = gateway.session(request)
        if payload is None:
            return _problem(401, "UNAUTHENTICATED", "Browser session is not active.")
        if gateway.reject_browser_bearer(request):
            return _problem(400, "INVALID_SCHEMA", "Use the browser session protocol.")
        path = "/api/v2/" + rest
        route = gateway.put_route(path)
        if route is None or _query(request, set()) is None:
            return _problem(404, "NOT_FOUND_OR_FORBIDDEN", "Resource is unavailable.")
        try:
            gateway.require_origin(request)
        except PermissionError:
            return _problem(403, "FORBIDDEN", "Browser origin is not allowed.")
        if_match, valid_match = _one_header(request, "if-match", maximum=1024)
        if not valid_match or not _IF_MATCH.fullmatch(if_match or ""):
            return _problem(422, "INVALID_SCHEMA", "If-Match must be a decimal revision.")
        body, error = await _validated_json(
            request, LayoutPatch, min(262_144, settings.max_request_bytes)
        )
        if error is not None:
            return error
        return await gateway.forward(
            request,
            payload,
            method="PUT",
            path=path,
            body=body,
            expect_json=True,
            mutation=True,
        )

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
