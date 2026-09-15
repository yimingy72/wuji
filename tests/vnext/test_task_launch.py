"""P11-C: the owner launch command finalises a created Task and publishes capability."""

from __future__ import annotations

from datetime import datetime, timezone
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
        definition=prepared["definition"], attempt=prepared["runtime_attempt"])
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
            with pytest.raises(DomainError) as activated:
                task_launch.finalise_definition(connection, owner=owner, config=config)
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
