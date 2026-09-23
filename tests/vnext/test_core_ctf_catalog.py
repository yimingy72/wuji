"""Core CTF catalog and launch composition without cluster or model access."""

from hashlib import sha256
import json
from pathlib import Path
import sys
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages/task-runtime/src"))
sys.path.insert(0, str(ROOT / "ops/vnext"))

import core_ctf_catalog as catalog  # noqa: E402
import task_launch  # noqa: E402
from wuji_core.http import canonical_json_bytes  # noqa: E402
from wuji_core.admission.registry import (  # noqa: E402
    SessionCapabilityRegistration,
    TaskAdmissionConfig,
    _mechanism_candidate_tool_allowed,
    configuration_digest,
    expected_session_capabilities,
    session_client_snapshot,
    verified_session_capability_ref,
)
from wuji_maf_worker.factory import ProblemHarnessProfile, parse_profile  # noqa: E402


def source():
    return {
        "database": {
            "host": "postgres.core.invalid", "port": 5432,
            "dbname": "core", "password": "must-not-copy",
        },
        "roles": {},
        "owner": ["tenant-core", "project-core", "catalog-anchor"],
        "identity": {
            "issuer": "https://identity.core.invalid",
            "audience": "wuji-core",
        },
        "ca_file": "/config/ca.crt",
        "public_key_file": "/config/identity.pub",
        "operator_token_file": "/run/wuji/operator.token",
        "operator_subject": "operator",
        "pod_controller_subject": "pod-controller",
    }


def config(*, mode="real_model", explore_limit=4, pool_capacity=5):
    return catalog.owner_template(
        source(),
        mode=mode,
        published_at=catalog.PUBLISHED_AT,
        lock_digest=task_launch.shipped_worker_lock_digest(),
        namespace="wuji-core-isolated",
        model_gateway_url=(
            "http://127.0.0.1:8081/v1/chat/completions"
            if mode == "mechanism_synthetic"
            else "https://model.core.invalid/v1/chat/completions"
        ),
        client_model="core-model",
        upstream_model="provider/core-model",
        task_key_ref="core-model-key",
        model_capability_ref="core-model-capability-v1",
        kali_image_digest="b" * 64,
        architecture="amd64",
        action_signing_key_ref="signing-key",
        action_signing_kid="deployment-key",
        explore_limit=explore_limit,
        pool_capacity=pool_capacity,
    )


def definition(value):
    return {
        **value["definition"],
        "evaluation_mode": "real_model",
        "task": {
            "schema_version": "wuji.api.v2",
            "project_id": "project-core",
            "name": "core fixture",
            "scenario": "ctf",
            "goal": {
                "text": "Recover the authorized challenge answer.",
                "criteria": [{
                    "criterion_id": "answer",
                    "object": "challenge",
                    "condition": "answer supported by captured evidence",
                    "evidence_requirements": ["sealed bytes"],
                    "allowed_methods": ["non-destructive execution"],
                    "responsible_party": "operator",
                    "required": True,
                }],
            },
            "authorization_scope": [{
                "host": "challenge.core.invalid", "protocol": "https", "port": 443,
            }],
            "authorization_expires_at": "2026-12-31T00:00:00Z",
            "entry_points": ["https://challenge.core.invalid/"],
            "external_analysis_approved": True,
            "model_profile_ref": value["definition"]["model_profile"]["ref"],
            "runtime_profile_ref": value["definition"]["runtime_profile"]["ref"],
            "budget": {"amount": "5", "currency": "USD"},
            "explore_concurrency": 4,
        },
        "start_points": ["https://challenge.core.invalid/"],
    }


def test_catalog_freezes_native_capabilities_limits_and_independent_capacity():
    value = config()
    assert value == config()
    assert value["namespace"] == "wuji-core-isolated"
    assert "must-not-copy" not in json.dumps(value)
    assert value["capacity"] == 5
    assert all("first-use" not in key for key in value["capacity_pool_keys"])
    runtime = value["definition"]["runtime_profile"]
    assert runtime["task_run_limits"] == {"explore": 4, "reason": 1}
    assert runtime["process_limits"]["max_active_execs"] == 4
    assert runtime["capture_policy"]["pcap_segment_bytes"] == 64_000_000
    assert runtime["capture_policy"]["max_session_bytes"] <= 1024**3
    assert value["executor"]["protocol"] == "process.v1"
    assert value["executor_action"]["audience"] != value["identity"]["audience"]
    assert {tool["name"] for tool in value["tools"]} == {
        "kali_exec", "kali_read", "kali_input", "kali_stop",
        "workspace_publish", "workspace_materialize",
    }
    mechanism = config(mode="mechanism_synthetic", explore_limit=7, pool_capacity=9)
    assert mechanism["evaluation_mode"] == "mechanism_synthetic"
    assert mechanism["definition"]["runtime_profile"]["task_run_limits"]["explore"] == 7
    assert mechanism["capacity"] == 9
    mechanism_definition = {
        "evaluation_mode": "mechanism_synthetic",
        "runtime_profile": mechanism["definition"]["runtime_profile"],
        "task": {"authorization_scope": []},
    }
    assert _mechanism_candidate_tool_allowed(
        mechanism_definition, "explore", ["process"], "imported_unverified"
    )
    assert _mechanism_candidate_tool_allowed(
        mechanism_definition, "explore", ["workspace_bundle"], "imported_unverified"
    )
    assert not _mechanism_candidate_tool_allowed(
        mechanism_definition, "reason", ["process"], "imported_unverified"
    )


