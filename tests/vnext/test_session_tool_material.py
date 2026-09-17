"""What a replayed tool message may contain at a native session boundary.

A Run sees the canonical receipt, and — when the platform can hand it over — the
exact bytes of its own result artifact. The boundary accepts that delivery only
after checking the delivered text against the sealed artifact, so a replay can
never smuggle invented evidence into a session that later Runs will trust.
"""

from hashlib import sha256

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
