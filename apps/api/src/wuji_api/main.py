"""Phase 1A Platform API with database-backed identity and project authority."""

from __future__ import annotations

import hmac
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Final, Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from wuji_api.database import (
    AuthorityUnavailable,
    DatabaseAuthority,
    HandshakeCompletionInvalid,
    HandshakeInProgress,
)
from wuji_api.oidc import OIDCClient, OIDCDependencyError, OIDCProtocolError
from wuji_api.security import (
    CursorCodec,
    CursorPosition,
    ExpiredCursor,
    InvalidCursor,
    InvalidReturnPath,
    normalize_return_path,
    opaque_token,
    token_hash,
)
from wuji_api.settings import Settings, optional_settings

ReadinessProbe = Callable[[], Awaitable[bool]]
NO_STORE: Final = {"Cache-Control": "no-store"}
SESSION_COOKIE = "wuji_session"
HANDSHAKE_COOKIE = "wuji_oidc_handshake"
ERROR_MESSAGES = {
    "UNAUTHENTICATED": "登录状态无效，请重新登录",
    "FORBIDDEN": "当前身份无权执行此操作",
    "NOT_FOUND": "请求的资源不存在",
    "VALIDATION_FAILED": "请求参数无效",
    "INVALID_TRANSITION": "当前登录流程仍在处理中",
    "SERVICE_UNAVAILABLE": "平台依赖暂时不可用",
    "CURSOR_EXPIRED": "分页状态已过期，请重新加载",
    "INTERNAL_ERROR": "服务暂时无法处理请求",
}
access_logger = logging.getLogger("wuji.access")


class HealthStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["live", "ready"]


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    trace_id: UUID


class SessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    display_name: str
    csrf_token: str
    expires_at: str
    permissions_version: int = Field(ge=1)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    tenant_id: UUID
    name: str
    permissions: list[str]


class ProjectPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ProjectResponse]
    next_cursor: str | None


@dataclass
class Runtime:
    settings: Settings
    authority: DatabaseAuthority
    oidc: OIDCClient
    cursors: CursorCodec

    async def close(self) -> None:
        await self.authority.close()


class ApiProblem(RuntimeError):
    def __init__(self, status_code: int, code: str, *, clear_session: bool = False):
        super().__init__(code)
        self.status_code = status_code
        self.code = code
        self.clear_session = clear_session


def _configured_runtime(settings: Settings | None) -> Runtime | None:
    if settings is None:
        return None
    return Runtime(
        settings=settings,
        authority=DatabaseAuthority(settings),
        oidc=OIDCClient(settings),
        cursors=CursorCodec(
            settings.cursor_signing_key.get_secret_value(), ttl_seconds=settings.cursor_ttl_seconds
        ),
    )


def _runtime(request: Request) -> Runtime:
    runtime: Runtime | None = request.app.state.runtime
    if runtime is None:
        raise ApiProblem(503, "SERVICE_UNAVAILABLE")
    return runtime


def _error_response(request: Request, status_code: int, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": ERROR_MESSAGES[code],
            "trace_id": str(request.state.trace_id),
        },
        headers=NO_STORE,
    )


def _delete_cookie(response: Response, name: str, *, secure: bool) -> None:
    response.delete_cookie(name, path="/", httponly=True, secure=secure, samesite="lax")


def _callback_error(
    request: Request,
    code: Literal["UNAUTHENTICATED", "FORBIDDEN", "SERVICE_UNAVAILABLE", "INTERNAL_ERROR"],
) -> RedirectResponse:
    return RedirectResponse(
        url=f"/login?error={code}&trace_id={request.state.trace_id}",
        status_code=303,
        headers=NO_STORE,
    )


async def _authenticated(request: Request, runtime: Runtime):
    if not await runtime.authority.ready():
        raise ApiProblem(503, "SERVICE_UNAVAILABLE")
    raw_token = request.cookies.get(SESSION_COOKIE)
    if not raw_token:
        raise ApiProblem(401, "UNAUTHENTICATED", clear_session=True)
    try:
        session = await runtime.authority.authenticate(raw_token)
    except AuthorityUnavailable as error:
        raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
    if session is None:
        raise ApiProblem(401, "UNAUTHENTICATED", clear_session=True)
    return session


