"""Pure URL normalization, scope evaluation, and canonical digest helpers."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping
from urllib.parse import SplitResult, urlsplit
from uuid import UUID

UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
PATH_CHARACTERS = UNRESERVED | frozenset("/:@!$&'()*+,;=")
PERCENT_ESCAPE = re.compile(r"%([0-9A-Fa-f]{2})")
DOMAIN_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")

PLATFORM_LIMITS: dict[str, int | float] = {
    "max_total_requests": 200,
    "requests_per_second": 2.0,
    "max_concurrent_requests": 2,
    "request_timeout_seconds": 10,
    "max_response_bytes": 1_048_576,
    "max_runtime_seconds": 600,
}
INTEGER_LIMITS = {
    "max_total_requests",
    "max_concurrent_requests",
    "request_timeout_seconds",
    "max_response_bytes",
    "max_runtime_seconds",
}


class ScopePolicyError(ValueError):
    """The supplied draft or approved policy is outside B1's supported syntax."""


def _ascii(value: str, *, field: str) -> str:
    try:
        value.encode("ascii")
    except UnicodeEncodeError as error:
        raise ScopePolicyError(f"{field} must use an ASCII representation") from error
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise ScopePolicyError(f"{field} contains a control character")
    if " " in value or "\\" in value:
        raise ScopePolicyError(f"{field} contains an unsupported character")
    return value


