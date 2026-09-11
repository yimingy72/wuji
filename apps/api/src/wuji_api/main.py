"""Phase 1B Platform API with identity, scopes, tasks, and event replay."""

from __future__ import annotations

import hmac
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit
from typing import Final, Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from wuji_api.database import (
    AuthorityUnavailable,
    CommandForbidden,
    CommandValidationFailed,
    DatabaseAuthority,
    FreshAuthorityInvalid,
    HandshakeCompletionInvalid,
    HandshakeInProgress,
    IdempotencyConflict,
    InvalidTransition,
    PreviewExpired,
    PreviewForbidden,
    ResourceNotFound,
    ScopeDenied,
    VersionConflict,
)
from wuji_api.model_gateway import ModelGateway
from wuji_api.task_creation import NewCreateTaskRequest, CreationBlocked
from wuji_api.task_creation_store import CreationStore
from wuji_api.execution_store import ExecutionStore
from wuji_api.oidc import OIDCClient, OIDCDependencyError, OIDCProtocolError
from wuji_api.scope_policy import ScopePolicyError, normalize_task_draft
from wuji_api.scopes import (
    ApprovedScopeResponse,
    ScopePageResponse,
    TaskDraftRequest,
    TaskPreviewResponse,
)
from wuji_api.security import (
    CursorCodec,
    CursorPosition,
    EventCursorPosition,
    ExpiredCursor,
    InvalidCursor,
    InvalidReturnPath,
    ScopeCursorPosition,
    TaskCursorPosition,
    normalize_return_path,
    opaque_token,
    token_hash,
)
from wuji_api.settings import Settings, optional_settings
from wuji_api.tasks import (
    CommandReceiptResponse,
    CreateTaskRequest,
    EventPageResponse,
    TaskControlRequest,
    TaskEventResponse,
    TaskPageResponse,
    TaskResponse,
    WebTaskResponse,
    TaskSnapshotResponse,
    command_request_digest,
)

