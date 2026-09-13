"""Public P11 Task and Work command routes over the canonical ControlService."""

from typing import Annotated

from fastapi import Header, Path, Request
from pydantic import ValidationError
import psycopg
from starlette.concurrency import run_in_threadpool

from wuji_core.contracts.execution import CommandReceipt, TaskCommand, WorkCommand
from wuji_core.execution.control_api import ControlAPI
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import current_principal
from wuji_core.http.model_gate import error_response
from wuji_core.persistence.uow import AccessContext, DomainError


IdempotencyKey = Annotated[
    str, Header(alias="Idempotency-Key", min_length=1, max_length=256)
]
ResourceId = Annotated[str, Path(min_length=1, max_length=256)]


def create_command_router(control_api):
    if not isinstance(control_api, ControlAPI):
        raise ValueError("the real ControlService HTTP adapter is required")
    router = VNextAPIRouter()

    async def execute(request, action, resource_id, payload, idempotency_key):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            receipt = await run_in_threadpool(
                action,
                access,
                resource_id,
                payload,
                idempotency_key=idempotency_key,
            )
            checked = CommandReceipt.model_validate(
                receipt.model_dump(mode="python")
            )
            return DecimalJSONResponse(
                checked.model_dump(mode="python"), status_code=202
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

    @router.post("/api/v2/tasks/{task_id}/commands")
    async def command_task(
        request: Request,
        task_id: ResourceId,
        payload: TaskCommand,
        idempotency_key: IdempotencyKey,
    ):
        return await execute(
            request,
            control_api.command_task,
            task_id,
            payload,
            idempotency_key,
        )

    @router.post("/api/v2/work-items/{work_item_id}/commands")
    async def command_work(
        request: Request,
        work_item_id: ResourceId,
        payload: WorkCommand,
        idempotency_key: IdempotencyKey,
    ):
        return await execute(
            request,
            control_api.command_work,
            work_item_id,
            payload,
            idempotency_key,
        )

    return router
