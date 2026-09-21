"""Canonical tool operations, receiver permits and evidence-first delivery."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from hmac import compare_digest
import os
from pathlib import Path, PurePosixPath
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, AwareDatetime
from starlette.concurrency import run_in_threadpool

from wuji_core.contracts.admission import (
    ToolCallRequest, ToolCallReceipt, ToolSettlementReceipt, ToolSettlementRequest,
)
from wuji_core.contracts.envelopes import RunIdentity, CaptureEnvelope, BlobRef
from wuji_core.contracts.generated import ToolResultMaterial, Reason as MaterialOmission
from wuji_core.admission.model_material import (
    MODEL_MATERIAL_SCHEMA,
    omitted_model_material,
    render_http_exchange_v2,
)
from wuji_core.http import strict_json_loads
from wuji_core.http.auth import Principal
from wuji_core.persistence.uow import AccessContext, DomainError, row, json_text
from wuji_core.admission.registry import TaskAdmissionConfig, RuntimeProfile
from wuji_core.admission import target_scope
from wuji_core.admission.mechanism_fixture import (
    authorization_scope,
    http_target_allowed,
)
from wuji_core.admission.common import audit, consume_attempt, current_run, digest, allocate_output
from wuji_core.admission.ledger import tool_receipt


def _string_rule(rule, allowed, *, minimum=None, maximum=None):
    if (
        not isinstance(rule, dict)
        or rule.get("type") != "string"
        or set(rule) - allowed
    ):
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    for key in ("minLength", "maxLength"):
        if key in rule and (type(rule[key]) is not int or rule[key] < 0):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    if minimum is not None and rule.get("minLength", 0) < minimum:
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    if maximum is not None and rule.get("maxLength", 0) > maximum:
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    if "enum" in rule and (
        not isinstance(rule["enum"], list)
        or not rule["enum"]
        or not all(isinstance(value, str) for value in rule["enum"])
    ):
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    return rule


def validate_input_schema(schema):
    """Two deliberately finite published schemas, not a JSON-Schema engine.

    A workspace read takes exactly ``{"path"}``; a target tool takes exactly
    ``{"url", "method"}`` with a bounded URL and a read-only method enum.
    """

    if (
        not isinstance(schema, dict)
        or schema.get("type") != "object"
        or schema.get("additionalProperties") is not False
        or set(schema)
        - {"type", "properties", "required", "additionalProperties", "description", "$schema"}
    ):
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    if schema.get("required") == ["path"] and set(properties) == {"path"}:
        _string_rule(
            properties["path"],
            {"type", "description", "minLength", "maxLength", "enum"},
        )
        return
    if schema.get("required") == ["url", "method"] and set(properties) == {
        "url",
        "method",
    }:
        url = _string_rule(
            properties["url"],
            {"type", "description", "minLength", "maxLength", "pattern"},
            minimum=1,
            maximum=target_scope.MAX_URL_LENGTH,
        )
        method = _string_rule(
            properties["method"], {"type", "description", "enum"}
        )
        if (
            url.get("maxLength", 0) > target_scope.MAX_URL_LENGTH
            or not method.get("enum")
            or not set(method["enum"]).issubset(target_scope.READ_ONLY_METHODS)
        ):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        return
    raise DomainError("CAPABILITY_UNAVAILABLE", 503)


def tool_kind(definition):
    """One tool serves exactly one target kind; a flag cannot widen it."""

    kinds = list(getattr(definition, "allowed_target_kinds", []) or [])
    if kinds not in (["workspace_read"], ["http_target"]):
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    return kinds[0]


def capture_condition(kind):
    return (
        "registered workspace read"
        if kind == "workspace_read"
        else "registered http target exchange"
    )


def task_definition(tx):
    """The immutable Task definition, or an empty document on broken storage."""

    raw = (tx.task or {}).get("definition_json")
    if not isinstance(raw, str):
        return {}
    try:
        document = strict_json_loads(raw)
    except ValueError:
        return {}
    return document if isinstance(document, dict) else {}


def task_scope(tx):
    """The Task's approved assets; an absent or broken scope approves nothing."""

    return authorization_scope(task_definition(tx))


def require_http_target_role(tx, work):
    """Repeat Scheduler's role/mode/fixture decision at ToolAdmission."""

    try:
        allowed = http_target_allowed(task_definition(tx), work.get("kind"), allow_legacy=True)
    except ValueError as error:
        raise DomainError("CAPABILITY_UNAVAILABLE", 503) from error
    if not allowed:
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)


def _http_arguments(definition, arguments, scope):
    """A read-only HTTP exchange whose target the platform already approved."""

    validate_input_schema(definition.input_schema)
    if not isinstance(arguments, dict) or set(arguments) != {"url", "method"}:
        raise DomainError("INVALID_SCHEMA", 422)
    url, method = arguments.get("url"), arguments.get("method")
    if not target_scope.method_allowed(method):
        raise DomainError("INVALID_SCHEMA", 422)
    properties = definition.input_schema.get("properties") or {}
    rule = properties.get("url") or {}
    if (
        not isinstance(url, str)
        or len(url) < rule.get("minLength", 0)
        or len(url) > rule.get("maxLength", target_scope.MAX_URL_LENGTH)
        or ("enum" in rule and url not in rule["enum"])
    ):
        raise DomainError("INVALID_SCHEMA", 422)
    method_rule = properties.get("method") or {}
    if "enum" in method_rule and method not in method_rule["enum"]:
        raise DomainError("INVALID_SCHEMA", 422)
    return target_scope.require_in_scope(scope, url)


def _arguments(definition, arguments):
    validate_input_schema(definition.input_schema)
    value = arguments.get("path")
    rule = definition.input_schema["properties"]["path"]
    if set(arguments) != {"path"} or not isinstance(value, str) or not 1 <= len(value) <= 4096 or "\x00" in value or "\\" in value or PurePosixPath(value).is_absolute() or any(part in {"..", ".", ""} for part in value.split("/")):
        raise DomainError("INVALID_SCHEMA", 422)
    if len(value) < rule.get("minLength", 0) or len(value) > rule.get("maxLength", 4096) or ("enum" in rule and value not in rule["enum"]):
        raise DomainError("INVALID_SCHEMA", 422)


class ToolExecutionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    tool_attempt_id: str
    receiver_id: str
    receipt_id: str
    status: Literal["not_started", "running", "exited", "unknown"]
    started_at: AwareDatetime | None
    exited_at: AwareDatetime | None
    source_receipt: dict
    output: bytes | None
    media_type: str | None
    completeness: Literal["complete", "partial", "unknown"]
    error_code: str | None


@dataclass(frozen=True)
class ToolPermit:
    tool_call_id: str
    tool_attempt_id: str | None
    identity: RunIdentity
    executor_ref: str
    tool_definition_ref: str
    arguments: dict = field(repr=False)
    arguments_digest: str
    resource_keys: tuple[str, ...]
    expires_at: datetime
    execution_token: str = field(repr=False)
    access: AccessContext = field(repr=False)
    runtime: RuntimeProfile = field(repr=False)
    replay: bool = False

    def stored(self):
        return {"tool_call_id": self.tool_call_id, "tool_attempt_id": self.tool_attempt_id, "identity": self.identity.model_dump(mode="json"), "executor_ref": self.executor_ref, "tool_definition_ref": self.tool_definition_ref, "arguments": self.arguments, "arguments_digest": self.arguments_digest, "resource_keys": list(self.resource_keys), "expires_at": self.expires_at.isoformat(), "execution_token": self.execution_token, "subject": self.access.principal.subject, "token_id": self.access.principal.token_id, "roles": sorted(self.access.principal.roles), "runtime": self.runtime.model_dump(mode="json")}

    @classmethod
    def restore(cls, value, *, request_id, replay=True):
        identity = RunIdentity.model_validate(value["identity"])
        # These are the original server-verified issuer fields from the stored permit,
        # never a client-selected controller role or arbitrary execution identity.
        access = AccessContext(Principal(value["subject"], identity.tenant_id, frozenset(value["roles"]), value["token_id"]), request_id)
        return cls(value["tool_call_id"], value["tool_attempt_id"], identity, value["executor_ref"], value["tool_definition_ref"], value["arguments"], value["arguments_digest"], tuple(value["resource_keys"]), datetime.fromisoformat(value["expires_at"]), value["execution_token"], access, RuntimeProfile.model_validate(value["runtime"]), replay)


