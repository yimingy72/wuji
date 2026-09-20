"""P08 B2 source/wire checks; actual DB/child candidate is separately assigned."""

from decimal import Decimal

import pytest

from support.session_transport import (
    BOUNDARY_BASE64,
    BOUNDARY_BYTES,
    BOUNDARY_DIGEST,
    assignment,
    boundary_objects,
    m1_resolved,
    published_session,
    remote_worker_host,
    remote_resolver,
    session_resolved,
    session_host_bridge,
    session_transport_codec,
    simple_session_values,
)
from wuji_core.contracts import generated as wire
from wuji_core.http import canonical_json_bytes
from wuji_core.persistence.uow import DomainError


def test_the_native_object_bound_names_the_root_and_the_sizes():
    """The live failure named only a generic bound; operators need the root."""

    from support.session_transport import compatibility, session_limits
    from wuji_maf_worker.sessions import NativeSessionAdapter

    adapter = NativeSessionAdapter(compatibility=compatibility(), limits=session_limits())
    adapter._bounded({"role": "user"}, "history")

    with pytest.raises(ValueError) as refused:
        adapter._bounded({"blob": "x" * 20_000}, "provider")
    message = str(refused.value)
    assert "native provider root exceeds the fixed object bound" in message
    # Two bounded byte counts, no message content.
    assert "(20011 > 16384)" in message
    assert "x" * 32 not in message


def test_session_boundary_transport_uses_explicit_binary_and_preserves_decimal():
    """Catch UTF-8/coercive bytes encoding or lossy JSON-mode SDK serialization."""
    original = boundary_objects()
    codec = session_transport_codec()

    encoded = codec.encode_boundary(original)

    assert encoded.schema_version.value == "wuji.worker.session.boundary.v1"
    assert "data" not in encoded.payload["objects"][0]
    assert encoded.binaries[0].slot.value == "boundary_object_data"
    assert encoded.binaries[0].key == "provider-raw"
    assert encoded.binaries[0].data_base64 == BOUNDARY_BASE64
    assert encoded.binaries[0].data_sha256.root == BOUNDARY_DIGEST
    assert encoded.binaries[0].size_bytes == len(BOUNDARY_BYTES)
    assert encoded.payload["provider_state"]["session_state"]["provider_decimal"] == Decimal("1.250")

    restored = codec.decode_boundary(encoded)

    assert restored == original
    assert restored.objects[0].data == BOUNDARY_BYTES
    assert restored.provider_state.session_state["provider_decimal"] == Decimal("1.250")


def test_session_resolved_transport_keeps_an_explicit_zero_tool_set():
    resolved = session_resolved()
    resolved["tools"] = []

    encoded = session_transport_codec().encode_resolved(resolved)

    assert encoded["tools"] == []


def test_published_session_transport_requires_the_exact_object_closure():
    """Catch omitted, duplicate, extra, or wrong-slot published object bytes."""
    original = published_session()
    codec = session_transport_codec()

    encoded = codec.encode_published(original)

    assert "object_bytes" not in encoded.payload
    assert {item.key for item in encoded.binaries} == set(original.object_bytes)
    assert {item.slot.value for item in encoded.binaries} == {"published_object_bytes"}
    restored = codec.decode_published(encoded)
    assert restored == original

    first = encoded.binaries[0]
    with_extra = encoded.model_copy(
        update={"binaries": [
            *encoded.binaries,
            first.model_copy(update={"key": "unexpected@1"}),
        ]}
    )
    with_duplicate = encoded.model_copy(
        update={"binaries": [*encoded.binaries, first]}
    )
    with_wrong_slot = encoded.model_copy(
        update={"binaries": [
            first.model_copy(update={"slot": type(first.slot).resolved_memory_file}),
            *encoded.binaries[1:],
        ]}
    )

    for malformed in (with_extra, with_duplicate, with_wrong_slot):
        try:
            codec.decode_published(malformed)
        except ValueError:
            pass
        else:
            raise AssertionError("malformed published Session binary closure was accepted")


