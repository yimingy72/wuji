"""Bounded, versioned data for an agent; no framework or access-control bypass.

The caller loads records through the authorized snapshot reader. This pure
builder preserves the data it receives and refuses to silently trim evidence.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib

from wuji_core.contracts.knowledge import (
    ArtifactRecord,
    ClaimRecord,
    IntentRecord,
    KnowledgeRef,
    ObservationRecord,
)
from wuji_core.contracts.views import RecordView
from wuji_core.http.json_boundary import canonical_json_bytes
from wuji_core.admission.model_material import validate_model_material_v2


class ContextLimitExceeded(ValueError):
    """The full context cannot be delivered under the published input budget."""


@dataclass(frozen=True)
class ContextLimits:
    max_records: int
    max_bytes: int

    def __post_init__(self) -> None:
        for value in (self.max_records, self.max_bytes):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("context limits must be positive integers")


OMISSION_REASONS = frozenset(
    {
        "not_delivered",
        "not_sealed",
        "not_text_media",
        "over_inline_limit",
        "unreadable",
        "not_utf8",
        "context_byte_limit",
        "source_unavailable",
        "source_not_sealed",
        "source_digest_mismatch",
        "unsupported_media",
        "unsupported_schema",
        "unsupported_charset",
        "invalid_encoding",
        "capture_truncated",
        "representation_limit",
        "delivery_error",
    }
)


@dataclass(frozen=True)
class InlineMaterial:
    """Already authorized, already bounded text bodies for a read set.

    The platform fetches the bytes; this object only carries them, together
    with a stable reason for every artifact whose body is *not* in the context.
    A body is never truncated: an artifact either arrives whole or is named as
    omitted.
    """

    bodies: Mapping[tuple[str, str, str], dict]
    reasons: Mapping[tuple[str, str, str], str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.bodies, Mapping) or not isinstance(self.reasons, Mapping):
            raise TypeError("inline material requires bounded mappings")
        for key in self.bodies:
            if (
                not isinstance(key, tuple)
                or len(key) != 3
                or any(not isinstance(part, str) or not part for part in key)
            ):
                raise ValueError("an inline material key is an exact reference")
        for key, reason in self.reasons.items():
            if key not in set(self.bodies) and not isinstance(key, tuple):
                raise ValueError("an omission names an exact reference")
            if reason not in OMISSION_REASONS:
                raise ValueError("an omission reason is from the fixed set")
        for value in self.bodies.values():
            if isinstance(value, dict) and value.get("schema_version") == "wuji.model-material.v2":
                packet = validate_model_material_v2(
                    value, tool_call_id=value.get("tool_call_id", "")
                )
                if packet is None or packet.status.value != "delivered":
                    raise ValueError("inline v2 material must be a delivered packet")
        if set(self.reasons) & set(self.bodies):
            raise ValueError("one artifact is either delivered or omitted")

    def get(self, key):
        return self.bodies.get(key)

    def omitted(self, key):
        return self.reasons.get(key, "not_delivered")


@dataclass(frozen=True)
class ContextRelation:
    source: KnowledgeRef
    target: KnowledgeRef
    relation: str

    def __post_init__(self) -> None:
        _key(self.source)
        _key(self.target)
        if not isinstance(self.relation, str) or not 1 <= len(self.relation) <= 128:
            raise ValueError("a bounded relation label is required")


@dataclass(frozen=True)
class ContextBundle:
    snapshot_id: str
    read_set: tuple[KnowledgeRef, ...]
    record_refs: tuple[KnowledgeRef, ...]
    text: str
    input_digest: str


def _key(ref: KnowledgeRef) -> tuple[str, str, str]:
    if not isinstance(ref, KnowledgeRef):
        raise TypeError("a KnowledgeRef is required")
    return ref.entity_type.value, ref.id, ref.revision.root


def _material_entry(value):
    """One bounded inline text body, exactly as the caller measured it."""

    if not isinstance(value, dict):
        raise ValueError("inline material must be a bounded text document")
    if value.get("schema_version") == "wuji.model-material.v2":
        packet = validate_model_material_v2(
            value, tool_call_id=value.get("tool_call_id", "")
        )
        if packet is None or packet.status.value != "delivered":
            raise ValueError("inline v2 material failed its digest/shape checks")
        return packet.model_dump(mode="json")
    encoding = value.get("encoding")
    text = value.get("text")
    length = value.get("byte_length")
    if (
        encoding != "utf-8"
        or not isinstance(text, str)
        or type(length) is not int
        or length < 0
        or len(text.encode("utf-8")) != length
    ):
        raise ValueError("inline material must be exact UTF-8 text")
    return {"encoding": "utf-8", "byte_length": length, "text": text}


def _normalize_record(record: RecordView, read_keys: set[tuple[str, str, str]], material=None):
    if not isinstance(record, RecordView):
        raise TypeError("an authorized RecordView is required")
    reference, payload = record.ref, record.record.root
    key = _key(reference)
    if key not in read_keys:
        raise ValueError("a rendered record is missing from the read set")

    related = []
    if isinstance(payload, ClaimRecord):
        expected = ("claim", payload.claim_id, payload.revision.root)
        related.extend(payload.basis_refs)
        if payload.supersedes is not None:
            related.append(payload.supersedes)
    elif isinstance(payload, IntentRecord):
        expected = ("intent", payload.intent_id, payload.revision.root)
        related.extend(payload.basis_refs)
    elif isinstance(payload, ObservationRecord):
        expected = ("observation", payload.observation_id, payload.revision.root)
        related.extend(
            KnowledgeRef.model_validate(
                {
                    "entity_type": "artifact",
                    "id": blob.id,
                    "revision": blob.version.root,
                }
            )
            for blob in payload.artifact_refs
        )
    elif isinstance(payload, ArtifactRecord):
        expected = (
            "artifact",
            payload.artifact_ref.id,
            payload.artifact_ref.version.root,
        )
    else:
        raise ValueError("this context reader does not support the record type")
    if key != expected:
        raise ValueError("record payload does not match its exact reference")
    if any(_key(ref) not in read_keys for ref in related):
        raise ValueError("a referenced input is missing from the read set")
    if record.assessment is not None and not isinstance(payload, ClaimRecord):
        raise ValueError("only a claim may carry a Claim assessment")

    # mode=python preserves Decimal in arbitrary structured assertions. Convert
    # only the known timestamp fields; opaque data is never reinterpreted.
    result = record.model_dump(mode="python")
    body = result["record"]
    for field in ("created_at", "observed_at", "received_at"):
        if field in body:
            timestamp = body[field]
            if (
                not isinstance(timestamp, datetime)
                or timestamp.tzinfo is None
                or timestamp.utcoffset() is None
            ):
                raise ValueError("record timestamp must include its time zone")
            body[field] = (
                timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            )
    result["display_kind"] = key[0]
    if isinstance(payload, ClaimRecord) and record.assessment is not None:
        result["display_kind"] = "fact" if record.assessment.eligible else "claim"
    if isinstance(payload, ArtifactRecord) and material is not None:
        # Only when the caller asked for inline bodies does the record say what
        # is and is not in this context. An artifact whose body is absent is
        # never silently indistinguishable from one that was delivered.
        entry = material.get(key)
        if entry is None:
            result["material_omitted"] = material.omitted(key)
        else:
            result["material"] = _material_entry(entry)
    return result, getattr(payload, "task_id", None)


def build_context_bundle(
    records: Sequence[RecordView],
    read_set: Sequence[KnowledgeRef],
    *,
    snapshot_id: str,
    limits: ContextLimits,
    relations: Sequence[ContextRelation] = (),
    material=None,
    states=None,
) -> ContextBundle:
    if not isinstance(limits, ContextLimits):
        raise TypeError("published ContextLimits are required")
    if not isinstance(snapshot_id, str) or not 1 <= len(snapshot_id) <= 256:
        raise ValueError("a bounded snapshot identity is required")
    if len(records) > limits.max_records:
        raise ContextLimitExceeded("context record count exceeds its configured limit")

    exact_refs = []
    read_keys = set()
    for reference in read_set:
        key = _key(reference)
        if key not in read_keys:
            exact_refs.append(reference.model_copy(deep=True))
            read_keys.add(key)

    relation_data = []
    for relation in relations:
        if not isinstance(relation, ContextRelation):
            raise TypeError("an authorized ContextRelation is required")
        if (
            _key(relation.source) not in read_keys
            or _key(relation.target) not in read_keys
        ):
            raise ValueError("a relation endpoint is missing from the read set")
        relation_data.append(
            {
                "source": relation.source.model_dump(mode="python"),
                "target": relation.target.model_dump(mode="python"),
                "relation": relation.relation,
            }
        )

    content = {
        "schema_version": "wuji.context.v2",
        "snapshot_id": snapshot_id,
        "read_set": [ref.model_dump(mode="python") for ref in exact_refs],
        "records": [],
        "relations": relation_data,
    }
    if states is not None:
        # The frozen Task/Work/Run/assessment state is part of the input the model
        # must be able to read: "what was already tried", "which claim is already
        # a fact", and whether an earlier completion review is still open. It is
        # the same bounded, checksummed document that the snapshot froze.
        if not isinstance(states, dict):
            raise ValueError("context states must be the frozen snapshot mapping")
        content["states"] = states
    # Account for the entire envelope as well as individual UTF-8 records. A
    # limit error never returns a smaller, selectively supportive bundle.
    size = len(canonical_json_bytes(content))
    if size > limits.max_bytes:
        raise ContextLimitExceeded("context metadata exceeds its configured byte limit")
    originals = {}
    record_refs = []
    task_ids = set()
    for record in records:
        normalized, task_id = _normalize_record(record, read_keys, material)
        if task_id is not None:
            task_ids.add(task_id)
            if len(task_ids) > 1:
                raise ValueError(
                    "a context cannot combine records from different tasks"
                )
        encoded = canonical_json_bytes(normalized)
        if (
            "material" in normalized
            and size + len(encoded) + (1 if record_refs else 0) > limits.max_bytes
        ):
            # The body does not fit this context. It is dropped by name, with
            # the exact reference kept: the model must see that the material
            # exists and was not delivered here, never a quietly smaller bundle.
            normalized["material_omitted"] = "context_byte_limit"
            normalized.pop("material")
            encoded = canonical_json_bytes(normalized)
        key = _key(record.ref)
        if key in originals:
            if originals[key] != encoded:
                raise ValueError("conflicting records for one exact reference")
            continue
        size += len(encoded) + (1 if record_refs else 0)
        if size > limits.max_bytes:
            raise ContextLimitExceeded("full context exceeds its configured byte limit")
        content["records"].append(normalized)
        originals[key] = encoded
        record_refs.append(record.ref.model_copy(deep=True))

    encoded = canonical_json_bytes(content)
    if len(encoded) > limits.max_bytes:
        raise ContextLimitExceeded("full context exceeds its configured byte limit")
    return ContextBundle(
        snapshot_id=snapshot_id,
        read_set=tuple(exact_refs),
        record_refs=tuple(record_refs),
        text=encoded.decode("utf-8"),
        input_digest=hashlib.sha256(encoded).hexdigest(),
    )
