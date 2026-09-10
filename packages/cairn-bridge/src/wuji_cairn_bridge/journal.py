"""Wuji operation journal; schema installation and production RLS are caller owned."""
from datetime import datetime, timezone
import re

from sqlalchemy import CheckConstraint, Column, DateTime, JSON, MetaData, String, Table, UniqueConstraint, Uuid, select, update
from sqlalchemy.exc import IntegrityError

from .errors import BindingConflict, BindingUnavailable, InvalidBridgeInput, OperationConflict
from .models import AgentResult, BindingRecord, ResultRecord, TaskKey, native_id, require_uuid

metadata = MetaData()
bindings = Table(
    "wuji_cairn_bindings", metadata,
    Column("task_id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, nullable=False), Column("project_id", Uuid, nullable=False),
    Column("server_id", Uuid, nullable=False), Column("native_project_id", String(128)),
    Column("request_digest", String(64), nullable=False), Column("state", String(16), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("server_id", "native_project_id"),
    CheckConstraint("state IN ('pending', 'sent', 'bound', 'rejected', 'unknown')"),
    CheckConstraint("(state = 'bound' AND native_project_id IS NOT NULL) OR (state <> 'bound' AND native_project_id IS NULL)"),
)
results = Table(
    "wuji_cairn_results", metadata,
    Column("operation_id", Uuid, primary_key=True),
    Column("task_id", Uuid, nullable=False), Column("tenant_id", Uuid, nullable=False),
    Column("project_id", Uuid, nullable=False), Column("server_id", Uuid, nullable=False),
    Column("native_project_id", String(128), nullable=False),
    Column("request_digest", String(64), nullable=False), Column("payload", JSON, nullable=False),
    Column("state", String(16), nullable=False), Column("fact_id", String(128)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("state IN ('pending', 'sent', 'applied', 'rejected', 'unknown', 'conflict')"),
    CheckConstraint("(state = 'applied' AND fact_id IS NOT NULL) OR (state <> 'applied' AND fact_id IS NULL)"),
)


def _identity(key):
    if not isinstance(key, TaskKey):
        raise InvalidBridgeInput("Task identity is required")
    return dict(task_id=key.task_id, tenant_id=key.tenant_id, project_id=key.project_id)


def _where(table, key):
    return [table.c[name] == value for name, value in _identity(key).items()]


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise InvalidBridgeInput("request digest must be SHA-256")


def _key(row):
    return TaskKey(row["tenant_id"], row["project_id"], row["task_id"])


def _binding(row):
    return BindingRecord(_key(row), row["server_id"], row["request_digest"], row["state"], row["native_project_id"])


def _result(row):
    from uuid import UUID
    payload = dict(row["payload"])
    payload["agent_run_id"] = UUID(payload["agent_run_id"])
    value = AgentResult(key=_key(row), operation_id=row["operation_id"], **payload)
    return ResultRecord(value, row["server_id"], row["native_project_id"], row["request_digest"], row["state"], row["fact_id"])


class SQLAlchemyJournal:
    def __init__(self, engine):
        self.engine = engine

    def get_binding(self, key):
        with self.engine.connect() as conn:
            row = conn.execute(select(bindings).where(*_where(bindings, key))).mappings().first()
            return _binding(row) if row else None

    def list_bindings(self, server_id):
        require_uuid(server_id, "server_id")
        with self.engine.connect() as conn:
            return [_binding(row) for row in conn.execute(select(bindings).where(bindings.c.server_id == server_id)).mappings()]

    def prepare_binding(self, key, server_id, digest):
        require_uuid(server_id, "server_id")
        _digest(digest)
        try:
            with self.engine.begin() as conn:
                conn.execute(bindings.insert().values(**_identity(key), server_id=server_id, request_digest=digest, state="pending", created_at=datetime.now(timezone.utc)))
        except IntegrityError:
            record = self.get_binding(key)
            if record is None or record.server_id != server_id or record.request_digest != digest:
                raise BindingConflict("binding identity or input conflicts") from None
            return record
        return self.get_binding(key)

    def claim_binding(self, key):
        with self.engine.begin() as conn:
            return conn.execute(update(bindings).where(*_where(bindings, key), bindings.c.state == "pending").values(state="sent")).rowcount == 1

    def finish_binding(self, key, project_id):
        native_id(project_id)
        try:
            with self.engine.begin() as conn:
                conn.execute(update(bindings).where(*_where(bindings, key), bindings.c.state == "sent").values(state="bound", native_project_id=project_id))
        except IntegrityError:
            raise BindingConflict("native project already bound") from None
        record = self.get_binding(key)
        if record is None or record.state != "bound" or record.project_id != project_id:
            raise BindingConflict("binding cannot be finalized")
        return record

    def set_binding_state(self, key, state):
        if state not in {"rejected", "unknown"}:
            raise InvalidBridgeInput("invalid binding transition")
        with self.engine.begin() as conn:
            conn.execute(update(bindings).where(*_where(bindings, key), bindings.c.state == "sent").values(state=state))
        record = self.get_binding(key)
        if record is None or record.state != state:
            raise BindingConflict("binding cannot change state")
        return record

    def get_result(self, key, operation_id):
        require_uuid(operation_id, "operation_id")
        with self.engine.connect() as conn:
            row = conn.execute(select(results).where(*_where(results, key), results.c.operation_id == operation_id)).mappings().first()
            return _result(row) if row else None

    def prepare_result(self, result, server_id, project_id, digest):
        require_uuid(server_id, "server_id")
        native_id(project_id)
        _digest(digest)
        if result.request_digest(server_id, project_id) != digest:
            raise OperationConflict("result digest does not match input")
        binding = self.get_binding(result.key)
        if binding is None or binding.state != "bound" or binding.server_id != server_id or binding.project_id != project_id:
            raise BindingUnavailable("bound Task context required")
        payload = {name: getattr(result, name) for name in ("intent_id", "description", "runtime_attempt", "execution_epoch", "scope_digest", "config_digest")}
        payload["agent_run_id"] = str(result.agent_run_id)
        try:
            with self.engine.begin() as conn:
                conn.execute(results.insert().values(**_identity(result.key), operation_id=result.operation_id, server_id=server_id, native_project_id=project_id, request_digest=digest, payload=payload, state="pending", created_at=datetime.now(timezone.utc)))
        except IntegrityError:
            record = self.get_result(result.key, result.operation_id)
            if record is None or record.result != result or record.server_id != server_id or record.project_id != project_id or record.request_digest != digest:
                raise OperationConflict("operation identity or input conflicts") from None
            return record
        return self.get_result(result.key, result.operation_id)

    def claim_result(self, key, operation_id):
        require_uuid(operation_id, "operation_id")
        with self.engine.begin() as conn:
            return conn.execute(update(results).where(*_where(results, key), results.c.operation_id == operation_id, results.c.state == "pending").values(state="sent")).rowcount == 1

    def finish_result(self, key, operation_id, fact_id):
        require_uuid(operation_id, "operation_id")
        native_id(fact_id)
        with self.engine.begin() as conn:
            conn.execute(update(results).where(*_where(results, key), results.c.operation_id == operation_id, results.c.state.in_(["sent", "unknown"])).values(state="applied", fact_id=fact_id))
        record = self.get_result(key, operation_id)
        if record is None or record.state != "applied" or record.fact_id != fact_id:
            raise OperationConflict("result cannot be finalized")
        return record

    def set_result_state(self, key, operation_id, state):
        require_uuid(operation_id, "operation_id")
        if state not in {"rejected", "unknown", "conflict"}:
            raise InvalidBridgeInput("invalid result transition")
        allowed = ["sent", "unknown"]
        if state == "rejected":
            allowed.append("pending")
        with self.engine.begin() as conn:
            conn.execute(update(results).where(*_where(results, key), results.c.operation_id == operation_id, results.c.state.in_(allowed)).values(state=state))
        record = self.get_result(key, operation_id)
        if record is None or record.state != state:
            raise OperationConflict("result cannot change state")
        return record