@dataclass
class PreparedToolCall:
    call: dict
    request: ToolCallRequest
    definition: object
    executor: object
    config: TaskAdmissionConfig
    run: dict
    target: str | None = None


class ToolExecutorPort(Protocol):
    async def dispatch(self, permit: ToolPermit) -> ToolExecutionReceipt: ...
    async def query(self, permit: ToolPermit) -> ToolExecutionReceipt: ...
    async def cancel(self, permit: ToolPermit, *, reason: str) -> ToolExecutionReceipt: ...


def _call(tx, call_id):
    value = row(tx.connection.execute("SELECT * FROM vnext.tool_call WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_call_id=%s AND access_level<=%s", (*tx.owner, call_id, tx.permissions["clearance"])))
    if not value:
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")
    return value


def _attempt(tx, attempt_id):
    value = row(tx.connection.execute("SELECT * FROM vnext.tool_attempt WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s", (*tx.owner, attempt_id)))
    if not value:
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")
    return value


def _open_operations(tx, run_id):
    """Count the Run's durable operations the platform has not closed yet.

    The count is derived from platform records only: a Run cannot make its own
    operation set look closed, and a producer that never registered anything
    contributes zero rather than blocking every Run that made no tool call.
    """

    query = (
        "SELECT count(*) FROM vnext.{} x WHERE x.tenant_id=%s AND x.project_id=%s"
        " AND x.task_id=%s AND x.agent_run_id=%s AND {}"
    )
    counts = {}
    for name, table, predicate in (
        ("tool_attempts", "tool_attempt",
         "x.status IS NOT NULL AND x.status NOT IN ('complete','cancelled','failed')"),
        ("model_calls", "model_call", "x.inflight"),
        ("resource_reservations", "resource_reservation", "x.state<>'released'"),
    ):
        counts[name] = tx.connection.execute(
            query.format(table, predicate), (*tx.owner, run_id)
        ).fetchone()[0]
    return counts


def operation_axes_closed(tx, run_id):
    """Whether every durable operation axis of one Run is provably closed."""

    return sum(_open_operations(tx, run_id).values()) == 0


def settle_operation_set(tx, run_id, *, basis="durable_tool_attempt_receipts"):
    """Recompute one Run's operation settlement from durable platform records.

    The Run states it will start no further operation, and the platform derives
    the status here. Another producer's unresolved fact is never erased; a row
    this function already owns is refreshed in place.
    """

    unsettled = tx.connection.execute("SELECT 1 FROM vnext.tool_attempt WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND status IS NOT NULL AND status NOT IN ('complete','cancelled','failed') LIMIT 1", (*tx.owner, run_id)).fetchone()
    old = row(tx.connection.execute("SELECT * FROM vnext.run_operation_settlement WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s", (*tx.owner, run_id)))
    if old and old["status"] != "settled" and strict_json_loads(old["source_receipt_json"]).get("producer") != "p06":
        return old["status"]  # Another producer's unresolved operation must not be erased.
    status = "pending" if unsettled else "settled"
    tx.connection.execute("INSERT INTO vnext.run_operation_settlement(tenant_id,project_id,task_id,agent_run_id,status,source_receipt_json) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(tenant_id,project_id,task_id,agent_run_id) DO UPDATE SET status=EXCLUDED.status,source_receipt_json=EXCLUDED.source_receipt_json", (*tx.owner, run_id, status, json_text({"producer": "p06", "basis": basis})))
    return status


def _settlement(tx, run_id):
    return settle_operation_set(tx, run_id)


def close_operation_set(tx, run_id):
    """Close the calling Run's own operation set from durable platform records.

    A Run that registered no operation (for example one refused before its first
    tool attempt) owns an empty operation set. The Run may say that it will
    start no further operation, but the status is still computed here: while any
    durable operation is open the row stays ``pending``, and a settlement
    already published by another producer keeps its own receipt.
    """

    existing = row(tx.connection.execute("SELECT * FROM vnext.run_operation_settlement WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s", (*tx.owner, run_id)))
    if existing is not None and existing["status"] == "settled":
        return "settled", 0
    if existing is not None and strict_json_loads(existing["source_receipt_json"]).get("producer") != "p06":
        # Another producer owns this Run's settlement facts; never erase them.
        return existing["status"], 0
    counts = _open_operations(tx, run_id)
    open_operations = sum(counts.values())
    if existing is None and open_operations and not counts["tool_attempts"]:
        # The Run never opened a tool operation, so no settlement row may exist
        # yet: the empty set is only closed once every axis is closed too.
        return "pending", open_operations
    tx.connection.execute(
        "INSERT INTO vnext.run_operation_settlement(tenant_id,project_id,task_id,agent_run_id,status,source_receipt_json) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(tenant_id,project_id,task_id,agent_run_id) DO UPDATE SET status=EXCLUDED.status,source_receipt_json=EXCLUDED.source_receipt_json",
        (*tx.owner, run_id, "pending" if open_operations else "settled",
         json_text({"producer": "p06", "basis": "run_closed_operation_set",
                    "open_operations": counts})),
    )
    return ("pending" if open_operations else "settled"), open_operations