def _project_response(record) -> ProjectResponse:
    return ProjectResponse(
        id=record.id,
        tenant_id=record.tenant_id,
        name=record.name,
        permissions=["project.read"],
    )


def create_app(
    readiness_probe: ReadinessProbe | None = None,
    *,
    settings: Settings | None = None,
) -> FastAPI:
    configured_settings = settings if settings is not None else optional_settings()
    runtime = _configured_runtime(configured_settings)

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if runtime is not None:
                await runtime.close()

    application = FastAPI(title="Wuji Platform API", version="0.2.0", lifespan=lifespan)
    application.state.runtime = runtime

    @application.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.trace_id = uuid4()
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        route = request.scope.get("route")
        route_name = getattr(route, "path", "<unmatched>")
        access_logger.info(
            "http_request method=%s route=%s status=%s trace_id=%s",
            request.method,
            route_name,
            response.status_code,
            request.state.trace_id,
        )
        return response

    @application.exception_handler(ApiProblem)
    async def api_problem(request: Request, error: ApiProblem) -> JSONResponse:
        response = _error_response(request, error.status_code, error.code)
        if error.clear_session:
            _delete_cookie(
                response,
                SESSION_COOKIE,
                secure=bool(configured_settings and configured_settings.secure_cookies),
            )
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _error: RequestValidationError) -> JSONResponse:
        return _error_response(request, 422, "VALIDATION_FAILED")

    @application.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
        if error.status_code == 404:
            return _error_response(request, 404, "NOT_FOUND")
        return _error_response(request, error.status_code, "INTERNAL_ERROR")

    @application.exception_handler(Exception)
    async def internal_error(request: Request, _error: Exception) -> JSONResponse:
        return _error_response(request, 500, "INTERNAL_ERROR")

    @application.get(
        "/health/live",
        tags=["Health"],
        response_model=HealthStatus,
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
    async def ready(request: Request) -> JSONResponse:
        try:
            if readiness_probe is not None:
                is_ready = await readiness_probe()
            else:
                current = _runtime(request)
                is_ready = await current.authority.ready()
        except Exception:
            is_ready = False
        if not is_ready:
            return _error_response(request, 503, "SERVICE_UNAVAILABLE")
        return JSONResponse({"status": "ready"}, headers=NO_STORE)

    @application.get(
        "/api/v1/auth/login",
        tags=["Authentication"],
        status_code=302,
        response_class=RedirectResponse,
        responses={
            302: {"description": "Redirect to the configured identity provider"},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
        openapi_extra={"security": []},
    )
    async def begin_login(
        request: Request, return_to: str = Query(default="/projects", max_length=2048)
    ):
        current = _runtime(request)
        try:
            normalized_return = normalize_return_path(return_to)
        except InvalidReturnPath as error:
            raise ApiProblem(422, "VALIDATION_FAILED") from error

        state = opaque_token()
        binding = opaque_token()
        nonce = opaque_token()
        verifier = opaque_token(64)
        handshake_id = uuid4()
        old_binding = request.cookies.get(HANDSHAKE_COOKIE)
        try:
            await current.authority.begin_handshake(
                existing_binding_hash=None if old_binding is None else token_hash(old_binding),
                handshake_id=handshake_id,
                state_hash_value=token_hash(state),
                binding_hash=token_hash(binding),
                nonce=nonce,
                code_verifier=verifier,
                return_to=normalized_return,
            )
        except HandshakeInProgress as error:
            raise ApiProblem(409, "INVALID_TRANSITION") from error
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        try:
            location = await current.oidc.authorization_url(
                state=state, nonce=nonce, code_verifier=verifier
            )
        except (OIDCDependencyError, OIDCProtocolError) as error:
            try:
                await current.authority.fail_handshake(handshake_id, reason="authorization_endpoint")
            except AuthorityUnavailable:
                pass
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        response = RedirectResponse(location, status_code=302, headers=NO_STORE)
        response.set_cookie(
            HANDSHAKE_COOKIE,
            binding,
            max_age=300,
            httponly=True,
            secure=current.settings.secure_cookies,
            samesite="lax",
            path="/",
        )
        return response

    @application.get(
        "/api/v1/auth/callback",
        tags=["Authentication"],
        status_code=303,
        response_class=RedirectResponse,
        responses={303: {"description": "Allowed local success or fixed error redirect"}},
        openapi_extra={"security": []},
    )
    async def finish_login(
        request: Request,
        code: str | None = Query(default=None),
        state: str | None = Query(default=None),
        provider_error: str | None = Query(default=None, alias="error"),
    ) -> RedirectResponse:
        current = application.state.runtime
        if current is None:
            return _callback_error(request, "SERVICE_UNAVAILABLE")
        binding = request.cookies.get(HANDSHAKE_COOKIE)
        if (
            state is None
            or binding is None
            or len(state) > 1024
            or len(binding) > 256
            or (code is not None and len(code) > 4096)
            or (provider_error is not None and len(provider_error) > 128)
        ):
            return _callback_error(request, "UNAUTHENTICATED")
        try:
            handshake = await current.authority.claim_handshake(
                state_hash_value=token_hash(state), binding_hash=token_hash(binding)
            )
        except AuthorityUnavailable:
            return _callback_error(request, "SERVICE_UNAVAILABLE")
        if handshake is None:
            return _callback_error(request, "UNAUTHENTICATED")

        error_code: Literal[
            "UNAUTHENTICATED", "FORBIDDEN", "SERVICE_UNAVAILABLE", "INTERNAL_ERROR"
        ] | None = None
        clear_handshake_cookie = True
        created = None
        if provider_error is not None or not code:
            error_code = "UNAUTHENTICATED"
            try:
                clear_handshake_cookie = await current.authority.fail_handshake(
                    handshake.id, reason="provider_or_missing_code"
                )
            except AuthorityUnavailable:
                error_code = "SERVICE_UNAVAILABLE"
                clear_handshake_cookie = False
        else:
            try:
                claims = await current.oidc.exchange(
                    code=code, code_verifier=handshake.code_verifier, nonce=handshake.nonce
                )
                created = await current.authority.complete_login(
                    handshake_id=handshake.id,
                    issuer=claims["iss"],
                    subject=claims["sub"],
                    old_session_token=request.cookies.get(SESSION_COOKIE),
                )
                if created is None:
                    error_code = "FORBIDDEN"
            except HandshakeCompletionInvalid:
                error_code = "UNAUTHENTICATED"
                clear_handshake_cookie = False
            except OIDCDependencyError:
                error_code = "SERVICE_UNAVAILABLE"
                try:
                    clear_handshake_cookie = await current.authority.fail_handshake(
                        handshake.id, reason="provider_dependency"
                    )
                except AuthorityUnavailable:
                    error_code = "SERVICE_UNAVAILABLE"
                    clear_handshake_cookie = False
            except OIDCProtocolError:
                error_code = "UNAUTHENTICATED"
                try:
                    clear_handshake_cookie = await current.authority.fail_handshake(
                        handshake.id, reason="protocol_validation"
                    )
                except AuthorityUnavailable:
                    error_code = "SERVICE_UNAVAILABLE"
                    clear_handshake_cookie = False
            except AuthorityUnavailable:
                error_code = "SERVICE_UNAVAILABLE"
                clear_handshake_cookie = False
            except Exception:
                error_code = "INTERNAL_ERROR"
                clear_handshake_cookie = False

        if error_code is not None:
            response = _callback_error(request, error_code)
            if clear_handshake_cookie:
                _delete_cookie(response, HANDSHAKE_COOKIE, secure=current.settings.secure_cookies)
            return response

        assert created is not None
        response = RedirectResponse(handshake.return_to, status_code=303, headers=NO_STORE)
        _delete_cookie(response, HANDSHAKE_COOKIE, secure=current.settings.secure_cookies)
        response.set_cookie(
            SESSION_COOKIE,
            created.token,
            httponly=True,
            secure=current.settings.secure_cookies,
            samesite="lax",
            path="/",
        )
        return response

    @application.post(
        "/api/v1/auth/logout",
        tags=["Authentication"],
        status_code=204,
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def logout(
        request: Request,
        csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    ) -> Response:
        current = _runtime(request)
        origin = request.headers.get("origin")
        if origin is None or not hmac.compare_digest(origin, current.settings.public_origin):
            raise ApiProblem(403, "FORBIDDEN")
        if not await current.authority.ready():
            raise ApiProblem(503, "SERVICE_UNAVAILABLE")
        raw_token = request.cookies.get(SESSION_COOKIE)
        if raw_token is None:
            raise ApiProblem(401, "UNAUTHENTICATED", clear_session=True)
        if csrf_token is None:
            raise ApiProblem(403, "FORBIDDEN")
        try:
            result = await current.authority.revoke_session(raw_token, csrf_token)
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        if result == "unauthenticated":
            raise ApiProblem(401, "UNAUTHENTICATED", clear_session=True)
        if result == "forbidden":
            raise ApiProblem(403, "FORBIDDEN")
        response = Response(status_code=204, headers=NO_STORE)
        _delete_cookie(response, SESSION_COOKIE, secure=current.settings.secure_cookies)
        return response

    @application.get(
        "/api/v1/session",
        tags=["Session"],
        response_model=SessionResponse,
        responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    async def get_session(request: Request) -> SessionResponse:
        current = _runtime(request)
        session = await _authenticated(request, current)
        return SessionResponse(
            user_id=session.user_id,
            display_name=session.display_name,
            csrf_token=session.csrf_token,
            expires_at=session.expires_at.isoformat(),
            permissions_version=session.permissions_version,
        )

    @application.get(
        "/api/v1/projects",
        tags=["Session"],
        response_model=ProjectPageResponse,
        responses={
            401: {"model": ErrorResponse},
            410: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def list_projects(
        request: Request,
        limit: int = Query(default=50, ge=1, le=100),
        cursor: str | None = Query(default=None, min_length=1, max_length=512),
    ) -> ProjectPageResponse:
        current = _runtime(request)
        session = await _authenticated(request, current)
        position = None
        if cursor is not None:
            try:
                position = current.cursors.decode(
                    cursor,
                    user_id=session.user_id,
                    permissions_version=session.permissions_version,
                    limit=limit,
                )
            except ExpiredCursor as error:
                raise ApiProblem(410, "CURSOR_EXPIRED") from error
            except InvalidCursor as error:
                raise ApiProblem(422, "VALIDATION_FAILED") from error
        try:
            records = await current.authority.list_projects(
                user_id=session.user_id, limit=limit, position=position
            )
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        has_more = len(records) > limit
        visible = records[:limit]
        next_cursor = None
        if has_more:
            last = visible[-1]
            next_cursor = current.cursors.encode(
                user_id=session.user_id,
                permissions_version=session.permissions_version,
                limit=limit,
                position=CursorPosition(created_at=last.created_at, project_id=last.id),
            )
        return ProjectPageResponse(
            items=[_project_response(record) for record in visible], next_cursor=next_cursor
        )

    @application.get(
        "/api/v1/projects/{project_id}",
        tags=["Session"],
        response_model=ProjectResponse,
        responses={
            401: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def get_project(request: Request, project_id: UUID) -> ProjectResponse:
        current = _runtime(request)
        session = await _authenticated(request, current)
        try:
            record = await current.authority.get_project(
                user_id=session.user_id, project_id=project_id
            )
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        if record is None:
            raise ApiProblem(404, "NOT_FOUND")
        return _project_response(record)

    return application


app = create_app()
