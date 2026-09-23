"""Controller-only Task process drain/archive/shutdown boundary."""

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field, StrictStr

from wuji_core.execution.process_gate import ProcessToolGate
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import current_principal
from wuji_core.http.model_gate import error_response
from wuji_core.persistence.uow import AccessContext, DomainError


class ProcessCleanupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: StrictStr = Field(min_length=1, max_length=256)
    execution_epoch: StrictStr = Field(pattern=r"^[1-9][0-9]*$")
    runtime_attempt: StrictStr = Field(pattern=r"^[1-9][0-9]*$")
    reason: StrictStr = Field(min_length=1, max_length=1024)


def create_process_cleanup_router(processes):
    if not isinstance(processes, ProcessToolGate):
        raise ValueError("the canonical process gate is required")
    router = VNextAPIRouter()

    @router.post("/internal/v2/process-control/cleanup")
    async def cleanup(request: Request, payload: ProcessCleanupRequest):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            result = await processes.cleanup_task(
                access,
                **payload.model_dump(mode="python"),
            )
            return DecimalJSONResponse(
                result, headers={"Cache-Control": "no-store"}
            )
        except (DomainError, OSError, ValueError, TypeError, TimeoutError) as error:
            return error_response(request, error)

    return router
