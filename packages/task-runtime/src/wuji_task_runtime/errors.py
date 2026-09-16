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
    """A refused start permission, optionally naming the refusing predicate.

    Only the bounded `code` is safe to surface in an operator log; the message
    stays internal and is never copied into one.
    """

    def __init__(self, message, *, code=None):
        super().__init__(message)
        if code is not None and (
            not isinstance(code, str)
            or not 1 <= len(code) <= 64
            or not code.isascii()
            or not code.replace("_", "").isalnum()
            or not code.islower()
        ):
            raise ValueError("bounded lowercase permit code required")
        self.code = code


class ResourceMissing(TaskRuntimeError):
    pass


class RuntimeTransportError(TaskRuntimeError):
    def __init__(self, operation: str, status: int | None = None):
        self.operation = operation
        self.status = status
        super().__init__(f"{operation} failed (status={status or 'unavailable'})")


class RuntimeStateUnknown(RuntimeTransportError):
    """A write may have been accepted; the caller must reconcile its result."""
