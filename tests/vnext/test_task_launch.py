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
            ref=f"harness.{kind}.deployment.v1",
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
        definition_lines=prepared["definition"],
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
    db_environment, audit_directory
):
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
        assert set(binding["profiles"]) == {
            "harness.reason.deployment.v1",
            "harness.explore.deployment.v1",
            "harness.report.deployment.v1",
        }
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
