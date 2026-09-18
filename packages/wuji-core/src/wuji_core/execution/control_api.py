"""P11 HTTP adapter into the existing ControlService state machine."""

from wuji_core.contracts.execution import TaskCommand, WorkCommand
from wuji_core.execution.control import ControlCommandContext, ControlService
from wuji_core.persistence.uow import AccessContext, DomainError


def task_for_work(uow, access, work_item_id):
    if not isinstance(access, AccessContext):
        raise TypeError("the authenticated AccessContext is required")
    if not isinstance(work_item_id, str) or not 1 <= len(work_item_id) <= 256:
        raise DomainError("INVALID_SCHEMA", 422)
    with uow.connection_factory() as connection:
        with connection.transaction():
            settings = {
                "tenant": access.principal.tenant_id,
                "subject": access.principal.subject,
                "task": "",
                "project": "",
                "clearance": "-1",
            }
            for key, value in settings.items():
                connection.execute(
                    "SELECT set_config(%s,%s,true)", ("wuji." + key, value)
                ).fetchone()
            found = connection.execute(
                "SELECT vnext.task_for_work(%s)", (work_item_id,)
            ).fetchone()
    if found is None or found[0] is None:
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")
    return found[0]


class ControlAPI:
    def __init__(self, control_service, *, launch_service=None):
        if not isinstance(control_service, ControlService):
            raise ValueError("a real ControlService is required")
        self.control = control_service
        self.launch = launch_service

    @staticmethod
    def _key(idempotency_key):
        if (
            not isinstance(idempotency_key, str)
            or not 1 <= len(idempotency_key) <= 256
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        return idempotency_key

    def command_task(self, access, task_id, command, *, idempotency_key):
        if not isinstance(access, AccessContext):
            raise TypeError("the authenticated AccessContext is required")
        if not isinstance(task_id, str) or not 1 <= len(task_id) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        if (
            self.launch is not None
            and command.command.value == "start"
            and work_id is None
        ):
            return self.launch.accept_start(
                access,
                task_id,
                TaskCommand.model_validate(command),
                idempotency_key=self._key(idempotency_key),
            )
        return self.control.apply(
            ControlCommandContext(
                access=access,
                task_id=task_id,
                operation_id=self._key(idempotency_key),
                command=TaskCommand.model_validate(command),
            )
        )

    def command_work(self, access, work_item_id, command, *, idempotency_key):
        if not isinstance(access, AccessContext):
            raise TypeError("the authenticated AccessContext is required")
        task_id = task_for_work(self.control.uow, access, work_item_id)
        return self.control.apply(
            ControlCommandContext(
                access=access,
                task_id=task_id,
                operation_id=self._key(idempotency_key),
                command=WorkCommand.model_validate(command),
                work_item_id=work_item_id,
            )
        )
