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
from wuji_core.http import strict_json_loads
from wuji_core.http.auth import Principal
from wuji_core.persistence.uow import AccessContext, DomainError, row, json_text
from wuji_core.admission.registry import TaskAdmissionConfig, RuntimeProfile
from wuji_core.admission.common import audit, consume_attempt, current_run, digest, allocate_output
from wuji_core.admission.ledger import tool_receipt


def validate_input_schema(schema):
    # A deliberately finite published file-read schema, not a substitute JSON Schema engine.
    if not isinstance(schema, dict) or schema.get("type") != "object" or schema.get("additionalProperties") is not False or schema.get("required") != ["path"] or set(schema.get("properties", {})) != {"path"} or set(schema) - {"type", "properties", "required", "additionalProperties", "description", "$schema"}:
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    path = schema["properties"]["path"]
    if not isinstance(path, dict) or path.get("type") != "string" or set(path) - {"type", "description", "minLength", "maxLength", "enum"}:
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    for key in ("minLength", "maxLength"):
        if key in path and (type(path[key]) is not int or path[key] < 0):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    if "enum" in path and (not isinstance(path["enum"], list) or not path["enum"] or not all(isinstance(v, str) for v in path["enum"])):
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)


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


def _settlement(tx, run_id):
    unsettled = tx.connection.execute("SELECT 1 FROM vnext.tool_attempt WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND status IS NOT NULL AND status NOT IN ('complete','cancelled','failed') LIMIT 1", (*tx.owner, run_id)).fetchone()
    old = row(tx.connection.execute("SELECT * FROM vnext.run_operation_settlement WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s", (*tx.owner, run_id)))
    if old and old["status"] != "settled" and strict_json_loads(old["source_receipt_json"]).get("producer") != "p06":
        return  # Another producer's unresolved operation must not be erased.
    tx.connection.execute("INSERT INTO vnext.run_operation_settlement(tenant_id,project_id,task_id,agent_run_id,status,source_receipt_json) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(tenant_id,project_id,task_id,agent_run_id) DO UPDATE SET status=EXCLUDED.status,source_receipt_json=EXCLUDED.source_receipt_json", (*tx.owner, run_id, "pending" if unsettled else "settled", json_text({"producer": "p06", "basis": "durable_tool_attempt_receipts"})))


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
        if definition.ref not in executor.allowed_tool_refs or executor.receiver_id != run["receiver_id"] or executor.environment_ref != run["environment_ref"] or definition.allowed_target_kinds != ["workspace_read"]:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        _arguments(definition, request.arguments)
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
        return PreparedToolCall(call, request, definition, executor, config, run)

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
        base = "workspace:" + run["environment_ref"] + ":" + prepared.request.arguments["path"]
        if prepared.definition.allowed_target_kinds == ["workspace_read"]:
            # The claim index allows one active claim per resource key, so a
            # shared read claim is made per Run. Readers only conflict with an
            # exclusive holder of the plain path.
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
            self.registry.tool(tx, permit.tool_definition_ref)
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
            collector = self.collector_accesses[
                (*tx.owner, executor.ref)
            ]
            saved = strict_json_loads(attempt["receipt_json"])
            existing_capture = attempt["capture_json"]
            level = _call(tx, permit.tool_call_id)["access_level"]
        if existing_capture:
            envelope = CaptureEnvelope.model_validate(strict_json_loads(existing_capture))
        else:
            ref = self.artifacts.stage(collector, permit.identity.task_id, permit.tool_attempt_id, bytes(attempt["output"]), attempt["output_media_type"], completeness=attempt["output_completeness"], conditions=("registered workspace read",), access_level=level)
            self.artifacts.seal(collector, permit.identity.task_id, ref)
            envelope = CaptureEnvelope.model_validate({"schema_version": "wuji.capture.v2", "capture_id": permit.tool_attempt_id, "identity": permit.identity.model_dump(mode="json"), "tool_call_id": permit.tool_call_id, "tool_attempt_id": permit.tool_attempt_id, "artifact_refs": [ref.model_dump(mode="json")], "capture_layer": executor.capture_layer, "observed_at": saved["exited_at"] or saved["started_at"], "received_at": saved["exited_at"] or saved["started_at"], "evidence_origin": executor.evidence_origin, "conditions": ["registered workspace read"], "completeness": attempt["output_completeness"]})
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

    def _receipt(self, permit, *, status, started=None, exited=None, output=None, completeness="unknown", error=None):
        receipt_id = str(uuid4())
        source = self._source(permit, receipt_id)
        if output is not None:
            source["output_bytes"] = len(output)
            source["output_sha256"] = sha256(output).hexdigest()
        return ToolExecutionReceipt(tool_attempt_id=permit.tool_attempt_id, receiver_id=self.receiver_id, receipt_id=receipt_id, status=status, started_at=started, exited_at=exited, source_receipt=source, output=output, media_type="application/octet-stream" if output is not None else None, completeness=completeness, error_code=error)

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
                if path.with_suffix(".cancel").exists() or datetime.now(timezone.utc) >= permit.expires_at:
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
        result = self._receipt(permit, status="exited", started=started, exited=datetime.now(timezone.utc), output=output, completeness="complete" if complete else "partial", error=error)
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
