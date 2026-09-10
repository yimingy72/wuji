"""Process-boundary and environment isolation helpers."""

from __future__ import annotations

import os


_SECRET_MARKERS = (
    "API_KEY",
    "ACCESS_KEY",
    "AUTH_TOKEN",
    "BEARER_TOKEN",
    "CLIENT_SECRET",
    "CREDENTIAL",
    "LANGSMITH_API_KEY",
)


def scrub_harness_environment() -> tuple[str, ...]:
    """Remove provider secrets and disable external tracing in this probe process."""

    removed: list[str] = []
    for name in tuple(os.environ):
        upper = name.upper()
        if any(marker in upper for marker in _SECRET_MARKERS):
            os.environ.pop(name, None)
            removed.append(name)
    os.environ.update(
        {
            "DO_NOT_TRACK": "1",
            "LANGCHAIN_TRACING": "false",
            "LANGCHAIN_TRACING_V2": "false",
            "LANGSMITH_TRACING": "false",
            "OTEL_SDK_DISABLED": "true",
        }
    )
    return tuple(sorted(removed))


def secret_environment_is_clear() -> bool:
    return not any(any(marker in name.upper() for marker in _SECRET_MARKERS) for name in os.environ)
