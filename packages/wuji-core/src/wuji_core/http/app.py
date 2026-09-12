"""Minimal isolated FastAPI composition boundary for vNext routers."""

from __future__ import annotations

from collections.abc import Iterable
import re
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp

from wuji_core.http.auth import BearerAuthMiddleware, TokenVerifier
from wuji_core.http.json_boundary import StrictJsonMiddleware


def create_app(
    *, token_verifier: TokenVerifier, routers: Iterable[APIRouter] = ()
) -> ASGIApp:
    application = FastAPI(
        title="Wuji vNext API",
        version="2.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    for router in routers:
        application.include_router(router)

    @application.exception_handler(RequestValidationError)
    async def invalid_request(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        request_id = request.state.request_id
        return JSONResponse(
            status_code=422,
            headers={"x-request-id": request_id},
            content={
                "code": "INVALID_SCHEMA",
                "message": "Request does not satisfy the v2 contract.",
                "request_id": request_id,
                "retryable": False,
                "details": {
                    "errors": [_public_validation_error(item) for item in error.errors()]
                },
            },
        )

    strict_json = StrictJsonMiddleware(application)
    return BearerAuthMiddleware(strict_json, token_verifier=token_verifier)


_SAFE_LOCATION_PART = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


def _public_validation_error(error: dict[str, Any]) -> dict[str, object]:
    error_type = error.get("type")
    if not isinstance(error_type, str) or not _SAFE_LOCATION_PART.fullmatch(error_type):
        error_type = "validation_error"
    raw_location = error.get("loc")
    location: list[str | int] = []
    if isinstance(raw_location, (list, tuple)):
        for part in raw_location:
            if isinstance(part, int) and not isinstance(part, bool) and part >= 0:
                location.append(part)
            elif isinstance(part, str):
                location.append(
                    part if _SAFE_LOCATION_PART.fullmatch(part) else "<field>"
                )
    return {
        "type": error_type,
        "loc": location,
        "msg": "Input does not satisfy the field contract.",
    }
