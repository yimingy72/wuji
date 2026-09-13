"""Short database transactions with server-derived access and fixed lock order."""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable

from wuji_core.http.auth import Principal
from wuji_core.http.json_boundary import canonical_json_bytes


class DomainError(ValueError):
    def __init__(self, code: str, status: int = 404):
        self.code, self.status = code, status
        super().__init__(code)


@dataclass(frozen=True)
class AccessContext:
    principal: Principal
    request_id: str


def json_text(value):
    return canonical_json_bytes(value).decode("utf-8")


def row(cursor):
    value = cursor.fetchone()
    return (
        dict(zip((column.name for column in cursor.description), value))
        if value is not None
        else None
    )


@dataclass
class Transaction:
    connection: Any
    owner: tuple[str, str, str]
    access: AccessContext
    permissions: dict[str, Any]
    task: dict[str, Any]
    capacity_pools: tuple[dict[str, Any], ...] = ()

    def semantic_event(
        self,
        kind: str,
        payload: object,
        *,
        observations: int = 0,
        access_level: int = 0,
    ):
        result = self.connection.execute(
            "UPDATE vnext.task SET board_revision=board_revision+1,event_seq=event_seq+1,observation_count=observation_count+%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s RETURNING event_seq",
            (observations, *self.owner),
        ).fetchone()
        self.connection.execute(
            "INSERT INTO vnext.outbox(tenant_id,project_id,task_id,event_seq,kind,payload_json,access_level) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (*self.owner, result[0], kind, json_text(payload), access_level),
        )

    def add_dependency(
        self, work_item_id: str, predecessor_id: str, condition: str, *, criterion=None
    ):
        values = (
            (None, None, None)
            if criterion is None
            else ("goal_criterion", criterion.criterion_id, criterion.revision.root)
        )
        self.connection.execute(
            "INSERT INTO vnext.work_dependency(tenant_id,project_id,task_id,work_item_id,predecessor_id,condition,criterion_type,criterion_id,criterion_revision) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (*self.owner, work_item_id, predecessor_id, condition, *values),
        )
        self.semantic_event(
            "work_dependency_added",
            {
                "work_item_id": work_item_id,
                "predecessor_id": predecessor_id,
                "condition": condition,
            },
        )


