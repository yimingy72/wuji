"""Errors contain operation/status information, never Kubernetes response bodies."""


class TaskRuntimeError(Exception):
    """Base error for the internal task-runtime API."""


class InvalidRuntimeConfig(TaskRuntimeError, ValueError):
    pass


class OwnershipError(TaskRuntimeError):
    pass


class RuntimeConflict(TaskRuntimeError):
    pass


class PermitDenied(TaskRuntimeError):
    pass


class ResourceMissing(TaskRuntimeError):
    pass


class RuntimeTransportError(TaskRuntimeError):
    def __init__(self, operation: str, status: int | None = None):
        self.operation = operation
        self.status = status
        super().__init__(f"{operation} failed (status={status or 'unavailable'})")


class RuntimeStateUnknown(RuntimeTransportError):
    """A write may have been accepted; the caller must reconcile its result."""