def test_session_transport_round_trips_each_nonbinary_internal_contract():
    """Catch an endpoint silently using a hand-written or lossy replacement DTO."""
    codec = session_transport_codec()
    values = simple_session_values()
    methods = {
        "staged": (codec.encode_staged, codec.decode_staged, "wuji.worker.session.staged.v1"),
        "receipt": (codec.encode_receipt, codec.decode_receipt, "wuji.worker.session.receipt.v1"),
        "compatibility": (
            codec.encode_compatibility,
            codec.decode_compatibility,
            "wuji.worker.session.compatibility.v1",
        ),
        "observation": (
            codec.encode_observation,
            codec.decode_observation,
            "wuji.worker.session.approval-observation.v1",
        ),
        "input_receipt": (
            codec.encode_input_receipt,
            codec.decode_input_receipt,
            "wuji.worker.session.input-receipt.v1",
        ),
        "human_input": (
            codec.encode_human_input,
            codec.decode_human_input,
            "wuji.worker.session.human-input.v1",
        ),
        "delivery_receipt": (
            codec.encode_delivery_receipt,
            codec.decode_delivery_receipt,
            "wuji.worker.session.delivery-receipt.v1",
        ),
    }

    for name, original in values.items():
        encode, decode, version = methods[name]
        envelope = encode(original)
        assert envelope.schema_version.value == version
        assert envelope.binaries == []
        assert decode(envelope) == original

    assert (
        values["observation"].contents[0]["amount"]
        == Decimal("1.250")
    )


def test_resolved_transport_preserves_m1_and_encodes_only_fixed_session_memory():
    """Catch M1 body drift or arbitrary/implicit encoding of resolved Session bytes."""
    codec = session_transport_codec()
    m1 = m1_resolved()
    m1_bytes = canonical_json_bytes(m1)

    assert codec.encode_resolved(m1) is m1
    assert canonical_json_bytes(codec.decode_resolved(m1)) == m1_bytes
    wire.WorkerResolvedHost.model_validate(m1)

    internal = session_resolved()
    encoded = codec.encode_resolved(internal)
    checked = wire.WorkerSessionResolvedHost.model_validate(encoded)
    assert checked.session_compatibility.schema_version.value == (
        "wuji.worker.session.compatibility.v1"
    )
    assert len(checked.memory_files) == 1
    assert checked.memory_files[0].slot.value == "resolved_memory_file"
    assert checked.memory_files[0].key == "notes.txt"
    assert checked.memory_files[0].data_base64 == "Zml4ZWQgbWVtb3J5"

    restored = codec.decode_resolved(encoded)
    assert restored["memory_files"] == internal["memory_files"]
    assert restored["session_compatibility"] == internal["session_compatibility"]
    assert restored["session_limits"] == internal["session_limits"]
    assert restored["delivery_id"] == "delivery-p08"

    for malformed in (
        {key: value for key, value in internal.items() if key != "memory_files"},
        {
            **m1,
            "profile": {
                **m1["profile"],
                "body": {**m1["profile"]["body"], "schema_version": "unknown"},
            },
        },
    ):
        try:
            codec.encode_resolved(malformed)
        except DomainError as error:
            assert error.code == "CAPABILITY_UNAVAILABLE"
        else:
            raise AssertionError("incomplete or unknown Session resolve shape was accepted")


def test_session_host_bridge_carries_all_six_typed_operations():
    """Catch a fake/local Host path or an RPC that drops its exact operation binding."""
    bridge, worker_bridge, codec = session_host_bridge()
    fixed_assignment = assignment()
    values = simple_session_values()
    published = published_session()
    access = object()

    staged = bridge.stage_session(
        access,
        wire.WorkerStageSessionRequest(
            assignment=fixed_assignment,
            boundary=codec.encode_boundary(boundary_objects()),
        ),
    )
    receipt = bridge.publish_session(
        access,
        wire.WorkerPublishSessionRequest(
            assignment=fixed_assignment,
            manifest=published.manifest,
            expected_revision="0",
        ),
    )
    loaded = bridge.load_session(
        access,
        wire.WorkerLoadSessionRequest(
            assignment=fixed_assignment,
            manifest_ref="manifest-p08-1",
        ),
    )
    input_receipt = bridge.register_input(
        access,
        wire.WorkerRegisterInputRequest(
            assignment=fixed_assignment,
            observation=codec.encode_observation(values["observation"]),
        ),
    )
    human_input = bridge.load_delivery(
        access,
        wire.WorkerLoadDeliveryRequest(
            assignment=fixed_assignment,
            delivery_id="delivery-p08",
        ),
    )
    delivery_receipt = bridge.acknowledge_delivery(
        access,
        wire.WorkerAcknowledgeDeliveryRequest(
            assignment=fixed_assignment,
            delivery_id="delivery-p08",
            payload_digest="c" * 64,
        ),
    )

    assert codec.decode_staged(staged) == values["staged"]
    assert codec.decode_receipt(receipt) == values["receipt"]
    assert codec.decode_published(loaded) == published
    assert codec.decode_input_receipt(input_receipt) == values["input_receipt"]
    assert codec.decode_human_input(human_input) == values["human_input"]
    assert codec.decode_delivery_receipt(delivery_receipt) == values["delivery_receipt"]
    assert len(worker_bridge.intake.saved) == 6
    assert len({name for _operation, name in worker_bridge.intake.saved}) == 6


