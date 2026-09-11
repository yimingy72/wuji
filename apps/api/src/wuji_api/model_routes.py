"""Tenant model configuration routes; public DTOs omit gateway identities and secrets."""
import hashlib
from uuid import UUID

from fastapi import Header, Query, Request

from wuji_api.database import AuthorityUnavailable, CommandForbidden, CommandValidationFailed, FreshAuthorityInvalid, IdempotencyConflict, InvalidTransition, ResourceNotFound, VersionConflict
from wuji_api.model_config import (ModelCheckRequest, ModelDefinitionPage, ModelDefinitionResponse, ModelOperationResponse,
    ModelVersionCommand, ModelVersionPage, ModelVersionResponse, ProfileVersionRequest, ServiceVersionRequest,
    TenantPage, TenantResponse, public_model)
from wuji_api.model_store import ModelStore
from wuji_api.model_workflow import ModelWorkflow
from wuji_api.security import ExpiredCursor, InvalidCursor, TaskCursorPosition


def register_model_routes(application):
    from wuji_api.main import ApiProblem, ErrorResponse, _authenticated, _command_problem, _require_write, _runtime
    errors = {code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 410, 422, 500, 503)}

    async def context(request):
        runtime = _runtime(request)
        return runtime, await _authenticated(request, runtime)

    async def invoke(awaitable):
        try:
            return await awaitable
        except (CommandForbidden, CommandValidationFailed, FreshAuthorityInvalid, IdempotencyConflict,
                InvalidTransition, ResourceNotFound, VersionConflict) as error:
            raise _command_problem(error) from error
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error

    def pagination(current, session, scope_id, purpose, limit, cursor=None, rows=None):
        endpoint = "mc_" + hashlib.sha256(purpose.encode()).hexdigest()[:24]
        args = dict(user_id=session.user_id, permissions_version=session.permissions_version,
                    project_id=scope_id, endpoint=endpoint, limit=limit)
        if rows is not None:
            if len(rows) <= limit:
                return None
            last = rows[limit - 1]
            return current.cursors.encode_task(**args, position=TaskCursorPosition(last["created_at"], last["id"]))
        if cursor is None:
            return None
        try:
            return current.cursors.decode_task(cursor, **args)
        except ExpiredCursor as error:
            raise ApiProblem(410, "CURSOR_EXPIRED") from error
        except InvalidCursor as error:
            raise ApiProblem(422, "VALIDATION_FAILED") from error

    @application.get("/api/v1/tenants", response_model=TenantPage, responses=errors, tags=["Models"])
    async def tenants(request: Request, limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, max_length=512)):
        current, session = await context(request)
        position = pagination(current, session, UUID(int=0), "tenants", limit, cursor)
        rows = await invoke(ModelStore(current.authority).list_tenants(session.user_id, limit, position))
        return TenantPage(items=[TenantResponse(id=r["id"], name=r["name"], permissions=(
            ["model.config.read", "model.config.write"] if r["is_admin"] else [])) for r in rows[:limit]],
            next_cursor=pagination(current, session, UUID(int=0), "tenants", limit, rows=rows))

    def definitions(kind, request_model):
        segment = "model-services" if kind == "service" else "model-profiles"
        path = "/api/v1/tenants/{tenant_id}/" + segment

        async def read_list(current, session, tenant_id, limit, position, definition_id=None):
            store = ModelStore(current.authority)
            async with store.actor(session.user_id, tenant_id, session.permissions_version) as actor:
                if definition_id is None:
                    return await store.list_definitions(actor, kind, limit, position)
                return await store.list_versions(actor, kind, definition_id, limit, position)

        @application.get(path, response_model=ModelDefinitionPage, responses=errors, tags=["Models"], operation_id=f"list_{kind}_definitions")
        async def list_definitions(request: Request, tenant_id: UUID, limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, max_length=512)):
            current, session = await context(request)
            purpose = f"{kind}:definitions"
            position = pagination(current, session, tenant_id, purpose, limit, cursor)
            rows = await invoke(read_list(current, session, tenant_id, limit, position))
            return ModelDefinitionPage(items=[public_model(ModelDefinitionResponse, r) for r in rows[:limit]],
                next_cursor=pagination(current, session, tenant_id, purpose, limit, rows=rows))

        @application.post(path, response_model=ModelOperationResponse, responses=errors, tags=["Models"], operation_id=f"create_{kind}_definition")
        async def create_definition(request: Request, tenant_id: UUID, body: request_model,
                key: UUID = Header(alias="Idempotency-Key"), csrf: str | None = Header(None, alias="X-CSRF-Token")):
            current, session = await context(request)
            _require_write(request, current, session, csrf)
            row = await invoke(ModelWorkflow(current).save(session, tenant_id, key, kind, body))
            return public_model(ModelOperationResponse, row)

        @application.get(path + "/{definition_id}/versions", response_model=ModelVersionPage, responses=errors, tags=["Models"], operation_id=f"list_{kind}_versions")
        async def versions(request: Request, tenant_id: UUID, definition_id: UUID,
                limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, max_length=512)):
            current, session = await context(request)
            purpose = f"{kind}:versions:{definition_id}"
            position = pagination(current, session, tenant_id, purpose, limit, cursor)
            rows = await invoke(read_list(current, session, tenant_id, limit, position, definition_id))
            return ModelVersionPage(items=[public_model(ModelVersionResponse, r) for r in rows[:limit]],
                next_cursor=pagination(current, session, tenant_id, purpose, limit, rows=rows))

        @application.post(path + "/{definition_id}/versions", response_model=ModelOperationResponse, responses=errors, tags=["Models"], operation_id=f"create_{kind}_version")
        async def create_version(request: Request, tenant_id: UUID, definition_id: UUID, body: request_model,
                key: UUID = Header(alias="Idempotency-Key"), csrf: str | None = Header(None, alias="X-CSRF-Token")):
            current, session = await context(request)
            _require_write(request, current, session, csrf)
            row = await invoke(ModelWorkflow(current).save(session, tenant_id, key, kind, body, definition_id))
            return public_model(ModelOperationResponse, row)

        single = "/api/v1/tenants/{tenant_id}/model-" + kind + "-versions/{version_id}"
        @application.get(single, response_model=ModelVersionResponse, responses=errors, tags=["Models"], operation_id=f"get_{kind}_version")
        async def version(request: Request, tenant_id: UUID, version_id: UUID):
            current, session = await context(request)
            async def read():
                store = ModelStore(current.authority)
                async with store.actor(session.user_id, tenant_id, session.permissions_version) as actor:
                    return await store.get_version(actor, version_id, kind)
            return public_model(ModelVersionResponse, await invoke(read()))

    definitions("service", ServiceVersionRequest)
    definitions("profile", ProfileVersionRequest)

    @application.post("/api/v1/tenants/{tenant_id}/model-profile-versions/{version_id}/checks", response_model=ModelOperationResponse, responses=errors, tags=["Models"])
    async def check_model(request: Request, tenant_id: UUID, version_id: UUID, body: ModelCheckRequest,
            key: UUID = Header(alias="Idempotency-Key"), csrf: str | None = Header(None, alias="X-CSRF-Token")):
        current, session = await context(request)
        _require_write(request, current, session, csrf)
        return public_model(ModelOperationResponse, await invoke(ModelWorkflow(current).action(session, tenant_id, key, version_id, "check")))

    @application.post("/api/v1/tenants/{tenant_id}/model-profile-versions/{version_id}/commands", response_model=ModelOperationResponse, responses=errors, tags=["Models"])
    async def command_model(request: Request, tenant_id: UUID, version_id: UUID, body: ModelVersionCommand,
            key: UUID = Header(alias="Idempotency-Key"), csrf: str | None = Header(None, alias="X-CSRF-Token")):
        current, session = await context(request)
        _require_write(request, current, session, csrf)
        return public_model(ModelOperationResponse, await invoke(ModelWorkflow(current).action(
            session, tenant_id, key, version_id, body.action, body.expected_version)))

    @application.get("/api/v1/tenants/{tenant_id}/model-operations/{operation_id}", response_model=ModelOperationResponse, responses=errors, tags=["Models"])
    async def operation(request: Request, tenant_id: UUID, operation_id: UUID):
        current, session = await context(request)
        return public_model(ModelOperationResponse, await invoke(ModelWorkflow(current).operation(session, tenant_id, operation_id)))

    @application.get("/api/v1/tenants/{tenant_id}/model-operation-keys/{key}", response_model=ModelOperationResponse, responses=errors, tags=["Models"])
    async def operation_key(request: Request, tenant_id: UUID, key: UUID):
        current, session = await context(request)
        async def read():
            store = ModelStore(current.authority)
            async with store.actor(session.user_id, tenant_id, session.permissions_version) as actor:
                return await store.get_operation_by_key(actor, key)
        return public_model(ModelOperationResponse, await invoke(read()))

    @application.get("/api/v1/projects/{project_id}/model-profiles", response_model=ModelVersionPage, responses=errors, tags=["Models"])
    async def project_models(request: Request, project_id: UUID, limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, max_length=512)):
        current, session = await context(request)
        position = pagination(current, session, project_id, "project-models", limit, cursor)
        rows = await invoke(ModelStore(current.authority).project_profiles(session.user_id, project_id, limit, position))
        return ModelVersionPage(items=[public_model(ModelVersionResponse, r) for r in rows[:limit]],
            next_cursor=pagination(current, session, project_id, "project-models", limit, rows=rows))
