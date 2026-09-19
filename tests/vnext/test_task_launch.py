"""P11-C: the owner launch command finalises a created Task and publishes capability."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import partial
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest

import importlib.util  # noqa: E402


def _load_launch_module():
    """Load the owner command by path: `ops/vnext/kubernetes/` must not shadow
    the installed Kubernetes client for this interpreter."""

    path = Path(__file__).resolve().parents[2] / "ops" / "vnext" / "task_launch.py"
    spec = importlib.util.spec_from_file_location("wuji_task_launch", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["wuji_task_launch"] = module
    spec.loader.exec_module(module)
    return module


from test_task_creation import OWNER, create, creation_case, runtime_profile  # noqa: E402
from wuji_core.admission.registry import (  # noqa: E402
    register_tool_definition,
)
from wuji_core.http import canonical_json_bytes  # noqa: E402
from wuji_core.http.auth import Principal  # noqa: E402
from wuji_core.persistence.uow import AccessContext, DomainError  # noqa: E402
from wuji_maf_worker.factory import HarnessProfile  # noqa: E402
task_launch = _load_launch_module()  # noqa: E402


PUBLISHED_AT = datetime(2026, 9, 15, 2, 0, tzinfo=timezone.utc)
TOOL_REF = "workspace-read-v1"
POD_UID = "11111111-2222-3333-4444-555555555555"


def tool_document() -> dict:
    return {
        "ref": TOOL_REF,
        "revision": "1",
        "name": "read_workspace",
        "published_at": PUBLISHED_AT.isoformat().replace("+00:00", "Z"),
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
        "allowed_target_kinds": ["workspace_read"],
        "executor_ref": "kali-workspace-v1",
        "approval_required": False,
    }


def deployment_config(definition) -> dict:
    lock = definition["runtime_profile"]["lock_digest"]
    profiles = {
        kind: HarnessProfile(
            ref=f"harness.{kind}.deployment.v2",
            revision="1",
            work_kind=kind,
            instructions="Read version.txt once using the registered workspace tool.",
            tool_definition_refs=(TOOL_REF,),
            lock_digest=lock,
            max_context_records=128,
            max_context_bytes=65536,
            max_output_tokens=2048,
        ).snapshot()
        for kind in ("reason", "explore", "report")
    }
    return {
        "owner": [OWNER[0], OWNER[1], OWNER[2]],
        "operator_subject": "control-fixture",
        "identity": {
            "issuer": "https://identity.wuji-vnext-test.invalid",
            "audience": "wuji-vnext-deployment",
        },
        "definition": {"worker_profiles": profiles},
        "tool": tool_document(),
        "executor": {
            "ref": "kali-workspace-v1",
            "receiver_id": "unused",
            "environment_ref": "unused",
            "collector_subject": "collector",
            "capture_layer": "fixture_file_bytes",
            "evidence_origin": "fixture_capture",
            "allowed_tool_refs": [TOOL_REF],
        },
    }


def seed_pools(connection, definition) -> None:
    pools = (
        ("deployment-global", "global", None),
        ("model:" + definition["model_profile"]["ref"], "model", None),
        ("tenant:" + OWNER[0], "tenant", OWNER[0]),
    )
    for pool_key, tier, tenant in pools:
        connection.execute(
            """INSERT INTO vnext.capacity_pool(pool_key,tier,tenant_id,capacity,published_ref)
            VALUES(%s,%s,%s,4,'deployment-v1') ON CONFLICT (pool_key) DO NOTHING""",
            (pool_key, tier, tenant),
        )
        # The deployment template Task carries the published capacity binding.
        connection.execute(
            """INSERT INTO vnext.task_capacity_pool(tenant_id,project_id,task_id,pool_key)
            VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (OWNER[0], OWNER[1], OWNER[2], pool_key),
        )


def stored_definition(connection, task_id):
    row = connection.execute(
        "SELECT definition_json, definition_digest FROM vnext.task WHERE task_id=%s",
        (task_id,),
    ).fetchone()
    return json.loads(row[0]), row[1]


def prepared_task(case, task_id, connection):
    definition, _ = stored_definition(connection, task_id)
    config = deployment_config(definition)
    register_tool_definition(connection, tenant_id=OWNER[0], definition=tool_document())
    seed_pools(connection, definition)
    owner = (OWNER[0], OWNER[1], task_id)
    prepared = task_launch.finalise_definition(connection, owner=owner, config=config)
    task_launch.ensure_operator_actor(connection, owner=owner, subject="control-fixture")
    published = task_launch.publish_admission(
        connection, owner=owner, config=config,
        definition=prepared["definition"], attempt=prepared["runtime_attempt"],
        pool_keys=task_launch.deployment_pool_keys(connection, config))
    receipt = task_launch.admit_initial_intent(
        case.environment.additional_app_connection,
        access=AccessContext(
            Principal(
                subject="control-fixture",
                tenant_id=OWNER[0],
                roles=frozenset({"operator"}),
                token_id="task-launch-fixture",
            ),
            "task-launch",
        ),
        task=task_id,
        document=task_launch.initial_intent_document(config, prepared["definition"]),
        idempotency_key=f"task-launch-intent-{task_id}",
    )
    return config, owner, prepared, published, receipt


def binding_for(config, task_id, prepared, published, *, pod_uid=POD_UID):
    document = task_launch.binding_document(
        config,
        task_id,
        agent_image="registry.invalid/agent@sha256:" + "a" * 64,
        kali_image="registry.invalid/kali@sha256:" + "b" * 64,
        prepared=prepared,
        extra={
            "runtime_origin": "https://runtime.wuji-vnext-test.svc:8443",
            "gate_url": "https://gates.wuji-vnext-test.svc:8443",
            "namespace": "wuji-vnext-test",
            "evidence_ref": "docs/vnext/evidence/P11/task-roundtrip-20260915/README.md",
            **published,
        },
    )
    # The Pod UID is observed by the wire phase, never invented by prepare.
    document["pod_uid"] = pod_uid
    return document


def register_pod_receiver(connection, *, task_id, binding, definition):
    attempt = binding["runtime_attempt"]
    connection.execute(
        """INSERT INTO vnext.scheduler_receiver(tenant_id,project_id,task_id,runtime_attempt,
        receiver_id,environment_ref,model_mode,receiver_subject,credential_template_ref,
        harness_profiles_json,enabled,pod_uid)
        VALUES(%s,%s,%s,%s,%s,%s,'synthetic','receiver','deployment-worker-v1',%s,true,%s)""",
        (OWNER[0], OWNER[1], task_id, attempt, binding["receiver_id"],
         binding["environment_ref"],
         canonical_json_bytes(definition["worker_profiles"]).decode(),
         binding["pod_uid"]),
    )


