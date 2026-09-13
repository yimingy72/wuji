"""P08 contract helpers that import the real production session boundary."""

from __future__ import annotations

import asyncio
from importlib import import_module
from inspect import Parameter, signature
from types import SimpleNamespace

import httpx
from agent_framework import AgentResponse, Content, Message
from openai.types.chat.chat_completion_chunk import (
    ChoiceDeltaToolCall,
    ChoiceDeltaToolCallFunction,
)

from wuji_core.contracts.admission import ToolCallReceipt
from wuji_core.contracts.sessions import SessionLimits
from wuji_maf_worker.tools import ModelCallIdentity


REQUIRED = Parameter.empty
MODEL_ATTEMPT_ID = "model-attempt-p08"
PROVIDER_CALL_ID = "provider-call-p08"
SDK_CONTENT_ID = "af-call-p08"
SESSION_LINEAGE = "run:first-p08-run"
TOOL_CALL_ID = "tool-call-p08"
TOOL_DEFINITION = {
    "ref": "fixture-reader-p08-v1",
    "revision": "1",
    "name": "read_fixture",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
        "additionalProperties": False,
    },
    "executor_ref": "fixture-reader-p08",
    "approval_required": True,
    "allowed_target_kinds": ["workspace_read"],
}
NATIVE_ARGUMENTS = '{"path":"version.txt"}'


def session_repository_type():
    """Return the production repository type without a test substitute."""

    try:
        module = import_module("wuji_core.execution.sessions")
    except ModuleNotFoundError as error:
        if error.name != "wuji_core.execution.sessions":
            raise
        raise AssertionError(
            "P08 SessionRepository production module is absent"
        ) from error
    repository_type = getattr(module, "SessionRepository", None)
    if repository_type is None:
        raise AssertionError("P08 SessionRepository production type is absent")
    return repository_type


def parameter_shape(callable_object):
    """Return names, kinds, and defaults from one frozen public call shape."""

    return tuple(
        (parameter.name, parameter.kind, parameter.default)
        for parameter in signature(callable_object).parameters.values()
    )


def session_limits():
    return SessionLimits(
        max_objects=32,
        max_reference_depth=8,
        max_object_bytes=65_536,
        max_total_bytes=262_144,
        max_messages=128,
        max_pending_approvals=4,
    )


def pending_native_identity():
    """Drive production identity hooks with public OpenAI/MAF content types."""

    identity = ModelCallIdentity([TOOL_DEFINITION], max_bytes=65_536)
    response = httpx.Response(
        200,
        headers={
            "X-Wuji-Model-Attempt-ID": MODEL_ATTEMPT_ID,
            "Content-Type": "text/event-stream",
        },
    )
    asyncio.run(identity.response(response))
    delta = ChoiceDeltaToolCall(
        index=0,
        id=PROVIDER_CALL_ID,
        type="function",
        function=ChoiceDeltaToolCallFunction(
            name=TOOL_DEFINITION["name"],
            arguments=NATIVE_ARGUMENTS,
        ),
    )
    identity.parse_response(SimpleNamespace(tool_calls=[delta]), [])
    function_call = Content.from_function_call(
        PROVIDER_CALL_ID,
        TOOL_DEFINITION["name"],
        arguments=NATIVE_ARGUMENTS,
        id=SDK_CONTENT_ID,
    )
    approval = Content.from_function_approval_request(
        SDK_CONTENT_ID,
        function_call,
    )
    native_response = AgentResponse(
        messages=[Message(role="assistant", contents=[function_call, approval])],
        finish_reason="tool_calls",
    )
    pending = identity.capture_pending(native_response, SESSION_LINEAGE)
    assert len(pending) == 1
    content, request = pending[0]
    receipt = ToolCallReceipt.model_validate(
        {
            "tool_call_id": TOOL_CALL_ID,
            "operation_id": "operation-p08",
            "tool_attempt_id": None,
            "status": "pending_approval",
            "evidence_receipt": None,
            "result_ref": None,
            "reason_code": None,
        }
    )
    identity.record_receipt(request, receipt)
    return identity, content, native_response
