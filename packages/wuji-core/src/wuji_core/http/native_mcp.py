"""Native MCP endpoint for process, board and workspace tools in the Gate."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent
from starlette.concurrency import run_in_threadpool

from wuji_core.blackboard.notifications import BoardPublishService
from wuji_core.contracts.admission import ToolCallRequest
from wuji_core.contracts.generated import WorkerAssignment
from wuji_core.contracts import generated as wire
from wuji_core.contracts.native_tools import BOARD_PUBLISH_SCHEMA
from wuji_core.evidence.workspace_bundles import (
    MATERIALIZE_SCHEMA,
    PUBLISH_SCHEMA,
    WorkspaceBundleService,
)
from wuji_core.execution.process_gate import ProcessToolGate
from wuji_core.execution.processes import PROCESS_ARGUMENT_MODELS, PROCESS_TOOL_SCHEMAS
from wuji_core.execution.workspace_gate import WorkspaceToolGate
from wuji_core.http import canonical_json_bytes
from wuji_core.http.auth import BearerAuthMiddleware, Principal, TokenVerifier
from wuji_core.http.json_boundary import DEFAULT_JSON_LIMITS, JsonBoundaryLimits, StrictJsonMiddleware
from wuji_core.persistence.uow import AccessContext, DomainError


MCP_INVOCATION_META = "wuji.dev/invocation"
MCP_RESULT_META = "wuji.dev/result"

_ACCESS = ContextVar("wuji_native_mcp_access", default=None)


class _FrozenFastMCP(FastMCP):
    def __init__(self, *args, schemas, **kwargs):
        self._frozen_schemas = dict(schemas)
        super().__init__(*args, **kwargs)

    async def list_tools(self):
        tools = await super().list_tools()
        return [
            tool.model_copy(
                update={"inputSchema": self._frozen_schemas.get(tool.name, tool.inputSchema)}
            )
            for tool in tools
        ]


class _AccessMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        principal = scope.get("state", {}).get("principal")
        request_id = scope.get("state", {}).get("request_id")
        if not isinstance(principal, Principal) or not isinstance(request_id, str):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        token = _ACCESS.set(AccessContext(principal, request_id))
        try:
            return await self.app(scope, receive, send)
        finally:
            _ACCESS.reset(token)


@dataclass(frozen=True)
class NativeMCPApplication:
    app: Any
    starlette: Any


def _invocation(ctx, name, arguments):
    access = _ACCESS.get()
    meta = ctx.request_context.meta
    extra = {} if meta is None else dict(meta.model_extra or {})
    value = extra.get(MCP_INVOCATION_META)
    if access is None or not isinstance(value, dict):
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")
    if set(value) != {"assignment", "native_occurrence", "tool_request"}:
        raise DomainError("INVALID_SCHEMA", 422)
    assignment = WorkerAssignment.model_validate(value["assignment"])
    tool_request = ToolCallRequest.model_validate(value["tool_request"])
    if assignment.identity.tenant_id != access.principal.tenant_id:
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")
    if name in {"kali_exec", "kali_read", "kali_input", "kali_stop"}:
        action = {
            "kali_exec": "exec",
            "kali_read": "read",
            "kali_input": "input",
            "kali_stop": "stop",
        }[name]
        expected_arguments = PROCESS_ARGUMENT_MODELS[action].model_validate(
            tool_request.arguments
        ).model_dump(mode="json")
        actual_arguments = PROCESS_ARGUMENT_MODELS[action].model_validate(
            arguments
        ).model_dump(mode="json")
    else:
        model = (
            wire.WorkspacePublishArgumentsV1
            if name == "workspace_publish"
            else wire.WorkspaceMaterializeArgumentsV1
        )
        expected_arguments = model.model_validate(
            tool_request.arguments
        ).model_dump(mode="json")
        actual_arguments = model.model_validate(arguments).model_dump(mode="json")
    if (
        canonical_json_bytes(expected_arguments)
        != canonical_json_bytes(actual_arguments)
        or tool_request.sdk_content_id is None
        or tool_request.sdk_content_id.root != value["native_occurrence"]
    ):
        raise DomainError("INVALID_REFERENCE", 422)
    return access, assignment, tool_request, value["native_occurrence"]


def _local_invocation(ctx, name, arguments):
    access = _ACCESS.get()
    meta = ctx.request_context.meta
    extra = {} if meta is None else dict(meta.model_extra or {})
    value = extra.get(MCP_INVOCATION_META)
    if (
        access is None
        or not isinstance(value, dict)
        or set(value) != {"assignment", "native_occurrence", "arguments_digest"}
    ):
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")
    assignment = WorkerAssignment.model_validate(value["assignment"])
    if (
        assignment.identity.tenant_id != access.principal.tenant_id
        or sha256(canonical_json_bytes(arguments)).hexdigest()
        != value["arguments_digest"]
    ):
        raise DomainError("INVALID_REFERENCE", 422)
    return access, assignment, value["native_occurrence"]


def _result(document, meta):
    value = document.model_dump(mode="json") if hasattr(document, "model_dump") else document
    return CallToolResult(
        content=[TextContent(type="text", text=canonical_json_bytes(value).decode())],
        structuredContent=value,
        isError=False,
        _meta={MCP_RESULT_META: meta},
    )


def create_native_mcp_app(
    *,
    token_verifier,
    process_gate,
    board_publisher=None,
    workspace_gate=None,
    allowed_hosts=("127.0.0.1:*", "localhost:*", "[::1]:*"),
    allowed_origins=("http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"),
    json_limits=DEFAULT_JSON_LIMITS,
):
    if not isinstance(token_verifier, TokenVerifier) or not isinstance(
        process_gate, ProcessToolGate
    ):
        raise ValueError("native MCP requires the deployed verifier and process gate")
    if board_publisher is not None and not isinstance(
        board_publisher, BoardPublishService
    ):
        raise ValueError("board publisher must be the in-process core service")
    if workspace_gate is not None and not isinstance(workspace_gate, WorkspaceToolGate):
        raise ValueError("workspace gate must use canonical ToolAdmission")
    if (
        not isinstance(json_limits, JsonBoundaryLimits)
        or not isinstance(allowed_hosts, (list, tuple))
        or not 1 <= len(allowed_hosts) <= 16
        or any(not isinstance(value, str) or not value for value in allowed_hosts)
        or not isinstance(allowed_origins, (list, tuple))
        or len(allowed_origins) > 16
        or any(not isinstance(value, str) or not value for value in allowed_origins)
    ):
        raise ValueError("bounded native MCP transport settings are required")
    schemas = {
        **PROCESS_TOOL_SCHEMAS,
        "board_publish": BOARD_PUBLISH_SCHEMA,
        "workspace_publish": PUBLISH_SCHEMA,
        "workspace_materialize": MATERIALIZE_SCHEMA,
    }
    server = _FrozenFastMCP(
        "Wuji Native Tools",
        schemas=schemas,
        streamable_http_path="/internal/v2/mcp",
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=list(allowed_hosts),
            allowed_origins=list(allowed_origins),
        ),
    )

    async def process(name, arguments, ctx):
        access, _assignment, request, _occurrence = _invocation(
            ctx, name, arguments
        )
        reply, action_receipt, parent_receipt = await process_gate.invoke(
            access, request, name=name
        )
        return _result(
            reply,
            {
                "kind": "process",
                "action_receipt": action_receipt.model_dump(mode="json"),
                "parent_receipt": (
                    None
                    if parent_receipt is None
                    else parent_receipt.model_dump(mode="json")
                ),
            },
        )

    @server.tool(name="kali_exec", description="Run one bounded command.", structured_output=False)
    async def kali_exec(
        command: str,
        cwd: str | None = None,
        timeout_seconds: float | None = None,
        ctx: Context = None,
    ):
        return await process(
            "kali_exec",
            {"command": command, "cwd": cwd, "timeout_seconds": timeout_seconds},
            ctx,
        )

    @server.tool(name="kali_read", description="Read bounded process output.", structured_output=False)
    async def kali_read(
        handle: str,
        cursor: dict,
        max_bytes: int,
        wait_ms: int = 0,
        ctx: Context = None,
    ):
        return await process(
            "kali_read",
            {"handle": handle, "cursor": cursor, "max_bytes": max_bytes, "wait_ms": wait_ms},
            ctx,
        )

    @server.tool(name="kali_input", description="Write one bounded stdin action.", structured_output=False)
    async def kali_input(
        handle: str,
        data: str,
        eof: bool = False,
        ctx: Context = None,
    ):
        return await process(
            "kali_input", {"handle": handle, "data": data, "eof": eof}, ctx
        )

    @server.tool(name="kali_stop", description="Stop one process group.", structured_output=False)
    async def kali_stop(handle: str, ctx: Context = None):
        return await process("kali_stop", {"handle": handle}, ctx)

    @server.tool(name="board_publish", description="Publish one evidence-based Claim.", structured_output=False)
    async def board_publish(
        revises: dict | None,
        client_ref: str,
        kind: str,
        assertion_role: str,
        text: str,
        structured_assertion: dict | None,
        basis_refs: list[dict],
        limitations: list[str],
        ctx: Context = None,
    ):
        if board_publisher is None:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        arguments = {
            "revises": revises,
            "client_ref": client_ref,
            "kind": kind,
            "assertion_role": assertion_role,
            "text": text,
            "structured_assertion": structured_assertion,
            "basis_refs": basis_refs,
            "limitations": limitations,
        }
        access, assignment, occurrence = _local_invocation(
            ctx, "board_publish", arguments
        )
        result = await run_in_threadpool(
            board_publisher.publish,
            access,
            assignment,
            native_occurrence=occurrence,
            claim=arguments,
        )
        return _result(
            result,
            {
                "kind": "board_publish",
                "delivery": result.delivery.model_dump(mode="json"),
            },
        )

    async def workspace(name, arguments, ctx):
        if workspace_gate is None:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        access, assignment, request, _occurrence = _invocation(
            ctx, name, arguments
        )
        result, receipt = await workspace_gate.invoke(
            access, request, name=name, assignment=assignment
        )
        delivery = getattr(result, "delivery", None)
        return _result(
            result,
            {
                "kind": name,
                "tool_receipt": receipt.model_dump(mode="json"),
                "delivery": None if delivery is None else delivery.model_dump(mode="json"),
            },
        )

    @server.tool(name="workspace_publish", description="Publish exact workspace files.", structured_output=False)
    async def workspace_publish(
        purpose: str,
        files: list[dict],
        entrypoint: dict,
        inputs_description: str,
        outputs_description: str,
        dependencies: list[dict],
        validation_statement: str,
        limitations: list[str],
        expected_base_publication_id: str | None,
        ctx: Context = None,
    ):
        return await workspace(
            "workspace_publish",
            {
                "purpose": purpose,
                "files": files,
                "entrypoint": entrypoint,
                "inputs_description": inputs_description,
                "outputs_description": outputs_description,
                "dependencies": dependencies,
                "validation_statement": validation_statement,
                "limitations": limitations,
                "expected_base_publication_id": expected_base_publication_id,
            },
            ctx,
        )

    @server.tool(name="workspace_materialize", description="Materialize one fixed publication.", structured_output=False)
    async def workspace_materialize(
        publication_id: str, manifest_ref: dict, ctx: Context = None
    ):
        return await workspace(
            "workspace_materialize",
            {"publication_id": publication_id, "manifest_ref": manifest_ref},
            ctx,
        )

    starlette = server.streamable_http_app()
    app = BearerAuthMiddleware(
        _AccessMiddleware(StrictJsonMiddleware(starlette, limits=json_limits)),
        token_verifier=token_verifier,
    )
    return NativeMCPApplication(app=app, starlette=starlette)