def test_launch_prepares_a_created_task_before_activation(db_environment, audit_directory):
    with creation_case(db_environment, audit_directory) as case:
        created = create(case)
        assert created.status_code == 201, created.text
        task_id = created.json()["task_id"]
        owner = (OWNER[0], OWNER[1], task_id)

        with db_environment.migration_connection() as connection:
            definition, _ = stored_definition(connection, task_id)
            assert "worker_profiles" not in definition
            config = deployment_config(definition)
            register_tool_definition(connection, tenant_id=OWNER[0], definition=tool_document())
            seed_pools(connection, definition)

            prepared = task_launch.finalise_definition(connection, owner=owner, config=config)
            stored, digest = stored_definition(connection, task_id)
            assert prepared["definition_changed"] is True
            assert digest == prepared["definition_digest"] == sha256(
                canonical_json_bytes(stored)
            ).hexdigest()
            assert stored["evaluation_mode"] == "mechanism_synthetic"
            assert set(stored["worker_profiles"]) == {"reason", "explore", "report"}
            assert (
                stored["worker_profiles"]["explore"]["body"]["schema_version"]
                == "wuji.harness.session.v1"
            )

            again = task_launch.finalise_definition(connection, owner=owner, config=config)
            assert again["definition_changed"] is False
            assert again["definition_digest"] == prepared["definition_digest"]

            conflicting = deployment_config(definition)
            conflicting["definition"]["worker_profiles"]["reason"]["body"]["instructions"] = (
                "different published instruction"
            )
            with pytest.raises(DomainError) as conflict:
                task_launch.finalise_definition(connection, owner=owner, config=conflicting)
            assert conflict.value.code == "INPUT_DIGEST_CONFLICT"

            connection.execute(
                "UPDATE vnext.task SET activated_at=now() WHERE task_id=%s", (task_id,)
            )
            # An activated Task must read back as unchanged; a late definition
            # change is refused because the permit already bound the digest.
            after = task_launch.finalise_definition(connection, owner=owner, config=config)
            assert after["definition_changed"] is False
            assert after["definition_digest"] == prepared["definition_digest"]
            with pytest.raises(DomainError) as activated:
                task_launch.finalise_definition(connection, owner=owner, config=conflicting)
            assert activated.value.code == "INVALID_STATE"


def test_launch_binds_admission_executor_intent_and_capability(
    db_environment, audit_directory, monkeypatch
):
    from itertools import count
    from types import SimpleNamespace
    clock = count(0, 121)
    monkeypatch.setattr(task_launch, "time", SimpleNamespace(monotonic=lambda: next(clock), sleep=lambda _: None))
    with creation_case(db_environment, audit_directory) as case:
        created = create(case)
        assert created.status_code == 201, created.text
        task_id = created.json()["task_id"]

        with db_environment.migration_connection() as connection:
            config, owner, prepared, published, receipt = prepared_task(
                case, task_id, connection
            )
            assert published["receiver_id"] == f"task-{task_id}-a1"
            assert published["environment_ref"] == f"pod-environment-{task_id}-a1"
            assert receipt.canonical_ref is not None, receipt.model_dump(mode="json")

            admission = connection.execute(
                "SELECT document_json FROM vnext.admission_config WHERE task_id=%s",
                (task_id,),
            ).fetchone()
            assert admission is not None
            assert json.loads(admission[0])["allowed_tool_refs"] == [TOOL_REF]
            grants = dict(
                (row[0], row[1:]) for row in connection.execute(
                    "SELECT subject, can_read, can_settle, can_observe, can_admit"
                    " FROM vnext.task_access WHERE task_id=%s AND subject IN"
                    " ('receiver','scheduler','collector','gate','pod-controller')",
                    (task_id,),
                ).fetchall()
            )
            assert grants["receiver"] == (True, True, True, True)
            assert grants["scheduler"] == (True, False, False, True)
            assert grants["gate"] == (True, False, False, False)
            executor = connection.execute(
                "SELECT document_json FROM vnext.executor_registration WHERE task_id=%s",
                (task_id,),
            ).fetchone()
            assert json.loads(executor[0])["receiver_id"] == published["receiver_id"]
            intents = connection.execute(
                "SELECT entity_id, acceptance_state, question, producer_subject"
                " FROM vnext.intent_revision WHERE task_id=%s ORDER BY entity_id",
                (task_id,),
            ).fetchall()
            assert len(intents) == 1
            assert intents[0][1] == "admitted"
            assert intents[0][3] == "control-fixture"
            assert "https://fixture.invalid:443" in intents[0][2]
            # Work items are the scheduler's derivation from an admitted Intent
            # once the Task can run; the owner command never invents them.
            assert connection.execute(
                "SELECT count(*) FROM vnext.work_item WHERE task_id=%s", (task_id,)
            ).fetchone() == (0,)

            binding = binding_for(config, task_id, prepared, published)
            with pytest.raises(DomainError) as missing:
                task_launch.publish_capabilities(connection, config=config, binding=binding)
            assert missing.value.code == "CAPABILITY_UNAVAILABLE"

            # The Pod registration path writes this row; the owner command must
            # refuse to publish a capability against a Pod that never registered.
            register_pod_receiver(
                connection, task_id=task_id, binding=binding,
                definition=prepared["definition"],
            )
            other = binding_for(config, task_id, prepared, published,
                                pod_uid="99999999-8888-7777-6666-555555555555")
            with pytest.raises(DomainError) as unregistered:
                task_launch.publish_capabilities(connection, config=config, binding=other)
            assert unregistered.value.code == "CAPABILITY_UNAVAILABLE"

            result = task_launch.publish_capabilities(
                connection, config=config, binding=binding
            )
            assert result["capabilities"] == [
                f"session-capability-{task_id}-a1-{kind}"
                for kind in ("reason", "explore", "report")
            ]
            rows = connection.execute(
                "SELECT ref, profile_digest, document_json, digest"
                " FROM vnext.session_capability ORDER BY ref"
            ).fetchall()
            assert [row[0] for row in rows] == sorted(result["capabilities"])
            for _, profile_digest, document_json, digest in rows:
                assert sha256(document_json.encode()).hexdigest() == digest
                document = json.loads(document_json)
                assert document["profile_digest"] == profile_digest
                assert document["candidate_binding"]["pod_uid"] == POD_UID
                assert document["candidate_binding"]["runtime_attempt"] == "1"
            repeat = task_launch.publish_capabilities(
                connection, config=config, binding=binding
            )
            assert repeat["capabilities"] == result["capabilities"]


def test_published_session_bounds_follow_the_admission_limits():
    """A real MAF history must fit one bounded Session object.

    Task A's attempt 3 child failed with "native history root exceeds the fixed
    object bound" while the profile's own runtime limits allowed a 32 KiB single
    output and 128 KiB total output. The Session bound is derived from those
    limits, not from a hard 16 KiB ceiling.
    """

    task_launch = _load_launch_module()
    lock = task_launch.shipped_worker_lock_digest()

    def definition(single, total):
        return {
            "evaluation_mode": "mechanism_synthetic",
            "task": {
                "scenario": "web_single",
                "goal": {
                    "text": "Read the isolated fixture.",
                    "criteria": [
                        {
                            "criterion_id": "c1",
                            "object": "fixture",
                            "condition": "durable read evidence",
                            "evidence_requirements": ["sealed bytes"],
                            "allowed_methods": ["deterministic"],
                            "responsible_party": "deployment-test",
                        }
                    ],
                },
                "authorization_scope": [
                    {"host": "fixture.invalid", "protocol": "https", "port": 443}
                ],
                "authorization_expires_at": "2026-12-31T00:00:00Z",
                "budget": {"amount": "1", "currency": "USD"},
            },
            "start_points": ["workspace:version.txt"],
            "runtime_profile": {
                "ref": "k8s-runtime-v1", "revision": "1", "lock_digest": lock,
                "allowed_tool_refs": ["workspace-read-v1"],
                "max_pending_operations": 4,
                "limits": {
                    "max_single_output_bytes": single, "max_total_output_bytes": total,
                    "max_work_items": 4, "max_reason_runs": 2, "max_model_requests": 8,
                    "max_tool_calls": 8, "max_attempts_per_work": 2,
                    "max_elapsed_seconds": 1800,
                },
            }
        }

    profiles = {
        kind: {"body": {"instructions": "read", "max_context_records": 8,
                        "max_context_bytes": 4096, "max_output_tokens": 512,
                        "tool_definition_refs": ["workspace-read-v1"]}}
        for kind in ("reason", "explore", "report")
    }
    config = {"definition": {"worker_profiles": profiles}, "tool": tool_document()}

    published = task_launch.published_session_profiles(config, definition(32768, 131072))
    limits = published["explore"]["body"]["session_limits"]
    # The profile's real numbers: one object may carry the largest allowed single
    # output, and the staged total may carry the allowed aggregate.
    assert limits["max_object_bytes"] == 32768
    assert limits["max_total_bytes"] == 131072

    # Both stay bounded even when a Task publishes far larger runtime limits.
    capped = task_launch.published_session_profiles(config, definition(4_000_000, 9_000_000))
    capped_limits = capped["explore"]["body"]["session_limits"]
    assert capped_limits["max_object_bytes"] == 65536
    assert capped_limits["max_total_bytes"] == 262144


