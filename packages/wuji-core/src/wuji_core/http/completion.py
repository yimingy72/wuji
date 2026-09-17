"""P12 product routes: read the review, drive the epoch, read the report.

The routes stay thin. Readiness, the canonical decision bytes and the frozen
report all come from the platform services; the caller only states its intent
(open the completion epoch, or close with a trigger and an outcome) and is
still required to hold ``can_control`` on that exact Task.
"""

from typing import Annotated

from fastapi import Header, Path, Request
from pydantic import ValidationError
import psycopg

from wuji_core.completion.portal import MAX_IDEMPOTENCY_KEY, TaskCompletionPortal
from wuji_core.contracts.generated import (
    ReportView,
    TaskCompletionCommand,
    TaskCompletionOutcome,
    TaskCompletionView,
)
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import current_principal
from wuji_core.http.model_gate import error_response
from wuji_core.persistence.uow import AccessContext, DomainError


IdempotencyKey = Annotated[
    str, Header(alias="Idempotency-Key", min_length=1, max_length=MAX_IDEMPOTENCY_KEY)
]
ResourceId = Annotated[str, Path(min_length=1, max_length=256)]
NO_STORE = {"Cache-Control": "no-store"}


def wire(document):
    """The wire keeps revisions as decimal strings; the domain keeps integers."""

    return {**document, "control_version": str(document["control_version"])}


def create_completion_router(portal):
    if not isinstance(portal, TaskCompletionPortal):
        raise ValueError("the real TaskCompletionPortal is required")
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

    @router.get("/api/v2/tasks/{task_id}/completion")
    def read_completion(request: Request, task_id: ResourceId):
        def operation(access):
            checked = TaskCompletionView.model_validate(
                wire(portal.review(access, task_id))
            )
            return DecimalJSONResponse(
                checked.model_dump(mode="json"), headers=NO_STORE
            )

        return execute(request, operation)

    @router.post("/api/v2/tasks/{task_id}/completion")
    def submit_completion(
        request: Request,
        task_id: ResourceId,
        payload: TaskCompletionCommand,
        idempotency_key: IdempotencyKey,
    ):
        def operation(access):
            outcome = portal.submit(
                access,
                task_id,
                action=payload.action.value,
                close_trigger=payload.close_trigger.value,
                result_outcome=payload.result_outcome.value,
                deadline_seconds=payload.deadline_seconds,
                idempotency_key=idempotency_key,
            )
            document = wire(outcome.document())
            checked = TaskCompletionOutcome.model_validate(document)
            return DecimalJSONResponse(
                checked.model_dump(mode="json"),
                status_code=outcome.status_code,
                headers=NO_STORE,
            )

        return execute(request, operation)

    @router.get("/api/v2/tasks/{task_id}/reports/{report_id}")
    def read_report(request: Request, task_id: ResourceId, report_id: ResourceId):
        def operation(access):
            found = portal.read_report(access, task_id, report_id)
            if found is None:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            checked = ReportView.model_validate(found)
            return DecimalJSONResponse(
                checked.model_dump(mode="json"), headers=NO_STORE
            )

        return execute(request, operation)

    return router
