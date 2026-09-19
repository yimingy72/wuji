"""Narrow trust boundary for the first-use mechanism HTTP fixture.

This is deliberately not a general private-network allowlist.  A deployment
owner may freeze one or more origins from the fixed first-use fixture catalog
into a mechanism Task.  The Task's complete authorization scope must then be a
non-empty subset of those frozen origins before Explore may receive or invoke
an HTTP target tool.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from wuji_core.admission import target_scope


FIRST_USE_FIXTURE_ORIGIN = (
    "http://first-use-fixture.wuji-vnext-test.svc:8080"
)
MECHANISM_HTTP_FIELD = "mechanism_http_origins"


def trusted_mechanism_http_origins(value) -> tuple[str, ...]:
    """Validate owner-supplied origins against the closed fixture catalog.

    The cluster fixture is one exact origin.  Explicit localhost/127.0.0.1
    origins with an explicit port are accepted solely so a local test can bind
    an ephemeral harmless server.  Paths, credentials, wildcards, HTTPS and
    every other public/private address are refused.
    """

    if value is None:
        return ()
    if not isinstance(value, (list, tuple)) or not 1 <= len(value) <= 8:
        raise ValueError("mechanism_http_origins must be a bounded non-empty list")
    result = []
    for origin in value:
        if not isinstance(origin, str) or not 1 <= len(origin) <= 512:
            raise ValueError("mechanism HTTP origin must be a bounded string")
        try:
            parts = urlsplit(origin)
            port = parts.port
        except ValueError as error:
            raise ValueError("mechanism HTTP origin is invalid") from error
        if (
            parts.scheme != "http"
            or parts.username is not None
            or parts.password is not None
            or parts.path
            or parts.query
            or parts.fragment
            or port is None
            or not 1 <= port <= 65535
        ):
            raise ValueError("mechanism HTTP origin is not an exact HTTP origin")
        host = parts.hostname
        normalized = f"http://{host}:{port}" if host is not None else ""
        if normalized != origin or (
            normalized != FIRST_USE_FIXTURE_ORIGIN
            and host not in {"127.0.0.1", "localhost"}
        ):
            raise ValueError("mechanism HTTP origin is outside the fixture catalog")
        if normalized in result:
            raise ValueError("mechanism HTTP origin is duplicated")
        result.append(normalized)
    return tuple(result)


def authorization_scope(definition) -> tuple[target_scope.Target, ...]:
    """Return the complete, well-formed Task scope or an empty tuple.

    Current Task definitions keep authorization under ``task``.  The top-level
    fallback preserves older focused fixtures without letting it override the
    canonical nested scope.
    """

    if not isinstance(definition, dict):
        return ()
    task = definition.get("task")
    if isinstance(task, dict) and "authorization_scope" in task:
        raw = task.get("authorization_scope")
    else:
        raw = definition.get("authorization_scope")
    if not isinstance(raw, list) or not raw:
        return ()
    assets = target_scope.approved_assets(raw)
    if len(assets) != len(raw):
        return ()
    return assets


def mechanism_http_origins(definition) -> tuple[str, ...]:
    """Validate the frozen field and require the entire scope to fit inside it."""

    if not isinstance(definition, dict):
        raise ValueError("Task definition is unavailable")
    value = definition.get(MECHANISM_HTTP_FIELD)
    if value is None:
        return ()
    origins = trusted_mechanism_http_origins(value)
    scope = authorization_scope(definition)
    if not scope:
        raise ValueError("mechanism HTTP requires a non-empty Task scope")
    allowed = set(origins)
    if any(asset.key not in allowed for asset in scope):
        raise ValueError("Task scope exceeds the frozen mechanism HTTP origins")
    return origins


def http_target_allowed(definition, work_kind: str) -> bool:
    """Whether this exact frozen Task/work role may use an HTTP target tool."""

    if work_kind != "explore" or not isinstance(definition, dict):
        return False
    mode = definition.get("evaluation_mode")
    if mode == "real_model":
        return True
    if mode == "mechanism_synthetic":
        return bool(mechanism_http_origins(definition))
    # Definitions predating evaluation_mode retain their existing target-tool
    # behavior.  A launched mechanism Task always freezes its explicit mode.
    return mode is None