def test_minted_operator_bearer_binds_the_deployment_identity(tmp_path):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    from wuji_core.http.auth import TokenVerifier

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_file = tmp_path / "signing.key"
    key_file.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    config = {
        "identity": {"issuer": "https://identity.fixture.invalid", "audience": "wuji-vnext-tests"},
        "owner": [OWNER[0], OWNER[1], OWNER[2]],
        "operator_subject": "control-fixture",
    }
    token = task_launch.mint_operator_token(config, key_file=str(key_file), ttl_seconds=300)
    if isinstance(token, bytes):
        token = token.decode()
    verifier = TokenVerifier(
        public_key_pem=key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ),
        issuer="https://identity.fixture.invalid",
        audience="wuji-vnext-tests",
    )
    principal = verifier.verify(token)
    assert principal.subject == "control-fixture"
    assert principal.tenant_id == OWNER[0]
    assert "operator" in principal.roles
    assert principal.token_id
    with pytest.raises(ValueError):
        task_launch.mint_operator_token(config, key_file=str(key_file), ttl_seconds=10)


def _deployment_auth_dir(tmp_path, *, window_seconds=1800, margin_seconds=900):
    """A deployment credential directory whose bearer covers the attempt."""

    import time as _time

    directory = tmp_path / "deployment-auth"
    directory.mkdir(parents=True, exist_ok=True)
    exp = int(_time.time()) + window_seconds + margin_seconds + 60
    (directory / "receiver.token").write_bytes(_bearer(exp).encode())
    return directory


def _bearer(exp, *, iat=None, sub="receiver"):
    import base64 as _b64

    def segment(value):
        raw = json.dumps(value, sort_keys=True).encode()
        return _b64.urlsafe_b64encode(raw).decode().rstrip("=")

    payload = {"sub": sub, "exp": exp}
    if iat is not None:
        payload["iat"] = iat
    return (segment({"alg": "RS256", "kid": "deployment-key"})
            + "." + segment(payload) + ".signature-not-read-here")


def test_run_phases_prepare_hands_the_command_real_connection_factories(
    monkeypatch, db_environment, audit_directory, tmp_path
):
    """The in-cluster path must pass factories, not one opened context manager."""

    with creation_case(db_environment, audit_directory) as case:
        created = create(case)
        assert created.status_code == 201, created.text
        task_id = created.json()["task_id"]
        owner = (OWNER[0], OWNER[1], task_id)

        with db_environment.migration_connection() as connection:
            definition, _ = stored_definition(connection, task_id)
            config = deployment_config(definition)
            register_tool_definition(connection, tenant_id=OWNER[0], definition=tool_document())
            seed_pools(connection, definition)

        live = []

        def _owner_connection(_config):
            """A live owner-role connection; ``run_phases`` closes it itself."""

            manager = db_environment.migration_connection()
            connection = manager.__enter__()
            live.append(manager)
            return connection

        monkeypatch.setattr(task_launch, "owner_connection", _owner_connection)
        monkeypatch.setattr(
            task_launch, "application_connection",
            lambda _config: db_environment.additional_app_connection(),
        )
        monkeypatch.setattr(
            task_launch, "operator_access",
            lambda _config, signing_key_file=None: AccessContext(
                Principal(
                    subject="control-fixture",
                    tenant_id=OWNER[0],
                    roles=frozenset({"operator"}),
                    token_id="task-launch-fixture",
                ),
                "task-launch",
            ),
        )

        binding, result = task_launch.run_phases(
            config,
            task_id=task_id,
            phases=["prepare"],
            options={
                "deployment_auth_dir": str(_deployment_auth_dir(tmp_path)),
                "agent_image": "registry.invalid/agent@sha256:" + "a" * 64,
                "kali_image": "registry.invalid/kali@sha256:" + "b" * 64,
                "runtime_origin": "https://runtime.wuji-vnext-test.svc:8443",
                "gate_url": "https://gates.wuji-vnext-test.svc:8443",
                "namespace": "wuji-vnext-test",
                "evidence_ref": "docs/vnext/evidence/P11/task-roundtrip-20260915/README.md",
            },
        )
        assert result["prepare"]["intent_ref"] is not None
        assert result["prepare"]["intent_status"] == "accepted_shared"
        assert binding["receiver_id"] == f"task-{task_id}-a1"
        assert binding["config_digest"] == result["prepare"]["definition_digest"]
        # E03: the profile identity is Task-scoped because its body now carries
        # this Task's own frozen context.
        for kind in ("reason", "explore", "report"):
            assert len(binding["profiles"]) == 3
            refs = [ref for ref, kinds in binding["profiles"].items() if kinds == [kind]]
            assert len(refs) == 1 and refs[0].startswith(f"harness.{kind}.task.")
        with db_environment.migration_connection() as connection:
            with connection.transaction():
                connection.execute(
                    "UPDATE vnext.task SET activated_at=now() WHERE task_id=%s", (task_id,)
                )
            assert connection.execute(
                "SELECT count(*) FROM vnext.session_capability WHERE tenant_id=%s",
                (OWNER[0],),
            ).fetchone() == (0,)
        assert owner == (OWNER[0], OWNER[1], task_id)


def test_attempt_material_binds_the_deployment_bearer_not_a_stale_task_secret(tmp_path):
    """The supervisor compares the controller bearer byte-for-byte."""

    deployment = tmp_path / "deployment"
    gates = tmp_path / "gates"
    agent = tmp_path / "agent"
    kali = tmp_path / "kali"
    for directory in (deployment, gates, agent, kali):
        directory.mkdir()
    (deployment / "receiver.token").write_bytes(b"current-receiver-bearer")
    (gates / "collector.token").write_bytes(b"current-collector-bearer")
    (agent / "receiver.token").write_bytes(b"stale-receiver-bearer")
    (kali / "collector.token").write_bytes(b"stale-collector-bearer")
    (agent / "tls.crt").write_bytes(b"agent-cert")
    (agent / "tls.key").write_bytes(b"agent-key")
    (kali / "tls.crt").write_bytes(b"kali-cert")
    (kali / "tls.key").write_bytes(b"kali-key")
    ca = tmp_path / "ca.crt"
    ca.write_bytes(b"ca")
    identity = tmp_path / "identity.pub"
    identity.write_bytes(b"identity")

    material = task_launch.requirement_material(
        {"ca_file": str(ca), "public_key_file": str(identity)},
        agent_auth_dir=str(agent), kali_auth_dir=str(kali),
        deployment_auth_dir=str(deployment), gates_auth_dir=str(gates),
    )
    assert material["receiver.token"] == b"current-receiver-bearer"
    assert material["collector.token"] == b"current-collector-bearer"
    assert material["task-agent.crt"] == b"agent-cert"
    assert material["task-kali.key"] == b"kali-key"
    assert material["ca.crt"] == b"ca"


