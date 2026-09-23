"""Pure C05 renderer checks; no target or artifact-store I/O is performed."""

from base64 import b64encode
import asyncio
from hashlib import sha256
import json
from types import SimpleNamespace

from wuji_core.admission.model_material import (
    HTTP_EXCHANGE_MEDIA_TYPE,
    render_http_exchange_v2,
    render_runtime_http_part_v1,
    validate_model_material_v2,
)
from wuji_core.contracts.admission import ToolCallReceipt
from wuji_core.contracts.envelopes import BlobRef
from wuji_core.execution.worker_bridge import inline_material
from wuji_maf_worker.tools import GateFunctions


CALL_ID = "call-material-fixture"


def exchange(body: bytes, *, content_type="text/plain; charset=utf-8", status=200, truncated=False):
    return json.dumps(
        {
            "schema_version": "wuji.http-exchange.v1",
            "tool_attempt_id": "attempt-material-fixture",
            "target": "http://fixture.invalid",
            "request": {"method": "GET", "url": "http://fixture.invalid/page", "headers": {}},
            "response": {
                "status": status,
                "headers": {
                    "content-type": content_type,
                    "x-secret": "must-not-be-rendered",
                },
                "body_base64": b64encode(body).decode("ascii"),
                "body_bytes": len(body),
                "truncated": truncated,
            },
        },
        separators=(",", ":"),
    ).encode()


def artifact(raw, *, completeness="complete", media_type=HTTP_EXCHANGE_MEDIA_TYPE):
    digest = sha256(raw).hexdigest()
    return (
        BlobRef.model_validate({"id": "artifact-material-fixture", "version": "1", "sha256": digest}),
        {
            "state": "sealed",
            "sha256": digest,
            "size_bytes": len(raw),
            "media_type": media_type,
            "completeness": completeness,
        },
    )


def test_http_renderer_accepts_text_subtypes_and_partial_captured_utf8():
    raw = exchange(("唯一正文标记\n" + "中文" * 40_000).encode())
    ref, record = artifact(raw, completeness="partial")

    packet = render_http_exchange_v2(
        CALL_ID,
        artifact_ref=ref,
        artifact_record=record,
        raw=raw,
    )

    assert packet.status.value == "delivered"
    assert packet.source.completeness.value == "partial"
    assert packet.representation.truncated is True
    encoded = packet.representation.text.encode("utf-8")
    assert len(encoded) == packet.representation.byte_length <= 32 * 1024
    assert sha256(encoded).hexdigest() == packet.representation.representation_sha256
    assert "唯一正文标记" in packet.representation.text
    assert "must-not-be-rendered" not in packet.representation.text
    assert validate_model_material_v2(
        packet.model_dump(mode="json"), tool_call_id=CALL_ID, result_ref=ref
    ) is not None


def test_http_renderer_accepts_json_and_html_but_not_binary():
    for content_type in ("application/json", "text/html; charset=utf-8"):
        raw = exchange(b'{"marker":"present"}', content_type=content_type)
        ref, record = artifact(raw)
        packet = render_http_exchange_v2(
            CALL_ID, artifact_ref=ref, artifact_record=record, raw=raw
        )
        assert packet.status.value == "delivered"
        assert packet.representation.truncated is False

    raw = exchange(b"\\x00\\xff", content_type="application/octet-stream")
    ref, record = artifact(raw)
    packet = render_http_exchange_v2(
        CALL_ID, artifact_ref=ref, artifact_record=record, raw=raw
    )
    assert packet.status.value == "omitted"
    assert packet.omission_reason.value == "unsupported_media"
    assert packet.source is not None
    assert packet.representation is None

    raw = exchange(b"", content_type="application/octet-stream", status=204)
    ref, record = artifact(raw)
    packet = render_http_exchange_v2(
        CALL_ID, artifact_ref=ref, artifact_record=record, raw=raw
    )
    assert packet.status.value == "delivered"
    assert "response.status: 204" in packet.representation.text


