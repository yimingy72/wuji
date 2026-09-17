"""Production model Gate routes, using the P02 precise JSON boundary."""

from typing import Annotated

from fastapi import Header, Request
from pydantic import ValidationError
import psycopg
from starlette.concurrency import run_in_threadpool

from wuji_core.http import VNextAPIRouter, DecimalJSONResponse
from wuji_core.http.auth import current_principal
from wuji_core.contracts.execution import ChatCompletionRequest
from wuji_core.contracts.envelopes import ErrorResponse
from wuji_core.persistence.uow import AccessContext, DomainError


# Governance services name their refusals for logs and tests; the public
# envelope only ever carries the frozen ErrorCode enum, so an unmapped internal
# code would turn an honest refusal into a 500.
PUBLIC_CODES = {
    "completion_precheck_incomplete": "COMPLETION_PRECHECK_INCOMPLETE",
    "completion_epoch_absent": "COMPLETION_EPOCH_ABSENT",
    "completion_epoch_unsettled": "COMPLETION_EPOCH_UNSETTLED",
    "completion_not_closed": "COMPLETION_NOT_CLOSED",
    "delivery_exchange_required": "DELIVERY_EXCHANGE_REQUIRED",
    "delivery_too_large": "DELIVERY_TOO_LARGE",
    "delivery_commit_corrupt": "DELIVERY_COMMIT_CORRUPT",
}


def error_response(request, error):
    code = error.code if isinstance(error, DomainError) else "CAPABILITY_UNAVAILABLE"
    code = PUBLIC_CODES.get(code, code)
    status = error.status if isinstance(error, DomainError) else 503
    result = ErrorResponse.model_validate({"code": code, "message": "The request could not be completed.", "request_id": request.state.request_id, "retryable": False, "details": getattr(error, "details", {})})
    return DecimalJSONResponse(result.model_dump(mode="python"), status_code=status)


def create_model_router(gate):
    router = VNextAPIRouter()

    @router.post("/internal/v2/model/chat/completions")
    async def complete(request: Request, payload: ChatCompletionRequest, request_id: Annotated[str, Header(alias="X-Wuji-Request-ID", min_length=1, max_length=256)]):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            return await gate.request(access, payload, request_id=request_id, original_json=await request.body())
        except (DomainError, ValidationError, psycopg.Error, OSError, ValueError, TimeoutError) as error:
            return error_response(request, error)

    @router.get("/internal/v2/model-attempts/{model_attempt_id}")
    async def receipt(request: Request, model_attempt_id: str):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            value = await run_in_threadpool(gate.ledger.model_attempt, access, model_attempt_id)
            return DecimalJSONResponse(value.model_dump(mode="python"))
        except (DomainError, ValidationError, psycopg.Error, OSError) as error:
            return error_response(request, error)

    return router
