"""Published configuration and independently revocable Run credentials."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from ipaddress import ip_address
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


class MechanismCandidateBinding(Configuration):
    tenant_id: str = Field(min_length=1, max_length=256)
    project_id: str = Field(min_length=1, max_length=256)
    task_id: str = Field(min_length=1, max_length=256)
    receiver_id: str = Field(min_length=1, max_length=256)
    runtime_attempt: str = Field(pattern=r"^[1-9][0-9]*$")
    pod_uid: str = Field(min_length=1, max_length=256)
    model_gateway_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    expires_at: AwareDatetime

    def matches_identity(self, identity):
        value = identity.model_dump(mode="json")
        return (
            (value["tenant_id"], value["project_id"], value["task_id"])
            == (self.tenant_id, self.project_id, self.task_id)
            and value["receiver_id"] == self.receiver_id
            and value["runtime_attempt"] == self.runtime_attempt
        )


class SessionCapabilityRegistration(Published):
    """Deployment publication of an exact tested combination, never a Worker flag."""
    validation_status: Literal["mechanism_candidate", "verified"]
    candidate_binding: MechanismCandidateBinding | None = None
    profile_snapshot: dict
    profile_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    client_snapshot: dict
    client_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    runtime_snapshot: dict
    runtime_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    framework_snapshot: dict
    framework_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    lock_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    limits: dict
    recovery_classes: list[Literal["settled_boundary", "approval_boundary"]] = Field(min_length=1, max_length=2)
    memory_mode: Literal["disabled", "pinned_context"]
    approver_subjects: list[str] = Field(min_length=1, max_length=256)
    approval_ttl_seconds: int = Field(gt=0, le=86400)
    evidence_refs: list[str] = Field(default_factory=list, max_length=128)

    @model_validator(mode="after")
    def validation_boundary(self):
        try:
            body = self.profile_snapshot["body"]
            expected = {
                "profile": self.profile_snapshot["digest"],
                "client": configuration_digest(self.client_snapshot),
                "runtime": configuration_digest(self.runtime_snapshot),
                "framework": configuration_digest(self.framework_snapshot),
            }
        except (KeyError, TypeError) as error:
            raise ValueError("capability snapshots require exact digests") from error
        if (
            self.profile_digest != expected["profile"]
            or self.profile_digest != configuration_digest(body)
            or self.client_digest != expected["client"]
            or self.runtime_digest != expected["runtime"]
            or self.framework_digest != expected["framework"]
        ):
            raise ValueError("capability snapshots require exact digests")
        if self.validation_status == "mechanism_candidate":
            lifetime = (
                None
                if self.candidate_binding is None
                else self.candidate_binding.expires_at - self.published_at
            )
            if (
                self.candidate_binding is None
                or lifetime is None
                or lifetime <= timedelta(0)
                or lifetime > timedelta(hours=1)
            ):
                raise ValueError("mechanism candidate requires a short-lived exact binding")
        elif self.candidate_binding is not None or not self.evidence_refs:
            raise ValueError("verified capability requires actual evidence and a new immutable record")
        return self


def configuration_digest(value):
    return sha256(canonical_json_bytes(value)).hexdigest()


def _storage_document(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _storage_document(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_storage_document(item) for item in value]
    return value


def model_gateway_digest(url):
    return configuration_digest({"gateway_url": url})


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
    if capability.validation_status == "mechanism_candidate":
        if capability.candidate_binding.tenant_id != tenant_id:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        try:
            _validate_mechanism_candidate(
                connection,
                capability=capability,
                run_binding=None,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503) from error
    # The owner must publish only after reviewing the referenced actual evidence.
    # Runtime consumers cannot create this record or turn a candidate into passed.
    raw = json_text(_storage_document(capability.model_dump(mode="python")))
    old = connection.execute("SELECT document_json FROM vnext.session_capability WHERE tenant_id=%s AND ref=%s", (tenant_id, capability.ref)).fetchone()
    if old:
        if old[0] != raw:
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        return
    connection.execute("INSERT INTO vnext.session_capability(tenant_id,ref,profile_digest,document_json,digest) VALUES(%s,%s,%s,%s,%s)",
        (tenant_id, capability.ref, profile["digest"], raw, sha256(raw.encode()).hexdigest()))


def _loopback_model(url):
    target = urlsplit(url)
    if (
        target.scheme != "http"
        or not target.hostname
        or target.username
        or target.password
        or target.query
        or target.fragment
    ):
        return False
    if target.hostname == "localhost":
        return True
    try:
        return ip_address(target.hostname).is_loopback
    except ValueError:
        return False


def _validate_mechanism_candidate(connection, *, capability, run_binding):
    binding = capability.candidate_binding
    if binding is None or binding.expires_at <= datetime.now(timezone.utc):
        raise ValueError("expired mechanism candidate")
    owner = (binding.tenant_id, binding.project_id, binding.task_id)
    task = row(connection.execute(
        "SELECT * FROM vnext.task WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
        owner,
    ))
    if task is None or not task["definition_json"] or sha256(task["definition_json"].encode()).hexdigest() != task["definition_digest"]:
        raise ValueError("mechanism candidate Task definition mismatch")
    definition = strict_json_loads(task["definition_json"])
    if (
        definition.get("evaluation_mode") != "mechanism_synthetic"
        or str(task["runtime_attempt"]) != binding.runtime_attempt
    ):
        raise ValueError("mechanism candidate Task is not synthetic")
    config_row = connection.execute(
        "SELECT document_json FROM vnext.admission_config WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
        owner,
    ).fetchone()
    if config_row is None:
        raise ValueError("mechanism candidate admission config absent")
    config = TaskAdmissionConfig.model_validate(strict_json_loads(config_row[0]))
    _match_definition(task, config)
    body = capability.profile_snapshot["body"]
    actual_profile = definition.get("worker_profiles", {}).get(body["work_kind"])
    if (
        canonical_json_bytes(actual_profile) != canonical_json_bytes(capability.profile_snapshot)
        or capability.client_snapshot != session_client_snapshot(config)
        or canonical_json_bytes(capability.runtime_snapshot) != canonical_json_bytes(config.runtime.model_dump(mode="json"))
        or not _loopback_model(config.model.gateway_url)
        or binding.model_gateway_digest != model_gateway_digest(config.model.gateway_url)
    ):
        raise ValueError("mechanism candidate fixed profile/model mismatch")
    schema_owner = connection.execute(
        "SELECT current_user=pg_get_userbyid(nspowner) "
        "FROM pg_namespace WHERE nspname='vnext'"
    ).fetchone() == (True,)
    if schema_owner:
        receiver = row(connection.execute(
            "SELECT * FROM vnext.scheduler_receiver WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND runtime_attempt=%s",
            (*owner, binding.runtime_attempt),
        ))
        receiver_matches = (
            receiver is not None
            and receiver["enabled"]
            and receiver["model_mode"] == "synthetic"
            and receiver["receiver_id"] == binding.receiver_id
            and receiver["pod_uid"] == binding.pod_uid
            and canonical_json_bytes(
                strict_json_loads(receiver["harness_profiles_json"]).get(
                    body["work_kind"]
                )
            )
            == canonical_json_bytes(capability.profile_snapshot)
        )
    else:
        receiver_matches = connection.execute(
            "SELECT vnext.mechanism_candidate_receiver_matches("
            "%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                *owner,
                binding.runtime_attempt,
                binding.receiver_id,
                binding.pod_uid,
                body["work_kind"],
                canonical_json_bytes(capability.profile_snapshot).decode(),
                "" if run_binding is None else run_binding.identity.agent_run_id,
            ),
        ).fetchone() == (True,)
    if not receiver_matches:
        raise ValueError("mechanism candidate receiver mismatch")
    tool_refs = body.get("tool_definition_refs")
    if not tool_refs or set(tool_refs) - set(config.allowed_tool_refs) or set(tool_refs) - set(config.runtime.allowed_tool_refs):
        raise ValueError("mechanism candidate tool profile mismatch")
    for ref in tool_refs:
        tool_row = row(connection.execute(
            "SELECT * FROM vnext.tool_definition WHERE tenant_id=%s AND ref=%s",
            (binding.tenant_id, ref),
        ))
        if tool_row is None or tool_row["revoked"]:
            raise ValueError("mechanism candidate tool unavailable")
        tool = ToolDefinition.model_validate(strict_json_loads(tool_row["document_json"]))
        executor_row = connection.execute(
            "SELECT document_json FROM vnext.executor_registration WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND ref=%s",
            (*owner, tool.executor_ref),
        ).fetchone()
        if executor_row is None:
            raise ValueError("mechanism candidate executor absent")
        executor = ExecutorRegistration.model_validate(strict_json_loads(executor_row[0]))
        if (
            tool.allowed_target_kinds != ["workspace_read"]
            or executor.evidence_origin != "fixture_capture"
            or executor.receiver_id != binding.receiver_id
            or ref not in executor.allowed_tool_refs
        ):
            raise ValueError("mechanism candidate requires fixture workspace reads")
    if run_binding is not None:
        identity = run_binding.identity
        if (
            not binding.matches_identity(identity)
            or set(tool_refs) - set(run_binding.allowed_tool_refs)
        ):
            raise ValueError("mechanism candidate current Run mismatch")
    return config


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


ACCESS_FLAGS = (
    "can_read",
    "can_write",
    "can_capture",
    "can_settle",
    "can_gc",
    "can_assess",
    "can_control",
    "can_observe",
    "can_admit",
)


def publish_task_admission(
    connection,
    *,
    owner,
    admission,
    capacity_pool_keys=(),
    access_grants=(),
    scheduler_identity=None,
    pod_controller=None,
):
    """Admit one created Task: config, capacity binding and execution identity.

    Owner-side deployment action. It matches the Task definition written by the
    creation entry, binds the deployment's published pools and records the
    scheduler/receiver identities that dispatch a Task needs. An empty argument
    keeps the corresponding part unpublished, so the caller decides when a Task
    becomes schedulable.
    """

    _owner_only(connection)
    task = row(
        connection.execute(
            "SELECT * FROM vnext.task WHERE tenant_id=%s AND project_id=%s AND task_id=%s FOR UPDATE",
            owner,
        )
    )
    if not task or not task["definition_json"]:
        raise DomainError("INVALID_REFERENCE", 422)
    register_task_config(connection, owner=owner, config=admission)
    for pool_key in capacity_pool_keys:
        pool = row(
            connection.execute(
                "SELECT * FROM vnext.capacity_pool WHERE pool_key=%s", (pool_key,)
            )
        )
        if not pool or (pool["tier"] == "tenant" and pool["tenant_id"] != owner[0]):
            raise DomainError("INVALID_REFERENCE", 422)
        old = connection.execute(
            "SELECT 1 FROM vnext.task_capacity_pool WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND pool_key=%s",
            (*owner, pool_key),
        ).fetchone()
        if old is None:
            connection.execute(
                "INSERT INTO vnext.task_capacity_pool(tenant_id,project_id,task_id,pool_key) VALUES(%s,%s,%s,%s)",
                (*owner, pool_key),
            )
    for grant in access_grants:
        subject = grant.get("subject")
        clearance = grant.get("clearance")
        if (
            not isinstance(subject, str)
            or not subject
            or type(clearance) is not int
            or clearance < 0
            or any(type(grant.get(flag, False)) is not bool for flag in ACCESS_FLAGS)
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        old = row(
            connection.execute(
                "SELECT * FROM vnext.task_access WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND subject=%s",
                (*owner, subject),
            )
        )
        values = tuple(bool(grant.get(flag, False)) for flag in ACCESS_FLAGS) + (clearance,)
        if old is not None:
            current = tuple(old[flag] for flag in ACCESS_FLAGS) + (old["clearance"],)
            if current != values:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            continue
        connection.execute(
            "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,"
            + ",".join(ACCESS_FLAGS)
            + ",clearance) VALUES("
            + ",".join(["%s"] * (len(ACCESS_FLAGS) + 5))
            + ")",
            (*owner, subject, *values),
        )
    if scheduler_identity is not None:
        identity = dict(scheduler_identity)
        required = (
            "template_ref",
            "issuer",
            "audience",
            "signing_key_ref",
            "signing_kid",
            "encryption_key_ref",
            "clearance",
        )
        if any(not identity.get(name) or (name == "clearance" and type(identity[name]) is not int) for name in required):
            raise DomainError("INVALID_SCHEMA", 422)
        old = row(
            connection.execute(
                "SELECT * FROM vnext.scheduler_identity_template WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND template_ref=%s",
                (*owner, identity["template_ref"]),
            )
        )
        expected = tuple(identity[name] for name in required[1:] if name != "clearance") + (identity["clearance"],)
        if old is not None:
            current = tuple(old[name] for name in required[1:] if name != "clearance") + (old["clearance"],)
            if current != expected or not old["enabled"]:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        else:
            connection.execute(
                """INSERT INTO vnext.scheduler_identity_template(tenant_id,project_id,task_id,
                template_ref,issuer,audience,signing_key_ref,signing_kid,encryption_key_ref,
                clearance,enabled) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true)""",
                (
                    *owner,
                    identity["template_ref"],
                    identity["issuer"],
                    identity["audience"],
                    identity["signing_key_ref"],
                    identity["signing_kid"],
                    identity["encryption_key_ref"],
                    identity["clearance"],
                ),
            )
    if pod_controller is not None:
        controller = dict(pod_controller)
        if not controller.get("controller_subject") or not controller.get("login_role"):
            raise DomainError("INVALID_SCHEMA", 422)
        old = row(
            connection.execute(
                "SELECT * FROM vnext.task_pod_controller WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND controller_subject=%s AND login_role=%s",
                (*owner, controller["controller_subject"], controller["login_role"]),
            )
        )
        if old is not None:
            if not old["enabled"]:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        else:
            connection.execute(
                """INSERT INTO vnext.task_pod_controller(tenant_id,project_id,task_id,
                controller_subject,login_role,enabled) VALUES(%s,%s,%s,%s,%s,true)""",
                (
                    *owner,
                    controller["controller_subject"],
                    controller["login_role"],
                ),
            )


def register_published_profile(connection, *, tenant_id, kind, document):
    """Publish one immutable model/runtime snapshot for Task creation."""

    _owner_only(connection)
    if kind not in {"model", "runtime"}:
        raise DomainError("INVALID_REFERENCE", 422)
    profile = (ModelProfile if kind == "model" else RuntimeProfile).model_validate(
        document
    )
    content = json_text(profile.model_dump(mode="json"))
    lock = profile.lock_digest if isinstance(profile, RuntimeProfile) else None
    existing = connection.execute(
        """SELECT document_json,lock_digest,revoked FROM vnext.published_profile
        WHERE tenant_id=%s AND kind=%s AND ref=%s AND revision=%s""",
        (tenant_id, kind, profile.ref, int(profile.revision)),
    ).fetchone()
    if existing:
        if existing[0] != content or existing[1] != lock:
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        if existing[2]:
            raise DomainError("STALE_EXECUTION", 409)
        return
    connection.execute(
        """INSERT INTO vnext.published_profile(tenant_id,kind,ref,revision,
        document_json,lock_digest,published_at)
        VALUES(%s,%s,%s,%s,%s,%s,%s)""",
        (
            tenant_id,
            kind,
            profile.ref,
            int(profile.revision),
            content,
            lock,
            profile.published_at,
        ),
    )


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
            stored_records = tx.connection.execute(
                "SELECT document_json,digest FROM vnext.session_capability WHERE tenant_id=%s AND profile_digest=%s AND NOT revoked",
                (tx.owner[0], profile_snapshot["digest"]),
            ).fetchall()
            disabled = {name: False for name in ("todo", "mode", "file_memory", "file_access", "skills", "shell", "web_search", "background_agents", "outer_loop", "auto_approval", "mcp")}
            caps = {**disabled, "restoration": True, "compaction": body["compaction_enabled"],
                "native_approval": True, "versioned_memory": body["memory_mode"] == "pinned_context"}
            matches = []
            for raw, stored_digest in stored_records:
                record = SessionCapabilityRegistration.model_validate(strict_json_loads(raw))
                limits = SessionLimits.model_validate(record.limits)
                if (record.published_at > datetime.now(timezone.utc) or sha256(raw.encode()).hexdigest() != stored_digest
                        or canonical_json_bytes(record.profile_snapshot) != canonical_json_bytes(profile_snapshot)
                        or record.profile_digest != profile_snapshot["digest"]
                        or record.client_snapshot != session_client_snapshot(config)
                        or canonical_json_bytes(record.runtime_snapshot) != canonical_json_bytes(config.runtime.model_dump(mode="json"))
                        or record.lock_digest != config.runtime.lock_digest or record.memory_mode != body["memory_mode"]
                        or record.limits != body["session_limits"] or body["capabilities"] != caps
                        or record.framework_snapshot != {"python": "3.13.15", "agent_framework_core": "1.18.0", "agent_framework_openai": "1.14.3"}
                        or limits.max_total_bytes > config.runtime.limits.max_total_output_bytes
                        or limits.max_object_bytes > config.runtime.limits.max_single_output_bytes
                        or limits.max_pending_approvals > config.runtime.max_pending_operations):
                    continue
                if record.validation_status == "mechanism_candidate":
                    try:
                        _validate_mechanism_candidate(
                            tx.connection,
                            capability=record,
                            run_binding=tx.run_binding,
                        )
                    except (DomainError, KeyError, TypeError, ValueError):
                        continue
                matches.append((record, limits, raw, stored_digest))
            verified = [item for item in matches if item[0].validation_status == "verified"]
            selected = verified if verified else matches
            if len(selected) != 1:
                raise ValueError("one exact verified or fixed mechanism candidate is required")
            record, limits, raw, stored_digest = selected[0]
            compatibility = SessionCompatibility(profile_snapshot=profile_snapshot,
                client_snapshot=record.client_snapshot, runtime_snapshot=record.runtime_snapshot,
                framework_snapshot=record.framework_snapshot, lock_digest=record.lock_digest,
                capability_ref=record.ref, capability_digest=stored_digest,
                validation_status=record.validation_status)
            return {"compatibility": compatibility, "limits": limits, "memory_mode": record.memory_mode,
                "recovery_classes": tuple(record.recovery_classes), "approval_ttl_seconds": record.approval_ttl_seconds,
                "approver_subjects": tuple(record.approver_subjects), "evidence_refs": tuple(record.evidence_refs),
                "validation_status": record.validation_status}
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
