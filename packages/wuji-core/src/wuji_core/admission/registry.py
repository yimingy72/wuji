"""Published configuration and independently revocable Run credentials."""

from datetime import datetime, timezone
from hashlib import sha256
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from wuji_core.contracts.execution import ExecutionLimits
from wuji_core.contracts.envelopes import RunIdentity
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError, row, json_text


class Configuration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Published(Configuration):
    ref: str = Field(min_length=1, max_length=256)
    revision: str = Field(pattern=r"^[1-9][0-9]*$")
    published_at: AwareDatetime


class ModelProfile(Published):
    capability_ref: str = Field(min_length=1, max_length=256)
    protocol: Literal["chat_completions"]
    client_model: str = Field(min_length=1, max_length=256)
    upstream_model: str = Field(min_length=1, max_length=256)
    gateway_url: str
    task_key_ref: str = Field(min_length=1, max_length=256)
    max_retries: Literal[0]

    @model_validator(mode="after")
    def endpoint(self):
        target = urlsplit(self.gateway_url)
        if target.scheme not in {"http", "https"} or not target.hostname or target.username or target.password or target.fragment:
            raise ValueError("a registered HTTP gateway endpoint is required")
        return self


class RuntimeProfile(Published):
    lock_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    limits: ExecutionLimits
    chunk_bytes: int = Field(gt=0, le=1048576)
    buffer_bytes: int = Field(gt=0, le=1073741824)
    idle_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    total_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    max_pending_operations: int = Field(gt=0, le=1000000)
    max_inflight_tools: int = Field(gt=0, le=1000000)
    max_inflight_model_requests: Literal[1]
    allowed_tool_refs: list[str] = Field(max_length=256)

    @model_validator(mode="after")
    def bounded(self):
        if self.buffer_bytes < self.chunk_bytes:
            raise ValueError("buffer must hold a chunk")
        return self


class TaskAdmissionConfig(Configuration):
    model: ModelProfile
    runtime: RuntimeProfile
    allowed_tool_refs: list[str] = Field(max_length=256)


class ToolDefinition(Published):
    name: str = Field(min_length=1, max_length=256)
    input_schema: dict
    executor_ref: str = Field(min_length=1, max_length=256)
    approval_required: bool
    allowed_target_kinds: list[Literal["workspace_read", "http_target"]] = Field(min_length=1, max_length=2)


class ExecutorRegistration(Configuration):
    ref: str
    receiver_id: str
    environment_ref: str
    collector_subject: str
    evidence_origin: Literal["fixture_capture", "live_capture"]
    capture_layer: str
    allowed_tool_refs: list[str] = Field(max_length=256)


class RunCredentialBinding(Configuration):
    identity: RunIdentity
    subject: str = Field(min_length=1, max_length=256)
    token_id: str = Field(min_length=1, max_length=256)
    expires_at: AwareDatetime
    purposes: list[Literal["model_request", "tool_request"]] = Field(min_length=1, max_length=2)
    session_lineage: str = Field(min_length=1, max_length=256)
    allowed_tool_refs: list[str] = Field(max_length=256)


class SessionCapabilityRegistration(Published):
    """Deployment publication of an exact tested combination, never a Worker flag."""
    profile_snapshot: dict
    client_snapshot: dict
    runtime_snapshot: dict
    framework_snapshot: dict
    lock_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    limits: dict
    recovery_classes: list[Literal["settled_boundary", "approval_boundary"]] = Field(min_length=1, max_length=2)
    memory_mode: Literal["disabled", "pinned_context"]
    approver_subjects: list[str] = Field(min_length=1, max_length=256)
    approval_ttl_seconds: int = Field(gt=0, le=86400)
    evidence_refs: list[str] = Field(min_length=1, max_length=128)


def session_client_snapshot(config):
    # No Gateway URL, key, key reference or upstream credential reaches a Session.
    return {key: getattr(config.model, key) for key in (
        "ref", "revision", "protocol", "client_model", "upstream_model", "capability_ref", "max_retries",
    )}


