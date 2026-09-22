"""Public SDK function identity -> the existing HTTP ToolGate."""

import asyncio
from contextvars import ContextVar
from hashlib import sha256
from urllib.parse import quote
from uuid import uuid4

from agent_framework import Content, FunctionMiddleware, FunctionTool, MiddlewareFailure

from wuji_maf_worker.remote_host import HostTransportError, error_code_from_bytes

from wuji_core.contracts.admission import ToolCallRequest, ToolCallReceipt
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.admission.model_material import (
    MODEL_MATERIAL_SCHEMA,
    omitted_model_material,
    validate_model_material_v2,
)
from wuji_maf_worker.capability_manifest import KNOWLEDGE_SCHEMAS


class FunctionBudget:
    """Per-Work counters persisted inside the native Session state."""

    SOURCE_ID = "wuji_function_usage"

    def __init__(self, limits):
        self.limits = {
            key: int(getattr(value, "root", value))
            for key, value in dict(limits).items()
        }
        self.state = None

    def bind(self, session):
        state = session.state.setdefault(self.SOURCE_ID, {
            "total": 0,
            "session_state": 0,
            "knowledge_read": 0,
            "environment_action": 0,
            "occurrences": [],
        })
        if (
            not isinstance(state, dict)
            or any(type(state.get(key)) is not int or state[key] < 0 for key in (
                "total", "session_state", "knowledge_read", "environment_action"
            ))
            or not isinstance(state.get("occurrences"), list)
        ):
            raise ValueError("published function counters are invalid")
        self.state = state

    def consume(self, *, category, occurrence):
        if self.state is None or category not in {
            "session_state", "knowledge_read", "environment_action"
        } or not isinstance(occurrence, str) or not occurrence:
            raise ValueError("function budget is not bound to an exact occurrence")
        if occurrence in self.state["occurrences"]:
            raise ValueError("native function occurrence was already consumed")
        category_limit = self.limits[category + "_per_work"]
        if (
            self.state["total"] >= self.limits["total_per_work"]
            or self.state[category] >= category_limit
        ):
            raise ValueError("published function limit exhausted")
        self.state["total"] += 1
        self.state[category] += 1
        self.state["occurrences"].append(occurrence)


def _difference_paths(left, right, path="$", *, limit=16):
    if limit <= 0:
        return [path + ":more"]
    if type(left) is not type(right):
        return [path + ":type"]
    if isinstance(left, dict):
        differences = [path + "." + key + ":key" for key in sorted(set(left) ^ set(right))]
        for key in sorted(set(left) & set(right)):
            differences.extend(
                _difference_paths(
                    left[key],
                    right[key],
                    path + "." + key,
                    limit=limit - len(differences),
                )
            )
            if len(differences) >= limit:
                break
        return differences[:limit]
    if isinstance(left, list):
        differences = [] if len(left) == len(right) else [path + ":length"]
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            differences.extend(
                _difference_paths(
                    left_item,
                    right_item,
                    f"{path}[{index}]",
                    limit=limit - len(differences),
                )
            )
            if len(differences) >= limit:
                break
        return differences[:limit]
    return [] if left == right else [path]


