"""Opaque handle, return-path, PKCE, and signed cursor helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

PROJECT_RETURN_PATH = re.compile(
    r"^/projects(?:/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(/tasks/new)?)?/?$"
)


class InvalidReturnPath(ValueError):
    pass


class InvalidCursor(ValueError):
    pass


class ExpiredCursor(ValueError):
    pass


def opaque_token(size: int = 32) -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(size)).rstrip(b"=").decode("ascii")


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def pkce_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(
        b"="
    ).decode("ascii")


def normalize_return_path(value: str) -> str:
    match = PROJECT_RETURN_PATH.fullmatch(value)
    if match is None:
        raise InvalidReturnPath("return path is outside the allowed project routes")
    project_id = match.group(1)
    if project_id is None:
        return "/projects"
    parsed = UUID(project_id)
    if str(parsed) != project_id.lower():
        raise InvalidReturnPath("project path UUID is not canonical")
    suffix = match.group(2) or ""
    return f"/projects/{parsed}{suffix}"


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass(frozen=True)
class CursorPosition:
    created_at: datetime
    project_id: UUID


@dataclass(frozen=True)
class ScopeCursorPosition:
    created_at: datetime
    policy_id: UUID
    version: int


class CursorCodec:
    def __init__(self, key: str, *, ttl_seconds: int = 900):
        if len(key) < 32:
            raise ValueError("cursor key is too short")
        if not 1 <= ttl_seconds <= 900:
            raise ValueError("cursor lifetime is outside the allowed range")
        self._key = key.encode("utf-8")
        self._ttl_seconds = ttl_seconds

    def encode(
        self,
        *,
        user_id: UUID,
        permissions_version: int,
        limit: int,
        position: CursorPosition,
        now: int | None = None,
    ) -> str:
        issued_at = int(time.time() if now is None else now)
        payload = {
            "created_at": position.created_at.isoformat(),
            "endpoint": "projects",
            "exp": issued_at + self._ttl_seconds,
            "iat": issued_at,
            "limit": limit,
            "permissions_version": permissions_version,
            "project_id": str(position.project_id),
            "user_id": str(user_id),
            "v": 1,
        }
        encoded = _b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        signature = _b64encode(hmac.digest(self._key, encoded.encode("ascii"), "sha256"))
        return f"{encoded}.{signature}"

    def decode(
        self,
        value: str,
        *,
        user_id: UUID,
        permissions_version: int,
        limit: int,
        now: int | None = None,
    ) -> CursorPosition:
        try:
            encoded, supplied_signature = value.split(".", 1)
            expected_signature = _b64encode(
                hmac.digest(self._key, encoded.encode("ascii"), "sha256")
            )
            if not hmac.compare_digest(supplied_signature, expected_signature):
                raise InvalidCursor("cursor signature is invalid")
            payload: dict[str, Any] = json.loads(_b64decode(encoded))
            expected_keys = {
                "created_at",
                "endpoint",
                "exp",
                "iat",
                "limit",
                "permissions_version",
                "project_id",
                "user_id",
                "v",
            }
            if set(payload) != expected_keys:
                raise InvalidCursor("cursor shape is invalid")
            if payload["v"] != 1 or payload["endpoint"] != "projects":
                raise InvalidCursor("cursor endpoint is invalid")
            issued_at = int(payload["iat"])
            expires_at = int(payload["exp"])
            current_time = int(time.time() if now is None else now)
            if issued_at > current_time or expires_at <= issued_at or expires_at - issued_at > 900:
                raise InvalidCursor("cursor timestamps are invalid")
            if expires_at <= current_time:
                raise ExpiredCursor("cursor has expired")
            if payload["user_id"] != str(user_id) or payload["limit"] != limit:
                raise InvalidCursor("cursor binding is invalid")
            if payload["permissions_version"] != permissions_version:
                raise ExpiredCursor("cursor authority version has changed")
            created_at = datetime.fromisoformat(payload["created_at"])
            if created_at.tzinfo is None:
                raise InvalidCursor("cursor timestamp requires a timezone")
            return CursorPosition(created_at=created_at, project_id=UUID(payload["project_id"]))
        except ExpiredCursor:
            raise
        except InvalidCursor:
            raise
        except Exception as error:
            raise InvalidCursor("cursor is malformed") from error

    def encode_scope(
        self,
        *,
        user_id: UUID,
        permissions_version: int,
        project_id: UUID,
        limit: int,
        position: ScopeCursorPosition,
        now: int | None = None,
    ) -> str:
        issued_at = int(time.time() if now is None else now)
        payload = {
            "created_at": position.created_at.isoformat(),
            "endpoint": "scopes",
            "exp": issued_at + 900,
            "iat": issued_at,
            "limit": limit,
            "permissions_version": permissions_version,
            "policy_id": str(position.policy_id),
            "project_id": str(project_id),
            "user_id": str(user_id),
            "v": 1,
            "version": position.version,
        }
        encoded = _b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        signature = _b64encode(hmac.digest(self._key, encoded.encode("ascii"), "sha256"))
        cursor = f"{encoded}.{signature}"
        if len(cursor) > 512:
            raise ValueError("scope cursor exceeds the contract limit")
        return cursor

    def decode_scope(
        self,
        value: str,
        *,
        user_id: UUID,
        permissions_version: int,
        project_id: UUID,
        limit: int,
        now: int | None = None,
    ) -> ScopeCursorPosition:
        try:
            encoded, supplied_signature = value.split(".", 1)
            expected_signature = _b64encode(
                hmac.digest(self._key, encoded.encode("ascii"), "sha256")
            )
            if not hmac.compare_digest(supplied_signature, expected_signature):
                raise InvalidCursor("cursor signature is invalid")
            payload: dict[str, Any] = json.loads(_b64decode(encoded))
            expected_keys = {
                "created_at",
                "endpoint",
                "exp",
                "iat",
                "limit",
                "permissions_version",
                "policy_id",
                "project_id",
                "user_id",
                "v",
                "version",
            }
            if set(payload) != expected_keys:
                raise InvalidCursor("cursor shape is invalid")
            if payload["v"] != 1 or payload["endpoint"] != "scopes":
                raise InvalidCursor("cursor endpoint is invalid")
            issued_at = int(payload["iat"])
            expires_at = int(payload["exp"])
            current_time = int(time.time() if now is None else now)
            if issued_at > current_time or expires_at <= issued_at or expires_at - issued_at > 900:
                raise InvalidCursor("cursor timestamps are invalid")
            if expires_at <= current_time:
                raise ExpiredCursor("cursor has expired")
            if (
                payload["user_id"] != str(user_id)
                or payload["project_id"] != str(project_id)
                or payload["limit"] != limit
            ):
                raise InvalidCursor("cursor binding is invalid")
            if payload["permissions_version"] != permissions_version:
                raise ExpiredCursor("cursor authority version has changed")
            created_at = datetime.fromisoformat(payload["created_at"])
            if created_at.tzinfo is None:
                raise InvalidCursor("cursor timestamp requires a timezone")
            version = int(payload["version"])
            if version < 1:
                raise InvalidCursor("cursor version position is invalid")
            return ScopeCursorPosition(
                created_at=created_at,
                policy_id=UUID(payload["policy_id"]),
                version=version,
            )
        except ExpiredCursor:
            raise
        except InvalidCursor:
            raise
        except Exception as error:
            raise InvalidCursor("cursor is malformed") from error