class ToolAdmission:
    def __init__(self, uow, *, registry, ledger, approvals=None):
        self.uow, self.registry, self.ledger = uow, registry, ledger
        self.approvals = approvals

    def authorize(self, access, request):
        binding = self.registry.binding(access)
        try:
            with self.uow.transaction(access, binding.identity.task_id, capability="tool_request") as tx:
                prepared = self.prepare_in_transaction(tx, request)
                approval_ref = prepared.request.approval_ref
                if approval_ref is None:
                    return self.authorize_in_transaction(tx, prepared)
                if self.approvals is None or not prepared.definition.approval_required:
                    raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                approval = self.approvals.bind_operation_in_transaction(tx, prepared, approval_ref)
                permit = self.authorize_in_transaction(tx, prepared, approval_binding=approval)
                self.approvals.finish_binding_in_transaction(tx, approval, permit)
                return permit
        except DomainError as exc:
            self.ledger.rejected(access, binding.identity.task_id, "tool_request", exc.code)
            raise

    def prepare_in_transaction(self, tx, request):
        if tx.purpose != "tool_request" or tx.run_binding is None:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        request = ToolCallRequest.model_validate(request)
        config = self.registry.config(tx)
        run, work = current_run(tx, config)
        allowed = set(config.allowed_tool_refs) & set(config.runtime.allowed_tool_refs) & set(tx.run_binding.allowed_tool_refs)
        if request.session_lineage != tx.run_binding.session_lineage or request.tool_definition_ref not in allowed:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        definition = self.registry.tool(tx, request.tool_definition_ref)
        executor = self.registry.executor(tx, definition.executor_ref)
        if definition.ref not in executor.allowed_tool_refs or executor.receiver_id != run["receiver_id"] or executor.environment_ref != run["environment_ref"]:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        kind = tool_kind(definition)
        target = None
        if kind == "workspace_read":
            _arguments(definition, request.arguments)
        else:
            require_http_target_role(tx, work)
            # The platform, never the model or the tool, decides whether this
            # concrete target is inside the Task's approved scope.
            target = _http_arguments(
                definition, request.arguments, task_scope(tx)
            ).key
        values = (request.session_lineage, request.message_id, request.provider_call_id, request.tool_definition_ref)
        call = row(tx.connection.execute("SELECT * FROM vnext.tool_call WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND session_lineage=%s AND message_id=%s AND provider_call_id=%s AND tool_definition_version=%s", (*tx.owner, *values)))
        request_values = request.model_dump(mode="python")
        call_digest = digest({"tool_definition_ref": request.tool_definition_ref, "arguments": request.arguments, "sdk_content_id": request_values["sdk_content_id"], "sdk_approval_id": request_values["sdk_approval_id"]})
        if call:
            if call["access_level"] > tx.permissions["clearance"] or call["work_item_id"] != work["work_item_id"]:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            if call["input_digest"] != call_digest:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            if request.message_id.startswith("model-attempt:") and request.message_id.endswith(":choice:0"):
                model_id = request.message_id[len("model-attempt:"):-len(":choice:0")]
                origin = tx.connection.execute("SELECT agent_run_id FROM vnext.model_call WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND model_attempt_id=%s", (*tx.owner, model_id)).fetchone()
                if origin is None:
                    raise DomainError("INVALID_REFERENCE", 422)
                if origin[0] != run["agent_run_id"]:
                    transfer = tx.connection.execute("SELECT 1 FROM vnext.session_holder h JOIN vnext.session_manifest s USING(tenant_id,project_id,task_id,manifest_ref) WHERE h.tenant_id=%s AND h.project_id=%s AND h.task_id=%s AND h.agent_run_id=%s AND h.work_item_id=%s AND h.session_lineage=%s AND s.session_id=%s AND s.revision=%s", (*tx.owner, run["agent_run_id"], work["work_item_id"], request.session_lineage, work["session_id"], work["session_revision"])).fetchone()
                    if transfer is None:
                        raise DomainError("STALE_EXECUTION", 409)
        else:
            pending = tx.connection.execute("SELECT count(*) FROM vnext.tool_call WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND status NOT IN ('complete','cancelled','failed')", tx.owner).fetchone()[0]
            if pending >= config.runtime.max_pending_operations:
                raise DomainError("LIMIT_BLOCKED", 429)
            call_id = str(uuid4())
            tx.connection.execute("INSERT INTO vnext.tool_call(tenant_id,project_id,task_id,tool_call_id,session_lineage,message_id,provider_call_id,tool_definition_version,work_item_id,input_digest,request_json,status,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (*tx.owner, call_id, *values, work["work_item_id"], call_digest, json_text(request.model_dump(mode="python")), "pending_approval" if definition.approval_required else "admitted", tx.permissions["clearance"]))
            call = _call(tx, call_id)
            audit(tx, "tool.proposed", {"tool_call_id": call_id, "tool_definition_ref": definition.ref})
        return PreparedToolCall(call, request, definition, executor, config, run, target)

    def authorize_in_transaction(self, tx, prepared, *, approval_binding=None):
        if tx.purpose != "tool_request" or prepared.run["agent_run_id"] != tx.run_binding.identity.agent_run_id:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        call = _call(tx, prepared.call["tool_call_id"])
        if approval_binding is not None:
            from wuji_core.contracts.sessions import ApprovalBinding
            approval_binding = ApprovalBinding.model_validate(approval_binding)
            approved = tx.connection.execute("SELECT decision_status,consumed_attempt_id FROM vnext.approval_request WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND approval_ref=%s AND version=%s AND tool_call_id=%s AND decision='approve'", (*tx.owner, approval_binding.approval_ref, approval_binding.decision_version, call["tool_call_id"])).fetchone()
            if (not approved or approval_binding.tool_call_id != call["tool_call_id"]
                    or approved[0] not in {"decided", "consumed"}
                    or (approved[0] == "consumed" and approved[1] != call["latest_attempt_id"])):
                raise DomainError("STALE_EXECUTION", 409)
        if call["latest_attempt_id"]:
            value = _attempt(tx, call["latest_attempt_id"])
            return ToolPermit.restore(strict_json_loads(value["permit_json"]), request_id=tx.access.request_id)
        if prepared.definition.approval_required:
            if approval_binding is None:
                return ToolPermit(call["tool_call_id"], None, tx.run_binding.identity, prepared.executor.ref, prepared.definition.ref, prepared.request.arguments, digest(prepared.request.arguments), (), tx.run_binding.expires_at, "", tx.access, prepared.config.runtime, True)
            if call["status"] != "admitted" or approval_binding.replay:
                raise DomainError("STALE_EXECUTION", 409)
        return self._new_attempt(tx, prepared)

    def _new_attempt(self, tx, prepared, *, retry_request_id=None):
        config, run = prepared.config, prepared.run
        # The RuntimeProfile operation limit is per Run, like the model budget:
        # two Runs of one Task are independent work and must not spend each
        # other's slot. Cross-Run coordination belongs to the resource lock below.
        active = tx.connection.execute("SELECT count(*) FROM vnext.tool_attempt WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND status IS NOT NULL AND status NOT IN ('complete','cancelled','failed')", (*tx.owner, run["agent_run_id"])).fetchone()[0]
        if active >= config.runtime.max_inflight_tools:
            raise DomainError("LIMIT_BLOCKED", 429)
        count = tx.connection.execute("SELECT count(*) FROM vnext.tool_attempt WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_call_id=%s", (*tx.owner, prepared.call["tool_call_id"])).fetchone()[0]
        if count >= config.runtime.limits.max_attempts_per_work:
            raise DomainError("LIMIT_BLOCKED", 429)
        # SPEC: whether reads may run in parallel depends on the tool's actual
        # behaviour. Only read-only workspace tools are admitted today, so they
        # share the path (multiple Runs may read it); an exclusive holder of the
        # path still blocks them, and a future writer key excludes both.
        kind = tool_kind(prepared.definition)
        if kind == "workspace_read":
            base = (
                "workspace:"
                + run["environment_ref"]
                + ":"
                + prepared.request.arguments["path"]
            )
        else:
            base = "target:" + str(prepared.target)
        if kind in {"workspace_read", "http_target"}:
            # Both published kinds are read-only: the claim index allows one
            # active claim per resource key, so a shared read claim is made per
            # Run. Readers only conflict with an exclusive holder of the base.
            resource = base + ":read:" + run["agent_run_id"]
            conflict = tx.connection.execute(
                "SELECT 1 FROM vnext.resource_reservation WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND resource_key=%s AND state<>'released'",
                (*tx.owner, base),
            ).fetchone()
        else:
            resource = base
            conflict = tx.connection.execute(
                "SELECT 1 FROM vnext.resource_reservation WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND state<>'released' AND (resource_key=%s OR left(resource_key,%s)=%s)",
                (*tx.owner, base, len(base) + 6, base + ":read:"),
            ).fetchone()
        if conflict:
            raise DomainError("LIMIT_BLOCKED", 429)
        consume_attempt(tx, model=False, maximum=config.runtime.limits.max_tool_calls)
        attempt_id = str(uuid4())
        permit = ToolPermit(prepared.call["tool_call_id"], attempt_id, tx.run_binding.identity, prepared.executor.ref, prepared.definition.ref, prepared.request.arguments, digest(prepared.request.arguments), (resource,), min(tx.run_binding.expires_at, datetime.now(timezone.utc) + timedelta(seconds=config.runtime.total_timeout_seconds)), str(uuid4()), tx.access, config.runtime)
        tx.connection.execute("INSERT INTO vnext.tool_attempt(tenant_id,project_id,task_id,tool_attempt_id,tool_call_id,agent_run_id,evidence_origin,capture_layer,receipt_json,status,permit_json,retry_request_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'admitted',%s,%s)", (*tx.owner, attempt_id, permit.tool_call_id, run["agent_run_id"], prepared.executor.evidence_origin, prepared.executor.capture_layer, "{}", json_text(permit.stored()), retry_request_id))
        tx.connection.execute("INSERT INTO vnext.collector_binding(tenant_id,project_id,task_id,tool_attempt_id,subject,can_settle) VALUES(%s,%s,%s,%s,%s,true)", (*tx.owner, attempt_id, prepared.executor.collector_subject))
        for key in permit.resource_keys:
            tx.connection.execute("INSERT INTO vnext.tool_resource_claim(tenant_id,project_id,task_id,resource_key,tool_attempt_id) VALUES(%s,%s,%s,%s,%s)", (*tx.owner, key, attempt_id))
            tx.connection.execute("INSERT INTO vnext.resource_reservation(tenant_id,project_id,task_id,resource_key,agent_run_id,state,source_receipt_json) VALUES(%s,%s,%s,%s,%s,'reserved',%s) ON CONFLICT(tenant_id,project_id,task_id,resource_key,agent_run_id) DO UPDATE SET state='reserved',source_receipt_json=EXCLUDED.source_receipt_json", (*tx.owner, key, run["agent_run_id"], json_text({"producer": "p06", "tool_attempt_id": attempt_id})))
        tx.connection.execute("UPDATE vnext.tool_call SET latest_attempt_id=%s,status='admitted' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_call_id=%s", (attempt_id, *tx.owner, permit.tool_call_id))
        _settlement(tx, run["agent_run_id"])
        tx.semantic_event("tool.dispatch_requested", {"tool_call_id": permit.tool_call_id, "tool_attempt_id": attempt_id, "executor_ref": permit.executor_ref})
        audit(tx, "tool.admitted", {"tool_call_id": permit.tool_call_id, "tool_attempt_id": attempt_id})
        return permit

    def check_execution(self, permit, *, receiver_id):
        with self.uow.transaction(permit.access, permit.identity.task_id, capability="tool_request") as tx:
            config = self.registry.config(tx)
            run, work = current_run(tx, config)
            actual = _attempt(tx, permit.tool_attempt_id)
            stored = strict_json_loads(actual["permit_json"])
            executor = self.registry.executor(tx, permit.executor_ref)
            definition = self.registry.tool(tx, permit.tool_definition_ref)
            if tool_kind(definition) == "http_target":
                require_http_target_role(tx, work)
            if not compare_digest(stored["execution_token"], permit.execution_token) or digest(stored) != digest(permit.stored()) or receiver_id != executor.receiver_id or run["agent_run_id"] != permit.identity.agent_run_id or executor.environment_ref != run["environment_ref"] or datetime.now(timezone.utc) >= permit.expires_at or actual["status"] != "admitted":
                raise DomainError("STALE_EXECUTION", 409)
            tx.connection.execute("UPDATE vnext.tool_attempt SET status='dispatched' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s", (*tx.owner, permit.tool_attempt_id))
            tx.connection.execute("UPDATE vnext.tool_call SET status='dispatched' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_call_id=%s", (*tx.owner, permit.tool_call_id))

    def validate_receipt_permit(self, permit, *, receiver_id):
        with self.uow.transaction(permit.access, permit.identity.task_id, capability="tool_settle") as tx:
            record = _attempt(tx, permit.tool_attempt_id)
            executor = self.registry.executor(tx, permit.executor_ref)
            if receiver_id != executor.receiver_id or digest(strict_json_loads(record["permit_json"])) != digest(permit.stored()):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")

    def retry(self, access, tool_call_id, *, prior_attempt_id, retry_request_id):
        binding = self.registry.binding(access)
        if not isinstance(retry_request_id, str) or not 1 <= len(retry_request_id) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        with self.uow.transaction(access, binding.identity.task_id, capability="tool_request") as tx:
            call = _call(tx, tool_call_id)
            prepared = self.prepare_in_transaction(tx, strict_json_loads(call["request_json"]))
            old = row(tx.connection.execute("SELECT * FROM vnext.tool_attempt WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_call_id=%s AND retry_request_id=%s", (*tx.owner, tool_call_id, retry_request_id)))
            if old:
                return ToolPermit.restore(strict_json_loads(old["permit_json"]), request_id=access.request_id)
            previous = _attempt(tx, prior_attempt_id)
            if previous["tool_call_id"] != tool_call_id or call["latest_attempt_id"] != prior_attempt_id or previous["status"] not in {"failed", "cancelled"} or strict_json_loads(previous["receipt_json"]).get("status") not in {"not_started", "exited"}:
                raise DomainError("OPERATION_UNKNOWN", 409)
            if prepared.definition.approval_required:
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            return self._new_attempt(tx, prepared, retry_request_id=retry_request_id)


class ToolCapabilityResolver:
    """Resolve model-advertised tools against the actual ToolGate assembly."""

    def __init__(self, gate):
        self.gate = gate

    def require_available(self, access, tools):
        binding = self.gate.registry.binding(access)
        with self.gate.admission.uow.transaction(
            access, binding.identity.task_id
        ) as tx:
            config = self.gate.registry.config(tx)
            allowed = (
                set(config.allowed_tool_refs)
                & set(config.runtime.allowed_tool_refs)
                & set(binding.allowed_tool_refs)
            )
            definitions = {
                self.gate.registry.tool(tx, ref).name: self.gate.registry.tool(tx, ref)
                for ref in allowed
            }
            refs = []
            for advertised in tools:
                value = advertised.model_dump(mode="python")
                function = value["function"]
                definition = definitions.get(function["name"])
                if (
                    definition is None
                    or digest(function["parameters"])
                    != digest(definition.input_schema)
                ):
                    raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                refs.append(definition.ref)
        for ref in refs:
            self.gate._assembly(access, ref)


class ToolGate:
    def __init__(self, admission, *, registry, ledger, artifacts, evidence, executors, collector_accesses):
        self.admission, self.registry, self.ledger = admission, registry, ledger
        self.artifacts, self.evidence = artifacts, evidence
        self.executors, self.collector_accesses = dict(executors), dict(collector_accesses)

    async def invoke(self, access, request):
        request = ToolCallRequest.model_validate(request)
        # Configuration is resolved before authorizing an attempt; an absent actual
        # executor cannot be advertised as an available tool via a fixture flag.
        await run_in_threadpool(self._assembly, access, request.tool_definition_ref)
        permit = await run_in_threadpool(self.admission.authorize, access, request)
        if permit.replay:
            return await run_in_threadpool(self.ledger.tool_call, access, permit.tool_call_id)
        return await self.execute_permit(access, permit)

    def _assembly(self, access, ref):
        binding = self.registry.binding(access)
        with self.admission.uow.transaction(access, binding.identity.task_id) as tx:
            definition = self.registry.tool(tx, ref)
            registration = self.registry.executor(tx, definition.executor_ref)
            # One deployment may serve several Tasks, and each Task keeps its
            # own executor binding: the key is the owning Task plus the ref.
            key = (*tx.owner, registration.ref)
            executor = self.executors.get(key)
            collector = self.collector_accesses.get(key)
            if executor is None or not all(callable(getattr(executor, method, None)) for method in ("dispatch", "query", "cancel")) or collector is None or collector.principal.subject != registration.collector_subject or collector.principal.tenant_id != tx.owner[0] or "collector" not in collector.principal.roles:
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            return registration

    def result_material(self, access, tool_call_id, *, representation=None):
        """The bounded body this exact call already captured, for its own Run.

        The receipt stays canonical and unchanged: this read only re-delivers the
        bytes the Run itself produced, under the published output bound, and it
        names an omission reason instead of pretending a body was delivered.
        Anything that is not this Run's own completed call is invisible here.
        """

        if representation not in (None, MODEL_MATERIAL_SCHEMA):
            raise DomainError("INVALID_SCHEMA", 422)
        binding = self.registry.binding(access)
        with self.admission.uow.transaction(access, binding.identity.task_id) as tx:
            call = row(
                tx.connection.execute(
                    "SELECT c.*,a.agent_run_id AS attempt_run_id FROM vnext.tool_call c "
                    "LEFT JOIN vnext.tool_attempt a ON (a.tenant_id,a.project_id,a.task_id,a.tool_attempt_id)="
                    "(c.tenant_id,c.project_id,c.task_id,c.latest_attempt_id) "
                    "WHERE c.tenant_id=%s AND c.project_id=%s AND c.task_id=%s AND c.tool_call_id=%s",
                    (*tx.owner, tool_call_id),
                )
            )
            if (
                call is None
                or call["work_item_id"] != binding.identity.work_item_id
                or call["attempt_run_id"] != binding.identity.agent_run_id
            ):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            receipt = tool_receipt(tx, call)
            limit = self.registry.config(tx).runtime.limits.max_single_output_bytes

            def omitted(reason):
                if representation == MODEL_MATERIAL_SCHEMA:
                    return omitted_model_material(tool_call_id, reason)
                return ToolResultMaterial.model_validate({
                    "tool_call_id": tool_call_id, "status": "omitted", "reason": reason,
                    "artifact_ref": None, "media_type": None, "byte_length": None,
                    "encoding": None, "text": None,
                })

            ref = receipt.result_ref
            if (
                receipt.status.value != "complete"
                or receipt.tool_attempt_id is None
                or ref is None
                or receipt.evidence_receipt is None
                or receipt.evidence_receipt.status.value != "accepted"
                or ref not in list(receipt.evidence_receipt.artifact_refs)
            ):
                return omitted(MaterialOmission.not_delivered)
            try:
                record = self.artifacts.record(tx, ref)
            except DomainError:
                return omitted(MaterialOmission.unreadable)
            if record["state"] != "sealed":
                if representation == MODEL_MATERIAL_SCHEMA:
                    return render_http_exchange_v2(
                        tool_call_id,
                        artifact_ref=ref,
                        artifact_record=record,
                        raw=None,
                        max_source_bytes=min(1 << 20, int(limit)),
                        max_representation_bytes=min(32 * 1024, int(limit)),
                    )
                return omitted(MaterialOmission.not_sealed)
            if representation == MODEL_MATERIAL_SCHEMA:
                source_limit = min(1 << 20, int(limit))
                if type(record.get("size_bytes")) is not int or record["size_bytes"] > source_limit:
                    return render_http_exchange_v2(
                        tool_call_id,
                        artifact_ref=ref,
                        artifact_record=record,
                        raw=None,
                        max_source_bytes=source_limit,
                        max_representation_bytes=min(32 * 1024, int(limit)),
                    )
                try:
                    body = self.artifacts.checked_bytes(record)
                except DomainError:
                    return omitted_model_material(tool_call_id, "source_unavailable")
                return render_http_exchange_v2(
                    tool_call_id,
                    artifact_ref=ref,
                    artifact_record=record,
                    raw=body,
                    max_source_bytes=min(1 << 20, int(limit)),
                    max_representation_bytes=min(32 * 1024, int(limit)),
                )
            if not str(record["media_type"]).startswith("text/"):
                return omitted(MaterialOmission.not_text_media)
            if record["size_bytes"] > limit:
                return omitted(MaterialOmission.over_inline_limit)
            try:
                body = self.artifacts.checked_bytes(record)
            except DomainError:
                return omitted(MaterialOmission.unreadable)
            try:
                body.decode("utf-8")
            except UnicodeDecodeError:
                return omitted(MaterialOmission.not_utf8)
            return ToolResultMaterial.model_validate({
                "tool_call_id": tool_call_id, "status": "delivered", "reason": None,
                "artifact_ref": ref.model_dump(mode="python"),
                "media_type": record["media_type"], "byte_length": len(body),
                "encoding": "utf-8", "text": body.decode("utf-8"),
            })

    def close_operations(self, access, request):
        """Close the calling Run's own operation set from durable records.

        The Run states only that it will start no further operation; whether the
        set is closed is recomputed here from the platform's records, so a Run
        cannot settle over its own unresolved attempt, in-flight model request
        or unreleased resource.
        """

        request = ToolSettlementRequest.model_validate(request)
        binding = self.registry.binding(access)
        with self.admission.uow.transaction(access, binding.identity.task_id, capability="tool_settle") as tx:
            status, open_operations = close_operation_set(tx, binding.identity.agent_run_id)
            audit(tx, "tool.operation_set_closed",
                  {"status": status, "open_operations": open_operations})
        return ToolSettlementReceipt.model_validate({
            "agent_run_id": binding.identity.agent_run_id,
            "status": status,
            "open_operations": open_operations,
        })

    async def execute_permit(self, access, permit):
        if access.principal != permit.access.principal:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        if permit.replay or permit.tool_attempt_id is None:
            return await run_in_threadpool(self.ledger.tool_call, access, permit.tool_call_id)
        registration = await run_in_threadpool(self._assembly, access, permit.tool_definition_ref)
        try:
            key = (
                permit.identity.tenant_id,
                permit.identity.project_id,
                permit.identity.task_id,
                registration.ref,
            )
            receipt = await asyncio.wait_for(self.executors[key].dispatch(permit), timeout=permit.runtime.total_timeout_seconds)
        except (Exception, asyncio.CancelledError):
            await asyncio.shield(run_in_threadpool(self._unknown, permit))
            return await run_in_threadpool(self.ledger.tool_call, access, permit.tool_call_id)
        await run_in_threadpool(self._receive_execution, permit, receipt)
        await run_in_threadpool(self._capture, permit)
        return await run_in_threadpool(self.ledger.tool_call, access, permit.tool_call_id)

    def _unknown(self, permit):
        with self.admission.uow.transaction(permit.access, permit.identity.task_id, capability="tool_settle") as tx:
            value = _attempt(tx, permit.tool_attempt_id)
            if value["status"] in {"complete", "failed", "cancelled"}:
                return
            tx.connection.execute("UPDATE vnext.tool_attempt SET status='unknown' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s", (*tx.owner, permit.tool_attempt_id))
            tx.connection.execute("UPDATE vnext.tool_call SET status='unknown' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_call_id=%s", (*tx.owner, permit.tool_call_id))
            for resource in permit.resource_keys:
                tx.connection.execute("UPDATE vnext.resource_reservation SET state='unknown' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND resource_key=%s", (*tx.owner, permit.identity.agent_run_id, resource))
            _settlement(tx, permit.identity.agent_run_id)
            audit(tx, "tool.execution_unknown", {"tool_attempt_id": permit.tool_attempt_id})

    def _release(self, tx, permit):
        tx.connection.execute("UPDATE vnext.tool_resource_claim SET active=false WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s", (*tx.owner, permit.tool_attempt_id))
        for key in permit.resource_keys:
            tx.connection.execute("UPDATE vnext.resource_reservation SET state='released' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND resource_key=%s AND source_receipt_json::jsonb->>'tool_attempt_id'=%s", (*tx.owner, permit.identity.agent_run_id, key, permit.tool_attempt_id))
        _settlement(tx, permit.identity.agent_run_id)

    def _receive_execution(self, permit, receipt):
        receipt = ToolExecutionReceipt.model_validate(receipt)
        with self.admission.uow.transaction(permit.access, permit.identity.task_id, capability="tool_settle") as tx:
            record = _attempt(tx, permit.tool_attempt_id)
            original = strict_json_loads(record["permit_json"])
            executor = self.registry.executor(tx, permit.executor_ref)
            source = receipt.source_receipt
            if digest(original) != digest(permit.stored()) or receipt.tool_attempt_id != permit.tool_attempt_id or receipt.receiver_id != executor.receiver_id or any(source.get(k) != v for k, v in {"tool_attempt_id": permit.tool_attempt_id, "receiver_id": executor.receiver_id, "environment_ref": executor.environment_ref, "arguments_digest": permit.arguments_digest, "receipt_id": receipt.receipt_id}.items()):
                raise DomainError("INVALID_REFERENCE", 422)
            if receipt.status == "exited" and (not receipt.started_at or not receipt.exited_at or receipt.exited_at < receipt.started_at):
                raise DomainError("INVALID_REFERENCE", 422)
            if receipt.status == "not_started" and (receipt.started_at is not None or receipt.output is not None):
                raise DomainError("INVALID_REFERENCE", 422)
            saved = receipt.model_dump(mode="json", exclude={"output"})
            raw_output = receipt.output
            raw_digest = sha256(raw_output).hexdigest() if raw_output is not None else None
            if raw_output is not None and (
                source.get("output_bytes") != len(raw_output)
                or source.get("output_sha256") != raw_digest
            ):
                raise DomainError("INVALID_REFERENCE", 422)
            if record["receipt_json"] != "{}":
                previous = strict_json_loads(record["receipt_json"])
                if previous.get("receipt_id") == receipt.receipt_id:
                    if (
                        digest(previous) != digest(saved)
                        or int(record["received_bytes"]) != len(raw_output or b"")
                        or record["received_digest"] != raw_digest
                    ):
                        raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                    return
                if record["status"] in {"complete", "failed", "cancelled", "evidence_pending"}:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            if record["status"] == "admitted" and receipt.status not in {"not_started", "unknown"}:
                raise DomainError("INVALID_REFERENCE", 422)  # Receiver skipped check_execution.
            status = "unknown" if receipt.status == "unknown" else "running" if receipt.status == "running" else "cancelled" if receipt.status == "not_started" else "failed" if receipt.output is None else "evidence_pending"
            data = receipt.output
            effective_completeness = receipt.completeness
            limit_reason = None
            if data is not None:
                if not isinstance(receipt.media_type, str) or not 1 <= len(receipt.media_type) <= 256 or "\r" in receipt.media_type or "\n" in receipt.media_type:
                    raise DomainError("INVALID_SCHEMA", 422)
                accepted_size = allocate_output(
                    tx,
                    len(data),
                    already=record["output_bytes"],
                    runtime=permit.runtime,
                    allow_partial=True,
                )
                if accepted_size < len(data):
                    data = data[:accepted_size] or None
                    effective_completeness = "partial"
                    limit_reason = "LIMIT_BLOCKED"
                    status = (
                        "evidence_pending"
                        if data is not None
                        else "failed" if receipt.status == "exited" else "unknown"
                    )
            tx.connection.execute("UPDATE vnext.tool_attempt SET status=%s,started_at=COALESCE(started_at,%s),receipt_json=%s,output=%s,output_media_type=%s,output_completeness=%s,received_bytes=received_bytes+%s,received_digest=%s,retained_bytes=retained_bytes+%s,output_bytes=output_bytes+%s,limit_reason=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s", (status, receipt.started_at, json_text(saved), data, receipt.media_type, effective_completeness, len(raw_output or b""), raw_digest, len(data or b""), len(data or b""), limit_reason, *tx.owner, permit.tool_attempt_id))
            tx.connection.execute("UPDATE vnext.tool_call SET status=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_call_id=%s", (status, *tx.owner, permit.tool_call_id))
            if receipt.status in {"exited", "not_started"}:
                self._release(tx, permit)
            audit(tx, "tool.execution_receipt", {"tool_attempt_id": permit.tool_attempt_id, "receipt_id": receipt.receipt_id, "status": status})

    def _capture(self, permit):
        access = permit.access
        with self.admission.uow.transaction(access, permit.identity.task_id, capability="tool_settle") as tx:
            attempt = _attempt(tx, permit.tool_attempt_id)
            if attempt["status"] != "evidence_pending":
                return
            executor = self.registry.executor(tx, permit.executor_ref)
            definition = self.registry.tool(tx, permit.tool_definition_ref)
            condition = capture_condition(tool_kind(definition))
            collector = self.collector_accesses[
                (*tx.owner, executor.ref)
            ]
            saved = strict_json_loads(attempt["receipt_json"])
            existing_capture = attempt["capture_json"]
            level = _call(tx, permit.tool_call_id)["access_level"]
        if existing_capture:
            envelope = CaptureEnvelope.model_validate(strict_json_loads(existing_capture))
        else:
            ref = self.artifacts.stage(collector, permit.identity.task_id, permit.tool_attempt_id, bytes(attempt["output"]), attempt["output_media_type"], completeness=attempt["output_completeness"], conditions=(condition,), access_level=level)
            self.artifacts.seal(collector, permit.identity.task_id, ref)
            envelope = CaptureEnvelope.model_validate({"schema_version": "wuji.capture.v2", "capture_id": permit.tool_attempt_id, "identity": permit.identity.model_dump(mode="json"), "tool_call_id": permit.tool_call_id, "tool_attempt_id": permit.tool_attempt_id, "artifact_refs": [ref.model_dump(mode="json")], "capture_layer": executor.capture_layer, "observed_at": saved["exited_at"] or saved["started_at"], "received_at": saved["exited_at"] or saved["started_at"], "evidence_origin": executor.evidence_origin, "conditions": [condition], "completeness": attempt["output_completeness"]})
            # Freeze the exact ingest envelope before sending it to EvidenceService.
            with self.admission.uow.transaction(access, permit.identity.task_id, capability="tool_settle") as tx:
                current = _attempt(tx, permit.tool_attempt_id)
                if current["capture_json"]:
                    envelope = CaptureEnvelope.model_validate(strict_json_loads(current["capture_json"]))
                else:
                    tx.connection.execute("UPDATE vnext.tool_attempt SET capture_json=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s", (json_text(envelope.model_dump(mode="json")), *tx.owner, permit.tool_attempt_id))
        evidence_receipt = self.evidence.ingest(collector, envelope)
        if evidence_receipt.status not in {"accepted", "historical_only"}:
            return
        with self.admission.uow.transaction(access, permit.identity.task_id, capability="tool_settle") as tx:
            current = _attempt(tx, permit.tool_attempt_id)
            if current["result_receipt_json"]:
                return
            result = ToolCallReceipt.model_validate({"tool_call_id": permit.tool_call_id, "operation_id": permit.tool_call_id, "tool_attempt_id": permit.tool_attempt_id, "status": "complete", "evidence_receipt": evidence_receipt.model_dump(mode="python"), "result_ref": envelope.artifact_refs[0].model_dump(mode="python"), "reason_code": current["limit_reason"]})
            tx.connection.execute("UPDATE vnext.tool_attempt SET status='complete',result_receipt_json=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s", (json_text(result.model_dump(mode="json")), *tx.owner, permit.tool_attempt_id))
            tx.connection.execute("UPDATE vnext.tool_call SET status='complete' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_call_id=%s", (*tx.owner, permit.tool_call_id))
            _settlement(tx, permit.identity.agent_run_id)
            audit(tx, "tool.result_ready", {"tool_attempt_id": permit.tool_attempt_id, "capture_id": envelope.capture_id})

    def _existing_permit(self, access, tool_call_id):
        binding = self.registry.binding(access)
        with self.admission.uow.transaction(access, binding.identity.task_id) as tx:
            call = _call(tx, tool_call_id)
            if call["work_item_id"] != binding.identity.work_item_id or call["session_lineage"] != binding.session_lineage:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            if not call["latest_attempt_id"]:
                return None
            attempt = _attempt(tx, call["latest_attempt_id"])
            return ToolPermit.restore(strict_json_loads(attempt["permit_json"]), request_id=access.request_id)

    async def reconcile(self, access, tool_call_id):
        permit = await run_in_threadpool(self._existing_permit, access, tool_call_id)
        if permit is not None:
            value = await run_in_threadpool(self.ledger.tool_call, access, tool_call_id)
            if value.status == "evidence_pending":
                await run_in_threadpool(self._capture, permit)
            elif value.status not in {"complete", "failed", "cancelled"}:
                executor = self.executors.get(
                    (
                        permit.identity.tenant_id,
                        permit.identity.project_id,
                        permit.identity.task_id,
                        permit.executor_ref,
                    )
                )
                if executor is None:
                    raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                receipt = await asyncio.wait_for(executor.query(permit), timeout=permit.runtime.idle_timeout_seconds)
                await run_in_threadpool(self._receive_execution, permit, receipt)
                await run_in_threadpool(self._capture, permit)
        return await run_in_threadpool(self.ledger.tool_call, access, tool_call_id)

    async def cancel(self, access, tool_call_id, *, operation_id, reason):
        binding = self.registry.binding(access)
        def register():
            with self.admission.uow.transaction(access, binding.identity.task_id, capability="tool_request") as tx:
                call = _call(tx, tool_call_id)
                if call["work_item_id"] != binding.identity.work_item_id:
                    raise DomainError("NOT_FOUND_OR_FORBIDDEN")
                current_run(tx, self.registry.config(tx))
                key_digest = digest({"tool_call_id": tool_call_id, "reason": reason})
                old = row(tx.connection.execute("SELECT * FROM vnext.tool_cancel_receipt WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_call_id=%s AND operation_id=%s", (*tx.owner, tool_call_id, operation_id)))
                if old:
                    if old["input_digest"] != key_digest:
                        raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                    return ToolCallReceipt.model_validate(strict_json_loads(old["receipt_json"])), True
                if call["status"] not in {"complete", "failed", "cancelled"}:
                    status = "cancel_requested" if call["latest_attempt_id"] else "cancelled"
                    tx.connection.execute("UPDATE vnext.tool_call SET status=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_call_id=%s", (status, *tx.owner, tool_call_id))
                result = tool_receipt(tx, _call(tx, tool_call_id))
                tx.connection.execute("INSERT INTO vnext.tool_cancel_receipt(tenant_id,project_id,task_id,tool_call_id,operation_id,input_digest,receipt_json) VALUES(%s,%s,%s,%s,%s,%s,%s)", (*tx.owner, tool_call_id, operation_id, key_digest, json_text(result.model_dump(mode="json"))))
                audit(tx, "tool.cancel_requested", {"tool_call_id": tool_call_id, "operation_id": operation_id})
                return result, False
        result, replay = await run_in_threadpool(register)
        if result.status == "cancel_requested":
            permit = await run_in_threadpool(self._existing_permit, access, tool_call_id)
            receiver = self.executors.get(
                (
                    permit.identity.tenant_id,
                    permit.identity.project_id,
                    permit.identity.task_id,
                    permit.executor_ref,
                )
            )
            if receiver is not None:
                try:
                    receipt = await asyncio.wait_for(receiver.cancel(permit, reason=reason), timeout=permit.runtime.idle_timeout_seconds)
                    await run_in_threadpool(self._receive_execution, permit, receipt)
                    await run_in_threadpool(self._capture, permit)
                except Exception:
                    await run_in_threadpool(self._unknown, permit)
        return result

    async def invoke_function(self, access, *, name, arguments, session_lineage, message_id, provider_call_id, tool_definition_ref):
        await run_in_threadpool(self._function_name, access, tool_definition_ref, name)
        return await self.invoke(access, ToolCallRequest.model_validate({"session_lineage": session_lineage, "message_id": message_id, "provider_call_id": provider_call_id, "tool_definition_ref": tool_definition_ref, "arguments": arguments}))

    def _function_name(self, access, ref, name):
        binding = self.registry.binding(access)
        with self.admission.uow.transaction(access, binding.identity.task_id) as tx:
            if self.registry.tool(tx, ref).name != name:
                raise DomainError("INVALID_REFERENCE", 422)

    async def invoke_mcp(self, access, request, *, session_lineage, message_id, provider_call_id, tool_definition_ref):
        try:
            from mcp.types import CallToolRequest
        except ImportError as exc:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503) from exc
        if not isinstance(request, CallToolRequest):
            raise DomainError("INVALID_SCHEMA", 422)
        return await self.invoke_function(access, name=request.params.name, arguments=request.params.arguments or {}, session_lineage=session_lineage, message_id=message_id, provider_call_id=provider_call_id, tool_definition_ref=tool_definition_ref)


