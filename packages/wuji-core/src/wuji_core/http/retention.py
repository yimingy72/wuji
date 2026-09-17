"""P16 retention route: an authorized purge that leaves its tombstone behind.

The route stays thin: authority, the retention guard and the recorded reason all
come from the platform service. The caller states one bounded intent (which
version to purge and why) and is still required to hold both the retention and
the control permission on that exact Task.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Annotated

from fastapi import Header, Path, Request
import psycopg
from pydantic import ValidationError

from wuji_core.audit.retention import MAX_KEY, RetentionService
from wuji_core.contracts.generated import ArtifactPurgeCommand, ArtifactPurgeView
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import current_principal
from wuji_core.http.model_gate import error_response
from wuji_core.persistence.uow import AccessContext, DomainError

IdempotencyKey = Annotated[
    str, Header(alias="Idempotency-Key", min_length=1, max_length=MAX_KEY)
]
ResourceId = Annotated[str, Path(min_length=1, max_length=MAX_KEY)]
NO_STORE = {"Cache-Control": "no-store"}


def purge_key_for(idempotency_key: str) -> str:
    return "purge:" + sha256(idempotency_key.encode()).hexdigest()[:32]


def create_retention_router(retention):
    if not isinstance(retention, RetentionService):
        raise ValueError("the real RetentionService is required")
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

    @router.post("/api/v2/tasks/{task_id}/artifacts/{artifact_id}/purges")
    def purge_artifact(
        request: Request,
        task_id: ResourceId,
        artifact_id: ResourceId,
        payload: ArtifactPurgeCommand,
        idempotency_key: IdempotencyKey,
    ):
        def operation(access):
            receipt = retention.purge(
                access,
                task_id,
                artifact_id=artifact_id,
                revision=int(payload.revision.root),
                reason=payload.reason,
                purge_key=purge_key_for(idempotency_key),
            )
            document = {
                **receipt.document,
                "artifact_revision": str(receipt.document["artifact_revision"]),
            }
            checked = ArtifactPurgeView.model_validate(document)
            return DecimalJSONResponse(
                checked.model_dump(mode="json"), headers=NO_STORE
            )

        return execute(request, operation)

    return router