def test_a_bearer_that_dies_inside_the_attempt_window_refuses_the_launch(tmp_path):
    """Attempt 2 dispatched its third Run 9 minutes after the bearer expired."""

    task_launch = _load_launch_module()
    token = tmp_path / "receiver.token"
    moment = 1_800_000_000
    margin = task_launch.RECEIVER_BEARER_MARGIN_SECONDS
    window = 1800

    # The exact live shape: mounted at 09:11, expires at 09:29, window 30 min.
    token.write_bytes(_bearer(moment + 18 * 60).encode())
    with pytest.raises(DomainError) as refused:
        task_launch.require_receiver_bearer_window(
            token, window_seconds=window, now=moment)
    assert refused.value.code == "receiver_bearer_expires_before_attempt_window"

    # Already expired is the same refusal, never a silent launch.
    token.write_bytes(_bearer(moment - 1).encode())
    with pytest.raises(DomainError) as expired:
        task_launch.require_receiver_bearer_window(
            token, window_seconds=window, now=moment)
    assert expired.value.code == "receiver_bearer_expires_before_attempt_window"

    # A bearer covering the window plus the fixed margin is accepted, and the
    # remaining lifetime is reported without exposing the token bytes.
    token.write_bytes(_bearer(moment + window + margin + 7, iat=moment).encode())
    assert task_launch.require_receiver_bearer_window(
        token, window_seconds=window, now=moment) == window + margin + 7

    # Unreadable material is refused as such instead of being treated as long-lived.
    token.write_bytes(b"not-a-registered-token")
    with pytest.raises(DomainError) as unreadable:
        task_launch.require_receiver_bearer_window(
            token, window_seconds=window, now=moment)
    assert unreadable.value.code == "receiver_bearer_unreadable"

    with pytest.raises(DomainError) as unbounded:
        task_launch.require_receiver_bearer_window(token, window_seconds=0, now=moment)
    assert unbounded.value.code == "INVALID_REFERENCE"


def test_operator_bearer_path_is_single_source(tmp_path):
    """A stale mounted file must never be used when the signing key is present."""

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_file = tmp_path / "signing.key"
    key_file.write_bytes(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()))
    stale = tmp_path / "operator.token"
    stale.write_text("stale-mounted-bearer")
    config = {
        "identity": {"issuer": "https://identity.fixture.invalid", "audience": "wuji-vnext-tests"},
        "owner": [OWNER[0], OWNER[1], OWNER[2]],
        "operator_subject": "control-fixture",
        "operator_token_file": str(stale),
    }
    assert task_launch.operator_token(config) == "stale-mounted-bearer"
    minted = task_launch.operator_token(config, signing_key_file=str(key_file))
    assert minted != "stale-mounted-bearer" and minted.count(".") == 2


EXECUTOR_TEMPLATE = {
    "binding": {
        "collector_subject": "collector",
        "gate_subject": "gate",
        "tenant_id": "tenant-fixture",
        "project_id": "project-fixture",
        "task_id": "task-old",
        "executor_ref": "kali-workspace-v1",
        "receiver_id": "receiver-old",
        "environment_ref": "environment-old",
    },
    "base_url": "https://task-kali.wuji-vnext-test.svc:8444",
    "gate_token_file": "/run/wuji/credentials/service.token",
    "collector_token_file": "/run/wuji/credentials/collector.token",
}


def executor_identity(task_id):
    return {
        "tenant_id": "tenant-fixture",
        "project_id": "project-fixture",
        "task_id": task_id,
        "executor_ref": "kali-workspace-v1",
        "receiver_id": "receiver-" + task_id,
        "environment_ref": "environment-" + task_id,
    }


def test_a_second_task_clones_the_deployment_executor_binding():
    """A new entry must not invent the deployment's published subjects."""

    executors = [{"binding": dict(EXECUTOR_TEMPLATE["binding"]), **{
        key: value for key, value in EXECUTOR_TEMPLATE.items() if key != "binding"
    }}]

    assert task_launch.merge_gates_executors(executors, executor_identity("task-new")) == "replaced"

    assert [entry["binding"]["task_id"] for entry in executors] == ["task-old", "task-new"]
    added = executors[1]
    assert added["binding"]["collector_subject"] == "collector"
    assert added["binding"]["gate_subject"] == "gate"
    assert added["base_url"] == EXECUTOR_TEMPLATE["base_url"]
    assert task_launch.merge_gates_executors(executors, executor_identity("task-new")) == "unchanged"


def test_a_task_that_lost_a_deployment_binding_field_is_repaired():
    """The published subjects come from the deployment's own entries."""

    executors = [
        {"binding": dict(EXECUTOR_TEMPLATE["binding"]), **{
            key: value for key, value in EXECUTOR_TEMPLATE.items() if key != "binding"
        }},
        {"binding": executor_identity("task-new"), "base_url": "https://task-kali.wuji-vnext-test.svc:8444",
         "gate_token_file": "/run/wuji/credentials/service.token",
         "collector_token_file": "/run/wuji/credentials/collector.token"},
    ]

    assert task_launch.merge_gates_executors(executors, executor_identity("task-new")) == "replaced"

    repaired = executors[1]["binding"]
    assert repaired["collector_subject"] == "collector"
    assert repaired["gate_subject"] == "gate"
    assert repaired["environment_ref"] == "environment-task-new"


def test_executor_entries_that_disagree_on_a_deployment_field_are_refused():
    executors = [
        {"binding": dict(EXECUTOR_TEMPLATE["binding"])},
        {"binding": {**EXECUTOR_TEMPLATE["binding"], "task_id": "task-other",
                     "collector_subject": "other-collector"}},
    ]

    with pytest.raises(DomainError, match="INPUT_DIGEST_CONFLICT"):
        task_launch.merge_gates_executors(executors, executor_identity("task-new"))


def admission_limits(connection, owner, *, max_elapsed_seconds: int) -> None:
    connection.execute(
        "INSERT INTO vnext.admission_config(tenant_id,project_id,task_id,document_json)"
        " VALUES(%s,%s,%s,%s)",
        (*owner, json.dumps({"runtime": {"limits": {"max_elapsed_seconds": max_elapsed_seconds}}})),
    )


