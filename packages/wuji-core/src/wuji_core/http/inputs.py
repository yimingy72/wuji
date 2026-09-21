"""Bounded public human-input reads and question answers."""

from typing import Annotated

from fastapi import Header, Request
from pydantic import ValidationError
import psycopg

from wuji_core.contracts.generated import InputAnswerCommandV1, InputAnswerReceiptV1
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import AuthenticationError, current_principal
from wuji_core.http.evidence import _error
from wuji_core.persistence.uow import AccessContext, DomainError
from wuji_core.projection.records import public_value


def create_input_router(inputs):
    router = VNextAPIRouter()

    def respond(request, operation):
        try:
            access = AccessContext(current_principal(request), request.state.request_id)
            return DecimalJSONResponse(
                public_value(operation(access)), headers={"Cache-Control": "no-store"}
            )
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

    @router.get("/api/v2/tasks/{task_id}/inputs")
    def list_inputs(request: Request, task_id: str):
        return respond(request, lambda access: inputs.list_pending(access, task_id))

    @router.post("/api/v2/inputs/{input_request_id}/answers")
    def answer_input(
        request: Request,
        input_request_id: str,
        payload: InputAnswerCommandV1,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=256)],
    ):
        def answer(access):
            delivery_id = inputs.answer_question(
                access, input_request_id, text=payload.text,
                idempotency_key=idempotency_key,
            )
            return InputAnswerReceiptV1.model_validate({
                "schema_version": "wuji.input-answer.v1",
                "input_request_id": input_request_id,
                "delivery_id": delivery_id,
                "status": "resolved",
            })

        return respond(request, answer)

    return router
