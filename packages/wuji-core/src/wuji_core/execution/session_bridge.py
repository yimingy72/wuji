"""Authenticated P08 Session transport over generated outer wire contracts."""

import base64
from datetime import datetime, timezone
from hashlib import sha256

from pydantic import ValidationError

from wuji_core.contracts import generated as wire
from wuji_core.contracts.sessions import (
    BoundaryObjects,
    DeliveryReceipt,
    HumanInput,
    InputReceipt,
    NativeApprovalObservation,
    PublishedSession,
    SessionCompatibility,
    SessionLimits,
    SessionReceipt,
    StagedSessionObjects,
)
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError


BOUNDARY_VERSION = "wuji.worker.session.boundary.v1"
STAGED_VERSION = "wuji.worker.session.staged.v1"
RECEIPT_VERSION = "wuji.worker.session.receipt.v1"
PUBLISHED_VERSION = "wuji.worker.session.published.v1"
OBSERVATION_VERSION = "wuji.worker.session.approval-observation.v1"
INPUT_RECEIPT_VERSION = "wuji.worker.session.input-receipt.v1"
HUMAN_INPUT_VERSION = "wuji.worker.session.human-input.v1"
DELIVERY_RECEIPT_VERSION = "wuji.worker.session.delivery-receipt.v1"
COMPATIBILITY_VERSION = "wuji.worker.session.compatibility.v1"


def _ref_key(ref):
    return ref.id + "@" + ref.version.root


def _outer_document(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="python")
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _outer_document(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_outer_document(item) for item in value]
    return value


def transport_document(value):
    """Render generated outer fields while preserving Decimal payload values."""
    return _outer_document(value)


