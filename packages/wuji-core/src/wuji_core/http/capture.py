"""Task-authorized Runtime capture inventory and bounded part downloads."""

from typing import Annotated

from fastapi import Path, Query, Request
from pydantic import ValidationError
import psycopg
from starlette.responses import StreamingResponse

from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import current_principal
from wuji_core.http.evidence import _error
from wuji_core.persistence.uow import AccessContext, DomainError


MAX_CAPTURE_PART_BYTES = 67_108_864


def create_capture_router(capture):
    router = VNextAPIRouter()

    def access(request):
        return AccessContext(current_principal(request), request.state.request_id)

    @router.get("/api/v2/tasks/{task_id}/capture-sessions")
    def sessions(request: Request, task_id: str):
        try:
            result = capture.list_sessions(access(request), task_id)
            return DecimalJSONResponse(
                result.model_dump(mode="json"), headers={"Cache-Control": "no-store"}
            )
        except DomainError as error:
            return _error(request, error.code, error.status)
        except (psycopg.Error, OSError, ValidationError):
            return _error(request, "CAPABILITY_UNAVAILABLE", 503)

    @router.get("/api/v2/tasks/{task_id}/capture-sessions/{capture_session_id}/items")
    def items(
        request: Request,
        task_id: str,
        capture_session_id: Annotated[str, Path(min_length=1, max_length=256)],
        after: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ):
        try:
            result = capture.list_items(
                access(request), task_id, capture_session_id, after=after, limit=limit
            )
            return DecimalJSONResponse(
                result.model_dump(mode="json"), headers={"Cache-Control": "no-store"}
            )
        except DomainError as error:
            return _error(request, error.code, error.status)
        except (psycopg.Error, OSError, ValidationError):
            return _error(request, "CAPABILITY_UNAVAILABLE", 503)

    @router.get(
        "/api/v2/tasks/{task_id}/capture-sessions/{capture_session_id}/items/"
        "{item_seq}/parts/{part}"
    )
    def part(
        request: Request,
        task_id: str,
        capture_session_id: Annotated[str, Path(min_length=1, max_length=256)],
        item_seq: Annotated[int, Path(ge=1, le=1_000_000)],
        part: Annotated[str, Path(pattern=r"^[a-z][a-z0-9_.-]{0,127}$")],
    ):
        try:
            data, _media_type, digest = capture.read_part(
                access(request),
                task_id,
                capture_session_id,
                item_seq,
                part,
                max_bytes=MAX_CAPTURE_PART_BYTES,
            )
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
