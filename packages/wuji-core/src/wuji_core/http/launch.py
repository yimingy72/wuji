"""Read-only launch progress route for the application API."""

import psycopg
from fastapi import Request
from pydantic import ValidationError

from wuji_core.contracts.generated import LaunchView
from wuji_core.execution.launch import LaunchService
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import current_principal
from wuji_core.http.model_gate import error_response
from wuji_core.persistence.uow import AccessContext, DomainError


def create_launch_router(launch_service):
    if not isinstance(launch_service, LaunchService):
        raise ValueError("the real LaunchService is required")
    router = VNextAPIRouter()

    @router.get("/api/v2/tasks/{task_id}/launch")
    def read_launch(request: Request, task_id: str):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            view = LaunchView.model_validate(launch_service.read_launch(access, task_id))
            return DecimalJSONResponse(view.model_dump(mode="python"), status_code=200)
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


__all__ = ["create_launch_router"]
