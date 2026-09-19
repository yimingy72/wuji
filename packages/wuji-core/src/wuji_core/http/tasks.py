"""Public P11 Task creation route over the canonical TaskService."""

from typing import Annotated

from fastapi import Header, Query, Request
from pydantic import ValidationError
import psycopg

from wuji_core.contracts.execution import TaskCreate, TaskView
from wuji_core.execution.tasks import TaskService
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import current_principal
from wuji_core.http.model_gate import error_response
from wuji_core.persistence.uow import AccessContext, DomainError
from wuji_core.projection.records import public_value


IdempotencyKey = Annotated[
    str, Header(alias="Idempotency-Key", min_length=1, max_length=256)
]


def create_task_router(tasks):
    if not isinstance(tasks, TaskService):
        raise ValueError("the real TaskService is required")
    router = VNextAPIRouter()

    @router.post("/api/v2/tasks")
    def create_task(
        request: Request,
        payload: TaskCreate,
        idempotency_key: IdempotencyKey,
    ):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            view = tasks.create(access, payload, idempotency_key=idempotency_key)
            checked = TaskView.model_validate(view.model_dump(mode="python"))
            return DecimalJSONResponse(
                public_value(checked), status_code=201
            )
        except (
            DomainError,
            ValidationError,
            psycopg.Error,
            OSError,
            ValueError,
            TimeoutError,
        ) as error:
            return error_response(request, error)

    @router.get("/api/v2/tasks")
    def list_tasks(
        request: Request,
        project_id: str = Query(..., min_length=1, max_length=256),
        limit: int = Query(20, ge=1, le=100),
        cursor: str | None = Query(None, min_length=1, max_length=4096),
    ):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            result = tasks.list(
                access, project_id=project_id, limit=limit, cursor=cursor
            )
            return DecimalJSONResponse(public_value(result), status_code=200)
        except (
            DomainError,
            ValidationError,
            psycopg.Error,
            OSError,
            ValueError,
            TimeoutError,
        ) as error:
            return error_response(request, error)

    @router.get("/api/v2/projects/{project_id}/task-options")
    def task_options(request: Request, project_id: str):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            return DecimalJSONResponse(
                public_value(tasks.options(access, project_id)),
                status_code=200,
            )
        except (
            DomainError,
            ValidationError,
            psycopg.Error,
            OSError,
            ValueError,
            TimeoutError,
        ) as error:
            return error_response(request, error)

    @router.get("/api/v2/tasks/{task_id}")
    def get_task(request: Request, task_id: str):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            view = tasks.get(access, task_id)
            return DecimalJSONResponse(public_value(view), status_code=200)
        except (
            DomainError,
            ValidationError,
            psycopg.Error,
            OSError,
            ValueError,
            TimeoutError,
        ) as error:
            return error_response(request, error)

    @router.get("/api/v2/tasks/{task_id}/readiness")
    def task_readiness(request: Request, task_id: str):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            return DecimalJSONResponse(
                public_value(tasks.readiness(access, task_id)),
                status_code=200,
            )
        except (
            DomainError,
            ValidationError,
            psycopg.Error,
            OSError,
            ValueError,
            TimeoutError,
        ) as error:
            return error_response(request, error)

    return router
