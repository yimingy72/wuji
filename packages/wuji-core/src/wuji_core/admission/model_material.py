"""Deterministic, bounded representations of sealed HTTP exchange artifacts.

This module is deliberately independent from HTTP routing and authorization.  A
caller supplies the already-authorized artifact row and its checked bytes; the
renderer never performs I/O, follows a redirect, decodes a second compression
layer, or invents a response status.  The same pure function is used by the
internal ToolGate material endpoint and by any future artifact presentation
endpoint.
"""

from __future__ import annotations

import base64
import binascii
from hashlib import sha256
import re
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit

from wuji_core.contracts.generated import (
    BlobRef,
    MaterialOmissionReason,
    ModelMaterialRepresentation,
    ModelMaterialSource,
    ModelMaterialV2,
)


MODEL_MATERIAL_SCHEMA = "wuji.model-material.v2"
HTTP_RENDERER_VERSION = "wuji-http-renderer.v2"
HTTP_EXCHANGE_SCHEMA = "wuji.http-exchange.v1"
HTTP_EXCHANGE_MEDIA_TYPE = "application/vnd.wuji.http-exchange+json"
REPRESENTATION_MEDIA_TYPE = "text/plain; charset=utf-8"

DEFAULT_SOURCE_BYTES = 1 * 1024 * 1024
DEFAULT_DECODED_BODY_BYTES = 256 * 1024
DEFAULT_REPRESENTATION_BYTES = 32 * 1024

_CONTENT_TYPE = "content-type"
_DISPLAY_HEADERS = frozenset(
    {"content-type", "content-length", "location", "server", "date"}
)
_SENSITIVE_HEADERS = frozenset(
    {
        "authorization",
        "cookie",
        "proxy-authorization",
        "proxy-authenticate",
        "set-cookie",
        "www-authenticate",
        "x-api-key",
        "x-auth-token",
    }
)
_TEXT_MEDIA = re.compile(
    r"^(?:text/[^;\s]+|application/(?:json|[^;+/]+\+json|xml|[^;+/]+\+xml|javascript|graphql|x-www-form-urlencoded))(?:$|;)",
    re.IGNORECASE,
)
_CHARSET = re.compile(r"(?:^|;)\s*charset\s*=\s*(?:\"([^\"]+)\"|([^;\s]+))", re.I)
_BODY_CREDENTIALS = (
    re.compile(r"(?i)(\bbearer\s+)[A-Za-z0-9._~+/-]+=*"),
    re.compile(r'''(?ix)(["']?(?:password|passwd|api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|secret)["']?\s*[:=]\s*["']?)[^\s"'&,;<>}]+'''),
)
_PROVIDER_KEY = re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")


def _redact_body(text):
    original = text
    for pattern in _BODY_CREDENTIALS:
        text = pattern.sub(lambda match: match.group(1) + "[REDACTED]", text)
    text = _PROVIDER_KEY.sub("[REDACTED]", text)
    return text, text != original


def _reason(value: str | MaterialOmissionReason) -> MaterialOmissionReason:
    legacy = {
        "not_sealed": "source_not_sealed",
        "not_text_media": "unsupported_media",
        "over_inline_limit": "representation_limit",
        "unreadable": "source_unavailable",
        "not_utf8": "invalid_encoding",
    }
    raw_value = getattr(value, "value", value)
    value = legacy.get(raw_value, raw_value)
    try:
        return value if isinstance(value, MaterialOmissionReason) else MaterialOmissionReason(value)
    except ValueError as error:
        raise ValueError("material omission reason is not registered") from error


def omitted_model_material(
    tool_call_id: str,
    reason: str | MaterialOmissionReason,
    *,
    source: ModelMaterialSource | dict | None = None,
) -> ModelMaterialV2:
    """Build the only valid omitted packet shape.

    Source metadata is optional: callers must leave it null when the source was
    not readable or authorization did not permit revealing its identity.
    """

    return ModelMaterialV2.model_validate(
        {
            "schema_version": MODEL_MATERIAL_SCHEMA,
            "tool_call_id": tool_call_id,
            "status": "omitted",
            "source": source,
            "representation": None,
            "omission_reason": _reason(reason),
        }
    )