def test_roll_moves_an_expired_attempt_and_refuses_a_runnable_one(
    db_environment, audit_directory
):
    """A failed launch cannot be retried in place; the roll is explicit."""

    with creation_case(db_environment, audit_directory) as case:
        created = create(case)
        assert created.status_code == 201, created.text
        task_id = created.json()["task_id"]
        owner = (OWNER[0], OWNER[1], task_id)
        with db_environment.migration_connection() as connection:
            definition, _ = stored_definition(connection, task_id)
            config = deployment_config(definition)
            task_launch.finalise_definition(connection, owner=owner, config=config)
            admission_limits(connection, owner, max_elapsed_seconds=1800)

            with pytest.raises(DomainError) as inactive:
                task_launch.roll_runtime_attempt(
                    connection, owner=owner, config=config, reason="fixture"
                )
            assert inactive.value.code == "attempt_not_activated"

            connection.execute(
                "UPDATE vnext.task SET activated_at=now(),desired_state='run',"
                " observed_state='running' WHERE task_id=%s",
                (task_id,),
            )
            with pytest.raises(DomainError) as live:
                task_launch.roll_runtime_attempt(
                    connection, owner=owner, config=config, reason="fixture"
                )
            assert live.value.code == "current_attempt_still_running"

            # The window is activated_at + the published limit; once it closes the
            # attempt can never run again, so the roll is the only way forward.
            connection.execute(
                "UPDATE vnext.task SET activated_at=now()-interval '2 hours'"
                " WHERE task_id=%s",
                (task_id,),
            )
            rolled = task_launch.roll_runtime_attempt(
                connection, owner=owner, config=config, reason="window closed"
            )
            assert rolled == {
                "previous_runtime_attempt": 1,
                "runtime_attempt": 2,
                "reason": "window closed",
            }
            row = connection.execute(
                "SELECT runtime_attempt,activated_at,desired_state,observed_state,"
                " execution_allowed,control_version,event_seq FROM vnext.task"
                " WHERE task_id=%s",
                (task_id,),
            ).fetchone()
            assert row[0] == 2
            assert row[1] is None
            assert (row[2], row[3], row[4]) == ("pause", "ready", True)
            assert int(row[5]) == 2
            events = connection.execute(
                "SELECT payload_json FROM vnext.outbox WHERE task_id=%s"
                " AND kind='task.attempt_rolled'",
                (task_id,),
            ).fetchall()
            assert json.loads(events[0][0]) == {
                "previous_runtime_attempt": "1",
                "reason": "window closed",
                "runtime_attempt": "2",
            }

            # A rolled Task is un-started again: another roll has nothing to move.
            with pytest.raises(DomainError) as unstarted:
                task_launch.roll_runtime_attempt(
                    connection, owner=owner, config=config, reason="again"
                )
            assert unstarted.value.code == "attempt_not_activated"

            # A registered receiver of the live attempt blocks the roll, so a Pod
            # that the runtime has not stopped is never replaced.
            connection.execute(
                "UPDATE vnext.task SET activated_at=now()-interval '2 hours'"
                " WHERE task_id=%s",
                (task_id,),
            )
            connection.execute(
                """INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject) 
                VALUES(%s,%s,%s,'receiver')""",
                owner,
            )
            connection.execute(
                """INSERT INTO vnext.scheduler_identity_template(tenant_id,project_id,
                task_id,template_ref,issuer,audience,signing_key_ref,signing_kid,
                encryption_key_ref,clearance,enabled)
                VALUES(%s,%s,%s,'deployment-worker-v1','https://identity.fixture.invalid',
                'wuji-vnext-deployment','deployment-key','kid','encryption-key',1,true)""",
                owner,
            )
            connection.execute(
                """INSERT INTO vnext.scheduler_receiver(tenant_id,project_id,task_id,
                runtime_attempt,receiver_id,environment_ref,model_mode,receiver_subject,
                credential_template_ref,harness_profiles_json,pod_uid,enabled)
                VALUES(%s,%s,%s,2,'receiver-a2','environment-a2','synthetic','receiver',
                'deployment-worker-v1','{}','pod-uid-a2',true)""",
                owner,
            )
            with pytest.raises(DomainError) as registered:
                task_launch.roll_runtime_attempt(
                    connection, owner=owner, config=config, reason="fixture"
                )
            assert registered.value.code == "attempt_receiver_still_enabled"


def test_a_rolled_task_supersedes_its_fixed_executor_binding(
    db_environment, audit_directory
):
    """The fixed executor row names the attempt, so a roll must replace it."""

    with creation_case(db_environment, audit_directory) as case:
        created = create(case)
        assert created.status_code == 201, created.text
        task_id = created.json()["task_id"]
        owner = (OWNER[0], OWNER[1], task_id)
        with db_environment.migration_connection() as connection:
            definition, _ = stored_definition(connection, task_id)
            config = deployment_config(definition)
            register_tool_definition(connection, tenant_id=OWNER[0], definition=tool_document())
            admission_limits(connection, owner, max_elapsed_seconds=1800)

            def executor_for(attempt, *, receiver=None, environment=None):
                document = dict(config["executor"])
                document["receiver_id"] = receiver or f"task-{task_id}-a{attempt}"
                document["environment_ref"] = environment or f"pod-environment-{task_id}-a{attempt}"
                return document

            task_launch.register_executor(connection, owner=owner, executor=executor_for(1))

            # Without a roll the fixed registration still refuses a change.
            with pytest.raises(DomainError) as conflict:
                task_launch.register_executor(connection, owner=owner, executor=executor_for(2))
            assert conflict.value.code == "INPUT_DIGEST_CONFLICT"

            # The rolled Task names attempt 2, but the previous attempt still has
            # an enabled receiver, so the supersede is refused there too.
            connection.execute(
                "UPDATE vnext.task SET runtime_attempt=2,activated_at=NULL,"
                " desired_state='pause',observed_state='ready' WHERE task_id=%s",
                (task_id,),
            )
            connection.execute(
                "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject)"
                " VALUES(%s,%s,%s,'receiver')",
                owner,
            )
            connection.execute(
                """INSERT INTO vnext.scheduler_identity_template(tenant_id,project_id,
                task_id,template_ref,issuer,audience,signing_key_ref,signing_kid,
                encryption_key_ref,clearance,enabled)
                VALUES(%s,%s,%s,'deployment-worker-v1','https://identity.fixture.invalid',
                'wuji-vnext-deployment','deployment-key','kid','encryption-key',1,true)""",
                owner,
            )
            connection.execute(
                """INSERT INTO vnext.scheduler_receiver(tenant_id,project_id,task_id,
                runtime_attempt,receiver_id,environment_ref,model_mode,receiver_subject,
                credential_template_ref,harness_profiles_json,pod_uid,enabled)
                VALUES(%s,%s,%s,1,'receiver-a1','environment-a1','synthetic','receiver',
                'deployment-worker-v1','{}','pod-uid-a1',true)""",
                owner,
            )
            with pytest.raises(DomainError) as live:
                task_launch.supersede_rolled_executor(
                    connection, owner=owner, executor=executor_for(2)
                )
            assert live.value.code == "attempt_receiver_still_enabled"

            # Once that attempt is stopped the row moves to the current attempt.
            connection.execute(
                "UPDATE vnext.scheduler_receiver SET enabled=false WHERE task_id=%s",
                (task_id,),
            )
            superseded = task_launch.supersede_rolled_executor(
                connection, owner=owner, executor=executor_for(2)
            )
            assert superseded == {
                "previous_runtime_attempt": 1,
                "runtime_attempt": 2,
                "ref": "kali-workspace-v1",
            }
            stored = json.loads(
                connection.execute(
                    "SELECT document_json FROM vnext.executor_registration"
                    " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND ref=%s",
                    (*owner, "kali-workspace-v1"),
                ).fetchone()[0]
            )
            assert stored["receiver_id"] == f"task-{task_id}-a2"
            assert stored["environment_ref"] == f"pod-environment-{task_id}-a2"
            # Registering it again is now a no-op rather than a conflict.
            task_launch.register_executor(connection, owner=owner, executor=executor_for(2))


def test_a_followup_intent_is_bounded_before_it_touches_storage():
    """The owner command refuses a malformed follow-up question or client ref."""

    with pytest.raises(DomainError) as blank:
        task_launch.admit_followup_intent(
            None, access=None, task="task-fixture", question="",
            client_ref="followup", idempotency_key="k",
        )
    assert blank.value.code == "INVALID_SCHEMA"
    with pytest.raises(DomainError) as long:
        task_launch.admit_followup_intent(
            None, access=None, task="task-fixture", question="x" * 2049,
            client_ref="followup", idempotency_key="k",
        )
    assert long.value.code == "INVALID_SCHEMA"
    with pytest.raises(DomainError) as empty_ref:
        task_launch.admit_followup_intent(
            None, access=None, task="task-fixture", question="read again",
            client_ref="---", idempotency_key="k",
        )
    assert empty_ref.value.code == "INVALID_REFERENCE"


def test_each_task_publishes_its_own_service_pair():
    """Two live Task Pods cannot share one Service name."""

    first = task_launch.task_service_names("2abfdd57-7a0f-4cba-8ce4-2a57f751d0b0")
    second = task_launch.task_service_names("083f6134-46bd-4237-9cdc-0c88a39da3d0")

    assert first == {"agent": "task-agent-2abfdd577a0f", "kali": "task-kali-2abfdd577a0f"}
    assert second == {"agent": "task-agent-083f613446bd", "kali": "task-kali-083f613446bd"}
    for name in (*first.values(), *second.values()):
        assert len(name) <= 63
        assert name.islower()
        assert all(character.isalnum() or character == "-" for character in name)
    with pytest.raises(DomainError):
        task_launch.task_service_names("---")