ReadinessProbe = Callable[[], Awaitable[bool]]
NO_STORE: Final = {"Cache-Control": "no-store"}
SESSION_COOKIE = "wuji_session"
HANDSHAKE_COOKIE = "wuji_oidc_handshake"
ERROR_MESSAGES = {
    "UNAUTHENTICATED": "登录状态无效，请重新登录",
    "FORBIDDEN": "当前身份无权执行此操作",
    "NOT_FOUND": "请求的资源不存在",
    "VALIDATION_FAILED": "请求参数无效",
    "SCOPE_DENIED": "当前批准范围不允许创建该任务",
    "PREVIEW_EXPIRED": "任务预览已过期，请重新预览",
    "VERSION_CONFLICT": "资源版本已变化，请重新加载",
    "IDEMPOTENCY_CONFLICT": "幂等键已绑定到不同请求",
    "INVALID_TRANSITION": "当前任务状态不允许该操作",
    "CREATION_BLOCKED": "创建条件已变化，请重新预览",
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
    model_gateway: ModelGateway | None = None

    async def close(self) -> None:
        await self.authority.close()
        if self.model_gateway is not None:
            await self.model_gateway.close()


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
        model_gateway=(ModelGateway(settings.model_gateway_url, settings.model_gateway_key.get_secret_value(), settings.model_gateway_instance_id)
                       if settings.model_gateway_url else None),
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
    permissions = ["project.read", "task.draft.read", "model.profile.read"]
    if record.role == "operator":
        permissions.extend(("task.preview", "task.read", "task.create", "task.control", "task.draft.write"))
    else:
        permissions.append("task.read")
    return ProjectResponse(
        id=record.id,
        tenant_id=record.tenant_id,
        name=record.name,
        permissions=permissions,
    )


def _scope_response(record) -> ApprovedScopeResponse:
    return ApprovedScopeResponse.model_validate(
        {
            "binding": {"policy_id": record.policy_id, "version": record.version},
            "label": record.scope["label"],
            "valid_until": record.valid_until,
            "origins": record.scope["origins"],
            "allowed_path_prefixes": record.scope["allowed_path_prefixes"],
            "excluded_path_prefixes": record.scope["excluded_path_prefixes"],
            "allowed_methods": record.scope["allowed_methods"],
            "limits": record.scope["limits"],
        }
    )


def _task_response(record: dict, *, can_control: bool) -> TaskResponse | WebTaskResponse:
    state = record["state"]
    draft = record["draft"]
    if record.get("task_kind") == "web_assessment":
        config = record["creation_config"]
        blockers=[]
        service=record.get("core_service_config")
        if state=="ready":
            if not service or service.get("ready") is not True: blockers.append("执行控制尚未就绪")
            else:
                if service.get("model_profile_version_id")!=config["model"]["id"]:blockers.append("当前环境仅支持登记的合成模型")
                parsed=urlsplit(config["actual_input"]["entry_url"])
                if parsed.scheme+"://"+parsed.netloc not in service.get("fixture_origins",[]):blockers.append("当前环境仅支持登记的测试夹具")
            if not record.get("current_model_usable"):blockers.append("模型方案已不可用")
            if datetime.fromisoformat(config["authorization"]["valid_until"].replace("Z","+00:00"))<=datetime.now(timezone.utc):
                blockers.append("授权已过期")
        actions=["cancel"] if can_control and state not in {"cancelled","completed","cancelling"} else []
        if can_control and state=="ready" and not blockers:actions.insert(0,"start")
        return WebTaskResponse.model_validate({
            "task_kind":"web_assessment", "id":record["id"], "tenant_id":record["tenant_id"],
            "project_id":record["project_id"],"name":draft["name"],
            "target_url":draft.get("entry_url") or draft.get("target_url"),
            "scope":{"authorization_id":record["task_authorization_id"],"version":1,
                     "hash":config["authorization_digest"]},
            "version":record["version"],"state":state,"cleanup_state":record["cleanup_state"],
            "execution":{"active_calls":record["active_calls"],"unknown_calls":record["unknown_calls"],
                         "egress_state":record["egress_state"]},
            "allowed_actions":actions,
            "assessment_outcome":record["assessment_outcome"],"stop_reason":record["stop_reason"],
            "creation_config":config,"start_blockers":blockers,
            "created_at":record["created_at"],"updated_at":record["updated_at"],
        })
    return TaskResponse.model_validate(
        {
            "id": record["id"],
            "tenant_id": record["tenant_id"],
            "project_id": record["project_id"],
            "name": draft["name"],
            "target_url": draft["target_url"],
            "scope": {
                "policy_id": record["policy_id"],
                "version": record["policy_version"],
            },
            "version": record["version"],
            "state": state,
            "cleanup_state": record["cleanup_state"],
            "execution": {
                "active_calls": record["active_calls"],
                "unknown_calls": record["unknown_calls"],
                "egress_state": record["egress_state"],
            },
            "allowed_actions": ["cancel"] if can_control and state == "queued" else [],
            "assessment_outcome": record["assessment_outcome"],
            "stop_reason": record["stop_reason"],
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }
    )


def _require_write(request: Request, runtime: Runtime, session, csrf_token: str | None) -> None:
    origin = request.headers.get("origin")
    if (
        origin is None
        or not hmac.compare_digest(origin, runtime.settings.public_origin)
        or csrf_token is None
        or not hmac.compare_digest(csrf_token, session.csrf_token)
    ):
        raise ApiProblem(403, "FORBIDDEN")


def _command_problem(error: Exception) -> ApiProblem:
    if isinstance(error, AuthorityUnavailable):
        return ApiProblem(503, "SERVICE_UNAVAILABLE")
    if isinstance(error, FreshAuthorityInvalid):
        return ApiProblem(401, "UNAUTHENTICATED", clear_session=True)
    if isinstance(error, CommandForbidden):
        return ApiProblem(403, "FORBIDDEN")
    if isinstance(error, ResourceNotFound):
        return ApiProblem(404, "NOT_FOUND")
    if isinstance(error, ScopeDenied):
        return ApiProblem(403, "SCOPE_DENIED")
    if isinstance(error, PreviewExpired):
        return ApiProblem(409, "PREVIEW_EXPIRED")
    if isinstance(error, VersionConflict):
        return ApiProblem(409, "VERSION_CONFLICT")
    if isinstance(error, IdempotencyConflict):
        return ApiProblem(409, "IDEMPOTENCY_CONFLICT")
    if isinstance(error, InvalidTransition):
        return ApiProblem(409, "INVALID_TRANSITION")
    if isinstance(error, CommandValidationFailed):
        return ApiProblem(422, "VALIDATION_FAILED")
    return ApiProblem(500, "INTERNAL_ERROR")


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

    application = FastAPI(title="Wuji Platform API", version="0.5.0", lifespan=lifespan)
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

    @application.get(
        "/api/v1/projects/{project_id}/scopes",
        tags=["Scopes"],
        response_model=ScopePageResponse,
        responses={
            401: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            410: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def list_approved_scopes(
        request: Request,
        project_id: UUID,
        limit: int = Query(default=50, ge=1, le=100),
        cursor: str | None = Query(default=None, min_length=1, max_length=512),
    ) -> ScopePageResponse:
        current = _runtime(request)
        session = await _authenticated(request, current)
        try:
            project = await current.authority.get_project(
                user_id=session.user_id, project_id=project_id
            )
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        if project is None:
            raise ApiProblem(404, "NOT_FOUND")
        position = None
        if cursor is not None:
            try:
                position = current.cursors.decode_scope(
                    cursor,
                    user_id=session.user_id,
                    permissions_version=session.permissions_version,
                    project_id=project_id,
                    limit=limit,
                )
            except ExpiredCursor as error:
                raise ApiProblem(410, "CURSOR_EXPIRED") from error
            except InvalidCursor as error:
                raise ApiProblem(422, "VALIDATION_FAILED") from error
        try:
            records = await current.authority.list_scopes(
                user_id=session.user_id,
                project=project,
                limit=limit,
                position=position,
            )
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        if records is None:
            raise ApiProblem(404, "NOT_FOUND")
        has_more = len(records) > limit
        visible = records[:limit]
        next_cursor = None
        if has_more:
            last = visible[-1]
            next_cursor = current.cursors.encode_scope(
                user_id=session.user_id,
                permissions_version=session.permissions_version,
                project_id=project_id,
                limit=limit,
                position=ScopeCursorPosition(
                    created_at=last.created_at,
                    policy_id=last.policy_id,
                    version=last.version,
                ),
            )
        return ScopePageResponse(
            items=[_scope_response(record) for record in visible], next_cursor=next_cursor
        )

    @application.post(
        "/api/v1/projects/{project_id}/task-previews",
        tags=["Scopes"],
        response_model=TaskPreviewResponse,
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def preview_task(
        request: Request,
        project_id: UUID,
        draft: TaskDraftRequest,
        csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    ) -> TaskPreviewResponse:
        current = _runtime(request)
        session = await _authenticated(request, current)
        _require_write(request, current, session, csrf_token)
        try:
            project = await current.authority.get_project(
                user_id=session.user_id, project_id=project_id
            )
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        if project is None:
            raise ApiProblem(404, "NOT_FOUND")
        if project.role != "operator":
            raise ApiProblem(403, "FORBIDDEN")
        try:
            normalized = normalize_task_draft(draft.model_dump(mode="json"))
        except ScopePolicyError as error:
            raise ApiProblem(422, "VALIDATION_FAILED") from error
        try:
            preview = await current.authority.create_task_preview(
                user_id=session.user_id,
                permissions_version=session.permissions_version,
                project_id=project_id,
                normalized_draft=normalized,
            )
        except PreviewForbidden as error:
            raise ApiProblem(403, "FORBIDDEN") from error
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        if preview is None:
            raise ApiProblem(404, "NOT_FOUND")
        return TaskPreviewResponse.model_validate(preview)

    @application.get(
        "/api/v1/projects/{project_id}/tasks",
        tags=["Tasks"],
        response_model=TaskPageResponse,
        responses={
            401: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            410: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def list_tasks(
        request: Request,
        project_id: UUID,
        limit: int = Query(default=50, ge=1, le=100),
        cursor: str | None = Query(default=None, min_length=1, max_length=512),
    ) -> TaskPageResponse:
        current = _runtime(request)
        session = await _authenticated(request, current)
        position = None
        if cursor is not None:
            try:
                position = current.cursors.decode_task(
                    cursor,
                    user_id=session.user_id,
                    permissions_version=session.permissions_version,
                    project_id=project_id,
                    limit=limit,
                )
            except ExpiredCursor as error:
                raise ApiProblem(410, "CURSOR_EXPIRED") from error
            except InvalidCursor as error:
                raise ApiProblem(422, "VALIDATION_FAILED") from error
        try:
            result = await current.authority.list_tasks(
                user_id=session.user_id,
                project_id=project_id,
                limit=limit,
                position=position,
            )
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        if result is None:
            raise ApiProblem(404, "NOT_FOUND")
        project, records = result
        has_more = len(records) > limit
        visible = records[:limit]
        next_cursor = None
        if has_more:
            last = visible[-1]
            next_cursor = current.cursors.encode_task(
                user_id=session.user_id,
                permissions_version=session.permissions_version,
                project_id=project_id,
                limit=limit,
                position=TaskCursorPosition(created_at=last["created_at"], task_id=last["id"]),
            )
        return TaskPageResponse(
            items=[
                _task_response(record, can_control=project.role == "operator")
                for record in visible
            ],
            next_cursor=next_cursor,
        )

    @application.post(
        "/api/v1/projects/{project_id}/tasks",
        tags=["Tasks"],
        response_model=CommandReceiptResponse,
        status_code=202,
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def create_task(
        request: Request,
        project_id: UUID,
        command: CreateTaskRequest | NewCreateTaskRequest,
        idempotency_key: UUID = Header(alias="Idempotency-Key"),
        csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    ) -> CommandReceiptResponse:
        current = _runtime(request)
        session = await _authenticated(request, current)
        _require_write(request, current, session, csrf_token)
        if isinstance(command, NewCreateTaskRequest):
            try:
                receipt = await CreationStore(current.authority).create_command(
                    user_id=session.user_id, permissions_version=session.permissions_version,
                    project_id=project_id, idempotency_key=idempotency_key, body=command,
                    request_digest=command_request_digest(kind="create", project_id=project_id,
                        task_id=None, request=command.model_dump(mode="json")),
                    trace_id=request.state.trace_id,
                )
            except CreationBlocked as error:
                raise ApiProblem(409, "CREATION_BLOCKED") from error
            except (CommandForbidden, CommandValidationFailed, FreshAuthorityInvalid,
                    IdempotencyConflict, PreviewExpired, ResourceNotFound, ScopeDenied,
                    VersionConflict, AuthorityUnavailable) as error:
                raise _command_problem(error) from error
            return CommandReceiptResponse.model_validate(receipt)
        try:
            normalized_draft = normalize_task_draft(command.draft.model_dump(mode="json"))
        except ScopePolicyError as error:
            raise ApiProblem(422, "VALIDATION_FAILED") from error
        request_payload = {
            "draft": normalized_draft,
            "input_digest": command.input_digest,
            "preview_id": str(command.preview_id),
        }
        digest = command_request_digest(
            kind="create", project_id=project_id, task_id=None, request=request_payload
        )
        try:
            receipt = await current.authority.create_task_command(
                user_id=session.user_id,
                permissions_version=session.permissions_version,
                project_id=project_id,
                idempotency_key=idempotency_key,
                preview_id=command.preview_id,
                supplied_input_digest=command.input_digest,
                normalized_draft=normalized_draft,
                request_digest=digest,
                trace_id=request.state.trace_id,
            )
        except (
            CommandForbidden,
            CommandValidationFailed,
            FreshAuthorityInvalid,
            IdempotencyConflict,
            PreviewExpired,
            ResourceNotFound,
            ScopeDenied,
            VersionConflict,
        ) as error:
            raise _command_problem(error) from error
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        return CommandReceiptResponse.model_validate(receipt)

    @application.get(
        "/api/v1/projects/{project_id}/tasks/{task_id}",
        tags=["Tasks"],
        response_model=TaskSnapshotResponse,
        responses={
            401: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def get_task(
        request: Request, project_id: UUID, task_id: UUID
    ) -> TaskSnapshotResponse:
        current = _runtime(request)
        session = await _authenticated(request, current)
        try:
            result = await current.authority.get_task_snapshot(
                user_id=session.user_id, project_id=project_id, task_id=task_id
            )
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        if result is None:
            raise ApiProblem(404, "NOT_FOUND")
        project, record = result
        return TaskSnapshotResponse(
            task=_task_response(record, can_control=project.role == "operator"),
            event_cursor=current.cursors.encode_event(
                user_id=session.user_id,
                permissions_version=session.permissions_version,
                project_id=project_id,
                task_id=task_id,
                position=EventCursorPosition(sequence=record["event_sequence"]),
            ),
        )

    @application.post(
        "/api/v1/projects/{project_id}/tasks/{task_id}/commands",
        tags=["Tasks"],
        response_model=CommandReceiptResponse,
        status_code=202,
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def control_task(
        request: Request,
        project_id: UUID,
        task_id: UUID,
        command: TaskControlRequest,
        idempotency_key: UUID = Header(alias="Idempotency-Key"),
        csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    ) -> CommandReceiptResponse:
        current = _runtime(request)
        session = await _authenticated(request, current)
        _require_write(request, current, session, csrf_token)
        request_payload = command.model_dump(mode="json")
        digest = command_request_digest(
            kind=command.action,
            project_id=project_id,
            task_id=task_id,
            request=request_payload,
        )
        try:
            if command.action == "start":
                receipt = await ExecutionStore(current.authority).start_command(
                    user_id=session.user_id, permissions_version=session.permissions_version,
                    project_id=project_id,task_id=task_id,idempotency_key=idempotency_key,
                    expected_version=command.expected_version,request_digest=digest,
                    trace_id=request.state.trace_id,
                )
            else:
                receipt = await current.authority.control_task_command(
                user_id=session.user_id,
                permissions_version=session.permissions_version,
                project_id=project_id,
                task_id=task_id,
                idempotency_key=idempotency_key,
                action=command.action,
                expected_version=command.expected_version,
                request_digest=digest,
                trace_id=request.state.trace_id,
            )
        except (
            CommandForbidden,
            FreshAuthorityInvalid,
            IdempotencyConflict,
            InvalidTransition,
            ResourceNotFound,
            VersionConflict,
        ) as error:
            raise _command_problem(error) from error
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        return CommandReceiptResponse.model_validate(receipt)

    async def _read_receipt(
        request: Request,
        project_id: UUID,
        *,
        command_id: UUID | None = None,
        idempotency_key: UUID | None = None,
    ) -> CommandReceiptResponse:
        current = _runtime(request)
        session = await _authenticated(request, current)
        try:
            receipt = await current.authority.get_command_receipt(
                user_id=session.user_id,
                project_id=project_id,
                command_id=command_id,
                idempotency_key=idempotency_key,
            )
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        if receipt is None:
            raise ApiProblem(404, "NOT_FOUND")
        return CommandReceiptResponse.model_validate(receipt)

    @application.get(
        "/api/v1/projects/{project_id}/commands/{command_id}",
        tags=["Tasks"],
        response_model=CommandReceiptResponse,
        responses={
            401: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def get_command(
        request: Request, project_id: UUID, command_id: UUID
    ) -> CommandReceiptResponse:
        return await _read_receipt(request, project_id, command_id=command_id)

    @application.get(
        "/api/v1/projects/{project_id}/command-keys/{idempotency_key}",
        tags=["Tasks"],
        response_model=CommandReceiptResponse,
        responses={
            401: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def find_command_by_key(
        request: Request, project_id: UUID, idempotency_key: UUID
    ) -> CommandReceiptResponse:
        return await _read_receipt(request, project_id, idempotency_key=idempotency_key)

    @application.get(
        "/api/v1/projects/{project_id}/tasks/{task_id}/events",
        tags=["Tasks"],
        response_model=EventPageResponse,
        responses={
            401: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            410: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def list_task_events(
        request: Request,
        project_id: UUID,
        task_id: UUID,
        after: str | None = Query(default=None, min_length=1, max_length=512),
        limit: int = Query(default=50, ge=1, le=100),
    ) -> EventPageResponse:
        current = _runtime(request)
        session = await _authenticated(request, current)
        position = EventCursorPosition(sequence=0)
        if after is not None:
            try:
                position = current.cursors.decode_event(
                    after,
                    user_id=session.user_id,
                    permissions_version=session.permissions_version,
                    project_id=project_id,
                    task_id=task_id,
                )
            except ExpiredCursor as error:
                raise ApiProblem(410, "CURSOR_EXPIRED") from error
            except InvalidCursor as error:
                raise ApiProblem(422, "VALIDATION_FAILED") from error
        try:
            records = await current.authority.list_task_events(
                user_id=session.user_id,
                project_id=project_id,
                task_id=task_id,
                after_sequence=position.sequence,
                limit=limit,
            )
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        if records is None:
            raise ApiProblem(404, "NOT_FOUND")
        has_more = len(records) > limit
        visible = records[:limit]
        next_position = position if not visible else EventCursorPosition(sequence=visible[-1]["sequence"])
        next_cursor = after if not visible and after is not None else current.cursors.encode_event(
            user_id=session.user_id,
            permissions_version=session.permissions_version,
            project_id=project_id,
            task_id=task_id,
            position=next_position,
        )
        items = [
            TaskEventResponse.model_validate(
                {
                    "schema_version": "1.0",
                    "event_id": record["event_id"],
                    "cursor": current.cursors.encode_event(
                        user_id=session.user_id,
                        permissions_version=session.permissions_version,
                        project_id=project_id,
                        task_id=task_id,
                        position=EventCursorPosition(sequence=record["sequence"]),
                    ),
                    "tenant_id": record["tenant_id"],
                    "project_id": record["project_id"],
                    "task_id": record["task_id"],
                    "aggregate_version": record["aggregate_version"],
                    "type": record["event_type"],
                    "occurred_at": record["occurred_at"],
                    "trace_id": record["trace_id"],
                    "summary": record["summary"],
                }
            )
            for record in visible
        ]
        return EventPageResponse(items=items, next_cursor=next_cursor, has_more=has_more)

    from wuji_api.draft_routes import register_draft_routes
    register_draft_routes(application)
    from wuji_api.model_routes import register_model_routes
    register_model_routes(application)
    from wuji_api.task_creation_routes import register_creation_routes
    register_creation_routes(application)
    from wuji_api.execution_routes import register_execution_routes
    register_execution_routes(application)
    from wuji_api.artifact_routes import register_artifact_routes
    register_artifact_routes(application)

    return application


app = create_app()
