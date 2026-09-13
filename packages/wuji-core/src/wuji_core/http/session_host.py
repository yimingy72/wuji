"""Private generated Session routes for the authenticated hosted Worker."""

from fastapi import Request
from pydantic import ValidationError
import psycopg
from starlette.concurrency import run_in_threadpool

from wuji_core.contracts.generated import (
    WorkerAcknowledgeDeliveryRequest,
    WorkerLoadDeliveryRequest,
    WorkerLoadSessionRequest,
    WorkerPublishSessionRequest,
    WorkerRegisterInputRequest,
    WorkerStageSessionRequest,
)
from wuji_core.execution.session_bridge import transport_document
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import current_principal
from wuji_core.http.model_gate import error_response
from wuji_core.persistence.uow import AccessContext, DomainError


def create_session_host_router(bridge):
    router = VNextAPIRouter()

    async def invoke(request, method, payload):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            result = await run_in_threadpool(method, access, payload)
            return DecimalJSONResponse(
                transport_document(result), headers={"Cache-Control": "no-store"}
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

    @router.post("/internal/v2/worker-host/stage-session")
    async def stage_session(request: Request, payload: WorkerStageSessionRequest):
        return await invoke(request, bridge.stage_session, payload)

    @router.post("/internal/v2/worker-host/publish-session")
    async def publish_session(request: Request, payload: WorkerPublishSessionRequest):
        return await invoke(request, bridge.publish_session, payload)

    @router.post("/internal/v2/worker-host/load-session")
    async def load_session(request: Request, payload: WorkerLoadSessionRequest):
        return await invoke(request, bridge.load_session, payload)

    @router.post("/internal/v2/worker-host/register-input")
    async def register_input(request: Request, payload: WorkerRegisterInputRequest):
        return await invoke(request, bridge.register_input, payload)

    @router.post("/internal/v2/worker-host/load-delivery")
    async def load_delivery(request: Request, payload: WorkerLoadDeliveryRequest):
        return await invoke(request, bridge.load_delivery, payload)

    @router.post("/internal/v2/worker-host/acknowledge-delivery")
    async def acknowledge_delivery(
        request: Request, payload: WorkerAcknowledgeDeliveryRequest
    ):
        return await invoke(request, bridge.acknowledge_delivery, payload)

    return router
