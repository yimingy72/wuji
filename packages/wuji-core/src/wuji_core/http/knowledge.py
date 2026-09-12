"""Production knowledge commands, through the strict vNext HTTP boundary."""

from typing import Annotated
from fastapi import Header, Request
from pydantic import ValidationError
import psycopg
from wuji_core.contracts.knowledge import (
    ClaimProposal,
    IntentProposal,
    AssessmentCommand,
    ComponentReceipt,
    AssessmentReceipt,
)
from wuji_core.contracts.envelopes import ResultEnvelope, ResultReceipt
from wuji_core.http import VNextAPIRouter, DecimalJSONResponse
from wuji_core.http.auth import current_principal
from wuji_core.http.evidence import _error
from wuji_core.persistence.uow import AccessContext, DomainError

Key = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=256)]


def create_knowledge_router(claims, assessments, committer):
    router = VNextAPIRouter()

    def execute(request, action, model, *args, **kwargs):
        try:
            access = AccessContext(current_principal(request), request.state.request_id)
            value = action(access, *args, **kwargs)
            validated = model.model_validate(value.model_dump(mode="python"))
            return DecimalJSONResponse(
                validated.model_dump(mode="python"), status_code=202
            )
        except DomainError as error:
            return _error(request, error.code, error.status)
        except (psycopg.Error, OSError, ValidationError):
            return _error(request, "CAPABILITY_UNAVAILABLE", 503)

    @router.post("/api/v2/tasks/{task_id}/claims/proposals")
    def propose(
        request: Request, task_id: str, payload: ClaimProposal, idempotency_key: Key
    ):
        return execute(
            request,
            claims.propose,
            ComponentReceipt,
            task_id,
            payload,
            idempotency_key=idempotency_key,
        )

    @router.post("/api/v2/tasks/{task_id}/intents/proposals")
    def intent(
        request: Request, task_id: str, payload: IntentProposal, idempotency_key: Key
    ):
        return execute(
            request,
            claims.propose_intent,
            ComponentReceipt,
            task_id,
            payload,
            idempotency_key=idempotency_key,
        )

    @router.post("/api/v2/tasks/{task_id}/assessments")
    def assess(
        request: Request, task_id: str, payload: AssessmentCommand, idempotency_key: Key
    ):
        principal = current_principal(request)
        if "agent" in principal.roles or "assessor" not in principal.roles:
            return _error(request, "FORBIDDEN_ASSESSOR", 403)
        return execute(
            request,
            assessments.record,
            AssessmentReceipt,
            task_id,
            payload,
            idempotency_key=idempotency_key,
        )

    @router.post("/internal/v2/results")
    def submit(request: Request, payload: ResultEnvelope, idempotency_key: Key):
        if idempotency_key != payload.submission_id:
            return _error(request, "INVALID_SCHEMA", 422)
        return execute(request, committer.submit, ResultReceipt, payload)

    return router
