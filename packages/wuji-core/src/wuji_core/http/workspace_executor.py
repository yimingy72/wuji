"""Action-permit protected Kali workspace export/import routes."""

from hmac import compare_digest

from fastapi import Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from wuji_core.admission.common import digest
from wuji_core.admission.remote_workspace import ExecutorActionVerifier
from wuji_core.contracts import generated as wire
from wuji_core.evidence.workspace_transfer import WorkspaceTransferHandler
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


def create_workspace_transfer_router(handler, *, verifier, binding):
    if (
        not isinstance(handler, WorkspaceTransferHandler)
        or not isinstance(verifier, ExecutorActionVerifier)
        or verifier.binding != binding
        or handler.environment_ref != binding.environment_ref
    ):
        raise ValueError("fixed workspace handler and action verifier required")
    router = VNextAPIRouter()

    async def invoke(request, action):
        try:
            principal = current_principal(request)
            if (
                principal.subject != verifier.subject
                or principal.tenant_id != binding.tenant_id
                or principal.roles != frozenset({"executor_action"})
            ):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            permit = verifier.verify(_bearer(request))
            if (
                principal.token_id != permit.jti
                or permit.action != action
                or action not in {"workspace_export", "workspace_import"}
            ):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            payload = await request.json()
            if not isinstance(payload, dict) or set(payload) != {"request"}:
                raise DomainError("INVALID_SCHEMA", 422)
            contract = (
                wire.WorkspaceExportRequestV1
                if action == "workspace_export"
                else wire.WorkspaceImportRequestV1
            )
            fixed = contract.model_validate(payload["request"])
            if not compare_digest(
                digest(fixed.model_dump(mode="json")), permit.arguments_digest
            ):
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            method = handler.export if action == "workspace_export" else handler.import_publication
            result = await run_in_threadpool(method, permit, fixed)
            return DecimalJSONResponse(
                result.model_dump(mode="python"),
                headers={"Cache-Control": "no-store"},
            )
        except (
            DomainError,
            ValidationError,
            OSError,
            ValueError,
            TypeError,
        ) as error:
            return error_response(request, error)

    @router.post("/internal/v2/workspace/export")
    async def export(request: Request):
        return await invoke(request, "workspace_export")

    @router.post("/internal/v2/workspace/import")
    async def import_publication(request: Request):
        return await invoke(request, "workspace_import")

    return router