def register_session_capability(connection, *, tenant_id, capability):
    _owner_only(connection)
    capability = SessionCapabilityRegistration.model_validate(capability)
    from wuji_core.contracts.sessions import SessionLimits
    SessionLimits.model_validate(capability.limits)
    profile = capability.profile_snapshot
    body = profile["body"]
    if (profile["digest"] != sha256(canonical_json_bytes(body)).hexdigest()
            or body["schema_version"] != "wuji.harness.session.v1"
            or body["memory_mode"] != capability.memory_mode
            or body["lock_digest"] != capability.lock_digest
            or not all(isinstance(ref, str) and 1 <= len(ref) <= 2048 for ref in capability.evidence_refs)
            or capability.framework_snapshot != {"python": "3.13.15", "agent_framework_core": "1.18.0", "agent_framework_openai": "1.14.3"}):
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    # The owner must publish only after reviewing the referenced actual evidence.
    # Runtime consumers cannot create this record or turn a candidate into passed.
    raw = json_text(capability.model_dump(mode="json"))
    old = connection.execute("SELECT document_json FROM vnext.session_capability WHERE tenant_id=%s AND ref=%s", (tenant_id, capability.ref)).fetchone()
    if old:
        if old[0] != raw:
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        return
    connection.execute("INSERT INTO vnext.session_capability(tenant_id,ref,profile_digest,document_json,digest) VALUES(%s,%s,%s,%s,%s)",
        (tenant_id, capability.ref, profile["digest"], raw, sha256(raw.encode()).hexdigest()))


def _owner_only(connection):
    owned = connection.execute("SELECT current_user=pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='vnext'").fetchone()
    if owned != (True,):
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")


def _insert_fixed(connection, table, keys, values, document):
    from psycopg import sql
    content = json_text(document.model_dump(mode="json"))
    names = sql.SQL(",").join(map(sql.Identifier, keys))
    where = sql.SQL(" AND ").join(sql.SQL("{}=%s").format(sql.Identifier(k)) for k in keys)
    old = connection.execute(sql.SQL("SELECT document_json FROM vnext.{} WHERE ").format(sql.Identifier(table)) + where, values).fetchone()
    if old:
        if old[0] != content:
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        return
    connection.execute(sql.SQL("INSERT INTO vnext.{} ({},document_json) VALUES ({},%s)").format(sql.Identifier(table), names, sql.SQL(",").join(sql.Placeholder() for _ in keys)), (*values, content))


def _match_definition(task, config):
    try:
        raw = task["definition_json"]
        if sha256(raw.encode()).hexdigest() != task["definition_digest"]:
            raise ValueError("changed definition")
        definition = strict_json_loads(raw)
        for name, profile in (("model_profile", config.model), ("runtime_profile", config.runtime)):
            published = definition[name]
            if published["ref"] != profile.ref or str(published["revision"]) != profile.revision or datetime.fromisoformat(published["published_at"].replace("Z", "+00:00")) != profile.published_at or profile.published_at > datetime.now(timezone.utc):
                raise ValueError("profile snapshot mismatch")
            if definition["task"][name + "_ref"] != profile.ref:
                raise ValueError("profile reference mismatch")
        if definition["lock_digest"] != config.runtime.lock_digest:
            raise ValueError("lock mismatch")
        return definition
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise DomainError("CAPABILITY_UNAVAILABLE", 503) from exc


def register_task_config(connection, *, owner, config):
    _owner_only(connection)
    config = TaskAdmissionConfig.model_validate(config)
    task = row(connection.execute("SELECT * FROM vnext.task WHERE tenant_id=%s AND project_id=%s AND task_id=%s FOR UPDATE", owner))
    if not task:
        raise DomainError("INVALID_REFERENCE", 422)
    _match_definition(task, config)
    previous = connection.execute("SELECT 1 FROM vnext.admission_config WHERE tenant_id=%s AND project_id=%s AND task_id=%s", owner).fetchone()
    if task["activated_at"] and not previous:
        raise DomainError("STALE_EXECUTION", 409)
    _insert_fixed(connection, "admission_config", ("tenant_id", "project_id", "task_id"), owner, config)