def test_http_renderer_never_invents_status_or_follows_a_redirect():
    raw = exchange(b"", status=0)
    ref, record = artifact(raw)
    packet = render_http_exchange_v2(
        CALL_ID, artifact_ref=ref, artifact_record=record, raw=raw
    )
    assert packet.status.value == "omitted"
    assert packet.omission_reason.value == "unsupported_schema"

    raw = exchange(b"", status=302)
    ref, record = artifact(raw)
    packet = render_http_exchange_v2(
        CALL_ID, artifact_ref=ref, artifact_record=record, raw=raw
    )
    assert packet.status.value == "delivered"
    assert "response.status: 302" in packet.representation.text


def test_http_renderer_rejects_source_digest_and_charset_mismatch():
    raw = exchange("内容".encode(), content_type="text/plain; charset=not-a-real-codec")
    ref, record = artifact(raw)
    packet = render_http_exchange_v2(
        CALL_ID, artifact_ref=ref, artifact_record=record, raw=raw
    )
    assert packet.omission_reason.value == "unsupported_charset"

    bad_record = dict(record, sha256="0" * 64)
    packet = render_http_exchange_v2(
        CALL_ID, artifact_ref=ref, artifact_record=bad_record, raw=raw
    )
    assert packet.omission_reason.value == "source_digest_mismatch"

    unavailable = render_http_exchange_v2(
        CALL_ID, artifact_ref=ref, artifact_record=record, raw=None
    )
    assert unavailable.status.value == "omitted"
    assert unavailable.omission_reason.value == "source_unavailable"
    assert unavailable.source is None


def test_worker_v2_material_read_is_explicit_and_keeps_the_full_packet():
    raw = exchange(b"worker-material-marker")
    ref, record = artifact(raw)
    receipt = ToolCallReceipt.model_validate(
        {
            "tool_call_id": CALL_ID,
            "operation_id": CALL_ID,
            "tool_attempt_id": "attempt-material-fixture",
            "status": "complete",
            "evidence_receipt": {
                "observation_ref": {
                    "entity_type": "observation",
                    "id": "observation-material-fixture",
                    "revision": "1",
                },
                "capture_id": "capture-material-fixture",
                "status": "accepted",
                "artifact_refs": [ref.model_dump(mode="json")],
                "request_id": "request-material-fixture",
                "code": None,
            },
            "result_ref": ref.model_dump(mode="json"),
            "reason_code": None,
        }
    )
    packet = render_http_exchange_v2(
        CALL_ID, artifact_ref=ref, artifact_record=record, raw=raw
    ).model_dump(mode="json")

    class Client:
        def __init__(self):
            self.calls = []

        async def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return SimpleNamespace(status_code=200, content=json.dumps(packet).encode())

    client = Client()
    functions = GateFunctions(
        definitions=[], identity=None, lineage="lineage-material-fixture",
        client=client, url="https://tool-gate.invalid/internal/v2/tool-calls",
        material_representation="wuji.model-material.v2",
    )
    delivered = json.loads(asyncio.run(functions._delivered_content(receipt)))
    assert client.calls[0][1]["params"] == {"representation": "wuji.model-material.v2"}
    assert delivered["material"]["schema_version"] == "wuji.model-material.v2"
    assert delivered["material"]["representation"]["text"].find("worker-material-marker") >= 0


def test_reason_context_reuses_the_exact_http_artifact_reference():
    raw = exchange("reason-read-set-marker".encode())
    ref, record = artifact(raw, completeness="partial")
    key = ("artifact", ref.id, ref.version.root)

    class Store:
        def __init__(self):
            self.reads = 0

        def checked_bytes(self, value):
            self.reads += 1
            return raw

    store = Store()
    material = inline_material(
        artifacts=store,
        artifact_rows={key: {**record, "tool_call_id": CALL_ID}},
        references={key},
        context_bytes=64 * 1024,
        max_single_output_bytes=64 * 1024,
        material_representation="wuji.model-material.v2",
    )
    assert store.reads == 1
    packet = material.bodies[key]
    assert packet["source"]["artifact_ref"]["id"] == ref.id
    assert packet["source"]["completeness"] == "partial"
    assert "reason-read-set-marker" in packet["representation"]["text"]

    legacy = inline_material(
        artifacts=store, artifact_rows={key: {**record, "tool_call_id": CALL_ID}},
        references={key}, context_bytes=64 * 1024, max_single_output_bytes=64 * 1024,
    )
    assert store.reads == 1
    assert key not in legacy.bodies
    assert legacy.reasons[key] == "not_text_media"


