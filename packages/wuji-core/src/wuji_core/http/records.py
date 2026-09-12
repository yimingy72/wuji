"""Authorized immutable knowledge records and bounded assessment read views."""

from typing import Annotated
from datetime import timezone
from fastapi import Query, Request
from pydantic import ValidationError
import psycopg
from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.contracts.generated import RecordView
from wuji_core.http import VNextAPIRouter, DecimalJSONResponse
from wuji_core.http.auth import current_principal
from wuji_core.http.evidence import _error
from wuji_core.persistence.uow import AccessContext, DomainError


def create_records_router(ledger):
    router = VNextAPIRouter()

    @router.get("/api/v2/tasks/{task_id}/records/{record_type}/{record_id}")
    def record(
        request: Request,
        task_id: str,
        record_type: str,
        record_id: str,
        revision: Annotated[str, Query(pattern=r"^[1-9][0-9]*$")],
        snapshot_id: Annotated[str | None, Query(min_length=1, max_length=256)] = None,
    ):
        try:
            access = AccessContext(current_principal(request), request.state.request_id)
            ref = KnowledgeRef.model_validate(
                dict(entity_type=record_type, id=record_id, revision=revision)
            )
            value = ledger.read(access, task_id, ref, snapshot_id=snapshot_id)
            result = RecordView.model_validate(value.model_dump(mode="python"))
            body = result.model_dump(mode="python")
            body["record"]["created_at"] = (
                body["record"]["created_at"]
                .astimezone(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )
            return DecimalJSONResponse(body, headers={"Cache-Control": "no-store"})
        except DomainError as error:
            return _error(request, error.code, error.status)
        except ValidationError:
            return _error(request, "INVALID_SCHEMA", 422)
        except (psycopg.Error, OSError):
            return _error(request, "CAPABILITY_UNAVAILABLE", 503)

    return router