def register_tool_definition(connection, *, tenant_id, definition):
    _owner_only(connection)
    definition = ToolDefinition.model_validate(definition)
    # No HTTP executor is published in this release. A flag cannot enable it.
    if definition.allowed_target_kinds != ["workspace_read"]:
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    from wuji_core.admission.tools import validate_input_schema
    validate_input_schema(definition.input_schema)
    _insert_fixed(connection, "tool_definition", ("tenant_id", "ref"), (tenant_id, definition.ref), definition)


def register_executor(connection, *, owner, executor):
    _owner_only(connection)
    executor = ExecutorRegistration.model_validate(executor)
    _insert_fixed(connection, "executor_registration", ("tenant_id", "project_id", "task_id", "ref"), (*owner, executor.ref), executor)


def bind_run_credential(connection, *, binding):
    _owner_only(connection)
    binding = RunCredentialBinding.model_validate(binding)
    identity = binding.identity.model_dump(mode="json")
    owner = tuple(identity[k] for k in ("tenant_id", "project_id", "task_id"))
    run = row(connection.execute("SELECT * FROM vnext.agent_run WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s", (*owner, identity["agent_run_id"])))
    if not run or any(str(run[k]) != str(v) for k, v in identity.items()):
        raise DomainError("INVALID_REFERENCE", 422)
    _insert_fixed(connection, "run_credential", ("tenant_id", "project_id", "task_id", "subject", "token_id", "agent_run_id"), (*owner, binding.subject, binding.token_id, identity["agent_run_id"]), binding)


def revoke_run_credential(connection, *, tenant_id, subject, token_id):
    _owner_only(connection)
    connection.execute("UPDATE vnext.run_credential SET revoked=true WHERE tenant_id=%s AND subject=%s AND token_id=%s", (tenant_id, subject, token_id))


def revoke_tool_definition(connection, *, tenant_id, tool_definition_ref):
    _owner_only(connection)
    connection.execute("UPDATE vnext.tool_definition SET revoked=true WHERE tenant_id=%s AND ref=%s", (tenant_id, tool_definition_ref))


