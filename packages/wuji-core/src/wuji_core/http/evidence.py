"""Real vNext evidence routes composed through the strict P02 boundary."""

from typing import Annotated

from fastapi import Header, Query, Request
from pydantic import ValidationError
import psycopg
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse

from wuji_core.contracts.envelopes import (
    CaptureEnvelope,
    EvidenceReceipt,
    ErrorResponse,
)
from wuji_core.http import VNextAPIRouter, DecimalJSONResponse
from wuji_core.http.auth import current_principal
from wuji_core.persistence.uow import AccessContext, DomainError


def _error(request, code, status):
    result = ErrorResponse.model_validate(
        {
            "code": code,
            "message": "The request could not be completed.",
            "request_id": request.state.request_id,
            "retryable": False,
            "details": {},
        }
    )
    return DecimalJSONResponse(result.model_dump(mode="python"), status_code=status)


def create_evidence_router(service):
    router = VNextAPIRouter()

    @router.post("/internal/v2/evidence")
    async def ingest(
        request: Request,
        payload: CaptureEnvelope,
        idempotency_key: Annotated[
            str, Header(alias="Idempotency-Key", min_length=1, max_length=256)
        ],
    ):
        if idempotency_key != payload.capture_id:
            return _error(request, "INVALID_SCHEMA", 422)
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            original_body = await request.body()
            # Create/use/commit the sync DB connection in the same worker thread.
            receipt = await run_in_threadpool(
                service.ingest, access, payload, original_json=original_body
            )
            result = EvidenceReceipt.model_validate(receipt.model_dump(mode="python"))
            return DecimalJSONResponse(
                result.model_dump(mode="python"), status_code=202
            )
        except DomainError as error:
            return _error(
                request, error.code, 403 if error.status == 404 else error.status
            )
        except (psycopg.Error, OSError, ValidationError):
            # A commit failure is not permission to replay an external tool operation.
            return _error(request, "CAPABILITY_UNAVAILABLE", 503)

    @router.get("/api/v2/artifacts/{artifact_id}/content")
    def content(
        request: Request,
        artifact_id: str,
        version: Annotated[str, Query(pattern=r"^(0|[1-9][0-9]*)$")],
    ):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            data, digest = service.artifacts.read(access, artifact_id, version)
            return StreamingResponse(
                iter((data,)),
                media_type="application/octet-stream",
                headers={
                    "Digest": digest,
                    "X-Content-Type-Options": "nosniff",
                    "Cache-Control": "no-store",
                    "Content-Disposition": "attachment",
                    "Content-Security-Policy": "default-src 'none'",
                },
            )
        except DomainError as error:
            return _error(request, error.code, error.status)
        except (psycopg.Error, OSError, ValidationError):
            return _error(request, "CAPABILITY_UNAVAILABLE", 503)

    return router