def test_the_started_task_points_its_own_executor_at_its_own_kali_service():
    """The gates host must reach this Task's kali Pod, not the last launched one."""

    executors = [{"binding": dict(EXECUTOR_TEMPLATE["binding"]), **{
        key: value for key, value in EXECUTOR_TEMPLATE.items() if key != "binding"
    }}]

    action = task_launch.merge_gates_executors(
        executors,
        executor_identity("task-new"),
        base_url="https://task-kali-0123456789ab.wuji-vnext-test.svc:8444",
    )

    assert action == "replaced"
    assert executors[1]["base_url"] == "https://task-kali-0123456789ab.wuji-vnext-test.svc:8444"
    # The deployment's own entry is untouched, and a repeat is idempotent.
    assert executors[0]["base_url"] == EXECUTOR_TEMPLATE["base_url"]
    assert task_launch.merge_gates_executors(
        executors,
        executor_identity("task-new"),
        base_url="https://task-kali-0123456789ab.wuji-vnext-test.svc:8444",
    ) == "unchanged"


HTTP_TOOL_REF = "http-target-v1"


def http_tool_document(ref=HTTP_TOOL_REF, executor_ref="kali-http-v1") -> dict:
    return {
        "ref": ref,
        "revision": "1",
        "name": "http_target_get",
        "published_at": PUBLISHED_AT.isoformat().replace("+00:00", "Z"),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["url", "method"],
            "properties": {
                "url": {"type": "string", "minLength": 1, "maxLength": 4096},
                "method": {"type": "string", "enum": ["GET", "HEAD", "OPTIONS"]},
            },
        },
        "allowed_target_kinds": ["http_target"],
        "executor_ref": executor_ref,
        "approval_required": False,
    }


def role_profiles(refs_by_kind) -> dict:
    lock = "a" * 64
    return {
        kind: {
            "body": {
                "ref": f"harness.{kind}.deployment.v2",
                "revision": "1",
                "work_kind": kind,
                "instructions": "read",
                "lock_digest": lock,
                "max_context_records": 8,
                "max_context_bytes": 4096,
                "max_output_tokens": 512,
                "tool_definition_refs": list(refs),
            }
        }
        for kind, refs in refs_by_kind.items()
    }


def bearer_token(exp) -> str:
    import base64 as _base64

    def part(value: dict) -> str:
        return _base64.urlsafe_b64encode(
            json.dumps(value, sort_keys=True).encode()
        ).decode().rstrip("=")

    return part({"alg": "RS256", "kid": "deployment-key"}) + "." + part(
        {"sub": "receiver", "exp": exp}
    ) + ".signature"


def write_bearer(directory: Path, *, seconds: int) -> Path:
    from datetime import timedelta

    path = Path(directory) / "receiver.token"
    path.write_bytes(
        bearer_token(int((datetime.now(timezone.utc) + timedelta(seconds=seconds)).timestamp())).encode()
    )
    return path


def test_e01_real_mode_is_trusted_deployment_configuration(db_environment, audit_directory):
    """E01: the mode comes from the deployment document and freezes with the Task."""

    with creation_case(db_environment, audit_directory) as case:
        created = create(case)
        assert created.status_code == 201, created.text
        task_id = created.json()["task_id"]
        owner = (OWNER[0], OWNER[1], task_id)

        with db_environment.migration_connection() as connection:
            definition, _ = stored_definition(connection, task_id)
            register_tool_definition(connection, tenant_id=OWNER[0], definition=tool_document())
            seed_pools(connection, definition)

            real = deployment_config(definition)
            real["evaluation_mode"] = "real_model"
            prepared = task_launch.finalise_definition(connection, owner=owner, config=real)
            stored, digest = stored_definition(connection, task_id)
            assert digest == prepared["definition_digest"]
            assert stored["evaluation_mode"] == "real_model"
            # Real mode is Reason-first: no fixture seed is written or admitted.
            assert "seed_intent" not in stored
            assert task_launch.initial_intent_document(real, stored) is None

            # The frozen mode is not replayed as a mechanism Task.
            with pytest.raises(DomainError) as frozen:
                task_launch.finalise_definition(
                    connection, owner=owner, config=deployment_config(definition)
                )
            assert frozen.value.code == "INVALID_STATE"

            # An unknown mode never reaches the Task definition.
            unknown = deployment_config(definition)
            unknown["evaluation_mode"] = "best_effort"
            with pytest.raises(DomainError) as invalid:
                task_launch.finalise_definition(connection, owner=owner, config=unknown)
            assert invalid.value.code == "INVALID_STATE"
            after, _ = stored_definition(connection, task_id)
            assert after["evaluation_mode"] == "real_model"

            # Repeating the same real prepare stays idempotent.
            again = task_launch.finalise_definition(connection, owner=owner, config=real)
            assert again["definition_changed"] is False
            assert again["definition_digest"] == prepared["definition_digest"]


def test_e01_real_mode_admits_only_an_explicitly_published_seed(
    db_environment, audit_directory
):
    """E01: a real Task never falls back to ``workspace:version.txt``."""

    with creation_case(db_environment, audit_directory) as case:
        created = create(case)
        assert created.status_code == 201, created.text
        task_id = created.json()["task_id"]
        owner = (OWNER[0], OWNER[1], task_id)

        with db_environment.migration_connection() as connection:
            definition, _ = stored_definition(connection, task_id)
            register_tool_definition(connection, tenant_id=OWNER[0], definition=tool_document())
            seed_pools(connection, definition)

            config = deployment_config(definition)
            config["evaluation_mode"] = "real_model"
            config["seed_intent"] = {
                "client_ref": "seed-entry",
                "question": "Read the published entry point once and cite it.",
            }
            prepared = task_launch.finalise_definition(connection, owner=owner, config=config)
            stored, _ = stored_definition(connection, task_id)
            assert stored["seed_intent"] == {
                "client_ref": "seed-entry",
                "question": "Read the published entry point once and cite it.",
                "expected_output": "wuji.agent-payload.v2",
            }
            document = task_launch.initial_intent_document(config, stored)
            assert document == stored["seed_intent"]
            assert "version.txt" not in document["question"]

            # An unusable seed is refused before the definition is written.
            broken = deployment_config(definition)
            broken["evaluation_mode"] = "real_model"
            broken["seed_intent"] = {"client_ref": "", "question": "x"}
            with pytest.raises(DomainError) as invalid:
                task_launch.finalise_definition(connection, owner=owner, config=broken)
            assert invalid.value.code == "INVALID_SCHEMA"


def test_e02_role_tool_refs_scope_target_tools_to_explore():
    """E02: the published role profile and the Task allowlist both have to agree."""

    task_launch = _load_launch_module()
    definition = {"runtime_profile": {"allowed_tool_refs": [TOOL_REF, HTTP_TOOL_REF]}}
    profiles = role_profiles(
        {
            "reason": [TOOL_REF, HTTP_TOOL_REF],
            "explore": [TOOL_REF, HTTP_TOOL_REF],
            "report": [TOOL_REF],
        }
    )
    config = {
        "evaluation_mode": "real_model",
        "definition": {"worker_profiles": profiles},
        "tools": [tool_document(), http_tool_document()],
    }

    assert task_launch.role_tool_refs(config, definition, "reason") == (TOOL_REF,)
    assert task_launch.role_tool_refs(config, definition, "explore") == (
        TOOL_REF,
        HTTP_TOOL_REF,
    )
    assert task_launch.role_tool_refs(config, definition, "report") == (TOOL_REF,)

    # The Task's own runtime profile is the ceiling: a deployment profile never
    # widens a Task beyond what its creation entry allowed.
    narrow = {"runtime_profile": {"allowed_tool_refs": [TOOL_REF]}}
    assert task_launch.role_tool_refs(config, narrow, "explore") == (TOOL_REF,)

    # Publishing a target tool is not a permission: while no role profile names
    # it, every role stays on the workspace read it was published with.
    unpublished = role_profiles(
        {"reason": [TOOL_REF], "explore": [TOOL_REF], "report": [TOOL_REF]}
    )
    catalog = {**config, "definition": {"worker_profiles": unpublished}}
    for kind in ("reason", "explore", "report"):
        assert task_launch.role_tool_refs(catalog, definition, kind) == (TOOL_REF,)

    # A role left with only a target tool fails instead of silently widening.
    target_only = role_profiles(
        {"reason": [HTTP_TOOL_REF], "explore": [TOOL_REF], "report": [TOOL_REF]}
    )
    with pytest.raises(DomainError) as error:
        task_launch.role_tool_refs(
            {**config, "definition": {"worker_profiles": target_only}},
            definition,
            "reason",
        )
    assert error.value.code == "CAPABILITY_UNAVAILABLE"


