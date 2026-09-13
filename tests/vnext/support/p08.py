"""P08 contract helpers that import the real production session boundary."""

from __future__ import annotations

from importlib import import_module
from inspect import Parameter, signature


REQUIRED = Parameter.empty


def session_repository_type():
    """Return the production repository type without a test substitute."""

    try:
        module = import_module("wuji_core.execution.sessions")
    except ModuleNotFoundError as error:
        if error.name != "wuji_core.execution.sessions":
            raise
        raise AssertionError(
            "P08 SessionRepository production module is absent"
        ) from error
    repository_type = getattr(module, "SessionRepository", None)
    if repository_type is None:
        raise AssertionError("P08 SessionRepository production type is absent")
    return repository_type


def parameter_shape(callable_object):
    """Return names, kinds, and defaults from one frozen public call shape."""

    return tuple(
        (parameter.name, parameter.kind, parameter.default)
        for parameter in signature(callable_object).parameters.values()
    )