def test_core_profiles_and_binding_select_native_mcp_and_v2_kali():
    value = config()
    frozen = definition(value)
    profiles = task_launch.published_session_profiles(value, frozen)
    reason, explore = profiles["reason"], profiles["explore"]
    assert isinstance(parse_profile(reason), ProblemHarnessProfile)
    assert isinstance(parse_profile(explore), ProblemHarnessProfile)
    assert reason["body"]["context_contract"] == "wuji.worker-context.v4"
    assert reason["body"]["capabilities"]["mcp"] is False
    assert not reason["body"]["tool_definition_refs"]
    reason_names = {item["name"] for item in reason["body"]["capability_manifest"]}
    assert "board_publish" not in reason_names
    explore_names = {item["name"] for item in explore["body"]["capability_manifest"]}
    assert explore["body"]["capabilities"]["mcp"] is True
    assert "board_publish" in explore_names
    assert {tool["name"] for tool in value["tools"]} <= explore_names
    assert explore["body"]["function_limits"] == value["function_limits"]["explore"]
    assert task_launch.published_tool_routes(value, frozen) == {}

    prepared = {
        "definition": frozen,
        "definition_digest": sha256(canonical_json_bytes(frozen)).hexdigest(),
        "runtime_attempt": 1,
        "execution_epoch": 2,
        "control_version": "3",
    }
    binding = task_launch.binding_document(
        value,
        "task-core",
        agent_image="registry.invalid/agent@sha256:" + "a" * 64,
        kali_image="registry.invalid/kali@sha256:" + "b" * 64,
        prepared=prepared,
        extra={
            "executor_ref": catalog.EXECUTOR_REF,
            "runtime_origin": "https://runtime.wuji-core-isolated.svc:8443",
            "gate_url": "https://gates.wuji-core-isolated.svc:8443",
            "namespace": "wuji-core-isolated",
            "evidence_ref": "work/core/evidence.md",
            "capture_image": "registry.invalid/capture@sha256:" + "c" * 64,
        },
    )
    runtime_config = task_launch.attempt_config(binding)
    assert runtime_config.template_version == "core-ctf-v1"
    assert runtime_config.agent_resources.memory_request == "512Mi"
    assert runtime_config.agent_resources.memory_limit == "1Gi"
    assert runtime_config.capture_policy.pcap_segment_bytes == 64_000_000
    assert task_launch.initial_intent_document(value, frozen) is None
    assert set(task_launch.task_service_names(
        "task-core", template_version="core-ctf-v1"
    )) == {"agent", "kali", "capture"}
    binding["kali_tls_sha256"] = "d" * 64
    entry = task_launch.gate_executor_entry(
        binding, base_url="https://task-kali.wuji-core-isolated.svc:8444"
    )
    assert "action" in entry and "gate_token_file" not in entry
    material = {
        "ca.crt": b"ca", "identity.pub": b"public",
        "receiver.token": b"receiver", "task-agent.crt": b"agent-cert",
        "task-agent.key": b"agent-key", "task-kali.crt": b"kali-cert",
        "task-kali.key": b"kali-key",
        "capture-tls.crt": b"capture-cert",
        "capture-tls.key": b"capture-key",
        "capture-client-ca.crt": b"capture-ca",
        "capture-client.sha256": ("e" * 64).encode(),
    }
    _, objects = task_launch.task_objects(
        binding, material, namespace="wuji-core-isolated"
    )
    agent_config = next(
        item for item in objects
        if item["kind"] == "ConfigMap" and item["metadata"]["name"].endswith("agent-config")
    )
    supervisor = json.loads(agent_config["data"]["supervisor.json"])
    assert supervisor["template_version"] == "core-ctf-v1"
    assert supervisor["namespace"] == "wuji-core-isolated"
    kali_config = next(
        item for item in objects
        if item["kind"] == "ConfigMap" and item["metadata"]["name"].endswith("kali-config")
    )
    assert json.loads(kali_config["data"]["kali.json"])["schema_version"] == "wuji.kali.deployment.v2"
    kali_secret = next(
        item for item in objects
        if item["kind"] == "Secret" and item["metadata"]["name"].endswith("kali-auth")
    )
    assert set(kali_secret["data"]) == {"tls.crt", "tls.key"}
    capture_secret = next(
        item for item in objects
        if item["kind"] == "Secret" and item["metadata"]["name"].endswith("capture-auth")
    )
    assert set(capture_secret["data"]) == {
        "tls.crt", "tls.key", "client-ca.crt", "client.sha256"
    }


