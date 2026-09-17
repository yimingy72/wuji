"""E03-B: authorized evidence bodies reach the model, or say why they did not.

The platform fetches a bounded text artifact only for a read set the snapshot
reader already authorized. A body is never truncated: it either arrives whole
inside the published context bytes, or the record keeps its exact reference and
a fixed omission reason.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json

from wuji_core.contracts.generated import (
    ArtifactRecord,
    ArtifactState,
    BlobRef,
    EvidenceOrigin,
    KnowledgeRef,
    NodeEntityType,
    ObservationRecord,
    RecordPayload,
    RecordView,
    CaptureCompleteness,
)
from wuji_core.execution.worker_bridge import inline_material
from wuji_maf_worker.context import (
    ContextLimits,
    InlineMaterial,
    build_context_bundle,
)


def _artifact_ref(identifier, revision="1"):
    return KnowledgeRef.model_validate(
        {"entity_type": NodeEntityType.artifact, "id": identifier, "revision": revision}
    )


def _artifact_view(ref, *, media_type="text/plain", state=ArtifactState.sealed, size=64):
    artifact = ArtifactRecord.model_validate(
        {
            "artifact_ref": {
                "id": ref.id,
                "version": ref.revision.root,
                "sha256": "a" * 64,
            },
            "state": state,
            "media_type": media_type,
            "size_bytes": str(size),
            "created_at": datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc),
        }
    )
    return RecordView(
        assessment=None,
        ref=ref,
        display_kind="artifact",
        record=RecordPayload(root=artifact),
    )


def _observation_view(ref, artifact_ref):
    observation = ObservationRecord.model_validate(
        {
            "observation_id": ref.id,
            "revision": ref.revision.root,
            "task_id": "task-evidence-1",
            "capture_id": "capture-evidence-1",
            "tool_attempt_id": "tool-attempt-evidence-1",
            "collector_ref": "collector-evidence-1",
            "artifact_refs": [artifact_ref.model_dump(mode="json")],
            "capture_layer": "http-response",
            "observed_at": datetime(2026, 9, 17, 8, 1, tzinfo=timezone.utc),
            "received_at": datetime(2026, 9, 17, 8, 2, tzinfo=timezone.utc),
            "environment_ref": "fixture-evidence-1",
            "conditions": [],
            "completeness": CaptureCompleteness.complete,
            "evidence_origin": EvidenceOrigin.fixture_capture,
        }
    )
    return RecordView(
        assessment=None,
        ref=ref,
        display_kind="observation",
        record=RecordPayload(root=observation),
    )


class _Store:
    def __init__(self, bodies=None):
        self.bodies = bodies or {}
        self.reads = []

    def checked_bytes(self, row):
        key = (row["media_type"], row["size_bytes"])
        self.reads.append(key)
        return self.bodies[key]


def test_inline_material_delivers_sealed_text_and_names_every_omission():
    store = _Store({("text/plain", 5): b"hello"})
    rows = {
        ("artifact", "delivered", "1"): {
            "state": "sealed", "media_type": "text/plain", "size_bytes": 5,
        },
        ("artifact", "binary", "1"): {
            "state": "sealed", "media_type": "application/octet-stream", "size_bytes": 5,
        },
        ("artifact", "staged", "1"): {
            "state": "staged", "media_type": "text/plain", "size_bytes": 5,
        },
        ("artifact", "huge", "1"): {
            "state": "sealed", "media_type": "text/plain", "size_bytes": 9000,
        },
    }
    material = inline_material(
        artifacts=store,
        artifact_rows=rows,
        references={key for key in rows},
        context_bytes=1024,
        max_single_output_bytes=512,
    )
    assert material.bodies[("artifact", "delivered", "1")] == {
        "encoding": "utf-8",
        "byte_length": 5,
        "text": "hello",
    }
    assert material.get(("artifact", "binary", "1")) is None
    assert material.omitted(("artifact", "binary", "1")) == "not_text_media"
    assert material.omitted(("artifact", "staged", "1")) == "not_sealed"
    assert material.omitted(("artifact", "huge", "1")) == "over_inline_limit"
    # The single body was read once; no other byte was touched.
    assert store.reads == [("text/plain", 5)]


def test_inline_material_stops_at_the_published_budget_without_truncating():
    first, second, third = b"a" * 20, b"b" * 20, b"c" * 20
    store = _Store(
        {
            ("text/plain", 20): first,
            ("text/plain", 21): second,
            ("text/plain", 22): third,
        }
    )
    rows = {
        ("artifact", "a", "1"): {
            "state": "sealed", "media_type": "text/plain", "size_bytes": 20,
        },
        ("artifact", "b", "1"): {
            "state": "sealed", "media_type": "text/plain", "size_bytes": 21,
        },
        ("artifact", "c", "1"): {
            "state": "sealed", "media_type": "text/plain", "size_bytes": 22,
        },
    }
    # 100 context bytes publish a 25-byte per-body bound and a 50-byte total
    # bound: two whole bodies fit, the third is named instead of truncated.
    material = inline_material(
        artifacts=store,
        artifact_rows=rows,
        references={key for key in rows},
        context_bytes=100,
        max_single_output_bytes=25,
    )
    assert material.bodies[("artifact", "a", "1")]["text"] == first.decode()
    assert material.bodies[("artifact", "b", "1")]["text"] == second.decode()
    assert material.omitted(("artifact", "c", "1")) == "context_byte_limit"
    assert ("text/plain", 22) not in store.reads


def test_inline_material_is_absent_without_an_artifact_reader():
    rows = {
        ("artifact", "a", "1"): {
            "state": "sealed", "media_type": "text/plain", "size_bytes": 6,
        }
    }
    assert (
        inline_material(
            artifacts=None,
            artifact_rows=rows,
            references={key for key in rows},
            context_bytes=1024,
            max_single_output_bytes=64,
        )
        is None
    )


def test_context_bundle_renders_the_delivered_body_with_its_reference():
    ref = _artifact_ref("artifact-delivered")
    observation_ref = KnowledgeRef.model_validate(
        {"entity_type": NodeEntityType.observation, "id": "obs-1", "revision": "1"}
    )
    blob = BlobRef.model_validate(
        {"id": ref.id, "version": ref.revision.root, "sha256": "a" * 64}
    )
    material = InlineMaterial(
        bodies={
            (ref.entity_type.value, ref.id, ref.revision.root): {
                "encoding": "utf-8",
                "byte_length": 5,
                "text": "hello",
            }
        }
    )
    bundle = build_context_bundle(
        [_observation_view(observation_ref, blob), _artifact_view(ref)],
        [observation_ref, ref],
        snapshot_id="snapshot-evidence-1",
        limits=ContextLimits(max_records=8, max_bytes=50_000),
        material=material,
    )
    payload = json.loads(bundle.text)
    records = {item["ref"]["id"]: item for item in payload["records"]}
    assert records[ref.id]["material"] == {
        "encoding": "utf-8",
        "byte_length": 5,
        "text": "hello",
    }
    assert records[ref.id]["record"]["state"] == "sealed"
    assert records[observation_ref.id]["record"]["artifact_refs"][0]["id"] == ref.id


def test_context_bundle_names_a_body_that_does_not_fit_the_context():
    ref = _artifact_ref("artifact-too-big-for-context")
    material = InlineMaterial(
        bodies={
            (ref.entity_type.value, ref.id, ref.revision.root): {
                "encoding": "utf-8",
                "byte_length": 4,
                "text": "body",
            }
        }
    )
    base = len(bundle_metadata(ref).encode())
    body_entry = ',"material":{"encoding":"utf-8","byte_length":4,"text":"body"}'
    # One byte short of carrying the body, but with room for the named omission.
    limits = ContextLimits(max_records=1, max_bytes=base - 2 + len(body_entry) - 1)
    bundle = build_context_bundle(
        [_artifact_view(ref)],
        [ref],
        snapshot_id="snapshot-evidence-2",
        limits=limits,
        material=material,
    )
    record = json.loads(bundle.text)["records"][0]
    assert "material" not in record
    assert record["material_omitted"] == "context_byte_limit"
    assert record["ref"]["id"] == ref.id


def bundle_metadata(ref):
    return build_context_bundle(
        [_artifact_view(ref)], [ref], snapshot_id="s", limits=ContextLimits(1, 50_000)
    ).text


def test_context_without_inline_material_is_unchanged():
    ref = _artifact_ref("artifact-metadata-only")
    bundle = build_context_bundle(
        [_artifact_view(ref)],
        [ref],
        snapshot_id="snapshot-evidence-3",
        limits=ContextLimits(max_records=1, max_bytes=50_000),
    )
    record = json.loads(bundle.text)["records"][0]
    assert "material" not in record and "material_omitted" not in record
