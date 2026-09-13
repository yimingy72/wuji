"""Private executor routes; original P06 admission and read/receipt/cancel ports."""

from fastapi import Request
from pydantic import ValidationError
import psycopg
from starlette.concurrency import run_in_threadpool

from wuji_core.admission.remote_workspace import (
    receipt_to_wire, restore_transport_permit,
)
from wuji_core.contracts.generated import (
    ExecutorCancelRequest, ExecutorDispatchRequest, ExecutorPermitCheckRequest,
    ExecutorQueryRequest,
)
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter, canonical_json_bytes
from wuji_core.http.auth import current_principal
from wuji_core.http.model_gate import error_response
from wuji_core.persistence.uow import AccessContext, DomainError


def create_executor_host_router(authority):
    router = VNextAPIRouter()

    @router.post("/internal/v2/executors/{executor_ref}/permits/check")
    async def check(request: Request, executor_ref: str, payload: ExecutorPermitCheckRequest):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            result = await run_in_threadpool(authority.check, access, executor_ref, payload)
            return DecimalJSONResponse(result, headers={"Cache-Control": "no-store"})
        except (DomainError, ValidationError, psycopg.Error, OSError,
                ValueError, TypeError, KeyError, TimeoutError) as error:
            return error_response(request, error)

    return router


def create_workspace_executor_router(executor, *, binding, max_response_bytes=2097152,
                                     max_output_bytes=1048576):
    router = VNextAPIRouter()
    if (type(max_response_bytes) is not int or max_response_bytes < 1
            or type(max_output_bytes) is not int or max_output_bytes < 1
            or executor.receiver_id != binding.receiver_id
            or executor.environment_ref != binding.environment_ref):
        raise ValueError("executor limits and deployment identity must match")

    async def invoke(request, action):
        try:
            binding.require_gate(current_principal(request))
            # Preserve the original complete JSON document, including datetime
            # spelling. Generated DTO validation must not silently drop fields or
            # change +00:00 to Z before checking the frozen permit digest.
            payload = await request.json()
            permit = restore_transport_permit(
                payload["permit"], permit_digest=payload["permit_digest"],
                request_id=request.state.request_id, binding=binding,
            )
            if min(permit.runtime.buffer_bytes,
                   permit.runtime.limits.max_single_output_bytes) > max_output_bytes:
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            if action == "cancel":
                receipt = await executor.cancel(permit, reason=payload["reason"])
            else:
                receipt = await getattr(executor, action)(permit)
            value = receipt_to_wire(permit, receipt, binding=binding,
                                    max_output_bytes=max_output_bytes)
            if len(canonical_json_bytes(value)) > max_response_bytes:
                raise DomainError("LIMIT_BLOCKED", 429)
            return DecimalJSONResponse(value, headers={"Cache-Control": "no-store"})
        except (DomainError, ValidationError, OSError, ValueError,
                TypeError, KeyError, TimeoutError) as error:
            return error_response(request, error)

    @router.post("/internal/v2/executor/dispatch")
    async def dispatch(request: Request, payload: ExecutorDispatchRequest):
        return await invoke(request, "dispatch")

    @router.post("/internal/v2/executor/query")
    async def query(request: Request, payload: ExecutorQueryRequest):
        return await invoke(request, "query")

    @router.post("/internal/v2/executor/cancel")
    async def cancel(request: Request, payload: ExecutorCancelRequest):
        return await invoke(request, "cancel")

    return router