def _source(ref: BlobRef | dict | None, record: Mapping[str, object] | None):
    if ref is None or record is None:
        return None
    try:
        source = ModelMaterialSource.model_validate(
            {
                "artifact_ref": ref,
                "artifact_sha256": record["sha256"],
                "media_type": record["media_type"],
                "completeness": record["completeness"],
            }
        )
    except (KeyError, TypeError, ValueError):
        return None
    return source


def _source_digest_ok(ref: BlobRef, record: Mapping[str, object], raw: bytes) -> bool:
    if not isinstance(raw, bytes):
        return False
    if type(record.get("size_bytes")) is not int or record["size_bytes"] != len(raw):
        return False
    expected = record.get("sha256")
    if not isinstance(expected, str) or sha256(raw).hexdigest() != expected:
        return False
    return ref.sha256.root == expected


def _bounded_prefix(text: str, maximum: int) -> tuple[str, bool]:
    encoded = text.encode("utf-8")
    if len(encoded) <= maximum:
        return text, False
    # UTF-8 boundaries are selected by code point, never by slicing encoded
    # bytes.  A body larger than the model budget is still useful evidence: it
    # is delivered with representation.truncated=true.
    return encoded[:maximum].decode("utf-8", errors="ignore"), True


def _charset(media_type: str) -> str:
    match = _CHARSET.search(media_type)
    if match is None:
        return "utf-8"
    value = (match.group(1) or match.group(2)).strip().lower().replace("_", "-")
    aliases = {
        "utf8": "utf-8",
        "us-ascii": "ascii",
        "iso8859-1": "latin-1",
        "iso-8859-1": "latin-1",
        "gb2312": "gb18030",
    }
    value = aliases.get(value, value)
    if value not in {"utf-8", "ascii", "gb18030", "gbk", "latin-1"}:
        raise LookupError(value)
    return value


def _safe_location(value: str) -> tuple[str, bool]:
    """Keep redirect path information without copying query credentials."""

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return "[redacted]", True
    if parsed.scheme not in {"", "http", "https"}:
        return "[redacted]", True
    credentials = parsed.username is not None or parsed.password is not None
    if not parsed.query and not parsed.fragment and not credentials:
        return value, False
    host = parsed.hostname or ""
    if ":" in host:
        host = "[" + host + "]"
    netloc = host + (":" + str(port) if port is not None else "")
    return urlunsplit((parsed.scheme, netloc, parsed.path, "", "")), True


def _headers(value: object) -> tuple[dict[str, str], bool, str | None]:
    if not isinstance(value, dict):
        return {}, False, "unsupported_schema"
    displayed: dict[str, str] = {}
    redacted = False
    for key, header_value in value.items():
        if (
            not isinstance(key, str)
            or not key
            or not isinstance(header_value, str)
            or "\r" in key
            or "\n" in key
            or "\r" in header_value
            or "\n" in header_value
        ):
            return {}, False, "unsupported_schema"
        normalized = key.lower()
        if normalized in displayed:
            return {}, False, "unsupported_schema"
        if normalized in _SENSITIVE_HEADERS or normalized not in _DISPLAY_HEADERS:
            redacted = True
            continue
        if normalized == "location":
            header_value, changed = _safe_location(header_value)
            redacted = redacted or changed
        displayed[normalized] = header_value
    return dict(sorted(displayed.items())), redacted, None


