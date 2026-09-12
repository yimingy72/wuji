"""P03 wire changes: catch split observations and unbound accepted receipts."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from wuji_core.contracts.envelopes import EvidenceReceipt
from wuji_core.contracts.knowledge import ObservationRecord


def observation():
    return {
        "observation_id": "obs-1",
        "revision": "1",
        "task_id": "task-fixture",
        "capture_id": "capture-1",
        "tool_attempt_id": "attempt-1",
        "collector_ref": "collector-fixture",
        "capture_layer": "fixture_file_bytes",
        "observed_at": "2026-09-13T00:00:00Z",
        "received_at": "2026-09-13T00:00:01Z",
        "environment_ref": "fixture-env",
        "conditions": ["isolated fixture"],
        "completeness": "partial",
        "evidence_origin": "fixture_capture",
        "artifact_refs": [
            {"id": "body", "version": "1", "sha256": "a" * 64},
            {"id": "metadata", "version": "1", "sha256": "b" * 64},
        ],
    }


def test_one_observation_preserves_all_ordered_artifact_refs():
    record = ObservationRecord.model_validate(observation())
    assert record.observation_id == "obs-1"
    assert [ref.id for ref in record.artifact_refs] == ["body", "metadata"]
    assert record.revision.root == "1"


@pytest.mark.parametrize("refs", [[], observation()["artifact_refs"] * 129])
def test_observation_artifact_refs_are_nonempty_and_bounded(refs):
    with pytest.raises(ValidationError):
        ObservationRecord.model_validate({**observation(), "artifact_refs": refs})


@pytest.mark.parametrize(
    "status", ["accepted", "historical_only", "pending", "rejected"]
)
def test_evidence_receipt_binds_exactly_the_published_observation(status):
    ref = {"entity_type": "observation", "id": "obs-1", "revision": "1"}
    published = status in {"accepted", "historical_only"}
    body = {
        "capture_id": "capture-1",
        "status": status,
        "artifact_refs": [],
        "request_id": "request-1",
        "observation_ref": ref if published else None,
    }
    receipt = EvidenceReceipt.model_validate(body)
    if published:
        assert receipt.observation_ref.id == "obs-1"
        assert receipt.observation_ref.revision.root == "1"
    else:
        assert receipt.observation_ref is None
    with pytest.raises(ValidationError):
        EvidenceReceipt.model_validate(
            {**body, "observation_ref": None if published else ref}
        )
    if published:
        with pytest.raises(ValidationError):
            EvidenceReceipt.model_validate(
                {**body, "observation_ref": {**ref, "entity_type": "claim"}}
            )


def test_openapi_evidence_requires_one_idempotency_header():
    source = yaml.safe_load(
        (
            Path(__file__).resolve().parents[2] / "packages/contracts/openapi-v2.yaml"
        ).read_text()
    )
    params = source["paths"]["/internal/v2/evidence"]["post"].get("parameters", [])
    assert {"$ref": "#/components/parameters/IdempotencyKey"} in params
