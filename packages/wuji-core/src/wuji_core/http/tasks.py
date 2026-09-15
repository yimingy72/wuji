"""Public P11 Task creation route over the canonical TaskService."""

from typing import Annotated

from fastapi import Header, Request
from pydantic import ValidationError
import psycopg

from wuji_core.contracts.execution import TaskCreate, TaskView
from wuji_core.execution.tasks import TaskService
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import current_principal
from wuji_core.http.model_gate import error_response
from wuji_core.persistence.uow import AccessContext, DomainError


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
                checked.model_dump(mode="python"), status_code=201
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
