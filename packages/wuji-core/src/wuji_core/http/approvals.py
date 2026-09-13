"""Public P11 approval decision route backed only by ApprovalService."""

from typing import Annotated

from fastapi import Header, Path, Request
from pydantic import ValidationError
import psycopg
from starlette.concurrency import run_in_threadpool

from wuji_core.contracts.execution import ApprovalDecision, CommandReceipt
from wuji_core.execution.approvals import ApprovalService
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import current_principal
from wuji_core.http.model_gate import error_response
from wuji_core.persistence.uow import AccessContext, DomainError


IdempotencyKey = Annotated[
    str, Header(alias="Idempotency-Key", min_length=1, max_length=256)
]
ApprovalId = Annotated[str, Path(min_length=1, max_length=256)]


def create_approval_router(approval_service):
    if not isinstance(approval_service, ApprovalService):
        raise ValueError("a real ApprovalService decision port is required")
    router = VNextAPIRouter()

    @router.post("/api/v2/approvals/{approval_id}/decisions")
    async def decide(
        request: Request,
        approval_id: ApprovalId,
        payload: ApprovalDecision,
        idempotency_key: IdempotencyKey,
    ):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            receipt = await run_in_threadpool(
                approval_service.decide,
                access,
                approval_id,
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

    return router