def test_e01_preflight_reports_declared_state_without_a_target_action(
    db_environment, audit_directory, tmp_path
):
    """E01: preflight is a local/platform read, so it can refuse before activation."""

    with creation_case(db_environment, audit_directory) as case:
        created = create(case)
        assert created.status_code == 201, created.text
        task_id = created.json()["task_id"]

        with db_environment.migration_connection() as connection:
            config, owner, prepared, published, _ = prepared_task(
                case, task_id, connection
            )
        write_bearer(tmp_path, seconds=7200)
        options = {
            "deployment_auth_dir": str(tmp_path),
            "base_url": "https://runtime.wuji-vnext-test.svc:8443",
        }

        with db_environment.migration_connection() as reader:
            report = task_launch.preflight(
                config, task_id=task_id, options=options, connection=reader
            )
            assert report["checks"], "preflight reported nothing"
        assert report["evaluation_mode"] == "mechanism_synthetic"
        assert report["blocked"] == [], report["checks"]
        by_name = {entry["check"]: entry for entry in report["checks"]}
        assert by_name["mode_binding"]["state"] == "ok"
        assert by_name["tool:" + TOOL_REF]["state"] == "ok"
        assert by_name["receiver_bearer"]["state"] == "ok"
        assert by_name["stop_entry"]["state"] == "ok"

        # An expired authorization is a real block, reported before activation.
        with db_environment.migration_connection() as connection:
            definition, _ = stored_definition(connection, task_id)
        expired = json.loads(json.dumps(definition))
        expired["task"]["authorization_expires_at"] = "2020-01-01T00:00:00Z"
        with db_environment.migration_connection() as connection:
            raw = canonical_json_bytes(expired).decode()
            connection.execute(
                "UPDATE vnext.task SET definition_json=%s, definition_digest=%s"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                (raw, sha256(raw.encode()).hexdigest(), OWNER[0], OWNER[1], task_id),
            )
        with db_environment.migration_connection() as reader:
            blocked = task_launch.preflight(
                config, task_id=task_id, options=options, connection=reader
            )
        assert "authorization_scope" in blocked["blocked"]

        # A short bearer cannot authorize the declared attempt window.
        write_bearer(tmp_path, seconds=60)
        with db_environment.migration_connection() as reader:
            short = task_launch.preflight(
                config, task_id=task_id, options=options, connection=reader
            )
        assert "receiver_bearer" in short["blocked"]


def test_e03_the_model_instructions_carry_the_frozen_task_context(
    db_environment, audit_directory
):
    """E03: Goal, scope, limits and role duty reach the published profile."""

    with creation_case(db_environment, audit_directory) as case:
        created = create(case)
        assert created.status_code == 201, created.text
        task_id = created.json()["task_id"]
        owner = (OWNER[0], OWNER[1], task_id)

        with db_environment.migration_connection() as connection:
            definition, _ = stored_definition(connection, task_id)
            register_tool_definition(connection, tenant_id=OWNER[0], definition=tool_document())
            seed_pools(connection, definition)
            config = deployment_config(definition)
            prepared = task_launch.finalise_definition(connection, owner=owner, config=config)
            stored, _ = stored_definition(connection, task_id)

            goal_text = stored["task"]["goal"]["text"]
            instructions = {
                kind: stored["worker_profiles"][kind]["body"]["instructions"]
                for kind in ("reason", "explore", "report")
            }
            for kind, text in instructions.items():
                assert goal_text in text, kind
                assert "authorized scope: https://fixture.invalid:443" in text, kind
                assert "amount budget: 5 USD" in text, kind
                assert "hard limits: work items 4" in text, kind
                assert "your duty as " + kind in text, kind
                assert "mark anything you did not actually read as unread" in text
            # The role duty is the only part that differs between roles.
            assert "never perform a target action" in instructions["reason"]
            assert "never claim a result you did not receive" in instructions["explore"]

            # The same Task re-renders the same identity and body.
            assert prepared["definition"]["worker_profiles"] == stored["worker_profiles"]
            again = task_launch.finalise_definition(connection, owner=owner, config=config)
            assert again["definition_changed"] is False
            assert again["definition_digest"] == prepared["definition_digest"]

            # A different Goal is a different model input under the same tools.
            other = json.loads(json.dumps(stored))
            other["task"]["goal"]["text"] = "Explain a different frozen goal."
            other.pop("worker_profiles")
            other.pop("evaluation_mode")
            rendered = task_launch.published_session_profiles(config, other)
            assert goal_text not in rendered["reason"]["body"]["instructions"]
            assert "Explain a different frozen goal." in rendered["reason"]["body"]["instructions"]
            assert rendered["reason"]["ref"] != stored["worker_profiles"]["reason"]["ref"]
            assert rendered["reason"]["body"]["tool_definition_refs"] == (
                stored["worker_profiles"]["reason"]["body"]["tool_definition_refs"]
            )


def test_e03_the_harness_receives_the_composed_instructions(monkeypatch):
    """E03: the composed Task context is what the released Harness is built with.

    ``build_agent`` passes the published profile straight into the MAF
    Harness' ``agent_instructions``; this captures that argument without
    contacting any model.
    """

    from wuji_maf_worker import factory as worker_factory

    captured = {}

    def fake_create_harness_agent(client, **kwargs):
        captured["client"] = client
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        worker_factory, "create_harness_agent", fake_create_harness_agent
    )
    instructions = (
        "published role instruction\n\n"
        "Frozen Task context (published before activation, never editable later):\n"
        "goal: explain the frozen materials"
    )
    profile = HarnessProfile(
        ref="harness.explore.task.deadbeefdeadbeef",
        revision="1",
        work_kind="explore",
        instructions=instructions,
        tool_definition_refs=(TOOL_REF,),
        lock_digest=task_launch.shipped_worker_lock_digest(),
        max_context_records=8,
        max_context_bytes=4096,
        max_output_tokens=512,
    )
    resolved = {
        "limits": {
            "max_model_requests": 2, "max_tool_calls": 2, "max_elapsed_seconds": 60,
            "max_single_output_bytes": 4096, "max_total_output_bytes": 8192,
        },
        "client_model": "fixture-model",
    }
    agent, native = worker_factory.build_agent(
        resolved=resolved, profile=profile, model_http=None,
        model_gate_url="https://gates.invalid", run_credential="run-token",
        tools=[{"name": "read_workspace"}], middleware=[], response_parser=None,
    )
    assert agent is not None and native is not None
    assert captured["agent_instructions"] == instructions
    assert captured["disable_todo"] is True
    assert captured["disable_tool_auto_approval"] is True


