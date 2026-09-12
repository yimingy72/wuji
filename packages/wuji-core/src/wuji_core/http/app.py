"""Minimal isolated FastAPI composition boundary for vNext routers."""

from __future__ import annotations

import re
from collections.abc import Iterable
from decimal import Decimal
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, get_args, get_origin, get_type_hints

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel
from starlette.responses import Response
from starlette.types import ASGIApp

from wuji_core.http.auth import BearerAuthMiddleware, TokenVerifier
from wuji_core.http.json_boundary import (
    DEFAULT_JSON_LIMITS,
    DecimalJSONResponse,
    JsonBoundaryLimits,
    StrictJsonRoute,
    StrictJsonMiddleware,
)


class UnsafeJsonResponse(RuntimeError):
    """Raised before FastAPI can coerce a precision-sensitive response."""


def create_app(
    *,
    token_verifier: TokenVerifier,
    routers: Iterable[APIRouter] = (),
    json_limits: JsonBoundaryLimits = DEFAULT_JSON_LIMITS,
) -> ASGIApp:
    application = FastAPI(
        title="Wuji vNext API",
        version="2.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    for router in routers:
        incompatible = [
            route.path
            for route in router.routes
            if isinstance(route, APIRoute) and not isinstance(route, StrictJsonRoute)
        ]
        if incompatible:
            raise ValueError(
                "vNext routers must use VNextAPIRouter/StrictJsonRoute: "
                + ", ".join(incompatible)
            )
        application.include_router(router)

    @application.exception_handler(RequestValidationError)
    async def invalid_request(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        request_id = request.state.request_id
        errors = error.errors()
        error_code = _validation_error_code(request, errors)
        safe_location_names = _request_schema_location_names(request)
        selected_errors = errors[:_MAX_PUBLIC_VALIDATION_ERRORS]
        return JSONResponse(
            status_code=422,
            headers={"x-request-id": request_id},
            content={
                "code": error_code,
                "message": (
                    "Unsupported schema_version."
                    if error_code == "INVALID_SCHEMA_VERSION"
                    else "Request does not satisfy the v2 contract."
                ),
                "request_id": request_id,
                "retryable": False,
                "details": {
                    "errors": [
                        _public_validation_error(item, safe_location_names)
                        for item in selected_errors
                    ],
                    "truncated": len(errors) > len(selected_errors),
                },
            },
        )

    @application.exception_handler(UnsafeJsonResponse)
    async def unsafe_json_response(
        request: Request, error: UnsafeJsonResponse
    ) -> JSONResponse:
        del error
        request_id = request.state.request_id
        return JSONResponse(
            status_code=503,
            headers={"x-request-id": request_id},
            content={
                "code": "CAPABILITY_UNAVAILABLE",
                "message": "Use DecimalJSONResponse for precision-sensitive output.",
                "request_id": request_id,
                "retryable": False,
                "details": {},
            },
        )

    strict_json = StrictJsonMiddleware(application, limits=json_limits)
    return BearerAuthMiddleware(strict_json, token_verifier=token_verifier)


class VNextAPIRouter(APIRouter):
    """Router whose body models consume the strict Decimal-preserving request."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        route_class = kwargs.pop("route_class", StrictJsonRoute)
        if route_class is not StrictJsonRoute:
            raise ValueError("VNextAPIRouter route_class must be StrictJsonRoute")
        super().__init__(*args, route_class=StrictJsonRoute, **kwargs)

    def add_api_route(self, path: str, endpoint: Any, **kwargs: Any) -> None:
        super().add_api_route(path, _guard_endpoint_response(endpoint), **kwargs)


def _guard_endpoint_response(endpoint: Any) -> Any:
    if iscoroutinefunction(endpoint):

        @wraps(endpoint)
        async def guarded_async(*args: Any, **kwargs: Any) -> Any:
            result = await endpoint(*args, **kwargs)
            _reject_lossy_decimal_response(result)
            return result

        return guarded_async

    @wraps(endpoint)
    def guarded_sync(*args: Any, **kwargs: Any) -> Any:
        result = endpoint(*args, **kwargs)
        _reject_lossy_decimal_response(result)
        return result

    return guarded_sync


def _reject_lossy_decimal_response(result: Any) -> None:
    if isinstance(result, Response):
        return
    if _contains_decimal(result, active=set()):
        raise UnsafeJsonResponse


def _contains_decimal(value: Any, *, active: set[int]) -> bool:
    if isinstance(value, Decimal):
        return True
    if isinstance(value, BaseModel):
        return _contains_decimal(value.model_dump(mode="python"), active=active)
    if isinstance(value, dict):
        identity = id(value)
        if identity in active:
            return False
        active.add(identity)
        try:
            return any(
                _contains_decimal(item, active=active) for item in value.values()
            )
        finally:
            active.remove(identity)
    if isinstance(value, (list, tuple)):
        identity = id(value)
        if identity in active:
            return False
        active.add(identity)
        try:
            return any(_contains_decimal(item, active=active) for item in value)
        finally:
            active.remove(identity)
    return False


_SAFE_LOCATION_PART = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_MAX_PUBLIC_VALIDATION_ERRORS = 16
_MAX_PUBLIC_LOCATION_DEPTH = 8
_SAFE_LOCATION_ROOTS = frozenset({"body", "query", "path", "header", "cookie"})


def _validation_error_code(request: Request, errors: list[dict[str, Any]]) -> str:
    parsed = getattr(request.state, "strict_json", None)
    if not isinstance(parsed, dict) or "schema_version" not in parsed:
        return "INVALID_SCHEMA"
    for error in errors:
        location = error.get("loc", ())
        if (
            error.get("type") in {"literal_error", "enum"}
            and isinstance(location, (list, tuple))
            and "schema_version" in location
        ):
            return "INVALID_SCHEMA_VERSION"
    return "INVALID_SCHEMA"


def _request_schema_location_names(request: Request) -> frozenset[str]:
    endpoint = request.scope.get("endpoint")
    if not callable(endpoint):
        return _SAFE_LOCATION_ROOTS
    try:
        annotations = get_type_hints(endpoint)
    except (NameError, TypeError):
        return _SAFE_LOCATION_ROOTS
    names = set(_SAFE_LOCATION_ROOTS)
    visited: set[type[BaseModel]] = set()
    for annotation in annotations.values():
        _collect_model_field_names(annotation, names, visited)
    return frozenset(names)


def _collect_model_field_names(
    annotation: Any, names: set[str], visited: set[type[BaseModel]]
) -> None:
    origin = get_origin(annotation)
    if origin is not None:
        for argument in get_args(annotation):
            _collect_model_field_names(argument, names, visited)
        return
    if not isinstance(annotation, type) or not issubclass(annotation, BaseModel):
        return
    if annotation in visited:
        return
    visited.add(annotation)
    for field_name, field in annotation.model_fields.items():
        names.add(field_name)
        if isinstance(field.alias, str):
            names.add(field.alias)
        _collect_model_field_names(field.annotation, names, visited)


def _public_validation_error(
    error: dict[str, Any], safe_location_names: frozenset[str]
) -> dict[str, object]:
    error_type = error.get("type")
    if not isinstance(error_type, str) or not _SAFE_LOCATION_PART.fullmatch(error_type):
        error_type = "validation_error"
    raw_location = error.get("loc")
    location: list[str | int] = []
    if isinstance(raw_location, (list, tuple)):
        selected_location = raw_location[:_MAX_PUBLIC_LOCATION_DEPTH]
        extra_field_position = (
            len(selected_location) - 1
            if error_type == "extra_forbidden" and selected_location
            else None
        )
        for position, part in enumerate(selected_location):
            if isinstance(part, int) and not isinstance(part, bool) and part >= 0:
                location.append(part)
            elif isinstance(part, str):
                is_known_field = part in safe_location_names
                if position == extra_field_position or not is_known_field:
                    location.append("<field>")
                else:
                    location.append(part)
        if len(raw_location) > len(selected_location):
            location[-1:] = ["<truncated>"]
    return {
        "type": error_type,
        "loc": location,
        "msg": "Input does not satisfy the field contract.",
    }