def _normalize_percent(value: str, *, decode_unreserved: bool, field: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(value):
        character = value[index]
        if character != "%":
            output.append(character)
            index += 1
            continue
        if index + 2 >= len(value) or PERCENT_ESCAPE.fullmatch(value[index : index + 3]) is None:
            raise ScopePolicyError(f"{field} contains an invalid percent escape")
        byte = int(value[index + 1 : index + 3], 16)
        decoded = chr(byte)
        if decode_unreserved and decoded in UNRESERVED:
            output.append(decoded)
        elif decode_unreserved:
            raise ScopePolicyError(f"{field} contains an unsupported encoded character")
        else:
            output.append(f"%{byte:02X}")
        index += 3
    return "".join(output)


def _normalize_path(value: str) -> str:
    if not value.startswith("/"):
        raise ScopePolicyError("path must be absolute")
    if "//" in value:
        raise ScopePolicyError("path contains a repeated slash")
    normalized = _normalize_percent(value, decode_unreserved=True, field="path")
    if any(character not in PATH_CHARACTERS for character in normalized):
        raise ScopePolicyError("path contains an unsupported character")
    if any(segment in {".", ".."} for segment in normalized.split("/")):
        raise ScopePolicyError("path contains a dot segment")
    return normalized


def _normalize_host(parsed: SplitResult) -> str:
    raw_netloc = parsed.netloc
    if raw_netloc.startswith("["):
        closing = raw_netloc.find("]")
        remainder = "" if closing < 0 else raw_netloc[closing + 1 :]
        if closing < 0 or (remainder and re.fullmatch(r":[0-9]+", remainder) is None):
            raise ScopePolicyError("IPv6 authority is invalid")
    else:
        if "[" in raw_netloc or "]" in raw_netloc or raw_netloc.count(":") > 1:
            raise ScopePolicyError("URL authority is invalid")
        if ":" in raw_netloc and re.fullmatch(r"[^:]+:[0-9]+", raw_netloc) is None:
            raise ScopePolicyError("URL port is invalid")
    try:
        host = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise ScopePolicyError("URL port is invalid") from error
    if host is None or not host:
        raise ScopePolicyError("URL host is required")
    if port is not None and not 1 <= port <= 65535:
        raise ScopePolicyError("URL port is outside the supported range")

    if ":" in host:
        if not parsed.netloc.startswith("[") or "%" in host:
            raise ScopePolicyError("IPv6 literals must be bracketed and cannot use a zone ID")
        try:
            normalized_host = f"[{ipaddress.IPv6Address(host).compressed.lower()}]"
        except ValueError as error:
            raise ScopePolicyError("IPv6 literal is invalid") from error
    elif re.fullmatch(r"[0-9.]+", host):
        try:
            normalized_host = str(ipaddress.IPv4Address(host))
        except ValueError as error:
            raise ScopePolicyError("IPv4 literals must use dotted decimal notation") from error
        if normalized_host != host:
            raise ScopePolicyError("IPv4 literal is not canonical dotted decimal")
    else:
        if len(host) > 253 or host.endswith("."):
            raise ScopePolicyError("domain name is invalid")
        labels = host.split(".")
        if labels and all(
            label.isdigit() or re.fullmatch(r"0[xX][0-9A-Fa-f]+", label) is not None
            for label in labels
        ):
            raise ScopePolicyError("non-standard numeric IP notation is not supported")
        if not labels or any(DOMAIN_LABEL.fullmatch(label) is None for label in labels):
            raise ScopePolicyError("domain name is invalid")
        normalized_host = host.lower()

    default_port = (parsed.scheme.lower() == "http" and port == 80) or (
        parsed.scheme.lower() == "https" and port == 443
    )
    return normalized_host if port is None or default_port else f"{normalized_host}:{port}"


def normalize_url(value: str) -> str:
    """Normalize one absolute ASCII HTTP(S) URL without resolving or contacting it."""

    if not isinstance(value, str) or not 1 <= len(value) <= 2048:
        raise ScopePolicyError("target URL length is invalid")
    _ascii(value, field="target URL")
    try:
        parsed = urlsplit(value)
    except ValueError as error:
        raise ScopePolicyError("target URL is invalid") from error
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.netloc:
        raise ScopePolicyError("target URL must be absolute HTTP(S)")
    if "@" in parsed.netloc or parsed.username is not None or parsed.password is not None:
        raise ScopePolicyError("userinfo is not supported")
    if parsed.fragment or "#" in value:
        raise ScopePolicyError("fragments are not supported")
    host = _normalize_host(parsed)
    path = _normalize_path(parsed.path or "/")
    query = _normalize_percent(parsed.query, decode_unreserved=False, field="query")
    normalized = f"{scheme}://{host}{path}"
    if query:
        normalized += f"?{query}"
    return normalized


def normalize_origin(value: str) -> str:
    normalized = normalize_url(value)
    parsed = urlsplit(normalized)
    if parsed.path != "/" or parsed.query:
        raise ScopePolicyError("scope origin cannot contain a path or query")
    return f"{parsed.scheme}://{parsed.netloc}"


def normalize_path_prefix(value: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 2048:
        raise ScopePolicyError("path prefix length is invalid")
    _ascii(value, field="path prefix")
    if "?" in value or "#" in value:
        raise ScopePolicyError("path prefix cannot contain a query or fragment")
    normalized = _normalize_path(value)
    return normalized if normalized == "/" else normalized.rstrip("/")


def normalize_limits(value: Mapping[str, Any]) -> dict[str, int | float]:
    if not isinstance(value, Mapping) or set(value) != set(PLATFORM_LIMITS):
        raise ScopePolicyError("limits must contain exactly the supported fields")
    normalized: dict[str, int | float] = {}
    for key, maximum in PLATFORM_LIMITS.items():
        candidate = value[key]
        if key in INTEGER_LIMITS:
            if type(candidate) is not int or not 1 <= candidate <= maximum:
                raise ScopePolicyError(f"{key} is outside the supported range")
            normalized[key] = candidate
        else:
            if isinstance(candidate, bool) or not isinstance(candidate, (int, float)):
                raise ScopePolicyError(f"{key} must be a finite number")
            candidate = float(candidate)
            if not math.isfinite(candidate) or not 0 < candidate <= float(maximum):
                raise ScopePolicyError(f"{key} is outside the supported range")
            normalized[key] = candidate
    return normalized


def normalize_approved_scope(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "label",
        "origins",
        "allowed_path_prefixes",
        "excluded_path_prefixes",
        "allowed_methods",
        "limits",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise ScopePolicyError("scope must contain exactly the supported fields")
    label = value["label"]
    if not isinstance(label, str):
        raise ScopePolicyError("scope label must be text")
    label = label.strip()
    if not 1 <= len(label) <= 120:
        raise ScopePolicyError("scope label length is invalid")
    origins = value["origins"]
    allowed_prefixes = value["allowed_path_prefixes"]
    excluded_prefixes = value["excluded_path_prefixes"]
    methods = value["allowed_methods"]
    if not isinstance(origins, list) or not 1 <= len(origins) <= 20:
        raise ScopePolicyError("scope must include at least one origin")
    if not isinstance(allowed_prefixes, list) or not 1 <= len(allowed_prefixes) <= 100:
        raise ScopePolicyError("scope must include at least one allowed path prefix")
    if not isinstance(excluded_prefixes, list) or len(excluded_prefixes) > 100:
        raise ScopePolicyError("excluded path prefix count is invalid")
    if not isinstance(methods, list) or not 1 <= len(methods) <= 2:
        raise ScopePolicyError("scope must include at least one method")
    normalized_methods: list[str] = []
    for method in methods:
        if method not in {"GET", "HEAD"}:
            raise ScopePolicyError("scope method is unsupported")
        if method not in normalized_methods:
            normalized_methods.append(method)
    return {
        "label": label,
        "origins": list(dict.fromkeys(normalize_origin(origin) for origin in origins)),
        "allowed_path_prefixes": list(
            dict.fromkeys(normalize_path_prefix(prefix) for prefix in allowed_prefixes)
        ),
        "excluded_path_prefixes": list(
            dict.fromkeys(normalize_path_prefix(prefix) for prefix in excluded_prefixes)
        ),
        "allowed_methods": normalized_methods,
        "limits": normalize_limits(value["limits"]),
    }


def normalize_task_draft(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {"name", "scope", "target_url", "tool", "method", "limits"}
    if not isinstance(value, Mapping) or set(value) != required:
        raise ScopePolicyError("task draft must contain exactly the supported fields")
    name = value["name"]
    if not isinstance(name, str):
        raise ScopePolicyError("task name must be text")
    name = name.strip()
    if not 1 <= len(name) <= 120:
        raise ScopePolicyError("task name length is invalid")
    binding = value["scope"]
    if not isinstance(binding, Mapping) or set(binding) != {"policy_id", "version"}:
        raise ScopePolicyError("scope binding is invalid")
    try:
        policy_id = str(UUID(str(binding["policy_id"])))
    except (TypeError, ValueError, AttributeError) as error:
        raise ScopePolicyError("scope policy ID is invalid") from error
    version = binding["version"]
    if type(version) is not int or not 1 <= version <= 9_007_199_254_740_991:
        raise ScopePolicyError("scope version is invalid")
    if value["tool"] != "http_observe" or value["method"] not in {"GET", "HEAD"}:
        raise ScopePolicyError("task observation profile is unsupported")
    return {
        "name": name,
        "scope": {"policy_id": policy_id, "version": version},
        "target_url": normalize_url(value["target_url"]),
        "tool": "http_observe",
        "method": value["method"],
        "limits": normalize_limits(value["limits"]),
    }


def _canonical_hash(marker: str, value: Mapping[str, Any]) -> str:
    payload = {"schema": marker, "value": value}
    encoded = json.dumps(
        payload, ensure_ascii=True, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def input_digest(normalized_draft: Mapping[str, Any]) -> str:
    return _canonical_hash("task-draft/v1", normalized_draft)


def policy_hash(immutable_policy: Mapping[str, Any]) -> str:
    return _canonical_hash("scope-policy/v1", immutable_policy)


def _path_matches(path: str, prefix: str) -> bool:
    return prefix == "/" or path == prefix or path.startswith(f"{prefix}/")


def evaluate_scope(
    normalized_draft: Mapping[str, Any],
    approved_scope: Mapping[str, Any],
    authorization: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return the persisted B1 preview result; this function performs no I/O."""

    current = datetime.now(UTC) if now is None else now
    if current.tzinfo is None:
        raise ScopePolicyError("preview time must include a timezone")
    valid_from = authorization["valid_from"]
    valid_until = authorization["valid_until"]
    revoked_at = authorization.get("revoked_at")
    if valid_from.tzinfo is None or valid_until.tzinfo is None:
        raise ScopePolicyError("authorization timestamps must include a timezone")

    effective_limits = {
        key: min(
            normalized_draft["limits"][key],
            approved_scope["limits"][key],
            PLATFORM_LIMITS[key],
        )
        for key in PLATFORM_LIMITS
    }
    effective_scope = {
        "binding": dict(normalized_draft["scope"]),
        "label": approved_scope["label"],
        "valid_until": valid_until.isoformat(),
        "origins": list(approved_scope["origins"]),
        "allowed_path_prefixes": list(approved_scope["allowed_path_prefixes"]),
        "excluded_path_prefixes": list(approved_scope["excluded_path_prefixes"]),
        "allowed_methods": list(approved_scope["allowed_methods"]),
        "limits": effective_limits,
    }

    blockers: list[dict[str, str]] = []
    if valid_until <= current:
        blockers.append({"code": "AUTHORIZATION_EXPIRED", "message": "范围授权已过期"})
    elif revoked_at is not None:
        blockers.append({"code": "SCOPE_DENIED", "message": "范围授权已撤销"})
    elif valid_from > current:
        blockers.append({"code": "SCOPE_DENIED", "message": "范围授权尚未生效"})

    parsed = urlsplit(normalized_draft["target_url"])
    origin = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path
    denied_reason: str | None = None
    if origin not in approved_scope["origins"]:
        denied_reason = "目标地址不在批准来源内"
    elif normalized_draft["method"] not in approved_scope["allowed_methods"]:
        denied_reason = "请求方法不在批准范围内"
    elif not any(_path_matches(path, prefix) for prefix in approved_scope["allowed_path_prefixes"]):
        denied_reason = "目标路径不在批准范围内"
    elif any(_path_matches(path, prefix) for prefix in approved_scope["excluded_path_prefixes"]):
        denied_reason = "目标路径命中排除范围"
    if denied_reason is not None:
        blockers.append({"code": "SCOPE_DENIED", "message": denied_reason})

    blockers.append({"code": "CREATION_UNAVAILABLE", "message": "任务创建尚未开放"})
    return {
        "draft": dict(normalized_draft),
        "input_digest": input_digest(normalized_draft),
        "effective_scope": effective_scope,
        "expires_at": min(current + timedelta(seconds=300), valid_until),
        "can_create": False,
        "blockers": blockers,
    }