class SessionTransportCodec:
    """Canonical JSON plus explicit bytes for the three declared Session slots."""

    def __init__(self, *, max_transport_bytes: int):
        if (
            type(max_transport_bytes) is not int
            or not 1 <= max_transport_bytes <= 67_108_864
        ):
            raise ValueError("bounded Session transport required")
        self.maximum = max_transport_bytes

    def _binary(self, slot: str, key: str, data: bytes):
        if not isinstance(data, bytes) or len(data) > self.maximum:
            raise DomainError("LIMIT_BLOCKED", 422)
        return wire.WorkerSessionBinary.model_validate(
            {
                "slot": slot,
                "key": key,
                "data_base64": base64.b64encode(data).decode("ascii"),
                "data_sha256": sha256(data).hexdigest(),
                "size_bytes": len(data),
            }
        )

    def _decode_binaries(self, values, *, expected_slot):
        decoded = {}
        total = 0
        for item in values:
            if isinstance(item, wire.WorkerSessionBinary):
                item = item.model_dump(mode="python")
            item = wire.WorkerSessionBinary.model_validate(item)
            if item.slot.value != expected_slot or item.key in decoded:
                raise DomainError("INVALID_SCHEMA", 422)
            if len(item.data_base64) > 4 * ((self.maximum + 2) // 3):
                raise DomainError("LIMIT_BLOCKED", 422)
            try:
                data = base64.b64decode(item.data_base64, validate=True)
            except (ValueError, TypeError):
                raise DomainError("INVALID_SCHEMA", 422) from None
            if (
                len(data) != item.size_bytes
                or sha256(data).hexdigest() != item.data_sha256.root
            ):
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            total += len(data)
            if total > self.maximum:
                raise DomainError("LIMIT_BLOCKED", 422)
            decoded[item.key] = data
        return decoded

    def _payload(self, version: str, payload: dict, binaries=()):
        body = canonical_json_bytes(payload)
        if len(body) > self.maximum:
            raise DomainError("LIMIT_BLOCKED", 422)
        value = wire.WorkerSessionPayload.model_validate(
            {
                "schema_version": version,
                "payload": payload,
                "payload_sha256": sha256(body).hexdigest(),
                "payload_size_bytes": len(body),
                "binaries": list(binaries),
            }
        )
        if len(canonical_json_bytes(value.model_dump(mode="python"))) > self.maximum:
            raise DomainError("LIMIT_BLOCKED", 422)
        return value

    def _decode(self, value, *, expected_version: str):
        if isinstance(value, wire.WorkerSessionPayload):
            value = value.model_dump(mode="python")
        value = wire.WorkerSessionPayload.model_validate(value)
        if value.schema_version.value != expected_version:
            raise DomainError("INVALID_SCHEMA", 422)
        payload_bytes = canonical_json_bytes(value.payload)
        if (
            len(payload_bytes) != value.payload_size_bytes
            or sha256(payload_bytes).hexdigest() != value.payload_sha256.root
            or len(canonical_json_bytes(value.model_dump(mode="python"))) > self.maximum
        ):
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        decoded = self._decode_binaries_by_slot(value.binaries)
        if len(payload_bytes) + sum(len(item[2]) for item in decoded) > self.maximum:
            raise DomainError("LIMIT_BLOCKED", 422)
        return strict_json_loads(payload_bytes), decoded

    def _decode_binaries_by_slot(self, values):
        decoded = []
        seen = set()
        for item in values:
            if isinstance(item, wire.WorkerSessionBinary):
                item = item.model_dump(mode="python")
            item = wire.WorkerSessionBinary.model_validate(item)
            identity = (item.slot.value, item.key)
            if identity in seen:
                raise DomainError("INVALID_SCHEMA", 422)
            seen.add(identity)
            binary = self._decode_binaries([item], expected_slot=item.slot.value)
            decoded.append((item.slot.value, item.key, binary[item.key]))
        return tuple(decoded)

    def _encode_model(self, value, *, model, version, mode="python", datetime_fields=()):
        value = model.model_validate(value)
        payload = value.model_dump(mode=mode)
        for name in datetime_fields:
            observed = getattr(value, name)
            payload[name] = (
                None
                if observed is None
                else observed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            )
        return self._payload(version, payload)

    def _decode_model(self, value, *, model, version):
        payload, binaries = self._decode(value, expected_version=version)
        if binaries:
            raise DomainError("INVALID_SCHEMA", 422)
        return model.model_validate(payload)

    def encode_boundary(self, objects):
        objects = BoundaryObjects.model_validate(objects)
        payload = {
            "history": objects.history.model_dump(mode="python"),
            "provider_state": objects.provider_state.model_dump(mode="python"),
            "memory": objects.memory.model_dump(mode="python"),
            "objects": [],
        }
        binaries = []
        seen = set()
        for item in objects.objects:
            if item.key in seen:
                raise DomainError("INVALID_SCHEMA", 422)
            seen.add(item.key)
            payload["objects"].append(item.model_dump(mode="python", exclude={"data"}))
            binaries.append(self._binary("boundary_object_data", item.key, item.data))
        return self._payload(BOUNDARY_VERSION, payload, binaries)

    def decode_boundary(self, value):
        payload, decoded = self._decode(value, expected_version=BOUNDARY_VERSION)
        binaries = {}
        for slot, key, data in decoded:
            if slot != "boundary_object_data" or key in binaries:
                raise DomainError("INVALID_SCHEMA", 422)
            binaries[key] = data
        items = payload.get("objects")
        if not isinstance(items, list):
            raise DomainError("INVALID_SCHEMA", 422)
        observed = set()
        for item in items:
            if not isinstance(item, dict) or "data" in item:
                raise DomainError("INVALID_SCHEMA", 422)
            key = item.get("key")
            if not isinstance(key, str) or key in observed or key not in binaries:
                raise DomainError("INVALID_SCHEMA", 422)
            observed.add(key)
            item["data"] = binaries[key]
        if observed != set(binaries):
            raise DomainError("INVALID_SCHEMA", 422)
        return BoundaryObjects.model_validate(payload)

    def encode_staged(self, value):
        return self._encode_model(
            value, model=StagedSessionObjects, version=STAGED_VERSION
        )

    def decode_staged(self, value):
        return self._decode_model(
            value, model=StagedSessionObjects, version=STAGED_VERSION
        )

    def encode_receipt(self, value):
        return self._encode_model(
            value, model=SessionReceipt, version=RECEIPT_VERSION, mode="json"
        )

    def decode_receipt(self, value):
        return self._decode_model(
            value, model=SessionReceipt, version=RECEIPT_VERSION
        )

    def encode_compatibility(self, value):
        return self._encode_model(
            value, model=SessionCompatibility, version=COMPATIBILITY_VERSION
        )

    def decode_compatibility(self, value):
        return self._decode_model(
            value, model=SessionCompatibility, version=COMPATIBILITY_VERSION
        )

    def encode_observation(self, value):
        return self._encode_model(
            value,
            model=NativeApprovalObservation,
            version=OBSERVATION_VERSION,
            datetime_fields=("observed_at",),
        )

    def decode_observation(self, value):
        return self._decode_model(
            value, model=NativeApprovalObservation, version=OBSERVATION_VERSION
        )

    def encode_input_receipt(self, value):
        return self._encode_model(
            value, model=InputReceipt, version=INPUT_RECEIPT_VERSION
        )

    def decode_input_receipt(self, value):
        return self._decode_model(
            value, model=InputReceipt, version=INPUT_RECEIPT_VERSION
        )

    def encode_human_input(self, value):
        return self._encode_model(
            value, model=HumanInput, version=HUMAN_INPUT_VERSION
        )

    def decode_human_input(self, value):
        return self._decode_model(
            value, model=HumanInput, version=HUMAN_INPUT_VERSION
        )

    def encode_delivery_receipt(self, value):
        return self._encode_model(
            value, model=DeliveryReceipt, version=DELIVERY_RECEIPT_VERSION
        )

    def decode_delivery_receipt(self, value):
        return self._decode_model(
            value, model=DeliveryReceipt, version=DELIVERY_RECEIPT_VERSION
        )

    def encode_resolved(self, resolved: dict) -> dict:
        if not isinstance(resolved, dict):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        try:
            schema_version = resolved["profile"]["body"].get("schema_version")
        except (KeyError, TypeError):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503) from None
        if schema_version is None:
            return resolved
        if schema_version not in {"wuji.harness.session.v1", "wuji.harness.problem.v1"}:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        required = {
            "session_compatibility",
            "session_limits",
            "delivery_id",
            "memory_files",
        }
        if not required <= set(resolved) or not isinstance(resolved["memory_files"], dict):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        try:
            compatibility = SessionCompatibility.model_validate(
                resolved["session_compatibility"]
            )
            limits = SessionLimits.model_validate(resolved["session_limits"])
        except ValidationError:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503) from None
        binaries = []
        for key, data in sorted(resolved["memory_files"].items()):
            if not isinstance(key, str) or not isinstance(data, bytes):
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            binaries.append(self._binary("resolved_memory_file", key, data))
        encoded = {
            **resolved,
            "session_compatibility": self.encode_compatibility(compatibility).model_dump(
                mode="python"
            ),
            "session_limits": limits.model_dump(mode="python"),
            "memory_files": [item.model_dump(mode="python") for item in binaries],
        }
        try:
            wire.WorkerSessionResolvedHost.model_validate(encoded)
        except ValidationError:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503) from None
        if len(canonical_json_bytes(encoded)) > self.maximum:
            raise DomainError("LIMIT_BLOCKED", 422)
        return encoded

    def decode_resolved(self, resolved):
        if isinstance(resolved, (wire.WorkerResolvedHost, wire.WorkerSessionResolvedHost)):
            resolved = _outer_document(resolved)
        if not isinstance(resolved, dict):
            raise DomainError("INVALID_SCHEMA", 422)
        try:
            schema_version = resolved["profile"]["body"].get("schema_version")
        except (KeyError, TypeError):
            raise DomainError("INVALID_SCHEMA", 422) from None
        if schema_version is None:
            wire.WorkerResolvedHost.model_validate(resolved)
            return resolved
        if schema_version not in {"wuji.harness.session.v1", "wuji.harness.problem.v1"}:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        if len(canonical_json_bytes(resolved)) > self.maximum:
            raise DomainError("LIMIT_BLOCKED", 422)
        checked = wire.WorkerSessionResolvedHost.model_validate(resolved)
        compatibility = self.decode_compatibility(checked.session_compatibility)
        limits = SessionLimits.model_validate(
            checked.session_limits.model_dump(mode="python")
        )
        memory_files = self._decode_binaries(
            checked.memory_files, expected_slot="resolved_memory_file"
        )
        value = dict(resolved)
        value["session_compatibility"] = compatibility.model_dump(mode="python")
        value["session_limits"] = limits.model_dump(mode="python")
        value["memory_files"] = memory_files
        return value

    @staticmethod
    def _published_closure(value):
        expected = {_ref_key(ref): ref for ref in value.object_refs}
        if len(expected) != len(value.object_refs):
            raise DomainError("INVALID_SCHEMA", 422)
        roots = (
            value.manifest.history_root,
            value.manifest.provider_state_ref,
            value.manifest.memory_manifest_ref,
        )
        if any(_ref_key(ref) not in expected or expected[_ref_key(ref)] != ref for ref in roots):
            raise DomainError("INVALID_REFERENCE", 422)
        if set(value.object_bytes) != set(expected):
            raise DomainError("INVALID_REFERENCE", 422)
        for key, ref in expected.items():
            data = value.object_bytes[key]
            if not isinstance(data, bytes) or sha256(data).hexdigest() != ref.sha256.root:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        return expected

    def encode_published(self, value):
        value = PublishedSession.model_validate(value)
        self._published_closure(value)
        payload = {
            "receipt": value.receipt.model_dump(mode="json"),
            "manifest": value.manifest.model_dump(mode="json"),
            "history": value.history.model_dump(mode="python"),
            "provider_state": value.provider_state.model_dump(mode="python"),
            "memory": value.memory.model_dump(mode="python"),
            "object_refs": [ref.model_dump(mode="json") for ref in value.object_refs],
            "recovery_check": (
                None
                if value.recovery_check is None
                else value.recovery_check.model_dump(mode="python")
            ),
        }
        binaries = [
            self._binary("published_object_bytes", key, value.object_bytes[key])
            for key in sorted(value.object_bytes)
        ]
        return self._payload(PUBLISHED_VERSION, payload, binaries)

    def decode_published(self, value):
        payload, decoded = self._decode(value, expected_version=PUBLISHED_VERSION)
        if "object_bytes" in payload:
            raise DomainError("INVALID_SCHEMA", 422)
        binaries = {}
        for slot, key, data in decoded:
            if slot != "published_object_bytes" or key in binaries:
                raise DomainError("INVALID_SCHEMA", 422)
            binaries[key] = data
        published = PublishedSession.model_validate({**payload, "object_bytes": binaries})
        self._published_closure(published)
        return published


