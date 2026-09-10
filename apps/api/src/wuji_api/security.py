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

UUID_PATH = (
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
PROJECT_RETURN_PATH = re.compile(
    rf"^/projects(?:/({UUID_PATH})(/tasks(?:/(new|{UUID_PATH}))?)?)?/?$"
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
    task_component = match.group(3)
    if task_component is not None and task_component != "new":
        task_id = UUID(task_component)
        if str(task_id) != task_component.lower():
            raise InvalidReturnPath("task path UUID is not canonical")
        suffix = suffix[: -len(task_component)] + str(task_id)
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


@dataclass(frozen=True)
class TaskCursorPosition:
    created_at: datetime
    task_id: UUID


@dataclass(frozen=True)
class EventCursorPosition:
    sequence: int


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

    def encode_task(
        self,
        *,
        user_id: UUID,
        permissions_version: int,
        project_id: UUID,
        limit: int,
        position: TaskCursorPosition,
        now: int | None = None,
    ) -> str:
        issued_at = int(time.time() if now is None else now)
        return self._signed(
            {
                "created_at": position.created_at.isoformat(),
                "endpoint": "tasks",
                "exp": issued_at + self._ttl_seconds,
                "iat": issued_at,
                "limit": limit,
                "permissions_version": permissions_version,
                "project_id": str(project_id),
                "task_id": str(position.task_id),
                "user_id": str(user_id),
                "v": 1,
            }
        )

    def decode_task(
        self,
        value: str,
        *,
        user_id: UUID,
        permissions_version: int,
        project_id: UUID,
        limit: int,
        now: int | None = None,
    ) -> TaskCursorPosition:
        payload = self._verified(value)
        expected_keys = {
            "created_at", "endpoint", "exp", "iat", "limit", "permissions_version",
            "project_id", "task_id", "user_id", "v",
        }
        self._validate_context(
            payload,
            expected_keys=expected_keys,
            endpoint="tasks",
            user_id=user_id,
            permissions_version=permissions_version,
            project_id=project_id,
            limit=limit,
            now=now,
        )
        try:
            created_at = datetime.fromisoformat(payload["created_at"])
            if created_at.tzinfo is None:
                raise InvalidCursor("cursor timestamp requires a timezone")
            return TaskCursorPosition(created_at=created_at, task_id=UUID(payload["task_id"]))
        except InvalidCursor:
            raise
        except Exception as error:
            raise InvalidCursor("cursor is malformed") from error

    def encode_event(
        self,
        *,
        user_id: UUID,
        permissions_version: int,
        project_id: UUID,
        task_id: UUID,
        position: EventCursorPosition,
        now: int | None = None,
    ) -> str:
        issued_at = int(time.time() if now is None else now)
        return self._signed(
            {
                "endpoint": "task-events",
                "exp": issued_at + self._ttl_seconds,
                "iat": issued_at,
                "permissions_version": permissions_version,
                "project_id": str(project_id),
                "sequence": position.sequence,
                "task_id": str(task_id),
                "user_id": str(user_id),
                "v": 1,
            }
        )

    def decode_event(
        self,
        value: str,
        *,
        user_id: UUID,
        permissions_version: int,
        project_id: UUID,
        task_id: UUID,
        now: int | None = None,
    ) -> EventCursorPosition:
        payload = self._verified(value)
        expected_keys = {
            "endpoint", "exp", "iat", "permissions_version", "project_id",
            "sequence", "task_id", "user_id", "v",
        }
        self._validate_context(
            payload,
            expected_keys=expected_keys,
            endpoint="task-events",
            user_id=user_id,
            permissions_version=permissions_version,
            project_id=project_id,
            task_id=task_id,
            now=now,
        )
        try:
            sequence = int(payload["sequence"])
            if sequence < 0 or type(payload["sequence"]) is not int:
                raise InvalidCursor("event cursor position is invalid")
            return EventCursorPosition(sequence=sequence)
        except InvalidCursor:
            raise
        except Exception as error:
            raise InvalidCursor("cursor is malformed") from error

    def _signed(self, payload: dict[str, Any]) -> str:
        encoded = _b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        signature = _b64encode(hmac.digest(self._key, encoded.encode("ascii"), "sha256"))
        cursor = f"{encoded}.{signature}"
        if len(cursor) > 512:
            raise ValueError("cursor exceeds the contract limit")
        return cursor

    def _verified(self, value: str) -> dict[str, Any]:
        try:
            encoded, supplied_signature = value.split(".", 1)
            expected_signature = _b64encode(
                hmac.digest(self._key, encoded.encode("ascii"), "sha256")
            )
            if not hmac.compare_digest(supplied_signature, expected_signature):
                raise InvalidCursor("cursor signature is invalid")
            payload = json.loads(_b64decode(encoded))
            if not isinstance(payload, dict):
                raise InvalidCursor("cursor shape is invalid")
            return payload
        except InvalidCursor:
            raise
        except Exception as error:
            raise InvalidCursor("cursor is malformed") from error

    def _validate_context(
        self,
        payload: dict[str, Any],
        *,
        expected_keys: set[str],
        endpoint: str,
        user_id: UUID,
        permissions_version: int,
        project_id: UUID,
        limit: int | None = None,
        task_id: UUID | None = None,
        now: int | None = None,
    ) -> None:
        try:
            if set(payload) != expected_keys or payload["v"] != 1 or payload["endpoint"] != endpoint:
                raise InvalidCursor("cursor endpoint or shape is invalid")
            issued_at = int(payload["iat"])
            expires_at = int(payload["exp"])
            current_time = int(time.time() if now is None else now)
            if issued_at > current_time or expires_at <= issued_at or expires_at - issued_at > 900:
                raise InvalidCursor("cursor timestamps are invalid")
            if expires_at <= current_time:
                raise ExpiredCursor("cursor has expired")
            if payload["user_id"] != str(user_id) or payload["project_id"] != str(project_id):
                raise InvalidCursor("cursor binding is invalid")
            if limit is not None and payload["limit"] != limit:
                raise InvalidCursor("cursor limit binding is invalid")
            if task_id is not None and payload["task_id"] != str(task_id):
                raise InvalidCursor("cursor task binding is invalid")
            if payload["permissions_version"] != permissions_version:
                raise ExpiredCursor("cursor authority version has changed")
        except (ExpiredCursor, InvalidCursor):
            raise
        except Exception as error:
            raise InvalidCursor("cursor is malformed") from error
