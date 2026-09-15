"""Personal layout GET/PUT routes over the isolated vNext API boundary."""

from typing import Annotated

from fastapi import Header, Path, Request
from pydantic import ValidationError
import psycopg

from wuji_core.contracts.views import LayoutPatch, LayoutReceipt
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import AuthenticationError, current_principal
from wuji_core.http.evidence import _error
from wuji_core.persistence.uow import AccessContext, DomainError
from wuji_core.projection.records import public_value


ViewName = Annotated[str, Path(pattern=r"^(knowledge-live|knowledge-history)$", max_length=128)]
IfMatch = Annotated[str, Header(alias="If-Match", pattern=r"^(0|[1-9][0-9]*)$", max_length=1024)]


def create_layout_router(layouts):
    router = VNextAPIRouter()

    def respond(request: Request, operation):
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

    @router.get("/api/v2/tasks/{task_id}/layouts/{view_name}")
    def get_layout(request: Request, task_id: str, view_name: ViewName):
        return respond(request, lambda access: layouts.read(task_id, access, view_name=view_name))

    @router.put("/api/v2/tasks/{task_id}/layouts/{view_name}")
    def put_layout(
        request: Request,
        task_id: str,
        view_name: ViewName,
        if_match: IfMatch,
        payload: LayoutPatch,
    ):
        return respond(
            request,
            lambda access: layouts.write(
                task_id,
                access,
                view_name=view_name,
                patch=payload,
                expected_revision=if_match,
                request_id=request.state.request_id,
            ),
        )

    return router