def _document(raw: bytes) -> tuple[dict, ModelMaterialSource | None, str | None]:
    """Validate the sealed exchange shape without performing any I/O."""

    from wuji_core.http import strict_json_loads

    try:
        value = strict_json_loads(raw)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return {}, None, "invalid_encoding"
    if not isinstance(value, dict):
        return {}, None, "unsupported_schema"
    if value.get("schema_version") != HTTP_EXCHANGE_SCHEMA:
        return {}, None, "unsupported_schema"
    response = value.get("response")
    request = value.get("request")
    if not isinstance(response, dict) or not isinstance(request, dict):
        return {}, None, "unsupported_schema"
    if not isinstance(value.get("tool_attempt_id"), str) or not isinstance(value.get("target"), str):
        return {}, None, "unsupported_schema"
    if set(request) != {"method", "url", "headers"} or not isinstance(request["method"], str) or not isinstance(request["url"], str):
        return {}, None, "unsupported_schema"
    if _headers(request["headers"])[2] is not None:
        return {}, None, "unsupported_schema"
    if set(response) != {"status", "headers", "body_base64", "body_bytes", "truncated"}:
        return {}, None, "unsupported_schema"
    status = response["status"]
    if type(status) is not int or not 100 <= status <= 599:
        # In particular, status=0 is not an observed HTTP response.
        return {}, None, "unsupported_schema"
    body_base64 = response["body_base64"]
    body_bytes = response["body_bytes"]
    if not isinstance(body_base64, str) or type(body_bytes) is not int or body_bytes < 0 or type(response["truncated"]) is not bool:
        return {}, None, "unsupported_schema"
    headers, redacted, error = _headers(response["headers"])
    if error:
        return {}, None, error
    return {
        "response": response,
        "status": status,
        "headers": headers,
        "redaction_applied": redacted,
        "content_type": next((v for k, v in headers.items() if k == _CONTENT_TYPE), ""),
    }, None, None


