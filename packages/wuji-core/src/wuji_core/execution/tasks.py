"""P11 Task creation over the deployment-published model/runtime profiles.

Creation never starts execution: the Task is stored in the non-running ready
state and only the creator receives access to that new Task. The database
function is the authority for tenant, subject, project permission, published
profiles and the idempotent receipt; this module validates the public payload
and maps the database decisions to the frozen error envelope.
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
from uuid import uuid4

import psycopg

from wuji_core.contracts.execution import TaskCreate, TaskView
from wuji_core.contracts.generated import ReadinessReport, TaskList, TaskOptions
from wuji_core.http import strict_json_loads
from wuji_core.persistence.uow import AccessContext, DomainError, json_text


CREATOR_ROLES = frozenset({"operator", "controller"})
NON_CREATOR_ROLES = frozenset({"agent", "collector", "worker", "supervisor", "receiver"})


class TaskService:
    """Create non-running Tasks; the control plane owns every later transition."""

    def __init__(self, uow) -> None:
        self.uow = uow

    @staticmethod
    def _key(value):
        if not isinstance(value, str) or not 1 <= len(value) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        return value

    @staticmethod
    def start_points(payload):
        """Return the frozen entry points without widening the authorization scope.

        ``entry_points`` was added after the original Task contract.  Reading it
        with ``getattr`` keeps older generated consumers source-compatible while
        ensuring that a new client cannot silently lose its path/query.  The
        origin (scheme/host/port) is checked here rather than delegated to the
        prompt or a later worker step.
        """

        explicit = getattr(payload, "entry_points", None)
        if explicit is not None:
            if (
                not isinstance(explicit, list)
                or not 1 <= len(explicit) <= 16
                or any(
                    not isinstance(value, str)
                    or not value
                    or len(value.encode("utf-8")) > 2048
                    for value in explicit
                )
            ):
                raise DomainError("INVALID_SCHEMA", 422)
            scope = tuple(
                (entry.protocol.value, entry.host.casefold(), entry.port)
                for entry in payload.authorization_scope
            )
            checked = []
            for value in explicit:
                try:
                    parsed = urlsplit(value)
                    port = parsed.port
                except ValueError as error:
                    raise DomainError("INVALID_REFERENCE", 422) from error
                if (
                    parsed.scheme not in {"http", "https"}
                    or not parsed.hostname
                    or parsed.username is not None
                    or parsed.password is not None
                    or parsed.fragment
                    or any(ord(char) < 0x20 for char in value)
                ):
                    raise DomainError("INVALID_REFERENCE", 422)
                if port is None:
                    port = {"http": 80, "https": 443}[parsed.scheme]
                origin = (parsed.scheme, parsed.hostname.casefold(), port)
                if origin not in scope:
                    raise DomainError("INVALID_REFERENCE", 422)
                # Preserve the exact path/query spelling for the frozen
                # ContextBundle; URL normalization here would lose evidence.
                checked.append(value)
            return checked

        points = []
        for entry in payload.authorization_scope:
            point = f"{entry.protocol}://{entry.host}:{entry.port}"
            if point not in points:
                points.append(point)
        if not points:
            raise DomainError("INVALID_SCHEMA", 422)
        return points

    @staticmethod
    def _budget(payload):
        try:
            amount = Decimal(payload.budget.amount.root)
        except (InvalidOperation, AttributeError, TypeError) as error:
            raise DomainError("INVALID_SCHEMA", 422) from error
        if not amount.is_finite() or amount <= 0:
            raise DomainError("INVALID_SCHEMA", 422)

    @staticmethod
    def _view(task):
        """Build the public summary from the authorized task read model."""

        definition = strict_json_loads(task["definition_json"])
        task_input = definition.get("task") or {}
        return TaskView.model_validate(
            {
                "task_id": task["task_id"],
                "tenant_id": task["tenant_id"],
                "project_id": task["project_id"],
                "version": str(task["control_version"]),
                "name": task_input.get("name", "Unnamed task"),
                "scenario": task_input.get("scenario"),
                "desired_state": task["desired_state"],
                "observed_state": task["observed_state"],
                "goal_revision": "1",
                "execution_epoch": str(task["execution_epoch"]),
                "activated_at": task["activated_at"],
                "close_trigger": task["close_trigger"],
                "result_outcome": task["result_outcome"],
                "allowed_actions": TaskService._allowed_actions(task),
            }
        )

    @staticmethod
    def _allowed_actions(task):
        if task["observed_state"] == "closed":
            return []
        if task["desired_state"] in {"cancel", "finish"}:
            return []
        if task["activated_at"] is None:
            return ["start", "cancel"]
        if task["desired_state"] == "run":
            return ["pause", "cancel", "finish"]
        return ["resume", "cancel"]

    def get(self, access, task_id):
        if not isinstance(access, AccessContext):
            raise TypeError("the authenticated AccessContext is required")
        with self.uow.transaction(access, task_id) as tx:
            return self._view(tx.task)

    @staticmethod
    def _session_settings(access):
        return {
            "tenant": access.principal.tenant_id,
            "subject": access.principal.subject,
            "token_id": access.principal.token_id,
            "project": "",
            "task": "",
            "clearance": "-1",
        }

    def _read_json_function(self, access, function, args):
        """Call a migration-owned, authorization-filtered read function."""

        if not isinstance(access, AccessContext):
            raise TypeError("the authenticated AccessContext is required")
        with self.uow.connection_factory() as connection:
            with connection.transaction():
                for name, value in self._session_settings(access).items():
                    connection.execute(
                        "SELECT set_config(%s,%s,true)", ("wuji." + name, value)
                    ).fetchone()
                try:
                    result = connection.execute(function, args).fetchone()
                except psycopg.errors.UndefinedFunction as error:
                    raise DomainError("CAPABILITY_UNAVAILABLE", 503) from error
        if not result or result[0] is None:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        try:
            return strict_json_loads(result[0])
        except (TypeError, ValueError) as error:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503) from error

    def list(self, access, *, project_id, limit=20, cursor=None):
        if not isinstance(project_id, str) or not 1 <= len(project_id) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise DomainError("INVALID_SCHEMA", 422)
        if cursor is not None and (
            not isinstance(cursor, str) or not 1 <= len(cursor) <= 4096
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        return TaskList.model_validate(self._read_json_function(
            access,
            "SELECT vnext.list_tasks(%s,%s,%s)",
            (project_id, limit, cursor),
        ))

    def options(self, access, project_id):
        if not isinstance(project_id, str) or not 1 <= len(project_id) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        return TaskOptions.model_validate(self._read_json_function(
            access,
            "SELECT vnext.task_options(%s)",
            (project_id,),
        ))

    def readiness(self, access, task_id):
        if not isinstance(task_id, str) or not 1 <= len(task_id) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        return ReadinessReport.model_validate(self._read_json_function(
            access,
            "SELECT vnext.task_readiness(%s)",
            (task_id,),
        ))

    def create(self, access, payload, *, idempotency_key):
        if not isinstance(access, AccessContext):
            raise TypeError("the authenticated AccessContext is required")
        task = TaskCreate.model_validate(payload)
        roles = set(access.principal.roles)
        if not roles & CREATOR_ROLES or roles & NON_CREATOR_ROLES:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        if task.authorization_expires_at <= datetime.now(timezone.utc):
            raise DomainError("INVALID_SCHEMA", 422)
        self._budget(task)
        points = self.start_points(task)
        key = self._key(idempotency_key)
        new_task = str(uuid4())
        settings = (
            ("tenant", access.principal.tenant_id),
            ("subject", access.principal.subject),
            ("token_id", access.principal.token_id),
        )
        with self.uow.connection_factory() as connection:
            with connection.transaction():
                for name, value in settings:
                    connection.execute(
                        "SELECT set_config(%s,%s,true)", ("wuji." + name, value)
                    ).fetchone()
                try:
                    found = connection.execute(
                        "SELECT vnext.create_task(%s,%s,%s,%s,%s)",
                        (
                            task.project_id,
                            json_text(task.model_dump(mode="json")),
                            json_text(points),
                            key,
                            new_task,
                        ),
                    ).fetchone()
                except psycopg.errors.InsufficientPrivilege as error:
                    raise DomainError("NOT_FOUND_OR_FORBIDDEN") from error
                except psycopg.errors.UniqueViolation as error:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409) from error
                except psycopg.errors.CheckViolation as error:
                    raise DomainError("INVALID_REFERENCE", 422) from error
                except psycopg.errors.InvalidParameterValue as error:
                    raise DomainError("INVALID_SCHEMA", 422) from error
        if not found or not isinstance(found[0], str) or not found[0]:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        try:
            return TaskView.model_validate(strict_json_loads(found[0]))
        except (TypeError, ValueError) as error:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503) from error
