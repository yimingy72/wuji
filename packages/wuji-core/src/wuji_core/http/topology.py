"""Frozen v2 topology/record/history routes; no execution, layout or stream."""

from typing import Annotated

from fastapi import Query, Request
from pydantic import ValidationError
import psycopg

from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.contracts.views import ViewMode, ViewQuery
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import AuthenticationError, current_principal
from wuji_core.http.evidence import _error
from wuji_core.persistence.uow import AccessContext, DomainError
from wuji_core.projection.records import public_value


def create_topology_router(projection):
    """Mount in place of the earlier records router, not alongside its route."""
    router = VNextAPIRouter()

    def respond(request, operation):
        try:
            access = AccessContext(current_principal(request), request.state.request_id)
            value = operation(access)
            return DecimalJSONResponse(public_value(value), headers={"Cache-Control": "no-store"})
        except AuthenticationError:
            result = _error(request, "UNAUTHENTICATED", 401)
        except DomainError as error:
            result = _error(request, error.code, error.status)
        except ValidationError:
            result = _error(request, "INVALID_SCHEMA", 422)
        except (psycopg.Error, OSError):
            result = _error(request, "CAPABILITY_UNAVAILABLE", 503)
        result.headers["Cache-Control"] = "no-store"
        return result

    @router.get("/api/v2/tasks/{task_id}/topology")
    def topology(
        request: Request, task_id: str,
        mode: ViewMode = ViewMode.live,
        snapshot_id: Annotated[str | None, Query(min_length=1, max_length=256)] = None,
        cursor: Annotated[str | None, Query(min_length=1, max_length=4096)] = None,
        node_limit: Annotated[int, Query(ge=1, le=1000)] = 300,
        edge_limit: Annotated[int, Query(ge=1, le=2000)] = 600,
    ):
        return respond(request, lambda access: projection.topology(
            task_id, access, query=ViewQuery.model_validate(dict(
                mode=mode, snapshot_id=snapshot_id, cursor=cursor,
                node_limit=node_limit, edge_limit=edge_limit,
            )),
        ))

    @router.get("/api/v2/tasks/{task_id}/snapshots")
    def history(
        request: Request, task_id: str,
        cursor: Annotated[str | None, Query(min_length=1, max_length=4096)] = None,
    ):
        return respond(request, lambda access: projection.history(task_id, access, cursor=cursor))

    @router.get("/api/v2/tasks/{task_id}/records/{record_type}/{record_id}")
    def record(
        request: Request, task_id: str, record_type: str, record_id: str,
        revision: Annotated[str, Query(pattern=r"^[1-9][0-9]*$", max_length=1024)],
        snapshot_id: Annotated[str | None, Query(min_length=1, max_length=256)] = None,
    ):
        return respond(request, lambda access: projection.record(
            task_id, access, KnowledgeRef.model_validate(dict(
                entity_type=record_type, id=record_id, revision=revision,
            )), snapshot_id=snapshot_id,
        ))

    return router