class WorkspaceReadExecutor:
    """Real bounded file read with a durable receiver inbox outside the workspace.

    A prepared inbox without a terminal receipt is unknown after a crash. Neither
    query nor repeated dispatch reopens the source file in that state.
    """
    def __init__(self, *, root, receipt_root, admission, receiver_id, environment_ref):
        self.root, self.receipt_root = Path(root).resolve(), Path(receipt_root).resolve()
        if self.receipt_root == self.root or self.root in self.receipt_root.parents:
            raise ValueError("receiver receipts must be outside the read workspace")
        self.receipt_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.admission, self.receiver_id, self.environment_ref = admission, receiver_id, environment_ref

    def _path(self, permit):
        from uuid import UUID
        return self.receipt_root / (str(UUID(permit.tool_attempt_id)) + ".json")

    def _source(self, permit, receipt_id):
        return {"tool_attempt_id": permit.tool_attempt_id, "receiver_id": self.receiver_id, "environment_ref": self.environment_ref, "arguments_digest": permit.arguments_digest, "receipt_id": receipt_id}

    def _receipt(self, permit, *, status, started=None, exited=None, output=None, completeness="unknown", error=None, media_type="application/octet-stream"):
        receipt_id = str(uuid4())
        source = self._source(permit, receipt_id)
        if output is not None:
            source["output_bytes"] = len(output)
            source["output_sha256"] = sha256(output).hexdigest()
        return ToolExecutionReceipt(tool_attempt_id=permit.tool_attempt_id, receiver_id=self.receiver_id, receipt_id=receipt_id, status=status, started_at=started, exited_at=exited, source_receipt=source, output=output, media_type=media_type if output is not None else None, completeness=completeness, error_code=error)

    def _write(self, path, receipt, *, exclusive=False):
        import base64
        from wuji_core.http import canonical_json_bytes
        value = receipt.model_dump(mode="json", exclude={"output"})
        value["output_base64"] = base64.b64encode(receipt.output).decode() if receipt.output is not None else None
        data = canonical_json_bytes(value)
        target = path if exclusive else path.with_name(path.name + "." + str(uuid4()) + ".tmp")
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            if not exclusive:
                os.replace(target, path)
            directory = os.open(self.receipt_root, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if not exclusive and target.exists():
                target.unlink()

    def _query(self, permit):
        import base64
        self.admission.validate_receipt_permit(permit, receiver_id=self.receiver_id)
        path = self._path(permit)
        if not path.exists():
            return self._receipt(permit, status="not_started", error="not_registered")
        with path.open("rb") as stream:
            maximum = permit.runtime.buffer_bytes * 2 + 32768
            raw = stream.read(maximum + 1)
        if len(raw) > maximum:
            raise DomainError("LIMIT_BLOCKED", 429)
        value = strict_json_loads(raw)
        body = value.pop("output_base64")
        value["output"] = base64.b64decode(body, validate=True) if body is not None else None
        receipt = ToolExecutionReceipt.model_validate(value)
        expected = self._source(permit, receipt.receipt_id)
        if any(receipt.source_receipt.get(key) != value for key, value in expected.items()):
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        if receipt.output is not None and (
            receipt.source_receipt.get("output_bytes") != len(receipt.output)
            or receipt.source_receipt.get("output_sha256")
            != sha256(receipt.output).hexdigest()
        ):
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        return receipt

    def _operate(self, permit):
        """One bounded operation; returns (output, completeness, error, media_type)."""

        descriptors = []
        data = bytearray()
        error = None
        complete = True
        try:
            import stat
            relative = permit.arguments["path"]
            if PurePosixPath(relative).is_absolute() or any(p in {"", ".", ".."} for p in relative.split("/")):
                raise ValueError("invalid workspace path")
            directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            descriptors.append(directory)
            parts = relative.split("/")
            for component in parts[:-1]:
                directory = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                descriptors.append(directory)
            descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            descriptors.append(descriptor)
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError("only regular workspace files are readable")
            limit = min(permit.runtime.limits.max_single_output_bytes, permit.runtime.buffer_bytes)
            while len(data) <= limit:
                if (
                    self._path(permit).with_suffix(".cancel").exists()
                    or datetime.now(timezone.utc) >= permit.expires_at
                ):
                    complete, error = False, "cancelled_or_expired"
                    break
                part = os.read(descriptor, min(permit.runtime.chunk_bytes, limit + 1 - len(data)))
                if not part:
                    break
                data.extend(part)
            if len(data) > limit:
                del data[limit:]
                complete, error = False, "output_limit"
        except (OSError, ValueError):
            complete, error = False, "workspace_read_failed"
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)
        output = bytes(data) if data or error is None else None
        # A complete read that is exactly UTF-8 text is published as text, so the
        # Run that produced it (and later Runs whose read set includes it) can
        # receive the body under the bound instead of an opaque octet stream.
        media_type = "application/octet-stream"
        if complete and output is not None:
            try:
                output.decode("utf-8")
            except UnicodeDecodeError:
                pass
            else:
                media_type = "text/plain; charset=utf-8"
        return output, "complete" if complete else "partial", error, media_type

    def _dispatch(self, permit):
        self.admission.validate_receipt_permit(permit, receiver_id=self.receiver_id)
        path = self._path(permit)
        prepared = self._receipt(permit, status="unknown", error="prepared_without_exit")
        try:
            self._write(path, prepared, exclusive=True)
        except FileExistsError:
            return self._query(permit)
        try:
            self.admission.check_execution(permit, receiver_id=self.receiver_id)
        except DomainError:
            result = self._receipt(permit, status="not_started", error="permission_denied")
            self._write(path, result)
            return result
        started = datetime.now(timezone.utc)
        output, completeness, error, media_type = self._operate(permit)
        result = self._receipt(permit, status="exited", started=started, exited=datetime.now(timezone.utc), output=output, completeness=completeness, error=error, media_type=media_type)
        self._write(path, result)
        return result

    async def dispatch(self, permit):
        return await asyncio.to_thread(self._dispatch, permit)

    async def query(self, permit):
        return await asyncio.to_thread(self._query, permit)

    async def cancel(self, permit, *, reason):
        await run_in_threadpool(self.admission.validate_receipt_permit, permit, receiver_id=self.receiver_id)
        def request_cancel():
            path = self._path(permit).with_suffix(".cancel")
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.fsync(fd)
                os.close(fd)
            except FileExistsError:
                pass
            return self._query(permit)
        return await asyncio.to_thread(request_cancel)


