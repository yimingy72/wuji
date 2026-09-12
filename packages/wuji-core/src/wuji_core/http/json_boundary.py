"""Strict JSON parsing and idempotency canonicalization for HTTP boundaries."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

import simplejson as json
from fastapi.routing import APIRoute
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class InvalidJsonDocument(ValueError):
    """Raised when bytes are not a single finite, duplicate-free JSON value."""


class ClientDisconnected(Exception):
    """Raised internally when ASGI reports that the request peer disconnected."""


@dataclass(frozen=True, slots=True)
class JsonBoundaryLimits:
    max_body_bytes: int = 1_048_576
    read_timeout_seconds: float = 5.0
    max_nesting_depth: int = 64
    max_number_characters: int = 256
    max_decimal_adjusted_exponent: int = 10_000

    def __post_init__(self) -> None:
        if self.max_body_bytes < 1:
            raise ValueError("max_body_bytes must be positive")
        if self.read_timeout_seconds <= 0:
            raise ValueError("read_timeout_seconds must be positive")
        if self.max_nesting_depth < 1:
            raise ValueError("max_nesting_depth must be positive")
        if self.max_number_characters < 1:
            raise ValueError("max_number_characters must be positive")
        if self.max_decimal_adjusted_exponent < 1:
            raise ValueError("max_decimal_adjusted_exponent must be positive")


DEFAULT_JSON_LIMITS = JsonBoundaryLimits()


def _reject_duplicate_keys(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise InvalidJsonDocument(f"duplicate object key: {key}")
        value[key] = item
    return value


def _reject_nonfinite_number(token: str) -> None:
    raise InvalidJsonDocument(f"non-finite JSON number: {token}")


def strict_json_loads(
    document: bytes | bytearray | memoryview | str,
    *,
    limits: JsonBoundaryLimits = DEFAULT_JSON_LIMITS,
) -> Any:
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

    _validate_nesting_depth(source, limits.max_nesting_depth)
    try:
        return json.loads(
            source,
            object_pairs_hook=_reject_duplicate_keys,
            parse_int=lambda token: _bounded_int(token, limits),
            parse_float=lambda token: _bounded_decimal(token, limits),
            parse_constant=_reject_nonfinite_number,
            allow_nan=False,
        )
    except InvalidJsonDocument:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError) as error:
        message = error.msg if isinstance(error, json.JSONDecodeError) else str(error)
        raise InvalidJsonDocument(f"invalid JSON document: {message}") from error


def canonical_json_bytes(
    value: Any, *, limits: JsonBoundaryLimits = DEFAULT_JSON_LIMITS
) -> bytes:
    """Canonicalize structure while preserving strings and array order exactly."""

    parsed = (
        strict_json_loads(value, limits=limits)
        if isinstance(value, (bytes, bytearray, memoryview, str))
        else value
    )
    _ensure_finite_numbers(parsed, limits=limits)
    try:
        encoded = json.dumps(
            parsed,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            use_decimal=True,
        )
    except (TypeError, ValueError) as error:
        raise InvalidJsonDocument(
            f"value cannot be encoded as finite JSON: {error}"
        ) from error
    return encoded.encode("utf-8")


class StrictJsonRequest(Request):
    """Return the object already parsed and bounded by StrictJsonMiddleware."""

    async def json(self) -> Any:
        if hasattr(self, "_json"):
            return self._json
        state = self.scope.setdefault("state", {})
        if "strict_json" in state:
            self._json = state["strict_json"]
            return self._json
        self._json = strict_json_loads(await self.body())
        return self._json


class StrictJsonRoute(APIRoute):
    """FastAPI public route extension that installs StrictJsonRequest."""

    def get_route_handler(self):
        original_handler = super().get_route_handler()

        async def strict_route_handler(request: Request):
            strict_request = StrictJsonRequest(request.scope, request.receive)
            return await original_handler(strict_request)

        return strict_route_handler


class DecimalJSONResponse(Response):
    """JSON response that writes Decimal values as JSON numbers."""

    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        _ensure_finite_numbers(content, limits=DEFAULT_JSON_LIMITS)
        try:
            return json.dumps(
                content,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                use_decimal=True,
            ).encode("utf-8")
        except (TypeError, ValueError, OverflowError) as error:
            raise InvalidJsonDocument(
                f"response cannot be encoded as finite JSON: {error}"
            ) from error


class StrictJsonMiddleware:
    """Reject unsafe JSON syntax before framework request parsing."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        limits: JsonBoundaryLimits = DEFAULT_JSON_LIMITS,
    ) -> None:
        self._app = app
        self._limits = limits

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not _is_json_request(scope):
            await self._app(scope, receive, send)
            return

        try:
            async with asyncio.timeout(self._limits.read_timeout_seconds):
                body = await _read_body(
                    receive, max_body_bytes=self._limits.max_body_bytes
                )
        except ClientDisconnected:
            return
        except (TimeoutError, InvalidJsonDocument):
            await _send_invalid_schema(scope, send)
            return
        if body:
            try:
                parsed = strict_json_loads(body, limits=self._limits)
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