class SessionHostBridge:
    """Six generated RPCs composed over WorkerHostBridge's current-Worker port."""

    def __init__(self, worker_bridge, *, codec: SessionTransportCodec):
        if not callable(getattr(worker_bridge, "current_worker_host", None)):
            raise ValueError("the existing authenticated WorkerHostBridge is required")
        if not callable(getattr(getattr(worker_bridge, "intake", None), "save", None)):
            raise ValueError("the existing private Worker intake is required")
        if not isinstance(codec, SessionTransportCodec):
            raise TypeError("the fixed Session transport codec is required")
        self.worker_bridge = worker_bridge
        self.codec = codec

    @staticmethod
    def _request(value, model):
        if isinstance(value, model):
            value = value.model_dump(mode="python")
        return model.model_validate(value)

    def _host(self, access, request, method):
        host = self.worker_bridge.current_worker_host(access, request.assignment)
        operation = getattr(host, method, None)
        if not callable(operation):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        document = _outer_document(request)
        digest = sha256(canonical_json_bytes(document)).hexdigest()
        self.worker_bridge.intake.save(
            request.assignment, "p08-" + method.replace("_", "-") + "-" + digest, request
        )
        return operation

    def stage_session(self, access, payload):
        request = self._request(payload, wire.WorkerStageSessionRequest)
        method = self._host(access, request, "stage_session")
        objects = self.codec.decode_boundary(request.boundary)
        return self.codec.encode_staged(method(request.assignment, objects))

    def publish_session(self, access, payload):
        request = self._request(payload, wire.WorkerPublishSessionRequest)
        method = self._host(access, request, "publish_session")
        receipt = method(
            request.assignment,
            request.manifest,
            expected_revision=request.expected_revision.root,
        )
        return self.codec.encode_receipt(receipt)

    def load_session(self, access, payload):
        request = self._request(payload, wire.WorkerLoadSessionRequest)
        method = self._host(access, request, "load_session")
        published = method(
            request.assignment,
            manifest_ref=request.manifest_ref,
        )
        return self.codec.encode_published(published)

    def register_input(self, access, payload):
        request = self._request(payload, wire.WorkerRegisterInputRequest)
        method = self._host(access, request, "register_input")
        observation = self.codec.decode_observation(request.observation)
        return self.codec.encode_input_receipt(
            method(request.assignment, observation)
        )

    def load_delivery(self, access, payload):
        request = self._request(payload, wire.WorkerLoadDeliveryRequest)
        method = self._host(access, request, "load_delivery")
        human_input = method(
            request.assignment,
            delivery_id=request.delivery_id,
        )
        return self.codec.encode_human_input(human_input)

    def acknowledge_delivery(self, access, payload):
        request = self._request(payload, wire.WorkerAcknowledgeDeliveryRequest)
        method = self._host(access, request, "acknowledge_delivery")
        receipt = method(
            request.assignment,
            delivery_id=request.delivery_id,
            payload_digest=request.payload_digest.root,
        )
        return self.codec.encode_delivery_receipt(receipt)
