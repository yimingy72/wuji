"""Isolated Wuji vNext HTTP composition and security boundaries."""

from wuji_core.http.app import UnsafeJsonResponse, VNextAPIRouter, create_app
from wuji_core.http.json_boundary import (
    DEFAULT_JSON_LIMITS,
    DecimalJSONResponse,
    InvalidJsonDocument,
    JsonBoundaryLimits,
    StrictJsonRequest,
    StrictJsonRoute,
    canonical_json_bytes,
    strict_json_loads,
)

__all__ = [
    "DEFAULT_JSON_LIMITS",
    "DecimalJSONResponse",
    "InvalidJsonDocument",
    "JsonBoundaryLimits",
    "StrictJsonRequest",
    "StrictJsonRoute",
    "UnsafeJsonResponse",
    "VNextAPIRouter",
    "canonical_json_bytes",
    "create_app",
    "strict_json_loads",
]
