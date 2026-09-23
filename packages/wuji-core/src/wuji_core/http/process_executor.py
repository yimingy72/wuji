"""Action-permit protected HTTP boundary for the Kali process supervisor."""

from hmac import compare_digest
import asyncio
from threading import Event

from fastapi import Request
from pydantic import ValidationError

from wuji_core.admission.remote_workspace import ExecutorActionVerifier
from wuji_core.execution.process_supervisor import ProcessSupervisor
from wuji_core.execution.processes import (
    PROCESS_ARGUMENT_MODELS,
    process_arguments_digest,
)
from wuji_core.http import DecimalJSONResponse, VNextAPIRouter
from wuji_core.http.auth import current_principal
from wuji_core.http.model_gate import error_response
from wuji_core.persistence.uow import DomainError


def _bearer(request):
    value = request.headers.get("authorization", "")
    scheme, separator, token = value.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token or " " in token:
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")
    return token


def create_process_executor_router(
    supervisor, *, verifier, binding, shutdown_callback
):
    if (
        not isinstance(supervisor, ProcessSupervisor)
        or not isinstance(verifier, ExecutorActionVerifier)
        or verifier.binding != binding
        or not callable(shutdown_callback)
    ):
        raise ValueError("fixed process supervisor and action verifier required")
    router = VNextAPIRouter()

    @router.post("/internal/v2/process/{action}")
    async def invoke(request: Request, action: str):
        try:
            principal = current_principal(request)
            if (
                principal.subject != verifier.subject
                or principal.tenant_id != binding.tenant_id
                or principal.roles != frozenset({"executor_action"})
            ):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            permit = verifier.verify(_bearer(request))
            if principal.token_id != permit.jti:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            if permit.action != action or action not in {"exec", "read", "input", "stop", "query"}:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            payload = await request.json()
            if not isinstance(payload, dict) or set(payload) != {"arguments"}:
                raise DomainError("INVALID_SCHEMA", 422)
            argument_action = "read" if action == "query" else action
            arguments = PROCESS_ARGUMENT_MODELS[argument_action].model_validate(
                payload["arguments"]
            ).model_dump(mode="json")
            if not compare_digest(
                process_arguments_digest(arguments), permit.arguments_digest
            ):
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            handle = arguments.get("handle")
            if (action == "exec") != (permit.parent_handle is None):
                raise DomainError("INVALID_REFERENCE", 422)
            if action != "exec" and handle != permit.parent_handle:
                raise DomainError("INVALID_REFERENCE", 422)
            common = {
                "action_id": permit.jti if action == "query" else permit.tool_attempt_id,
                "handle": permit.tool_attempt_id if action == "exec" else handle,
                "arguments_digest": permit.arguments_digest,
            }
            if action == "exec":
                reply = await asyncio.to_thread(supervisor.exec,
                    **common,
                    command=arguments["command"],
                    cwd=arguments["cwd"],
                    timeout_seconds=arguments["timeout_seconds"],
                )
            elif action in {"read", "query"}:
                reply = await asyncio.to_thread(supervisor.read,
                    **common,
                    cursor=arguments["cursor"],
                    max_bytes=arguments["max_bytes"],
                    wait_ms=arguments["wait_ms"],
                    durable=action != "query",
                )
            elif action == "input":
                reply = await asyncio.to_thread(supervisor.input,
                    **common, data=arguments["data"], eof=arguments["eof"]
                )
            else:
                reply = await asyncio.to_thread(supervisor.stop, **common)
            return DecimalJSONResponse(
                reply.model_dump(mode="json"), headers={"Cache-Control": "no-store"}
            )
        except (DomainError, ValidationError, OSError, ValueError, TypeError) as error:
            return error_response(request, error)

    @router.post("/internal/v2/process-control/shutdown")
    async def shutdown(request: Request):
        try:
            principal = current_principal(request)
            permit = verifier.verify_shutdown(_bearer(request))
            if (
                principal.subject != verifier.subject
                or principal.tenant_id != binding.tenant_id
                or principal.roles != frozenset({"executor_action"})
                or principal.token_id != permit.jti
                or await request.json() != {}
            ):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            supervisor.shutdown(shutdown_callback)
            return DecimalJSONResponse(
                {
                    "status": "accepted",
                    "task_id": binding.task_id,
                    "runtime_attempt": permit.runtime_attempt,
                    "request_id": permit.jti,
                },
                headers={"Cache-Control": "no-store"},
            )
        except (DomainError, ValidationError, OSError, ValueError, TypeError) as error:
            return error_response(request, error)

    @router.post("/internal/v2/process-control/drain")
    async def drain(request: Request):
        try:
            principal = current_principal(request)
            permit = verifier.verify_shutdown(_bearer(request))
            if (
                principal.subject != verifier.subject
                or principal.tenant_id != binding.tenant_id
                or principal.roles != frozenset({"executor_action"})
                or principal.token_id != permit.jti
                or await request.json() != {}
            ):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            completed = Event()
            supervisor.shutdown(completed.set)
            timeout = min(30.0, supervisor.stop_grace_seconds + 5.0)
            if not await asyncio.to_thread(completed.wait, timeout):
                raise DomainError("OPERATION_UNKNOWN", 409)
            return DecimalJSONResponse(
                {
                    "status": "drained",
                    "task_id": binding.task_id,
                    "runtime_attempt": permit.runtime_attempt,
                    "request_id": permit.jti,
                },
                headers={"Cache-Control": "no-store"},
            )
        except (DomainError, ValidationError, OSError, ValueError, TypeError) as error:
            return error_response(request, error)

    return router
