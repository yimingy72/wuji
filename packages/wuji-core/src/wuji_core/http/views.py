"""P15 ViewStream: one authorized SSE stream of a saved view's changes.

The stream never invents authority. It resolves the Task from the view for the
acting tenant *and* subject, then asks the projection repository to advance that
same view. Every batch carries the opaque cursor that resumes it; a view whose
authorization, lifetime or change size can no longer be described as one bounded
patch batch ends with an explicit ``ViewReset`` instead of a partial update.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Annotated

from fastapi import Header, Path, Query, Request
import psycopg
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse

from wuji_core.http import VNextAPIRouter
from wuji_core.http.auth import current_principal
from wuji_core.http.model_gate import error_response
from wuji_core.persistence.uow import AccessContext, DomainError


POLL_SECONDS = 1.0
KEEPALIVE_SECONDS = 15.0
STREAM_SECONDS = 300.0
ViewId = Annotated[str, Path(min_length=1, max_length=256)]
Cursor = Annotated[str | None, Query(max_length=4096)]
LastEventId = Annotated[str | None, Header(alias="Last-Event-ID", max_length=4096)]
RESET_REASONS = {
    "VIEW_EXPIRED": "view_expired",
    "SNAPSHOT_EXPIRED": "snapshot_expired",
    "VIEW_RESET_REQUIRED": "change_too_large",
    "NOT_FOUND_OR_FORBIDDEN": "authorization_changed",
}

TRANSIENT = (psycopg.Error, OSError, TimeoutError, ValueError)


def _event(name: str, document: dict, *, event_id: str | None = None) -> str:
    lines = []
    if event_id is not None:
        lines.append("id: " + event_id)
    lines.append("event: " + name)
    lines.append("data: " + json.dumps(document, ensure_ascii=False, separators=(",", ":")))
    return "\n".join(lines) + "\n\n"


def _reset(view_id: str, reason: str) -> dict:
    return {
        "schema_version": "wuji.view-reset.v2",
        "view_id": view_id,
        "reason": reason[:256],
        "action": "resnapshot",
    }


def create_view_router(projection):
    if not callable(getattr(projection, "stream_step", None)) or not callable(
        getattr(projection, "stream_task", None)
    ):
        raise ValueError("the real ProjectionRepository is required")
    router = VNextAPIRouter()

    @router.get("/api/v2/views/{view_id}/events")
    async def stream_view(
        request: Request,
        view_id: ViewId,
        cursor: Cursor = None,
        last_event_id: LastEventId = None,
    ):
        access = AccessContext(current_principal(request), request.state.request_id)
        resume = cursor or last_event_id
        if resume is not None and not 1 <= len(resume) <= 4096:
            return error_response(request, DomainError("INVALID_SCHEMA", 422))
        try:
            await run_in_threadpool(projection.stream_task, access, view_id)
            first = await run_in_threadpool(projection.stream_step, access, view_id, resume)
            initial_reset = None
        except DomainError as error:
            if error.code != "VIEW_RESET_REQUIRED":
                return error_response(request, error)
            first, initial_reset = None, _reset(view_id, RESET_REASONS[error.code])
        except (ValidationError, psycopg.Error, OSError, TimeoutError, ValueError) as error:
            return error_response(request, error)

        async def events():
            started = time.monotonic()
            idle_since = started
            if initial_reset is not None:
                yield _event("reset", initial_reset)
                return
            item = first
            handle = resume
            while True:
                if item is not None:
                    handle = item["cursor"]
                    idle_since = time.monotonic()
                    yield _event("view", item, event_id=handle)
                if time.monotonic() - started >= STREAM_SECONDS:
                    # A bounded stream: the client reconnects with its cursor and
                    # receives only what changed in between.
                    return
                await asyncio.sleep(POLL_SECONDS)
                try:
                    item = await run_in_threadpool(
                        projection.stream_step, access, view_id, handle
                    )
                except DomainError as error:
                    reason = RESET_REASONS.get(error.code, "resnapshot")
                    yield _event("reset", _reset(view_id, reason))
                    return
                except TRANSIENT:
                    # A transient database/transport failure never invents a
                    # change; the next poll retries with the same cursor.
                    item = None
                if item is None and time.monotonic() - idle_since >= KEEPALIVE_SECONDS:
                    idle_since = time.monotonic()
                    yield ": keepalive\n\n"

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-store",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return router
