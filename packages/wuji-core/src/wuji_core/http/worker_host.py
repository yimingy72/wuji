"""Private authenticated Host routes over existing generated v2 contracts."""

from fastapi import Request
from pydantic import ValidationError
import psycopg
from starlette.concurrency import run_in_threadpool

from wuji_core.contracts.generated import (
    ReceiverBridgeRequest, WorkerArchiveRequest, WorkerBridgeRequest, WorkerSubmitRequest,
)
from wuji_core.execution.worker_bridge import document
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import current_principal
from wuji_core.http.model_gate import error_response
from wuji_core.persistence.uow import AccessContext, DomainError


def create_worker_host_router(bridge):
    router = VNextAPIRouter()

    async def invoke(request, method, payload, *, exclude_unset=False):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            result = await run_in_threadpool(method, access, payload)
            if exclude_unset and hasattr(result, "model_dump"):
                result = result.model_dump(mode="python", exclude_unset=True)
            return DecimalJSONResponse(document(result), headers={"Cache-Control": "no-store"})
        except (DomainError, ValidationError, psycopg.Error, OSError, ValueError, TimeoutError) as error:
            return error_response(request, error)

    @router.post("/internal/v2/worker-host/await-start")
    async def await_start(request: Request, payload: WorkerBridgeRequest):
        return await invoke(request, bridge.await_start, payload.assignment)

    @router.post("/internal/v2/worker-host/resolve")
    async def resolve(request: Request, payload: WorkerBridgeRequest):
        return await invoke(
            request,
            bridge.resolve,
            payload.assignment,
            exclude_unset=True,
        )

    @router.post("/internal/v2/worker-host/archive-sdk")
    async def archive(request: Request, payload: WorkerArchiveRequest):
        return await invoke(request, bridge.archive_sdk, payload)

    @router.post("/internal/v2/worker-host/submit-result")
    async def submit(request: Request, payload: WorkerSubmitRequest):
        return await invoke(request, bridge.submit_result, payload)

    @router.post("/internal/v2/worker-host/replay")
    async def replay(request: Request, payload: WorkerSubmitRequest):
        return await invoke(request, bridge.replay, payload)

    @router.post("/internal/v2/worker-host/receiver-authorize")
    async def authorize(request: Request, payload: ReceiverBridgeRequest):
        return await invoke(request, bridge.receiver_authorize, payload)

    @router.post("/internal/v2/worker-host/receiver-bootstrap")
    async def bootstrap(request: Request, payload: WorkerBridgeRequest):
        return await invoke(request, bridge.receiver_bootstrap, payload.assignment)

    @router.post("/internal/v2/worker-host/receiver-replay")
    async def receiver_replay(request: Request, payload: WorkerSubmitRequest):
        return await invoke(request, bridge.receiver_replay, payload)

    @router.post("/internal/v2/worker-host/receiver-archive")
    async def receiver_archive(request: Request, payload: WorkerArchiveRequest):
        return await invoke(request, bridge.receiver_archive, payload)

    return router
