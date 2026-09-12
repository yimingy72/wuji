"""Strict JSON parsing and idempotency canonicalization for HTTP boundaries."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class InvalidJsonDocument(ValueError):
    """Raised when bytes are not a single finite, duplicate-free JSON value."""


def _reject_duplicate_keys(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise InvalidJsonDocument(f"duplicate object key: {key}")
        value[key] = item
    return value


def _reject_nonfinite_number(token: str) -> None:
    raise InvalidJsonDocument(f"non-finite JSON number: {token}")


def strict_json_loads(document: bytes | bytearray | memoryview | str) -> Any:
    """Parse JSON without accepting duplicate keys or non-finite numbers."""

    if isinstance(document, (bytes, bytearray, memoryview)):
        try:
            source = bytes(document).decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise InvalidJsonDocument("JSON body is not valid UTF-8") from error
    elif isinstance(document, str):
        source = document
    else:
        raise TypeError("strict_json_loads expects UTF-8 bytes or text")

    try:
        return json.loads(
            source,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_number,
        )
    except InvalidJsonDocument:
        raise
    except (json.JSONDecodeError, RecursionError) as error:
        raise InvalidJsonDocument(f"invalid JSON document: {error.msg if isinstance(error, json.JSONDecodeError) else 'nesting too deep'}") from error


def canonical_json_bytes(value: Any) -> bytes:
    """Canonicalize structure while preserving strings and array order exactly."""

    parsed = strict_json_loads(value) if isinstance(value, (bytes, bytearray, memoryview, str)) else value
    try:
        encoded = json.dumps(
            parsed,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise InvalidJsonDocument(f"value cannot be encoded as finite JSON: {error}") from error
    return encoded.encode("utf-8")


class StrictJsonMiddleware:
    """Reject unsafe JSON syntax before framework request parsing."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not _is_json_request(scope):
            await self._app(scope, receive, send)
            return

        body = await _read_body(receive)
        if body:
            try:
                parsed = strict_json_loads(body)
            except InvalidJsonDocument:
                await _send_invalid_schema(scope, send)
                return
            scope.setdefault("state", {})["strict_json"] = parsed

        delivered = False

        async def replay_body() -> Message:
            nonlocal delivered
            if delivered:
                return {"type": "http.request", "body": b"", "more_body": False}
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self._app(scope, replay_body, send)


def _is_json_request(scope: Scope) -> bool:
    for name, value in scope.get("headers", []):
        if name.lower() == b"content-type":
            media_type = value.decode("latin-1").split(";", 1)[0].strip().lower()
            return media_type == "application/json" or media_type.endswith("+json")
    return False


async def _read_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message["type"] != "http.request":
            continue
        chunks.append(message.get("body", b""))
        if not message.get("more_body", False):
            return b"".join(chunks)


async def _send_invalid_schema(scope: Scope, send: Send) -> None:
    request_id = scope.setdefault("state", {}).setdefault("request_id", str(uuid4()))
    body = json.dumps(
        {
            "code": "INVALID_SCHEMA",
            "message": "Request body is not valid strict JSON.",
            "request_id": request_id,
            "retryable": False,
            "details": {},
        },
        separators=(",", ":"),
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 422,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
                (b"x-request-id", request_id.encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