def test_published_material_version_roundtrips_without_changing_legacy_profile_bytes():
    from dataclasses import replace
    from wuji_core.contracts.sessions import SessionLimits
    from wuji_maf_worker.factory import HarnessProfile, SessionHarnessProfile, parse_profile

    common = dict(
        ref="harness.fixture", revision="1", work_kind="explore", instructions="Read evidence.",
        tool_definition_refs=("fixture-reader",), lock_digest="a" * 64,
        max_context_records=32, max_context_bytes=65_536, max_output_tokens=512,
    )
    profiles = [
        HarnessProfile(**common),
        SessionHarnessProfile(**common, history_source_id="history", memory_source_id="memory",
            memory_mode="disabled", session_limits=SessionLimits(
                max_objects=32, max_reference_depth=8, max_object_bytes=65_536,
                max_total_bytes=262_144, max_messages=128, max_pending_approvals=4,
            ), max_context_window_tokens=8192, compaction_enabled=False),
    ]
    for profile in profiles:
        old = profile.snapshot()
        assert "material_representation" not in old["body"]
        assert parse_profile(old).snapshot() == old
        current = replace(profile, material_representation="wuji.model-material.v2")
        assert parse_profile(current.snapshot()) == current
        assert current.snapshot()["digest"] != old["digest"]


def test_redirect_credentials_and_body_secrets_are_redacted_without_changing_source():
    document = json.loads(exchange(b'password=fixture-secret api_key=fixture-api-key'))
    document["response"]["headers"]["location"] = "https://fixture-user:fixture-password@example.invalid/path?token=fixture"
    raw = json.dumps(document).encode()
    ref, record = artifact(raw)
    packet = render_http_exchange_v2(CALL_ID, artifact_ref=ref, artifact_record=record, raw=raw)
    assert packet.representation.redaction_applied
    assert "https://example.invalid/path" in packet.representation.text
    assert all(secret not in packet.representation.text for secret in (
        "fixture-user", "fixture-password", "fixture-secret", "fixture-api-key", "token=fixture",
    ))
    assert packet.source.artifact_sha256 == sha256(raw).hexdigest()


def test_runtime_capture_body_uses_sealed_metadata_and_redacts_credentials():
    raw = b'password=fixture-secret&message=visible'
    metadata = json.dumps(
        {
            "schema_version": "wuji.http-capture-record.v1",
            "exchange_id": "exchange-fixture",
            "stage": "response",
            "metadata": {
                "status_code": 200,
                "headers": [
                    ["Content-Type", "application/x-www-form-urlencoded"],
                    ["Set-Cookie", "session=must-not-render"],
                ],
            },
            "body_length": len(raw),
            "body_sha256": sha256(raw).hexdigest(),
            "record_digest": "0" * 64,
            "persisted_at": "2026-09-23T00:00:00Z",
        },
        separators=(",", ":"),
    ).encode()
    ref, record = artifact(raw, media_type="application/octet-stream")

    packet = render_runtime_http_part_v1(
        "capture:session:1:response_body",
        part="response_body",
        artifact_ref=ref,
        artifact_record=record,
        raw=raw,
        metadata_raw=metadata,
    )

    assert packet.status.value == "delivered"
    assert packet.representation.redaction_applied is True
    assert "message=visible" in packet.representation.text
    assert "fixture-secret" not in packet.representation.text
    assert "must-not-render" not in packet.representation.text
    assert packet.source.artifact_sha256 == sha256(raw).hexdigest()


def test_capture_truncation_conflict_and_duplicate_container_fields_are_not_delivered():
    raw = exchange(b"partial text", truncated=True)
    ref, record = artifact(raw, completeness="complete")
    packet = render_http_exchange_v2(CALL_ID, artifact_ref=ref, artifact_record=record, raw=raw)
    assert packet.status.value == "omitted"
    assert packet.omission_reason.value == "capture_truncated"
    raw = raw.replace(b'"status":200', b'"status":404,"status":200')
    ref, record = artifact(raw, completeness="partial")
    packet = render_http_exchange_v2(CALL_ID, artifact_ref=ref, artifact_record=record, raw=raw)
    assert packet.status.value == "omitted"