class AdmissionRegistry:
    def __init__(self, uow):
        self.uow = uow

    def binding(self, access):
        return self.uow.locate_run_credential(access)

    def session_capability(self, tx, profile_snapshot):
        from wuji_core.contracts.sessions import SessionCompatibility, SessionLimits
        config = self.config(tx)
        try:
            body = profile_snapshot["body"]
            definition = strict_json_loads(tx.task["definition_json"])
            actual = definition["worker_profiles"][body["work_kind"]]
            if (canonical_json_bytes(actual) != canonical_json_bytes(profile_snapshot)
                    or profile_snapshot["digest"] != sha256(canonical_json_bytes(body)).hexdigest()
                    or body["schema_version"] != "wuji.harness.session.v1"
                    or profile_snapshot["ref"] != body["ref"] or profile_snapshot["revision"] != body["revision"]
                    or body["lock_digest"] != config.runtime.lock_digest):
                raise ValueError("unpublished Session profile")
            candidates = tx.connection.execute(
                "SELECT document_json,digest FROM vnext.session_capability WHERE tenant_id=%s AND profile_digest=%s AND NOT revoked",
                (tx.owner[0], profile_snapshot["digest"]),
            ).fetchall()
            candidates = [(raw, stored_digest) for raw, stored_digest in candidates
                if strict_json_loads(raw).get("client_snapshot") == session_client_snapshot(config)
                and canonical_json_bytes(strict_json_loads(raw).get("runtime_snapshot")) == canonical_json_bytes(config.runtime.model_dump(mode="json"))]
            if len(candidates) != 1:
                raise ValueError("an exact verified Session capability is required")
            raw, stored_digest = candidates[0]
            record = SessionCapabilityRegistration.model_validate(strict_json_loads(raw))
            limits = SessionLimits.model_validate(record.limits)
            disabled = {name: False for name in ("todo", "mode", "file_memory", "file_access", "skills", "shell", "web_search", "background_agents", "outer_loop", "auto_approval", "mcp")}
            caps = {**disabled, "restoration": True, "compaction": body["compaction_enabled"],
                "native_approval": True, "versioned_memory": body["memory_mode"] == "pinned_context"}
            if (record.published_at > datetime.now(timezone.utc) or sha256(raw.encode()).hexdigest() != stored_digest
                    or canonical_json_bytes(record.profile_snapshot) != canonical_json_bytes(profile_snapshot)
                    or record.client_snapshot != session_client_snapshot(config)
                    or canonical_json_bytes(record.runtime_snapshot) != canonical_json_bytes(config.runtime.model_dump(mode="json"))
                    or record.lock_digest != config.runtime.lock_digest or record.memory_mode != body["memory_mode"]
                    or record.limits != body["session_limits"] or body["capabilities"] != caps
                    or record.framework_snapshot != {"python": "3.13.15", "agent_framework_core": "1.18.0", "agent_framework_openai": "1.14.3"}
                    or limits.max_total_bytes > config.runtime.limits.max_total_output_bytes
                    or limits.max_object_bytes > config.runtime.limits.max_single_output_bytes
                    or limits.max_pending_approvals > config.runtime.max_pending_operations):
                raise ValueError("Session capability combination differs")
            compatibility = SessionCompatibility(profile_snapshot=profile_snapshot,
                client_snapshot=record.client_snapshot, runtime_snapshot=record.runtime_snapshot,
                framework_snapshot=record.framework_snapshot, lock_digest=record.lock_digest,
                capability_ref=record.ref, capability_digest=stored_digest)
            return {"compatibility": compatibility, "limits": limits, "memory_mode": record.memory_mode,
                "recovery_classes": tuple(record.recovery_classes), "approval_ttl_seconds": record.approval_ttl_seconds,
                "approver_subjects": tuple(record.approver_subjects), "evidence_refs": tuple(record.evidence_refs)}
        except (KeyError, TypeError, ValueError) as error:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503) from error

    def config(self, tx):
        item = tx.connection.execute("SELECT document_json FROM vnext.admission_config WHERE tenant_id=%s AND project_id=%s AND task_id=%s", tx.owner).fetchone()
        if not item:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        config = TaskAdmissionConfig.model_validate(strict_json_loads(item[0]))
        _match_definition(tx.task, config)
        return config

    def tool(self, tx, ref):
        item = row(tx.connection.execute("SELECT * FROM vnext.tool_definition WHERE tenant_id=%s AND ref=%s", (tx.owner[0], ref)))
        if not item:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        if item["revoked"]:
            raise DomainError("STALE_EXECUTION", 409)
        definition = ToolDefinition.model_validate(strict_json_loads(item["document_json"]))
        if definition.published_at > datetime.now(timezone.utc):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        return definition

    def executor(self, tx, ref):
        item = tx.connection.execute("SELECT document_json FROM vnext.executor_registration WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND ref=%s", (*tx.owner, ref)).fetchone()
        if not item:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        return ExecutorRegistration.model_validate(strict_json_loads(item[0]))

    def routes(self, access):
        return TaskModelRouteResolver(self, access)


class TaskModelRouteResolver:
    def __init__(self, registry, access):
        self.registry, self.access = registry, access

    def resolve(self, task_id, model_profile_ref):
        with self.registry.uow.transaction(self.access, task_id) as tx:
            profile = self.registry.config(tx).model
            if profile.ref != model_profile_ref:
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            return profile