def test_core_attempt_issues_exact_task_server_leaves_without_ca_or_client_key():
    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "core test CA")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca_name).issuer_name(ca_name).public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "runtime")]))
        .issuer_name(ca.subject).public_key(client_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    ca_bytes = ca.public_bytes(serialization.Encoding.PEM)
    material, fingerprints = task_launch.core_attempt_tls_material(
        {"task_id": "task-core", "namespace": "wuji-core-isolated"},
        ca_certificate=ca_bytes,
        ca_private_key=ca_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        runtime_client_certificate=client.public_bytes(serialization.Encoding.PEM),
    )
    assert set(material) == {
        "task-kali.crt", "task-kali.key", "capture-tls.crt", "capture-tls.key",
        "capture-client-ca.crt", "capture-client.sha256",
    }
    assert material["capture-client-ca.crt"] == ca_bytes
    assert fingerprints["capture_client_sha256"] == client.fingerprint(hashes.SHA256()).hex()
    for role in ("task-kali", "capture-tls"):
        leaf = x509.load_pem_x509_certificate(material[role + ".crt"])
        assert leaf.extensions.get_extension_for_class(
            x509.SubjectKeyIdentifier
        ).value.digest == x509.SubjectKeyIdentifier.from_public_key(leaf.public_key()).digest
        assert leaf.extensions.get_extension_for_class(
            x509.AuthorityKeyIdentifier
        ).value.key_identifier == x509.SubjectKeyIdentifier.from_public_key(ca.public_key()).digest
    kali = x509.load_pem_x509_certificate(material["task-kali.crt"])
    sans = set(kali.extensions.get_extension_for_class(
        x509.SubjectAlternativeName
    ).value.get_values_for_type(x509.DNSName))
    assert sans == {
        "task-kali-taskcore",
        "task-kali-taskcore.wuji-core-isolated",
        "task-kali-taskcore.wuji-core-isolated.svc",
        "task-kali-taskcore.wuji-core-isolated.svc.cluster.local",
    }
    assert not any("*" in name for name in sans)


def test_core_requirement_material_does_not_read_shared_kali_or_collector_keys(tmp_path):
    agent = tmp_path / "agent"
    deployment = tmp_path / "deployment"
    agent.mkdir()
    deployment.mkdir()
    (agent / "tls.crt").write_bytes(b"agent-cert")
    (agent / "tls.key").write_bytes(b"agent-key")
    (deployment / "receiver.token").write_bytes(b"receiver")
    ca = tmp_path / "ca.crt"
    public = tmp_path / "identity.pub"
    ca.write_bytes(b"ca")
    public.write_bytes(b"public")
    material = task_launch.requirement_material(
        {"template_version": "core-ctf-v1", "ca_file": str(ca),
         "public_key_file": str(public)},
        agent_auth_dir=agent,
        kali_auth_dir=tmp_path / "missing-shared-kali",
        deployment_auth_dir=deployment,
        gates_auth_dir=tmp_path / "missing-collector",
    )
    assert set(material) == {
        "ca.crt", "identity.pub", "receiver.token", "task-agent.crt", "task-agent.key"
    }


def test_all_core_roles_form_exact_bounded_session_capability_fixtures():
    value = config()
    profiles = task_launch.published_session_profiles(value, definition(value))
    admission = TaskAdmissionConfig.model_validate(value["admission"])
    client = session_client_snapshot(admission)
    runtime = admission.runtime.model_dump(mode="json")
    framework = dict(task_launch.FRAMEWORK_SNAPSHOT)
    kinds = {
        tool["ref"]: tool["allowed_target_kinds"] for tool in value["tools"]
    }
    expected_mcp = {"reason": False, "explore": True, "report": False}
    for kind, profile in profiles.items():
        body = profile["body"]
        caps = expected_session_capabilities(
            body, [kinds[ref] for ref in body["tool_definition_refs"]]
        )
        assert caps["mcp"] is expected_mcp[kind]
        if "capabilities" in body:
            assert body["capabilities"] == caps
        capability = SessionCapabilityRegistration.model_validate({
            "ref": verified_session_capability_ref(profile["digest"]),
            "revision": "1",
            "published_at": value["definition"]["model_profile"]["published_at"],
            "validation_status": "verified",
            "profile_snapshot": profile,
            "profile_digest": profile["digest"],
            "client_snapshot": client,
            "client_digest": configuration_digest(client),
            "runtime_snapshot": runtime,
            "runtime_digest": configuration_digest(runtime),
            "framework_snapshot": framework,
            "framework_digest": configuration_digest(framework),
            "lock_digest": admission.runtime.lock_digest,
            "limits": body["session_limits"],
            "recovery_classes": ["settled_boundary", "approval_boundary"],
            "memory_mode": body["memory_mode"],
            "approver_subjects": ["fixture-operator"],
            "approval_ttl_seconds": 300,
            "evidence_refs": [f"fixture-only:core-session-{kind}"],
        })
        limits = capability.limits
        assert limits["max_total_bytes"] <= runtime["limits"]["max_total_output_bytes"]
        assert limits["max_object_bytes"] <= runtime["limits"]["max_single_output_bytes"]
        assert limits["max_pending_approvals"] <= runtime["max_pending_operations"]
        assert capability.published_at == admission.model.published_at
        assert capability.lock_digest == body["lock_digest"]