class HttpTargetExecutor(WorkspaceReadExecutor):
    """Read-only HTTP exchange whose target the platform already approved.

    The URL must match the permit's own resource key, redirects are recorded
    instead of followed, environment proxies are ignored, and both the response
    and the total exchange document stay inside the permit's output budget. The
    document keeps the exact request and response so the capture layer can seal
    raw bytes instead of a paraphrase.
    """

    MEDIA_TYPE = "application/vnd.wuji.http-exchange+json"
    SCHEMA_VERSION = "wuji.http-exchange.v1"

    def __init__(self, *, receipt_root, admission, receiver_id, environment_ref,
                 timeout_seconds=30):
        # No workspace root: this executor never reads the Task's files, it only
        # reaches the exact target the permit already names.
        if not 1 <= int(timeout_seconds) <= 300:
            raise ValueError("a bounded target timeout is required")
        self.receipt_root = Path(receipt_root).resolve()
        self.receipt_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.admission = admission
        self.receiver_id = receiver_id
        self.environment_ref = environment_ref
        self.timeout_seconds = int(timeout_seconds)

    def _budget(self, permit):
        return min(
            permit.runtime.limits.max_single_output_bytes, permit.runtime.buffer_bytes
        )

    def _exchange(self, permit, url, method, *, body, headers, status, response_headers, truncated):
        import base64

        from wuji_core.http import canonical_json_bytes

        budget = self._budget(permit)
        target = target_scope.permit_target_matches(permit.resource_keys, url).key

        def encode(size):
            kept = body[:size]
            return canonical_json_bytes(
                {
                    "schema_version": self.SCHEMA_VERSION,
                    "tool_attempt_id": permit.tool_attempt_id,
                    "target": target,
                    "request": {"method": method, "url": url, "headers": headers},
                    "response": {
                        "status": status,
                        "headers": response_headers,
                        "body_base64": base64.b64encode(kept).decode(),
                        "body_bytes": len(kept),
                        "truncated": truncated or len(kept) < len(body),
                    },
                }
            )

        raw = encode(len(body))
        if len(raw) <= budget:
            return raw, False
        empty = encode(0)
        if len(empty) > budget:
            return None, True
        low, high, fitted = 0, len(body), empty
        while low <= high:
            size = (low + high) // 2
            candidate = encode(size)
            if len(candidate) <= budget:
                fitted, low = candidate, size + 1
            else:
                high = size - 1
        return fitted, True

    def _operate(self, permit):
        import httpx

        url = permit.arguments["url"]
        method = permit.arguments["method"]
        target_scope.permit_target_matches(permit.resource_keys, url)
        request_headers = {"accept": "*/*", "user-agent": "wuji-target-read/1"}
        budget = self._budget(permit)
        cancel_path = self._path(permit).with_suffix(".cancel")

        async def fetch():
            body = b""
            async with httpx.AsyncClient(
                follow_redirects=False,
                trust_env=False,
                verify=True,
                timeout=min(self.timeout_seconds, permit.runtime.total_timeout_seconds),
            ) as client:
                async with client.stream(method, url, headers=request_headers) as response:
                    response_headers = {
                        key.lower(): value
                        for key, value in response.headers.items()
                        if key.lower() in {"content-type", "content-length", "location", "server", "date"}
                    }
                    async for chunk in response.aiter_bytes(permit.runtime.chunk_bytes):
                        if cancel_path.exists() or datetime.now(timezone.utc) >= permit.expires_at:
                            return body, response.status_code, response_headers, False, False, "cancelled_or_expired"
                        if len(body) + len(chunk) > budget:
                            body += chunk[: max(0, budget - len(body))]
                            return body, response.status_code, response_headers, True, False, "output_limit"
                        body += chunk
                    return body, response.status_code, response_headers, False, True, None

        async def cancellable_fetch():
            if cancel_path.exists() or datetime.now(timezone.utc) >= permit.expires_at:
                return b"", None, {}, False, False, "cancelled_or_expired"
            operation = asyncio.create_task(fetch())
            while True:
                done, _pending = await asyncio.wait({operation}, timeout=0.1)
                if operation in done:
                    return operation.result()
                if cancel_path.exists() or datetime.now(timezone.utc) >= permit.expires_at:
                    operation.cancel()
                    try:
                        await operation
                    except asyncio.CancelledError:
                        pass
                    return b"", None, {}, False, False, "cancelled_or_expired"

        try:
            body, status, response_headers, truncated, complete, error = asyncio.run(
                cancellable_fetch()
            )
        except (httpx.HTTPError, OSError, ValueError, TimeoutError):
            body, status, response_headers = b"", None, {}
            truncated, complete, error = False, False, "http_target_failed"
        if status is None and error is None:
            complete, error = False, "http_target_failed"
        document, envelope_truncated = self._exchange(
            permit,
            url,
            method,
            body=body,
            headers=request_headers,
            status=status if status is not None else 0,
            response_headers=response_headers,
            truncated=truncated,
        )
        if envelope_truncated:
            complete, error = False, error or "output_limit"
        if document is None:
            return None, "unknown", error or "output_limit", self.MEDIA_TYPE
        return document, "complete" if complete else "partial", error, self.MEDIA_TYPE


class ToolExecutorRouter:
    """Select a built-in adapter by the deployment's frozen tool identity."""

    def __init__(self, *, executor_ref, routes):
        if (
            not isinstance(executor_ref, str)
            or not executor_ref
            or not isinstance(routes, dict)
            or not routes
            or any(not isinstance(ref, str) or not ref for ref in routes)
        ):
            raise ValueError("a fixed executor and tool routes are required")
        implementations = list(routes.values())
        identities = {
            (item.receiver_id, item.environment_ref) for item in implementations
        }
        if len(identities) != 1:
            raise ValueError(
                "every tool implementation must share one receiver identity"
            )
        self.executor_ref = executor_ref
        self.receiver_id, self.environment_ref = identities.pop()
        self.routes = dict(routes)

    def _select(self, permit):
        if permit.executor_ref != self.executor_ref:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        try:
            return self.routes[permit.tool_definition_ref]
        except KeyError as error:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503) from error

    async def dispatch(self, permit):
        return await self._select(permit).dispatch(permit)

    async def query(self, permit):
        return await self._select(permit).query(permit)

    async def cancel(self, permit, *, reason):
        return await self._select(permit).cancel(permit, reason=reason)