def test_e06_published_materials_seed_the_workspace_without_shell_interpretation():
    """E06: a case's closed materials are written by the initializer, not the Agent."""

    task_launch = _load_launch_module()
    materials = task_launch.deployment_materials(
        {
            "materials": [
                {"path": "materials/entry.json", "text": '{"pointer": "materials/a.json"}'},
                {"path": "top.txt", "text": "line one\nline two"},
            ]
        }
    )
    assert [item["path"] for item in materials] == ["materials/entry.json", "top.txt"]
    command = task_launch.workspace_seed_command(materials)
    assert command.startswith("umask 077")
    assert "mkdir -p /workspace/materials" in command
    assert "base64 -d" in command
    # Material text never reaches the shell as literal characters.
    assert "pointer" not in command and "line two" not in command
    for item in materials:
        import base64 as _base64

        encoded = _base64.b64encode(item["text"].encode("utf-8")).decode("ascii")
        assert encoded in command

    # Without published materials the original fixture file is unchanged.
    assert "version.txt" in task_launch.workspace_seed_command(())

    for broken in (
        {"path": "../escape", "text": "x"},
        {"path": "/absolute", "text": "x"},
        {"path": "a", "text": ""},
        {"path": "a", "text": "x" * 4097},
        {"path": "a", "text": "x", "extra": "y"},
        {"path": "a", "text": "x\x00y"},
    ):
        with pytest.raises(DomainError) as error:
            task_launch.deployment_materials({"materials": [broken]})
        assert error.value.code == "INVALID_SCHEMA"

    with pytest.raises(DomainError):
        task_launch.deployment_materials(
            {"materials": [{"path": "a", "text": "x"}] * 17}
        )


def test_a_published_session_profile_is_identified_by_its_whole_body(
    db_environment, audit_directory
):
    """Two Tasks must never share one profile key with different bodies."""

    with creation_case(db_environment, audit_directory) as case:
        created = create(case)
        assert created.status_code == 201, created.text
        task_id = created.json()["task_id"]
        with db_environment.migration_connection() as connection:
            definition, _ = stored_definition(connection, task_id)
        config = deployment_config(definition)
        base = task_launch.published_session_profiles(config, definition)
        assert task_launch.published_session_profiles(config, definition) == base

        raised = json.loads(json.dumps(definition))
        raised["runtime_profile"]["limits"] = {
            **raised["runtime_profile"]["limits"],
            "max_single_output_bytes": raised["runtime_profile"]["limits"][
                "max_single_output_bytes"
            ] * 2,
        }
        wider = task_launch.published_session_profiles(config, raised)
        for kind, snapshot in base.items():
            assert wider[kind]["ref"] != snapshot["ref"]
            assert (
                wider[kind]["body"]["session_limits"]["max_object_bytes"]
                != snapshot["body"]["session_limits"]["max_object_bytes"]
            )
            # The instructions are unchanged: only the published bounds moved.
            assert (
                wider[kind]["body"]["instructions"]
                == snapshot["body"]["instructions"]
            )


def test_e01_a_stale_worker_lock_is_named_and_relock_publishes_a_new_revision(
    db_environment, audit_directory, tmp_path
):
    """E01: a rebuild that changes the worker lock is caught before activation."""

    from wuji_core.admission.registry import register_published_profile

    with creation_case(db_environment, audit_directory) as case:
        with db_environment.migration_connection() as connection:
            stale = runtime_profile().model_dump(mode="json")
            stale["revision"] = "2"
            stale["lock_digest"] = "c" * 64
            register_published_profile(
                connection, tenant_id=OWNER[0], kind="runtime", document=stale
            )
        created = create(case)
        assert created.status_code == 201, created.text
        task_id = created.json()["task_id"]
        owner = (OWNER[0], OWNER[1], task_id)

        with db_environment.migration_connection() as connection:
            definition, _ = stored_definition(connection, task_id)
            assert definition["runtime_profile"]["lock_digest"] == "c" * 64
            register_tool_definition(connection, tenant_id=OWNER[0], definition=tool_document())
            seed_pools(connection, definition)
            config = deployment_config(definition)
            write_bearer(tmp_path, seconds=7200)
            report = task_launch.preflight(
                config, task_id=task_id,
                options={"deployment_auth_dir": str(tmp_path),
                         "base_url": "https://runtime.invalid"},
                connection=connection,
            )
            assert "worker_lock" in report["blocked"], report["checks"]

            declared = runtime_profile().model_dump(mode="json")
            declared.pop("lock_digest")
            relocked = task_launch.republish_runtime_profile(
                connection,
                owner=owner,
                config={"admission": {"runtime": declared}},
            )
            assert relocked["changed"] is True
            assert relocked["previous_revision"] == "2"
            assert relocked["revision"] == "3"
            assert relocked["lock_digest"] == task_launch.shipped_worker_lock_digest()

            # Repeating the owner action is idempotent and never rewrites a row.
            again = task_launch.republish_runtime_profile(
                connection,
                owner=owner,
                config={"admission": {"runtime": declared}},
            )
            assert again["changed"] is False and again["revision"] == "3"

            # A declaration whose limits changed is published as the next
            # revision of the same ref, and only then.
            raised = json.loads(json.dumps(declared))
            raised["limits"] = {**raised["limits"], "max_work_items": raised["limits"]["max_work_items"] + 4}
            changed = task_launch.republish_runtime_profile(
                connection,
                owner=owner,
                config={"admission": {"runtime": raised}},
            )
            assert changed["changed"] is True
            assert changed["previous_revision"] == "3"
            assert changed["revision"] == "4"
            assert task_launch.republish_runtime_profile(
                connection,
                owner=owner,
                config={"admission": {"runtime": raised}},
            )["changed"] is False

            # A ref the deployment never published starts at its declared revision.
            fresh = json.loads(json.dumps(declared))
            fresh["ref"] = "k8s-runtime-trial-v1"
            first = task_launch.republish_runtime_profile(
                connection,
                owner=owner,
                config={"admission": {"runtime": fresh}},
            )
            assert (first["changed"], first["previous_revision"], first["revision"]) == (True, None, "1")

            # The Task that froze the stale revision must be recreated: its
            # definition is immutable, so preflight keeps naming the mismatch.
            still = task_launch.preflight(
                config, task_id=task_id,
                options={"deployment_auth_dir": str(tmp_path),
                         "base_url": "https://runtime.invalid"},
                connection=connection,
            )
            assert "worker_lock" in still["blocked"]


def test_the_shared_runtime_host_never_serves_two_worker_locks():
    """A host serves one lock: other-lock profiles are retired, not merged."""

    task_launch = _load_launch_module()

    def profile(ref, lock):
        return {"ref": ref, "revision": "1", "body": {"lock_digest": lock}}

    document = [profile("old-a", "a" * 64), profile("old-b", "a" * 64)]
    current = {
        kind: profile(f"harness.{kind}.task.x", "b" * 64)
        for kind in ("reason", "explore", "report")
    }
    action = task_launch.replace_runtime_profiles(document, current)
    assert action == "replaced"
    assert {item["ref"] for item in document} == {
        "harness.reason.task.x", "harness.explore.task.x", "harness.report.task.x",
    }

    # Nothing to add and nothing to retire is reported as unchanged.
    assert task_launch.replace_runtime_profiles(document, current) == "unchanged"

    # Retiring an old-lock entry alone is reported, and it is the only change.
    document.append(profile("old-c", "a" * 64))
    assert task_launch.replace_runtime_profiles(document, current) == "pruned:1"
    assert all(item["ref"] != "old-c" for item in document)

    # Same key, different bytes is a real conflict, never a silent replacement.
    conflicting = dict(current)
    conflicting["explore"] = profile("harness.explore.task.x", "c" * 64)
    with pytest.raises(DomainError) as error:
        task_launch.replace_runtime_profiles(document, conflicting)
    assert error.value.code == "INPUT_DIGEST_CONFLICT"