class ModelCallIdentity:
    """Gate-observed calls, including identity retained before native approval."""

    def __init__(self, definitions, *, max_bytes, require_initial_tool=False,
                 capability_manifest=()):
        if type(require_initial_tool) is not bool:
            raise ValueError("initial tool requirement must be explicit")
        self.definitions = {d["name"]: d for d in definitions}
        self.capability_manifest = {
            item["name"]: item for item in capability_manifest
        }
        if len(self.capability_manifest) != len(tuple(capability_manifest)):
            raise ValueError("capability manifest function names must be unique")
        self.max_bytes = max_bytes
        self.require_initial_tool = require_initial_tool
        self.attempt_id = None
        self.calls = {}
        self.mapping = []
        self.local_mapping = []
        self._restored = {}
        self._pending_contents = {}
        self._decisions = {}
        self._published_bindings = {}
        self._lineage = None

    async def request(self, request):
        body = strict_json_loads(request.content)
        if body.get("n", 1) != 1 or body.get("stream") is not True:
            raise ValueError("M1 requires single-choice native streaming")
        advertised_tools = body.get("tools", [])
        if (
            not isinstance(body.get("max_completion_tokens"), int)
            or isinstance(body.get("max_completion_tokens"), bool)
            or "max_tokens" in body
            or body.get("stream_options") != {"include_usage": True}
            or (
                advertised_tools
                and body.get("parallel_tool_calls") is not False
            )
            or (
                "parallel_tool_calls" in body
                and body["parallel_tool_calls"] is not False
            )
            or (
                self.require_initial_tool
                and advertised_tools
                and not self.mapping
                and body.get("tool_choice") != "required"
            )
        ):
            raise ValueError("SDK request does not match the frozen M1 transport")
        for advertised in advertised_tools:
            proposed = advertised["function"]
            definition = self.definitions.get(proposed["name"])
            capability = self.capability_manifest.get(proposed["name"])
            if self.capability_manifest:
                if (
                    capability is None
                    or sha256(canonical_json_bytes(proposed["parameters"])).hexdigest()
                    != capability["input_schema_digest"]
                    or capability["category"] == "environment_action"
                    and (
                        definition is None
                        or canonical_json_bytes(proposed["parameters"])
                        != canonical_json_bytes(definition["input_schema"])
                    )
                ):
                    raise ValueError("SDK advertised a function outside the capability manifest")
            elif definition is None or canonical_json_bytes(proposed["parameters"]) != canonical_json_bytes(definition["input_schema"]):
                raise ValueError("SDK advertised a tool outside the frozen profile")
        if self.capability_manifest and {
            item["function"]["name"] for item in advertised_tools
        } != set(self.capability_manifest):
            raise ValueError("SDK visible functions differ from the capability manifest")
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
        approval = context.metadata.get("approval_response")
        if approval is not None:
            binding = self._restored.get(occurrence)
            decision = self._decisions.get(occurrence)
            pending = self._pending_contents.get(occurrence)
            approval_body = approval.to_dict() if isinstance(approval, Content) else None
            expected_approval = (
                pending.to_function_approval_response(approved=True).to_dict()
                if pending is not None
                else None
            )
            approval_request_id = None
            if approval_body is not None:
                properties = approval_body.get("additional_properties") or {}
                if isinstance(properties, dict):
                    approval_request_id = properties.pop(
                        "_approval_request_id", None
                    )
                if approval_request_id is None:
                    # The SDK only records the private request id when it rebinds
                    # a response through a caller-owned approval session. A
                    # decision restored by the Host keeps the same native
                    # identity on the public approval content instead.
                    approval_request_id = approval_body.get("id")
            checks = {
                "binding": binding is not None,
                "pending": pending is not None,
                "decision": decision is not None,
                "approved": decision is not None and decision.decision == "approve",
                "lineage": lineage == self._lineage,
                "call": binding is not None and call_id == binding.provider_call_id,
                "definition": binding is not None
                and definition["ref"] == binding.tool_definition_ref,
                "approval_type": isinstance(approval, Content),
                "approval_request_id": pending is not None
                and approval_request_id == pending.id,
                "approval_content": approval_body is not None
                and expected_approval is not None
                and canonical_json_bytes(approval_body)
                == canonical_json_bytes(expected_approval),
            }
            if not all(checks.values()):
                failed = ",".join(name for name, matched in checks.items() if not matched)
                if not checks["approval_content"] and approval_body is not None and expected_approval is not None:
                    differences = _difference_paths(
                        approval_body,
                        expected_approval,
                    )
                    failed += "[" + ";".join(differences) + "]"
                raise ValueError(
                    "approval callback differs from the fixed original "
                    "call/decision: "
                    + failed
                )
            arguments = strict_json_loads(binding.native_arguments)
            supplied = context.arguments
            if hasattr(supplied, "model_dump"):
                supplied = supplied.model_dump(mode="python")
            if canonical_json_bytes(arguments) != canonical_json_bytes(dict(supplied)):
                raise ValueError("restored SDK arguments differ from the original call")
            return ToolCallRequest.model_validate({
                "session_lineage": lineage, "message_id": binding.message_id,
                "provider_call_id": binding.provider_call_id,
                "sdk_content_id": binding.sdk_content_id,
                "sdk_approval_id": binding.sdk_approval_id,
                "tool_definition_ref": binding.tool_definition_ref,
                "arguments": arguments, "approval_ref": decision.approval_ref,
            })
        if occurrence in self._restored:
            raise ValueError("a published native call cannot execute without its original approval")
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

    def bind_local(self, context):
        name = context.function.name
        capability = self.capability_manifest.get(name)
        call_id = context.metadata.get("call_id")
        occurrence = context.metadata.get("function_call_occurrence_id")
        if (
            capability is None
            or capability["category"] == "environment_action"
            or not isinstance(call_id, str)
            or not call_id
            or not isinstance(occurrence, str)
            or not occurrence
            or self.attempt_id is None
        ):
            raise ValueError("unpublished local function invocation")
        matches = [value for value in self.calls.values() if value["id"] == call_id]
        if len(matches) != 1 or matches[0]["name"] != name:
            raise ValueError("local function differs from the observed model response")
        original = matches[0]["arguments"]
        arguments = strict_json_loads(original)
        supplied = context.arguments
        if hasattr(supplied, "model_dump"):
            supplied = supplied.model_dump(mode="python")
        if canonical_json_bytes(arguments) != canonical_json_bytes(dict(supplied)):
            raise ValueError("SDK changed native local-function arguments")
        self.local_mapping.append({
            "model_attempt_id": self.attempt_id,
            "provider_call_id": call_id,
            "sdk_content_id": occurrence,
            "name": name,
            "category": capability["category"],
            "arguments_digest": sha256(canonical_json_bytes(arguments)).hexdigest(),
        })
        return capability, occurrence

    def capture_pending(self, response, lineage):
        """Bind at the native return boundary, before FunctionMiddleware exists."""
        pending = []
        seen = set()
        for message in response.messages:
            for content in message.contents:
                if content.type != "function_approval_request":
                    continue
                call = content.function_call
                if (
                    call is None or not content.id or content.id != call.id
                    or content.id in seen or self.attempt_id is None
                ):
                    raise ValueError("native approval has no actual original model identity")
                matches = [value for value in self.calls.values() if value["id"] == call.call_id]
                definition = self.definitions.get(call.name)
                if (
                    len(matches) != 1 or definition is None
                    or matches[0]["name"] != call.name or not definition["approval_required"]
                ):
                    raise ValueError("approval is not the frozen tool from the observed model response")
                original = matches[0]["arguments"]
                arguments = strict_json_loads(original)
                native_arguments = call.arguments
                if isinstance(native_arguments, str):
                    native_arguments = strict_json_loads(native_arguments)
                if canonical_json_bytes(native_arguments) != canonical_json_bytes(arguments):
                    raise ValueError("approval changed the original provider arguments")
                request = ToolCallRequest.model_validate({
                    "session_lineage": lineage,
                    "message_id": "model-attempt:" + self.attempt_id + ":choice:0",
                    "provider_call_id": call.call_id, "sdk_content_id": call.id,
                    "sdk_approval_id": content.id,
                    "tool_definition_ref": definition["ref"], "arguments": arguments,
                })
                self.mapping.append({
                    "model_attempt_id": self.attempt_id,
                    "request": request.model_dump(mode="json"), "native_arguments": original,
                })
                pending.append((content, request))
                seen.add(content.id)
        return tuple(pending)

    def record_receipt(self, request, receipt):
        occurrence = request.sdk_content_id.root
        matches = [record for record in self.mapping if record["request"]["sdk_content_id"] == occurrence]
        if len(matches) != 1:
            raise ValueError("receipt has no unambiguous native occurrence")
        existing = matches[0].get("tool_call_id")
        if existing is not None and existing != receipt.tool_call_id:
            raise ValueError("restored native call acquired a different canonical operation")
        matches[0]["tool_call_id"] = receipt.tool_call_id

    def export_bindings(self):
        from wuji_core.contracts.sessions import NativeCallBinding

        result = []
        for record in self.mapping:
            request = record["request"]
            original = record["native_arguments"]
            published = self._published_bindings.get(request["sdk_content_id"])
            if published is not None:
                if (
                    published.tool_call_id != record.get("tool_call_id")
                    or published.native_arguments != original
                    or published.sdk_content_id != request["sdk_content_id"]
                ):
                    raise ValueError("restored binding changed before export")
                result.append(published)
                continue
            result.append(NativeCallBinding(
                model_attempt_id=record["model_attempt_id"], message_id=request["message_id"],
                provider_call_id=request["provider_call_id"], sdk_content_id=request["sdk_content_id"],
                sdk_approval_id=request.get("sdk_approval_id"),
                tool_definition_ref=request["tool_definition_ref"], native_arguments=original,
                arguments_digest=sha256(canonical_json_bytes(strict_json_loads(original))).hexdigest(),
                tool_call_id=record.get("tool_call_id"),
            ))
        return tuple(result)

    def restore_bindings(self, *, call_bindings, pending_contents, lineage):
        from wuji_maf_worker.approvals import validate_pending

        if self.mapping or self._restored or not lineage:
            raise ValueError("call identities can only be imported into a new runtime")
        self._lineage = lineage
        definitions = {value["ref"]: value for value in self.definitions.values()}
        for binding in call_bindings:
            if binding.tool_definition_ref not in definitions or binding.sdk_content_id in self._restored:
                raise ValueError("published call differs from the fixed tool definitions")
            original = strict_json_loads(binding.native_arguments)
            if sha256(canonical_json_bytes(original)).hexdigest() != binding.arguments_digest:
                raise ValueError("published original arguments digest mismatch")
            if binding.message_id != "model-attempt:" + binding.model_attempt_id + ":choice:0":
                raise ValueError("published call does not retain its original model attempt")
            self._restored[binding.sdk_content_id] = binding
            self._published_bindings[binding.sdk_content_id] = binding
            request = ToolCallRequest.model_validate({
                "session_lineage": lineage, "message_id": binding.message_id,
                "provider_call_id": binding.provider_call_id,
                "sdk_content_id": binding.sdk_content_id, "sdk_approval_id": binding.sdk_approval_id,
                "tool_definition_ref": binding.tool_definition_ref, "arguments": original,
            })
            self.mapping.append({
                "model_attempt_id": binding.model_attempt_id, "request": request.model_dump(mode="json"),
                "native_arguments": binding.native_arguments,
                "tool_call_id": binding.tool_call_id,
            })
        for content in pending_contents:
            binding = self._restored.get(content.id)
            if binding is None or content.function_call.name != definitions[binding.tool_definition_ref]["name"]:
                raise ValueError("pending approval no longer matches its ToolDefinition")
            validate_pending(content, binding)
            self._pending_contents[content.id] = content

    def bind_delivery(self, delivery):
        """Accept only the already-loaded fixed decision payload, never a flag."""
        from wuji_maf_worker.approvals import validate_pending

        decisions = {}
        for decision in delivery.payload.decisions:
            binding = decision.call_binding
            original = self._restored.get(binding.sdk_content_id)
            pending = self._pending_contents.get(binding.sdk_content_id)
            if (
                original is None or original != binding or pending is None
                or canonical_json_bytes(pending.to_dict()) != canonical_json_bytes(decision.pending_content)
                or binding.sdk_content_id in decisions
            ):
                raise ValueError("delivery changed its published original approval")
            validate_pending(pending, binding)
            decisions[binding.sdk_content_id] = decision
        if set(decisions) != set(self._pending_contents):
            raise ValueError("delivery does not resolve the complete original approval batch")
        self._decisions = decisions

    def rejected_decisions(self):
        return tuple(
            self._decisions[key]
            for key in sorted(self._decisions)
            if self._decisions[key].decision == "reject"
        )


