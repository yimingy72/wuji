"""One production ToolAdmission path for tool HTTP, function and MCP adapters."""

from typing import Annotated
from fastapi import Header, Request
from pydantic import ValidationError
import psycopg
from starlette.concurrency import run_in_threadpool

from wuji_core.contracts.admission import (
    ToolCallRequest, ToolCancelRequest, ToolSettlementRequest,
)
from wuji_core.http import VNextAPIRouter, DecimalJSONResponse
from wuji_core.http.auth import current_principal
from wuji_core.http.model_gate import error_response
from wuji_core.persistence.uow import AccessContext, DomainError


def create_tool_router(gate):
    router = VNextAPIRouter()

    @router.post("/internal/v2/tool-calls")
    async def invoke(request: Request, payload: ToolCallRequest):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            receipt = await gate.invoke(access, payload)
            return DecimalJSONResponse(receipt.model_dump(mode="python"))
        except (DomainError, ValidationError, psycopg.Error, OSError, ValueError) as error:
            return error_response(request, error)

    @router.post("/internal/v2/tool-settlement")
    async def settlement(request: Request, payload: ToolSettlementRequest):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            receipt = await run_in_threadpool(gate.close_operations, access, payload)
            return DecimalJSONResponse(receipt.model_dump(mode="python"))
        except (DomainError, ValidationError, psycopg.Error, OSError, ValueError) as error:
            return error_response(request, error)

    @router.get("/internal/v2/tool-calls/{tool_call_id}")
    async def receipt(request: Request, tool_call_id: str):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            value = await run_in_threadpool(gate.ledger.tool_call, access, tool_call_id)
            return DecimalJSONResponse(value.model_dump(mode="python"))
        except (DomainError, ValidationError, psycopg.Error, OSError) as error:
            return error_response(request, error)

    @router.get("/internal/v2/tool-calls/{tool_call_id}/material")
    async def material(request: Request, tool_call_id: str, representation: str | None = None):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            value = await run_in_threadpool(
                gate.result_material,
                access,
                tool_call_id,
                representation=representation,
            )
            payload = value.model_dump(mode="python") if hasattr(value, "model_dump") else value
            return DecimalJSONResponse(payload)
        except (DomainError, ValidationError, psycopg.Error, OSError, ValueError) as error:
            return error_response(request, error)

    @router.post("/internal/v2/tool-calls/{tool_call_id}/cancel")
    async def cancel(request: Request, tool_call_id: str, payload: ToolCancelRequest, operation_id: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=256)]):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            value = await gate.cancel(access, tool_call_id, operation_id=operation_id, reason=payload.reason)
            return DecimalJSONResponse(value.model_dump(mode="python"))
        except (DomainError, ValidationError, psycopg.Error, OSError, ValueError) as error:
            return error_response(request, error)

    return router