def test_session_host_router_exposes_only_the_six_generated_worker_endpoints():
    """Catch an unmounted RPC or an accidental public approval execution route."""
    from wuji_core.http.session_host import create_session_host_router

    bridge, _worker_bridge, _codec = session_host_bridge()
    router = create_session_host_router(bridge)
    paths = {
        route.path
        for route in router.routes
        if "POST" in getattr(route, "methods", set())
    }

    assert paths == {
        "/internal/v2/worker-host/stage-session",
        "/internal/v2/worker-host/publish-session",
        "/internal/v2/worker-host/load-session",
        "/internal/v2/worker-host/register-input",
        "/internal/v2/worker-host/load-delivery",
        "/internal/v2/worker-host/acknowledge-delivery",
    }


def test_remote_worker_host_uses_generated_six_rpc_transport_and_bound_spool_keys(
    tmp_path,
):
    """Catch local Host fallback, hand-written wire, or one fixed file per method."""
    host, _codec = remote_worker_host(tmp_path / "remote-session")
    fixed_assignment = assignment()
    values = simple_session_values()
    published = published_session()

    assert host.stage_session(fixed_assignment, boundary_objects()) == values["staged"]
    assert host.publish_session(
        fixed_assignment, published.manifest, expected_revision="0"
    ) == values["receipt"]
    assert host.load_session(
        fixed_assignment, manifest_ref="manifest-p08-1"
    ) == published
    assert host.register_input(
        fixed_assignment, values["observation"]
    ) == values["input_receipt"]
    assert host.load_delivery(
        fixed_assignment, delivery_id="delivery-p08"
    ) == values["human_input"]
    assert host.acknowledge_delivery(
        fixed_assignment,
        delivery_id="delivery-p08",
        payload_digest="c" * 64,
    ) == values["delivery_receipt"]

    retained = sorted(path.name for path in host.directory.glob("p08-*.json"))
    assert len(retained) == 12
    assert len(set(retained)) == 12
    assert all(len(name.rsplit("-", 1)[-1].split(".", 1)[0]) == 64 for name in retained)


def test_child_completion_returns_saved_input_receipt_as_its_own_kind():
    """Catch conversion of a saved Input into a result or a process-exit receipt."""
    from wuji_maf_worker.child_entrypoint import validate_completion_receipt

    receipt = simple_session_values()["input_receipt"]

    assert validate_completion_receipt(receipt) is receipt
    try:
        validate_completion_receipt(receipt.model_dump(mode="python"))
    except TypeError:
        pass
    else:
        raise AssertionError("child accepted an untyped self-reported input receipt")


def test_remote_resolve_preserves_m1_and_restores_session_memory_bytes():
    """Catch a Session resolved wire document leaking base64 objects into Runtime."""
    fixed_assignment = assignment()
    m1 = m1_resolved()
    m1_host, context = remote_resolver(m1)

    assert canonical_json_bytes(
        m1_host.resolve(
            fixed_assignment,
            context,
            verified_principal="verified-worker-principal",
        )
    ) == canonical_json_bytes(m1)

    session = session_resolved()
    session_host, context = remote_resolver(session)
    restored = session_host.resolve(
        fixed_assignment,
        context,
        verified_principal="verified-worker-principal",
    )
    assert restored["memory_files"] == {"notes.txt": b"fixed memory"}
    assert restored["session_compatibility"] == session["session_compatibility"]
    assert restored["session_limits"] == session["session_limits"]
    session_host_bridge,