class UnitOfWork:
    def __init__(self, connection_factory: Callable):
        self.connection_factory = connection_factory

    @contextmanager
    def transaction(
        self,
        access: AccessContext,
        task_id: str,
        *,
        capability="read",
        repeatable_read=False,
    ):
        if capability not in {
            "read",
            "write",
            "capture",
            "settle",
            "gc",
            "assess",
            "evidence",
            "snapshot",
            "model_output",
            "control",
            "observe",
            "admit",
        }:
            raise ValueError("unsupported capability")
        with self.connection_factory() as connection:
            with connection.transaction():
                if repeatable_read:
                    connection.execute(
                        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"
                    )
                connection.execute(
                    "SELECT set_config('statement_timeout','5000',true),set_config('lock_timeout','5000',true)"
                ).fetchone()
                for key, value in {
                    "tenant": access.principal.tenant_id,
                    "subject": access.principal.subject,
                    "project": "",
                    "task": "",
                    "clearance": "-1",
                    "write": "false",
                    "assess": "false",
                    "capture": "false",
                    "snapshot": "false",
                    "domain_write": "false",
                    "gc": "false",
                    "model_output": "false",
                    "control": "false",
                    "observe": "false",
                    "admit": "false",
                }.items():
                    connection.execute(
                        "SELECT set_config(%s,%s,true)", ("wuji." + key, value)
                    ).fetchone()
                permission = row(
                    connection.execute(
                        "SELECT * FROM vnext.task_access WHERE tenant_id=%s AND subject=%s AND task_id=%s",
                        (access.principal.tenant_id, access.principal.subject, task_id),
                    )
                )
                allowed = permission and (
                    (permission["can_capture"] or permission["can_settle"])
                    if capability == "evidence"
                    else (
                        permission["can_read"]
                        if capability == "snapshot"
                        else permission["can_" + capability]
                    )
                )
                if not permission or not permission["can_read"] or not allowed:
                    raise DomainError("NOT_FOUND_OR_FORBIDDEN")
                _require_control_actor(access, capability)
                values = {
                    "project": permission["project_id"],
                    "task": task_id,
                    "clearance": str(permission["clearance"]),
                    "write": str(capability != "read").lower(),
                    "capture": str(
                        capability in {"evidence", "capture", "settle"}
                        and "collector" in access.principal.roles
                        and "agent" not in access.principal.roles
                        and (permission["can_capture"] or permission["can_settle"])
                    ).lower(),
                    "snapshot": str(capability == "snapshot").lower(),
                    "model_output": str(
                        capability == "model_output"
                        and bool(access.principal.roles & {"worker", "supervisor"})
                        and "agent" not in access.principal.roles
                    ).lower(),
                    "domain_write": str(
                        permission["can_write"]
                        and capability in {"write", "model_output"}
                    ).lower(),
                    "gc": str(capability == "gc").lower(),
                    "assess": str(
                        permission["can_assess"]
                        and "assessor" in access.principal.roles
                        and "agent" not in access.principal.roles
                        and capability == "assess"
                    ).lower(),
                    "control": str(capability == "control").lower(),
                    "observe": str(capability == "observe").lower(),
                    "admit": str(capability == "admit").lower(),
                }
                for key, value in values.items():
                    connection.execute(
                        "SELECT set_config(%s,%s,true)", ("wuji." + key, value)
                    ).fetchone()
                owner = (permission["tenant_id"], permission["project_id"], task_id)
                pools = ()
                if capability in {"control", "observe", "admit"}:
                    from wuji_core.execution.capacity import prelock_pools

                    pools = prelock_pools(connection, owner)
                # Capacity prelocks, when needed, already precede Task. Resources follow it.
                lock = " FOR UPDATE" if capability != "read" else ""
                task = row(
                    connection.execute(
                        "SELECT * FROM vnext.task WHERE tenant_id=%s AND project_id=%s AND task_id=%s"
                        + lock,
                        owner,
                    )
                )
                if task is None:
                    raise DomainError("NOT_FOUND_OR_FORBIDDEN")
                if capability in {"control", "observe", "admit"}:
                    current = row(
                        connection.execute(
                            "SELECT * FROM vnext.task_access WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND subject=%s",
                            (*owner, access.principal.subject),
                        )
                    )
                    if (
                        not current
                        or not current["can_read"]
                        or not current["can_" + capability]
                    ):
                        raise DomainError("NOT_FOUND_OR_FORBIDDEN")
                    permission = current
                    connection.execute(
                        "SELECT set_config('wuji.clearance',%s,true)",
                        (str(permission["clearance"]),),
                    ).fetchone()
                yield Transaction(connection, owner, access, permission, task, pools)

    def locate_artifact(self, access, artifact_id, version):
        # A locator read is tenant/subject ACL filtered, then the scoped read reauthorizes.
        with self.connection_factory() as connection:
            with connection.transaction():
                for key, value in {
                    "tenant": access.principal.tenant_id,
                    "subject": access.principal.subject,
                    "task": "",
                    "project": "",
                    "clearance": "-1",
                }.items():
                    connection.execute(
                        "SELECT set_config(%s,%s,true)", ("wuji." + key, value)
                    ).fetchone()
                return row(
                    connection.execute(
                        "SELECT task_id,sha256 FROM vnext.artifact WHERE entity_id=%s AND revision=%s",
                        (artifact_id, version),
                    )
                )


def _require_control_actor(access, capability):
    roles = {
        "control": {"operator", "controller"},
        "observe": {"controller", "reconciler"},
        "admit": {"scheduler", "controller"},
    }
    if capability in roles and (
        "agent" in access.principal.roles
        or not access.principal.roles.intersection(roles[capability])
    ):
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")
