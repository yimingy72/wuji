"""What a replayed tool message may contain at a native session boundary.

A Run sees the canonical receipt, and — when the platform can hand it over — the
exact bytes of its own result artifact. The boundary accepts that delivery only
after checking the delivered text against the sealed artifact, so a replay can
never smuggle invented evidence into a session that later Runs will trust.
"""

from hashlib import sha256
import copy

from wuji_core.execution.sessions import SessionRepository


REF = {"id": "artifact-fixture", "version": "1", "sha256": "a" * 64}
RECEIPT = {
    "tool_call_id": "call-fixture",
    "operation_id": "call-fixture",
    "tool_attempt_id": "attempt-fixture",
    "status": "complete",
    "evidence_receipt": {
        "capture_id": "capture-fixture",
        "status": "accepted",
        "observation_ref": {
            "entity_type": "observation",
            "id": "observation-fixture",
            "revision": "1",
        },
        "artifact_refs": [REF],
        "code": None,
        "request_id": "fixture",
    },
    "result_ref": REF,
    "reason_code": None,
}
TEXT = "fixture-version=17\n"


class Store:
    def __init__(self, record):
        self.record_value = record

    def record(self, tx, ref):
        return self.record_value


def repository(**overrides):
    record = {
        "state": "sealed",
        "sha256": sha256(TEXT.encode()).hexdigest(),
        "size_bytes": len(TEXT.encode()),
    }
    record.update(overrides)
    return SessionRepository(None, artifacts=Store(record), registry=None)


def delivered(**extra):
    return {**RECEIPT, **extra}


def test_the_canonical_receipt_alone_still_verifies():
    assert repository().delivered_result(None, RECEIPT, RECEIPT) is True


def test_the_verified_bytes_of_the_result_artifact_are_accepted():
    assert repository().delivered_result(
        None,
        RECEIPT,
        delivered(material={"encoding": "utf-8", "byte_length": len(TEXT.encode()), "text": TEXT}),
    ) is True


def test_named_omission_is_accepted_but_an_unknown_reason_is_not():
    assert repository().delivered_result(
        None, RECEIPT, delivered(material_omitted="over_inline_limit")
    ) is True
    assert repository().delivered_result(
        None, RECEIPT, delivered(material_omitted="because_i_said_so")
    ) is False


def test_text_that_is_not_the_artifact_bytes_is_refused():
    assert repository().delivered_result(
        None,
        RECEIPT,
        delivered(material={"encoding": "utf-8", "byte_length": 4, "text": "fake"}),
    ) is False
    # Same length, different bytes: only the digest decides.
    assert repository().delivered_result(
        None,
        RECEIPT,
        delivered(material={"encoding": "utf-8", "byte_length": len(TEXT), "text": "fixture-version=18\n"}),
    ) is False


def test_an_unsealed_or_missing_artifact_cannot_deliver_a_body():
    assert repository(state="staged").delivered_result(
        None,
        RECEIPT,
        delivered(material={"encoding": "utf-8", "byte_length": len(TEXT), "text": TEXT}),
    ) is False


def test_any_other_added_field_is_refused():
    assert repository().delivered_result(None, RECEIPT, delivered(summary="trust me")) is False
    assert repository().delivered_result(
        None,
        RECEIPT,
        delivered(
            material={"encoding": "utf-8", "byte_length": len(TEXT), "text": TEXT},
            summary="trust me",
        ),
    ) is False


class V2Store(Store):
    def __init__(self, record, raw):
        super().__init__(record)
        self.raw = raw

    def checked_bytes(self, record):
        return self.raw


def test_v2_material_recovery_rejects_forged_text_even_with_a_recomputed_digest():
    import base64
    import json
    from wuji_core.admission.model_material import render_http_exchange_v2

    raw = json.dumps({
        "schema_version": "wuji.http-exchange.v1", "tool_attempt_id": "attempt-fixture",
        "target": "http://fixture.invalid",
        "request": {"method": "GET", "url": "http://fixture.invalid", "headers": {}},
        "response": {"status": 200, "headers": {"content-type": "text/plain; charset=utf-8"},
                     "body_base64": base64.b64encode("唯一正文标记".encode()).decode(),
                     "body_bytes": len("唯一正文标记".encode()), "truncated": False},
    }).encode()
    ref = {"id": "artifact-v2", "version": "1", "sha256": sha256(raw).hexdigest()}
    receipt = copy.deepcopy(RECEIPT)
    receipt["result_ref"] = ref
    receipt["evidence_receipt"]["artifact_refs"] = [ref]
    record = {"state": "sealed", "sha256": ref["sha256"], "size_bytes": len(raw),
              "media_type": "application/vnd.wuji.http-exchange+json", "completeness": "complete"}
    packet = render_http_exchange_v2(
        receipt["tool_call_id"], artifact_ref=ref, artifact_record=record, raw=raw,
    ).model_dump(mode="json")
    assert "唯一正文标记" in packet["representation"]["text"]
    repo = SessionRepository(None, artifacts=V2Store(record, raw), registry=None)
    assert repo.delivered_result(None, receipt, {**receipt, "material": packet}) is True

    tampered = copy.deepcopy(packet)
    forged = "forged evidence"
    tampered["representation"].update(
        text=forged, byte_length=len(forged.encode()),
        representation_sha256=sha256(forged.encode()).hexdigest(),
    )
    assert repo.delivered_result(None, receipt, {**receipt, "material": tampered}) is False

    omitted = {
        "schema_version": "wuji.model-material.v2", "tool_call_id": receipt["tool_call_id"],
        "status": "omitted", "source": None, "representation": None,
        "omission_reason": "source_unavailable",
    }
    assert repo.delivered_result(None, receipt, {**receipt, "material": omitted}) is True
