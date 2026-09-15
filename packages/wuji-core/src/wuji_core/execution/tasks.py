"""P11 Task creation over the deployment-published model/runtime profiles.

Creation never starts execution: the Task is stored in the non-running ready
state and only the creator receives access to that new Task. The database
function is the authority for tenant, subject, project permission, published
profiles and the idempotent receipt; this module validates the public payload
and maps the database decisions to the frozen error envelope.
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4

import psycopg

from wuji_core.contracts.execution import TaskCreate, TaskView
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
        """Explicit entry points derived from the confirmed authorization scope."""

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
