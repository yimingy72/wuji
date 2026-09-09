"""Minimal platform application shell for the Phase 1A CORE gate."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Final, Literal
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

ReadinessProbe = Callable[[], Awaitable[bool]]
NO_STORE: Final = {"Cache-Control": "no-store"}


class HealthStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["live", "ready"]


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    trace_id: str


async def _not_configured() -> bool:
    return False


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message, "trace_id": str(uuid4())},
        headers=NO_STORE,
    )


def create_app(readiness_probe: ReadinessProbe | None = None) -> FastAPI:
    """Create the API shell; SERVER supplies the database/migration readiness probe."""

    probe = readiness_probe or _not_configured
    application = FastAPI(title="Wuji Platform API", version="0.2.0")

    @application.middleware("http")
    async def disable_storage(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, _error: RequestValidationError) -> JSONResponse:
        return _error_response(422, "VALIDATION_FAILED", "请求参数无效")

    @application.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, error: StarletteHTTPException) -> JSONResponse:
        if error.status_code == 404:
            return _error_response(404, "NOT_FOUND", "请求的资源不存在")
        return _error_response(error.status_code, "INTERNAL_ERROR", "请求处理失败")

    @application.exception_handler(Exception)
    async def internal_error(_request: Request, _error: Exception) -> JSONResponse:
        return _error_response(500, "INTERNAL_ERROR", "服务暂时无法处理请求")

    @application.get(
        "/health/live",
        tags=["Health"],
        response_model=HealthStatus,
        responses={500: {"model": ErrorResponse}},
        openapi_extra={"security": [], "servers": [{"url": "/"}]},
    )
    async def live() -> JSONResponse:
        return JSONResponse({"status": "live"}, headers=NO_STORE)

    @application.get(
        "/health/ready",
        tags=["Health"],
        response_model=HealthStatus,
        responses={503: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
        openapi_extra={"security": [], "servers": [{"url": "/"}]},
    )
    async def ready() -> JSONResponse:
        try:
            is_ready = await probe()
        except Exception:
            is_ready = False
        if not is_ready:
            return _error_response(503, "SERVICE_UNAVAILABLE", "平台依赖尚未就绪")
        return JSONResponse({"status": "ready"}, headers=NO_STORE)

    return application


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return _error(status_code, code, message)


app = create_app()