async def _read_body(
    receive: Receive, *, max_body_bytes: int = DEFAULT_JSON_LIMITS.max_body_bytes
) -> bytes:
    body = bytearray()
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            raise ClientDisconnected
        if message["type"] != "http.request":
            raise InvalidJsonDocument("unexpected ASGI request event")
        chunk = message.get("body", b"")
        if not isinstance(chunk, bytes):
            raise InvalidJsonDocument("ASGI request body chunk is not bytes")
        if len(body) + len(chunk) > max_body_bytes:
            raise InvalidJsonDocument("JSON body exceeds max_body_bytes")
        body.extend(chunk)
        if not message.get("more_body", False):
            return bytes(body)


def _bounded_int(token: str, limits: JsonBoundaryLimits) -> int:
    if len(token.lstrip("-")) > limits.max_number_characters:
        raise InvalidJsonDocument("JSON integer token exceeds configured limit")
    try:
        return int(token)
    except ValueError as error:
        raise InvalidJsonDocument("invalid JSON integer") from error


def _bounded_decimal(token: str, limits: JsonBoundaryLimits) -> Decimal:
    if len(token) > limits.max_number_characters:
        raise InvalidJsonDocument("JSON decimal token exceeds configured limit")
    try:
        value = Decimal(token)
    except InvalidOperation as error:
        raise InvalidJsonDocument("invalid JSON decimal") from error
    if not value.is_finite():
        raise InvalidJsonDocument("non-finite JSON decimal")
    if abs(value.adjusted()) > limits.max_decimal_adjusted_exponent:
        raise InvalidJsonDocument("JSON decimal exponent exceeds configured limit")
    return value


def _ensure_finite_numbers(
    value: Any,
    *,
    limits: JsonBoundaryLimits,
    depth: int = 0,
    active: set[int] | None = None,
) -> None:
    if depth > limits.max_nesting_depth:
        raise InvalidJsonDocument("JSON nesting exceeds configured limit")
    if active is None:
        active = set()
    item = value
    if isinstance(item, bool) or item is None or isinstance(item, str):
        return
    if isinstance(item, int):
        decimal_digits = Decimal(abs(item)).adjusted() + 1 if item else 1
        if decimal_digits > limits.max_number_characters:
            raise InvalidJsonDocument("JSON integer token exceeds configured limit")
        return
    if isinstance(item, Decimal):
        if not item.is_finite():
            raise InvalidJsonDocument("non-finite Decimal cannot be encoded")
        if len(item.as_tuple().digits) > limits.max_number_characters:
            raise InvalidJsonDocument("JSON decimal token exceeds configured limit")
        if abs(item.adjusted()) > limits.max_decimal_adjusted_exponent:
            raise InvalidJsonDocument("JSON decimal exponent exceeds configured limit")
        return
    if isinstance(item, float):
        if not math.isfinite(item):
            raise InvalidJsonDocument("non-finite float cannot be encoded")
        return
    if isinstance(item, dict):
        identity = id(item)
        if identity in active:
            raise InvalidJsonDocument("cyclic object cannot be encoded")
        active.add(identity)
        try:
            for child in item.values():
                _ensure_finite_numbers(
                    child, limits=limits, depth=depth + 1, active=active
                )
        finally:
            active.remove(identity)
        return
    if isinstance(item, (list, tuple)):
        identity = id(item)
        if identity in active:
            raise InvalidJsonDocument("cyclic array cannot be encoded")
        active.add(identity)
        try:
            for child in item:
                _ensure_finite_numbers(
                    child, limits=limits, depth=depth + 1, active=active
                )
        finally:
            active.remove(identity)


def _validate_nesting_depth(source: str, max_depth: int) -> None:
    depth = 0
    in_string = False
    escaped = False
    for character in source:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > max_depth:
                raise InvalidJsonDocument("JSON nesting exceeds configured limit")
        elif character in "]}":
            depth -= 1


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