class ToolGateRefused(ValueError):
    """A bounded, published refusal code from the platform ToolGate.

    The refusal is still an enforcement outcome: it escapes the native loop
    instead of being handed back as a retry invitation. Only the bounded code
    and HTTP status travel with it, never response text.
    """


def _refusal_failure(refusal):
    failure = MiddlewareFailure("Wuji ToolGate refused the invocation")
    code = getattr(refusal, "code", None)
    if isinstance(code, str) and 1 <= len(code) <= 64 and code.isascii():
        failure.code = code
    status = getattr(refusal, "status_code", None)
    if type(status) is int and 100 <= status <= 599:
        failure.status_code = status
    return failure


class GateFunctions(FunctionMiddleware):
    def __init__(self, *, definitions, identity, lineage, client, url,
                 native_approval=False, material_representation="v1",
                 budget=None, host=None, assignment=None):
        self.definitions = {d["name"]: d for d in definitions}
        self.identity, self.lineage, self.client, self.url = identity, lineage, client, url
        if material_representation not in {"v1", MODEL_MATERIAL_SCHEMA}:
            raise ValueError("unsupported published material representation")
        self.material_representation = material_representation
        self.receipts = []
        self.native_approval = native_approval
        self.pending_receipts = []
        self._invocation = ContextVar("wuji_gate_invocation", default=None)
        self._local_invocation = ContextVar("wuji_local_invocation", default=None)
        self.budget, self.host, self.assignment = budget, host, assignment
        self.knowledge_deliveries = []

    async def process(self, context, call_next):
        token = capability = None
        try:
            name = context.function.name
            capability = self.identity.capability_manifest.get(name)
            if capability is not None and capability["category"] != "environment_action":
                capability, occurrence = self.identity.bind_local(context)
                if self.budget is None:
                    raise ValueError("local function has no published budget")
                self.budget.consume(
                    category=capability["category"], occurrence=occurrence
                )
                token = self._local_invocation.set({
                    "name": name, "occurrence": occurrence,
                    "category": capability["category"],
                })
            else:
                definition = self.definitions[name]
                request = self.identity.bind(context, definition, self.lineage)
                if self.budget is not None:
                    self.budget.consume(
                        category="environment_action",
                        occurrence=context.metadata["function_call_occurrence_id"],
                    )
                token = self._invocation.set(request)
            await call_next()
        except ToolGateRefused as refusal:
            # Keep the escape, but name the refusing predicate so the child's
            # bounded exit signal is not an opaque MiddlewareFailure.
            raise _refusal_failure(refusal) from refusal
        except Exception as error:
            # MAF ordinary tool errors become model input. Enforcement failures must
            # escape the native loop instead of becoming an invitation to retry.
            raise MiddlewareFailure("Wuji ToolGate invocation failed") from error
        finally:
            if token is not None:
                if capability is not None and capability["category"] != "environment_action":
                    self._local_invocation.reset(token)
                else:
                    self._invocation.reset(token)

    def registered_knowledge_tools(self):
        if self.host is None or self.assignment is None:
            return []

        async def call(method, **kwargs):
            try:
                return await asyncio.to_thread(
                    method, self.assignment, **kwargs
                )
            except HostTransportError as error:
                code = getattr(error, "code", None)
                if getattr(error, "status_code", None) == 422 and code in {
                    "INVALID_REFERENCE", "INVALID_SCHEMA", "REPRESENTATION_LIMIT",
                    "UNSUPPORTED_MEDIA",
                }:
                    return canonical_json_bytes({
                        "status": "rejected", "code": code, "retryable": False,
                    }).decode()
                raise

        def invocation(name):
            value = self._local_invocation.get()
            if value is None or value["name"] != name or value["category"] != "knowledge_read":
                raise ValueError("knowledge function called outside verified middleware")
            return value

        async def knowledge_list(snapshot_id, material_types=(), cursor=None, limit=10):
            current = invocation("knowledge_list")
            value = await call(
                self.host.knowledge_list,
                snapshot_id=snapshot_id,
                material_types=tuple(material_types),
                cursor=cursor,
                limit=limit,
                native_occurrence=current["occurrence"],
            )
            if isinstance(value, str):
                return value
            return canonical_json_bytes(value.model_dump(mode="json")).decode()

        async def knowledge_read(snapshot_id, ref, selector):
            current = invocation("knowledge_read")
            value = await call(
                self.host.knowledge_read,
                snapshot_id=snapshot_id,
                ref=ref,
                selector=selector,
                native_occurrence=current["occurrence"],
            )
            if isinstance(value, str):
                return value
            self.knowledge_deliveries.append({
                "delivery_id": value.delivery_id,
                "representation_digest": value.representation_digest.root,
            })
            return canonical_json_bytes(value.model_dump(mode="json")).decode()

        async def knowledge_refresh(snapshot_id, neighborhood):
            current = invocation("knowledge_refresh")
            value = await call(
                self.host.knowledge_refresh,
                snapshot_id=snapshot_id,
                native_occurrence=current["occurrence"],
            )
            if isinstance(value, str):
                return value
            self.knowledge_deliveries.append({
                "delivery_id": value.delivery_id,
                "representation_digest": value.representation_digest.root,
            })
            return canonical_json_bytes(value.model_dump(mode="json")).decode()

        functions = {
            "knowledge_list": knowledge_list,
            "knowledge_read": knowledge_read,
            "knowledge_refresh": knowledge_refresh,
        }
        selected = {
            name for name, capability in self.identity.capability_manifest.items()
            if capability["category"] == "knowledge_read"
        }
        return [
            FunctionTool(
                name=name,
                description={
                    "knowledge_list": "List authorized fixed records without reading their content.",
                    "knowledge_read": "Read one exact authorized record field set or safe text range.",
                    "knowledge_refresh": "Refresh only the current problem's authorized record neighborhood.",
                }[name],
                input_model=schema,
                func=functions[name],
                approval_mode="never_require",
            )
            for name, schema in KNOWLEDGE_SCHEMAS.items()
            if name in selected
        ]

    def registered_tools(self):
        result = []
        for definition in self.definitions.values():
            if definition["allowed_target_kinds"] not in (
                ["workspace_read"],
                ["http_target"],
            ) or (definition["approval_required"] and not self.native_approval):
                raise ValueError(
                    "only one published kind per tool is exposed to the child"
                )

            async def invoke(**arguments):
                request = self._invocation.get()
                if request is None or request.arguments != arguments:
                    raise ValueError("function called outside the verified SDK middleware")
                response = await self.client.post(
                    self.url, content=canonical_json_bytes(request.model_dump(mode="python")),
                )
                if response.status_code != 200:
                    # Bounded classification on the refusal path only: the
                    # success body is never consumed here.
                    refusal = ToolGateRefused("ToolGate refused the tool call")
                    refusal.status_code = response.status_code
                    code = error_code_from_bytes(
                        response.content,
                        encoding=response.headers.get("content-encoding", "identity"),
                    )
                    if code is not None:
                        refusal.code = code
                    raise refusal
                receipt = ToolCallReceipt.model_validate(strict_json_loads(response.content))
                if self.native_approval:
                    self.identity.record_receipt(request, receipt)
                self.receipts.append(receipt)
                if receipt.status.value != "complete" or receipt.evidence_receipt is None or receipt.evidence_receipt.status.value != "accepted" or receipt.evidence_receipt.observation_ref is None or receipt.result_ref is None:
                    raise ValueError("ToolGate did not deliver complete durable evidence")
                return await self._delivered_content(receipt)

            result.append(FunctionTool(
                name=definition["name"],
                description=definition["input_schema"].get("description", ""),
                input_model=definition["input_schema"], func=invoke,
                approval_mode="always_require" if definition["approval_required"] else "never_require",
            ))
        return result

    async def _delivered_content(self, receipt):
        """What the model sees: the canonical receipt plus bounded real bytes.

        The receipt itself never changes, so every durable digest stays valid.
        The captured body is delivered beside it, exactly once, under the
        published output bound; when the platform cannot deliver a body it says
        which fixed reason applies instead of leaving the model to guess.
        """

        document = receipt.model_dump(mode="python")
        if self.material_representation == MODEL_MATERIAL_SCHEMA:
            try:
                response = await self.client.get(
                    self.url + "/" + quote(receipt.tool_call_id, safe="") + "/material",
                    params={"representation": MODEL_MATERIAL_SCHEMA},
                )
                material = None
                if response.status_code == 200:
                    material = validate_model_material_v2(
                        strict_json_loads(response.content),
                        tool_call_id=receipt.tool_call_id,
                        result_ref=receipt.result_ref,
                    )
                if material is None:
                    material = omitted_model_material(receipt.tool_call_id, "delivery_error")
            except Exception:
                material = omitted_model_material(receipt.tool_call_id, "delivery_error")
            document["material"] = material.model_dump(mode="python")
            return canonical_json_bytes(document).decode()
        material = None
        try:
            response = await self.client.get(
                self.url + "/" + quote(receipt.tool_call_id, safe="") + "/material"
            )
            if response.status_code == 200:
                material = strict_json_loads(response.content)
        except Exception:
            material = None
        if not isinstance(material, dict) or material.get("tool_call_id") != receipt.tool_call_id:
            document["material_omitted"] = "not_delivered"
        elif material.get("status") == "delivered":
            document["material"] = {
                "encoding": material.get("encoding"),
                "byte_length": material.get("byte_length"),
                "text": material.get("text"),
            }
        else:
            document["material_omitted"] = material.get("reason") or "not_delivered"
        return canonical_json_bytes(document).decode()

    async def register_pending(self, response):
        if not self.native_approval:
            raise ValueError("M1 does not permit native approval")
        pending = self.identity.capture_pending(response, self.lineage)
        for _content, request in pending:
            response = await self.client.post(
                self.url, content=canonical_json_bytes(request.model_dump(mode="python")),
            )
            if response.status_code != 200:
                refusal = ToolGateRefused("ToolGate refused the pending approval call")
                refusal.status_code = response.status_code
                code = error_code_from_bytes(
                    response.content,
                    encoding=response.headers.get("content-encoding", "identity"),
                )
                if code is not None:
                    refusal.code = code
                raise refusal
            receipt = ToolCallReceipt.model_validate(strict_json_loads(response.content))
            if (
                receipt.status.value != "pending_approval"
                or receipt.tool_attempt_id is not None or receipt.evidence_receipt is not None
                or receipt.result_ref is not None
            ):
                raise ValueError("initial native approval did not remain an unexecuted pending call")
            self.identity.record_receipt(request, receipt)
            self.pending_receipts.append(receipt)
        return pending
