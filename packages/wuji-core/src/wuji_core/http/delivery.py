"""P16 product routes: deliver a frozen report and read what was delivered.

The routes stay thin. The material index, the missing requirements and the
frozen profile digest all come from the platform service; the caller declares
one profile, states its intent with an idempotency key, and is still required to
hold ``can_control`` on that exact Task.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Annotated

from fastapi import Header, Path, Request
import psycopg
from pydantic import ValidationError

from wuji_core.audit.delivery import MAX_KEY, ReportDeliveryService
from wuji_core.contracts.generated import (
    ReportDeliveryCommand,
    ReportDeliverySummary,
    ReportDeliveryView,
)
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import current_principal
from wuji_core.http.model_gate import error_response
from wuji_core.persistence.uow import AccessContext, DomainError

IdempotencyKey = Annotated[
    str, Header(alias="Idempotency-Key", min_length=1, max_length=MAX_KEY)
]
ResourceId = Annotated[str, Path(min_length=1, max_length=MAX_KEY)]
NO_STORE = {"Cache-Control": "no-store"}


def delivery_key_for(idempotency_key: str) -> str:
    """One bounded platform key per (caller intent, retry) pair."""

    return "delivery:" + sha256(idempotency_key.encode()).hexdigest()[:32]


def summarize(document) -> dict:
    return {
        "delivery_id": document["delivery_id"],
        "report_id": document["report_id"],
        "profile_id": document["profile"]["profile_id"],
        "mode": document["mode"],
        "state": document["state"],
        "missing_required": sum(
            1 for item in document["missing"] if item.get("required") is True
        ),
        "error_code": document["error_code"],
        "created_at": document["created_at"],
    }


def create_delivery_router(deliveries):
    if not isinstance(deliveries, ReportDeliveryService):
        raise ValueError("the real ReportDeliveryService is required")
    router = VNextAPIRouter()

    def execute(request, operation):
        try:
            access = AccessContext(current_principal(request), request.state.request_id)
            return operation(access)
        except (
            DomainError,
            ValidationError,
            psycopg.Error,
            OSError,
            ValueError,
            TimeoutError,
        ) as error:
            result = error_response(request, error)
            result.headers["Cache-Control"] = "no-store"
            return result

    @router.get("/api/v2/tasks/{task_id}/reports/{report_id}/deliveries")
    def list_deliveries(request: Request, task_id: ResourceId, report_id: ResourceId):
        def operation(access):
            documents = [
                summarize(document)
                for document in deliveries.list(access, task_id, report_id)
            ]
            checked = [
                ReportDeliverySummary.model_validate(document)
                for document in documents
            ]
            return DecimalJSONResponse(
                [item.model_dump(mode="json") for item in checked], headers=NO_STORE
            )

        return execute(request, operation)

    @router.post("/api/v2/tasks/{task_id}/reports/{report_id}/deliveries")
    def deliver_report(
        request: Request,
        task_id: ResourceId,
        report_id: ResourceId,
        payload: ReportDeliveryCommand,
        idempotency_key: IdempotencyKey,
    ):
        def operation(access):
            receipt = deliveries.deliver(
                access,
                task_id,
                report_key=report_id,
                delivery_key=delivery_key_for(idempotency_key),
                profile=payload.profile.model_dump(mode="json", exclude_none=False),
                exchange=(
                    None
                    if payload.exchange is None
                    else payload.exchange
                ),
            )
            checked = ReportDeliveryView.model_validate(receipt.document)
            return DecimalJSONResponse(
                checked.model_dump(mode="json"), headers=NO_STORE
            )

        return execute(request, operation)

    @router.get(
        "/api/v2/tasks/{task_id}/reports/{report_id}/deliveries/{delivery_id}"
    )
    def read_delivery(
        request: Request,
        task_id: ResourceId,
        report_id: ResourceId,
        delivery_id: ResourceId,
    ):
        def operation(access):
            document = deliveries.read(access, task_id, report_id, delivery_id)
            checked = ReportDeliveryView.model_validate(document)
            return DecimalJSONResponse(
                checked.model_dump(mode="json"), headers=NO_STORE
            )

        return execute(request, operation)

    return router
