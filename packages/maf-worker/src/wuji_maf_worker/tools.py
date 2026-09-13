"""Public SDK function identity -> the existing HTTP ToolGate."""

from contextvars import ContextVar
from uuid import uuid4

from agent_framework import FunctionMiddleware, FunctionTool, MiddlewareFailure

from wuji_core.contracts.admission import ToolCallRequest, ToolCallReceipt
from wuji_core.http import canonical_json_bytes, strict_json_loads


class ModelCallIdentity:
    """Fresh-Run mapping observed from HTTP headers and the public response parser."""

    def __init__(self, definitions, *, max_bytes):
        self.definitions = {d["name"]: d for d in definitions}
        self.max_bytes = max_bytes
        self.attempt_id = None
        self.calls = {}
        self.mapping = []

    async def request(self, request):
        body = strict_json_loads(request.content)
        if body.get("n", 1) != 1 or body.get("stream") is not True:
            raise ValueError("M1 requires single-choice native streaming")
        if (
            not isinstance(body.get("max_completion_tokens"), int)
            or isinstance(body.get("max_completion_tokens"), bool)
            or "max_tokens" in body
            or body.get("parallel_tool_calls") is not False
            or body.get("stream_options") != {"include_usage": True}
        ):
            raise ValueError("SDK request does not match the frozen M1 transport")
        for advertised in body.get("tools", []):
            proposed = advertised["function"]
            definition = self.definitions.get(proposed["name"])
            if definition is None or canonical_json_bytes(proposed["parameters"]) != canonical_json_bytes(definition["input_schema"]):
                raise ValueError("SDK advertised a tool outside the frozen profile")
        request.headers["X-Wuji-Request-ID"] = str(uuid4())
        self.attempt_id = None
        self.calls = {}

    async def response(self, response):
        if response.status_code != 200:
            return  # The native client propagates the actual HTTP failure.
        attempt = response.headers.get("X-Wuji-Model-Attempt-ID")
        if not attempt or len(attempt) > 220:
            raise ValueError("ModelGate response lacks model-attempt identity")
        if "text/event-stream" not in response.headers.get("content-type", ""):
            raise ValueError("M1 streaming ModelGate response is not native SSE")
        self.attempt_id = attempt

    def parse_response(self, message, contents):
        # Public provider delta hook: retain exact JSON argument fragments before SDK
        # validation/coercion. M1's published schema has only a string path.
        for call in message.tool_calls or []:
            if self.attempt_id is None or call.index is None:
                raise ValueError("tool delta has no proven model response identity")
            item = self.calls.setdefault(call.index, {"id": "", "name": "", "arguments": ""})
            if call.id:
                if item["id"] and item["id"] != call.id:
                    raise ValueError("provider changed a tool-call identity")
                item["id"] = call.id
            if call.function:
                if call.function.name:
                    item["name"] += call.function.name
                if call.function.arguments:
                    item["arguments"] += call.function.arguments
            if len(item["arguments"].encode()) > self.max_bytes:
                raise ValueError("tool arguments exceed published output limit")
        return contents

    def bind(self, context, definition, lineage):
        call_id = context.metadata.get("call_id")
        occurrence = context.metadata.get("function_call_occurrence_id")
        if not isinstance(call_id, str) or not call_id or not isinstance(occurrence, str) or not occurrence or self.attempt_id is None:
            raise ValueError("missing actual FunctionInvocationContext identity")
        matches = [value for value in self.calls.values() if value["id"] == call_id]
        if len(matches) != 1 or matches[0]["name"] != definition["name"]:
            raise ValueError("function does not match the observed model response")
        original = matches[0]["arguments"]
        arguments = strict_json_loads(original)
        supplied = context.arguments
        if hasattr(supplied, "model_dump"):
            supplied = supplied.model_dump(mode="python")
        if canonical_json_bytes(arguments) != canonical_json_bytes(dict(supplied)):
            raise ValueError("SDK changed native function arguments")
        request = ToolCallRequest.model_validate({
            "session_lineage": lineage,
            "message_id": "model-attempt:" + self.attempt_id + ":choice:0",
            "provider_call_id": call_id, "sdk_content_id": occurrence,
            "tool_definition_ref": definition["ref"], "arguments": arguments,
        })
        record = {
            "model_attempt_id": self.attempt_id, "request": request.model_dump(mode="json"),
            "native_arguments": original,
        }
        if record not in self.mapping:
            self.mapping.append(record)
        return request


class GateFunctions(FunctionMiddleware):
    def __init__(self, *, definitions, identity, lineage, client, url):
        self.definitions = {d["name"]: d for d in definitions}
        self.identity, self.lineage, self.client, self.url = identity, lineage, client, url
        self.receipts = []
        self._invocation = ContextVar("wuji_gate_invocation", default=None)

    async def process(self, context, call_next):
        token = None
        try:
            definition = self.definitions[context.function.name]
            request = self.identity.bind(context, definition, self.lineage)
            token = self._invocation.set(request)
            await call_next()
        except Exception as error:
            # MAF ordinary tool errors become model input. Enforcement failures must
            # escape the native loop instead of becoming an invitation to retry.
            raise MiddlewareFailure("Wuji ToolGate invocation failed") from error
        finally:
            if token is not None:
                self._invocation.reset(token)

    def registered_tools(self):
        result = []
        for definition in self.definitions.values():
            if definition["allowed_target_kinds"] != ["workspace_read"] or definition["approval_required"]:
                raise ValueError("M1 only supports published fresh workspace reads")

            async def invoke(**arguments):
                request = self._invocation.get()
                if request is None or request.arguments != arguments:
                    raise ValueError("function called outside the verified SDK middleware")
                response = await self.client.post(
                    self.url, content=canonical_json_bytes(request.model_dump(mode="python")),
                )
                response.raise_for_status()
                receipt = ToolCallReceipt.model_validate(strict_json_loads(response.content))
                self.receipts.append(receipt)
                if receipt.status.value != "complete" or receipt.evidence_receipt is None or receipt.evidence_receipt.status.value != "accepted" or receipt.evidence_receipt.observation_ref is None or receipt.result_ref is None:
                    raise ValueError("ToolGate did not deliver complete durable evidence")
                return canonical_json_bytes(receipt.model_dump(mode="python")).decode()

            result.append(FunctionTool(
                name=definition["name"],
                description=definition["input_schema"].get("description", ""),
                input_model=definition["input_schema"], func=invoke,
                approval_mode="never_require",
            ))
        return result