def render_http_exchange_v2(
    tool_call_id: str,
    *,
    artifact_ref: BlobRef | dict | None,
    artifact_record: Mapping[str, object] | None,
    raw: bytes | None,
    max_source_bytes: int = DEFAULT_SOURCE_BYTES,
    max_decoded_body_bytes: int = DEFAULT_DECODED_BODY_BYTES,
    max_representation_bytes: int = DEFAULT_REPRESENTATION_BYTES,
) -> ModelMaterialV2:
    """Render one already-authorized HTTP artifact into ``ModelMaterialV2``.

    ``raw`` must be the exact bytes returned by the artifact store.  The
    function returns an omitted packet for every invalid or over-bound input;
    it never performs a fallback fetch.  A partial capture can still be
    delivered: its source completeness remains ``partial`` and only renderer
    cropping controls ``representation.truncated``.
    """

    if not isinstance(tool_call_id, str) or not tool_call_id:
        raise ValueError("a canonical tool call id is required")
    if type(max_source_bytes) is not int or max_source_bytes < 1:
        raise ValueError("max_source_bytes must be positive")
    if type(max_decoded_body_bytes) is not int or max_decoded_body_bytes < 1:
        raise ValueError("max_decoded_body_bytes must be positive")
    if type(max_representation_bytes) is not int or not 1 <= max_representation_bytes <= DEFAULT_REPRESENTATION_BYTES:
        raise ValueError("max_representation_bytes must be within the v2 bound")

    try:
        ref = BlobRef.model_validate(artifact_ref) if artifact_ref is not None else None
    except ValueError:
        return omitted_model_material(tool_call_id, "source_digest_mismatch")
    source = _source(ref, artifact_record)
    if ref is None or artifact_record is None:
        return omitted_model_material(tool_call_id, "source_unavailable")
    if artifact_record.get("state") != "sealed":
        return omitted_model_material(tool_call_id, "source_not_sealed", source=source)
    if (
        type(artifact_record.get("size_bytes")) is not int
        or artifact_record["size_bytes"] > max_source_bytes
    ):
        return omitted_model_material(tool_call_id, "representation_limit", source=source)
    if raw is None:
        return omitted_model_material(tool_call_id, "source_unavailable")
    if not _source_digest_ok(ref, artifact_record, raw):
        return omitted_model_material(tool_call_id, "source_digest_mismatch", source=source)
    if len(raw) > max_source_bytes:
        return omitted_model_material(tool_call_id, "representation_limit", source=source)
    if artifact_record.get("media_type") != HTTP_EXCHANGE_MEDIA_TYPE:
        return omitted_model_material(tool_call_id, "unsupported_media", source=source)

    document, _unused, error = _document(raw)
    if error:
        return omitted_model_material(tool_call_id, error, source=source)
    response = document["response"]
    if response["truncated"] and artifact_record.get("completeness") == "complete":
        return omitted_model_material(tool_call_id, "capture_truncated", source=source)
    body_base64 = response["body_base64"]
    if len(body_base64) > ((max_decoded_body_bytes + 2) // 3) * 4 + 4:
        return omitted_model_material(tool_call_id, "representation_limit", source=source)
    try:
        body = base64.b64decode(body_base64.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error):
        return omitted_model_material(tool_call_id, "invalid_encoding", source=source)
    if len(body) != response["body_bytes"]:
        return omitted_model_material(tool_call_id, "source_digest_mismatch", source=source)
    if len(body) > max_decoded_body_bytes:
        return omitted_model_material(tool_call_id, "representation_limit", source=source)

    content_type = document["content_type"]
    if body and not content_type:
        return omitted_model_material(tool_call_id, "unsupported_media", source=source)
    if body and content_type and not _TEXT_MEDIA.match(content_type):
        return omitted_model_material(tool_call_id, "unsupported_media", source=source)
    try:
        # An empty body is still a useful observed 204/3xx/4xx result even when
        # its declared media type is binary; no bytes are decoded or faked.
        charset = _charset(content_type if body else "text/plain; charset=utf-8")
    except LookupError:
        return omitted_model_material(tool_call_id, "unsupported_charset", source=source)
    try:
        text = body.decode(charset)
    except (UnicodeDecodeError, LookupError):
        return omitted_model_material(tool_call_id, "invalid_encoding", source=source)
    text, body_redacted = _redact_body(text)

    lines = [
        f"schema_version: {HTTP_EXCHANGE_SCHEMA}",
        f"response.status: {document['status']}",
        "response.headers:",
    ]
    lines.extend(f"{key}: {value}" for key, value in document["headers"].items())
    lines.extend(("response.body:", text))
    rendered, truncated = _bounded_prefix("\n".join(lines), max_representation_bytes)
    encoded = rendered.encode("utf-8")
    representation = ModelMaterialRepresentation.model_validate(
        {
            "renderer_version": HTTP_RENDERER_VERSION,
            "media_type": REPRESENTATION_MEDIA_TYPE,
            "encoding": "utf-8",
            "text": rendered,
            "byte_length": len(encoded),
            "representation_sha256": sha256(encoded).hexdigest(),
            "truncated": truncated,
            "redaction_applied": document["redaction_applied"] or body_redacted,
        }
    )
    return ModelMaterialV2.model_validate(
        {
            "schema_version": MODEL_MATERIAL_SCHEMA,
            "tool_call_id": tool_call_id,
            "status": "delivered",
            "source": source,
            "representation": representation,
            "omission_reason": None,
        }
    )


def validate_model_material_v2(
    value: object,
    *,
    tool_call_id: str,
    result_ref: BlobRef | dict | None = None,
    artifact_record: Mapping[str, object] | None = None,
) -> ModelMaterialV2 | None:
    """Validate a worker-returned packet before it crosses a Session boundary."""

    try:
        packet = ModelMaterialV2.model_validate(value)
    except ValueError:
        return None
    if packet.tool_call_id != tool_call_id:
        return None
    if packet.status.value == "delivered":
        if packet.source is None or packet.representation is None or packet.omission_reason is not None:
            return None
        encoded = packet.representation.text.encode("utf-8")
        if (
            len(encoded) != packet.representation.byte_length
            or len(encoded) > DEFAULT_REPRESENTATION_BYTES
            or sha256(encoded).hexdigest() != packet.representation.representation_sha256
        ):
            return None
    else:
        if packet.representation is not None or packet.omission_reason is None:
            return None
    if result_ref is not None and packet.source is not None:
        try:
            expected = BlobRef.model_validate(result_ref)
        except ValueError:
            return None
        if packet.source.artifact_ref != expected or packet.source.artifact_sha256 != expected.sha256.root:
            return None
    if artifact_record is not None and packet.source is not None:
        if packet.source.artifact_sha256 != artifact_record.get("sha256"):
            return None
    return packet
