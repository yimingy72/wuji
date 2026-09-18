"""Explicit public preview route; not the Worker-only material endpoint."""

from typing import Annotated

from fastapi import Query, Request
from pydantic import ValidationError
import psycopg

from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import current_principal
from wuji_core.http.evidence import _error
from wuji_core.persistence.uow import AccessContext, DomainError


def create_material_router(material):
    router = VNextAPIRouter()

    @router.get("/api/v2/tasks/{task_id}/artifacts/{artifact_id}/material")
    def preview(
        request: Request, task_id: str, artifact_id: str,
        version: Annotated[str, Query(pattern=r"^[1-9][0-9]*$", max_length=128)],
    ):
        access = AccessContext(current_principal(request), request.state.request_id)
        try:
            result = material.read(access, task_id, artifact_id, version)
            return DecimalJSONResponse(result.model_dump(mode="python"), headers={
                "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
            })
        except DomainError as error:
            return _error(request, error.code, error.status)
        except (psycopg.Error, OSError, ValidationError):
            return _error(request, "CAPABILITY_UNAVAILABLE", 503)

    return router
