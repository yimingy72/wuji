"""Owner command that takes a product-created Task to a real worker round trip.

Order is fixed and every step is idempotent:

1. ``prepare``    finalise the Task definition with the deployment-published
                  worker profiles *before* the first activation, publish the
                  admission config, register the attempt executor, and admit the
                  initial Intent through the public domain service.
2. ``activate``   send ``start`` through the product command endpoint.
3. ``wire``       render and apply this attempt's Task-owned resources, re-point
                  the fixed Task Services, refresh the runtime/gates Task
                  bindings, roll those two deployments, then wait for the runtime
                  to report a ready Task Pod.
4. ``capability`` publish the tenant session capability bound to the observed
                  Pod UID so the supervisor can build a Session.

The command never creates the Pod itself (the runtime controller owns it), never
writes Facts, Runs, results or completion state, and never invents a Pod UID or
a process exit. A missing or conflicting prerequisite aborts the step instead of
repairing it silently.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from functools import partial
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import time

import httpx
import psycopg

from wuji_core.admission.registry import (
    TaskAdmissionConfig,
    configuration_digest,
    model_gateway_digest,
    publish_task_admission,
    register_executor,
    register_session_capability,
    session_client_snapshot,
)
from wuji_core.blackboard.claims import ClaimService
from wuji_core.contracts.sessions import SessionLimits
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.http.auth import TokenVerifier
from wuji_core.persistence.uow import AccessContext, DomainError, UnitOfWork
from wuji_maf_worker.factory import SessionHarnessProfile


SCHEMA_VERSION = "wuji.task-launch.v1"


def k8s_client():
    """Imported lazily: the domain phases never need the Kubernetes client."""

    from kubernetes import client

    return client
FRAMEWORK_SNAPSHOT = {
    "python": "3.13.15",
    "agent_framework_core": "1.18.0",
    "agent_framework_openai": "1.14.3",
}
GRANT_CATALOG = {
    "scheduler": ("can_read", "can_admit"),
    "receiver": ("can_read", "can_settle", "can_observe", "can_admit"),
    "pod-controller": ("can_read", "can_control", "can_observe", "can_admit"),
    "collector": ("can_read", "can_capture", "can_settle"),
    "gate": ("can_read",),
}
SERVICE_NAMES = {"agent": "task-agent", "kali": "task-kali"}
FIXED_TASK_FIELDS = (
    "namespace",
    "tmp_size_limit",
    "pod_deadline_seconds",
    "expose_pod_identity",
    "kali_receipts_enabled",
    "agent_resources",
    "kali_resources",
)


def _read_json(path):
    return json.loads(Path(path).read_text())


def _read_bytes(path, maximum=1 << 20):
    data = Path(path).read_bytes()
    if not 0 < len(data) <= maximum:
        raise ValueError("deployment material is missing or unbounded")
    return data


def _tls_document(config):
    return {
        "sslmode": "verify-full",
        "sslrootcert": config["ca_file"],
        "connect_timeout": 5,
    }


def owner_connection(config):
    params = dict(config["database"])
    params["user"] = "wuji_migration"
    params["password"] = config["roles"]["wuji_migration"]
    return psycopg.connect(**params, **_tls_document(config), autocommit=True)


@contextmanager
def application_connection(config):
    params = dict(config["database"])
    params["user"] = "wuji_app"
    params["password"] = config["roles"]["wuji_app"]
    with psycopg.connect(**params, **_tls_document(config), autocommit=True) as connection:
        yield connection


def mint_operator_token(config, *, key_file, ttl_seconds=900):
    """Mint a bounded operator bearer from the mounted deployment signing key.

    Deployment bearer files are minted once at configure time and expire; a
    long-lived owner action must not depend on a stale file or extend it.
    """

    from joserfc import jwt
    from joserfc.jwk import RSAKey
    from uuid import uuid4

    if not 60 <= ttl_seconds <= 3600:
        raise ValueError("operator bearer lifetime must stay bounded")
    now = int(time.time())
    claims = {
        "iss": config["identity"]["issuer"],
        "aud": config["identity"]["audience"],
        "sub": config.get("operator_subject", "operator"),
        "tenant_id": config["owner"][0],
        "roles": ["operator"],
        "iat": now,
        "nbf": now - 1,
        "exp": now + ttl_seconds,
        "jti": str(uuid4()),
    }
    key = RSAKey.import_key(_read_bytes(key_file, 65536))
    return jwt.encode({"alg": "RS256", "kid": "deployment-key"}, claims, key)


def operator_access(config, *, signing_key_file=None):
    verifier = TokenVerifier(
        public_key_pem=_read_bytes(config["public_key_file"]),
        issuer=config["identity"]["issuer"],
        audience=config["identity"]["audience"],
    )
    if signing_key_file:
        token = mint_operator_token(config, key_file=signing_key_file)
        if isinstance(token, bytes):
            token = token.decode()
    else:
        token = _read_bytes(config["operator_token_file"], 16384).decode().strip()
    return AccessContext(verifier.verify(token), "task-launch")


def deployment_profiles(config):
    profiles = config["definition"].get("worker_profiles")
    if not isinstance(profiles, dict) or set(profiles) != {"reason", "explore", "report"}:
        raise ValueError("the deployment publishes no bounded worker profile set")
    return profiles


def published_session_profiles(config, definition):
    """Fixed Session profiles derived from the deployment's published profiles."""

    runtime = definition["runtime_profile"]
    limits = runtime["limits"]
    allowed = tuple(runtime["allowed_tool_refs"])
    if not allowed or len(set(allowed)) != len(allowed):
        raise ValueError("the Task runtime profile has no bounded tool set")
    session_limits = SessionLimits(
        max_objects=32,
        max_reference_depth=8,
        max_messages=128,
        max_object_bytes=min(16384, limits["max_single_output_bytes"]),
        max_total_bytes=min(65536, limits["max_total_output_bytes"]),
        max_pending_approvals=min(4, runtime["max_pending_operations"]),
    )
    return {
        kind: SessionHarnessProfile(
            ref=f"harness.{kind}.deployment.v1",
            revision="1",
            work_kind=kind,
            instructions=profile["body"]["instructions"],
            tool_definition_refs=allowed,
            lock_digest=runtime["lock_digest"],
            max_context_records=profile["body"]["max_context_records"],
            max_context_bytes=profile["body"]["max_context_bytes"],
            max_output_tokens=profile["body"]["max_output_tokens"],
            history_source_id="deployment",
            memory_mode="disabled",
            memory_source_id="deployment_memory",
            session_limits=session_limits,
            max_context_window_tokens=8192,
            compaction_enabled=False,
        ).snapshot()
        for kind, profile in deployment_profiles(config).items()
    }


def finalise_definition(connection, *, owner, config):
    """Merge the deployment's published Session profiles into the definition.

    The definition must be final before the first activation: the Task permit
    binds the digest recorded by the earliest ``task.started`` event.
    """

    row = connection.execute(
        "SELECT definition_json, definition_digest, runtime_attempt, execution_epoch,"
        " activated_at, control_version FROM vnext.task"
        " WHERE tenant_id=%s AND project_id=%s AND task_id=%s FOR UPDATE",
        owner,
    ).fetchone()
    if row is None or not row[0]:
        raise DomainError("INVALID_REFERENCE", 422)
    raw, digest, attempt, epoch, activated_at, version = row
    if activated_at is not None:
        raise DomainError("INVALID_STATE", 409)
    definition = strict_json_loads(raw)
    if sha256(raw.encode()).hexdigest() != digest:
        raise DomainError("INPUT_DIGEST_CONFLICT", 409)
    profiles = json.loads(canonical_json_bytes(published_session_profiles(config, definition)))
    if definition.get("worker_profiles") not in (None, profiles):
        raise DomainError("INPUT_DIGEST_CONFLICT", 409)
    if definition.get("evaluation_mode") not in (None, "mechanism_synthetic"):
        raise DomainError("INVALID_STATE", 409)
    definition["worker_profiles"] = profiles
    definition["evaluation_mode"] = "mechanism_synthetic"
    updated = json.loads(canonical_json_bytes(definition))
    latest = canonical_json_bytes(updated).decode()
    changed = latest != raw
    raw, digest = latest, sha256(latest.encode()).hexdigest()
    if changed:
        connection.execute(
            "UPDATE vnext.task SET definition_json=%s, definition_digest=%s"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
            (raw, digest, *owner),
        )
    return {
        "definition": updated,
        "definition_digest": digest,
        "runtime_attempt": int(attempt),
        "execution_epoch": int(epoch),
        "control_version": str(version),
        "definition_changed": changed,
    }


def ensure_operator_actor(connection, *, owner, subject):
    """The creator needs a human knowledge actor before its Intent is admitted."""

    existing = connection.execute(
        "SELECT producer_kind, qualified_human FROM vnext.knowledge_actor"
        " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND subject=%s",
        (*owner, subject),
    ).fetchone()
    if existing is None:
        connection.execute(
            "INSERT INTO vnext.knowledge_actor(tenant_id,project_id,task_id,subject,"
            "producer_kind,qualified_human) VALUES(%s,%s,%s,%s,'human',true)",
            (*owner, subject),
        )
    elif existing != ("human", True):
        raise DomainError("INPUT_DIGEST_CONFLICT", 409)


def admission_document(config, definition):
    runtime = definition["runtime_profile"]
    return {
        "model": definition["model_profile"],
        "runtime": runtime,
        "allowed_tool_refs": list(runtime["allowed_tool_refs"]),
    }


def admission_grants():
    return [
        {
            "subject": subject,
            **{flag: flag in flags for flag in (
                "can_read", "can_write", "can_capture", "can_settle", "can_gc",
                "can_assess", "can_control", "can_observe", "can_admit",
            )},
            "clearance": 1,
        }
        for subject, flags in GRANT_CATALOG.items()
    ]


def deployment_pool_keys(connection, config):
    """Capacity pools are the deployment's published catalog, not a guess.

    The owner command reads the keys the deployment already bound to its
    template Task; every key must still exist in ``vnext.capacity_pool``.
    """

    if not isinstance(config.get("owner"), list) or len(config["owner"]) != 3:
        raise ValueError("the deployment template Task is required")
    rows = connection.execute(
        "SELECT pool_key FROM vnext.task_capacity_pool"
        " WHERE tenant_id=%s AND project_id=%s AND task_id=%s ORDER BY pool_key",
        tuple(config["owner"]),
    ).fetchall()
    keys = tuple(row[0] for row in rows)
    if not keys:
        raise ValueError("the deployment publishes no capacity pools")
    return keys


def publish_admission(connection, *, owner, config, definition, attempt, pool_keys):
    receiver_id, environment_ref = receiver_ids(owner[2], attempt)
    runtime = definition["runtime_profile"]
    publish_task_admission(
        connection,
        owner=owner,
        admission=admission_document(config, definition),
        capacity_pool_keys=pool_keys,
        access_grants=admission_grants(),
        scheduler_identity={
            "template_ref": "deployment-worker-v1",
            "issuer": config["identity"]["issuer"],
            "audience": config["identity"]["audience"],
            "signing_key_ref": "signing-key",
            "signing_kid": "deployment-key",
            "encryption_key_ref": "encryption-key",
            "clearance": 1,
        },
        pod_controller={
            "controller_subject": config.get("pod_controller_subject", "pod-controller"),
            "login_role": "wuji_pod",
        },
    )
    executor = dict(config["executor"])
    executor["receiver_id"] = receiver_id
    executor["environment_ref"] = environment_ref
    executor["allowed_tool_refs"] = list(runtime["allowed_tool_refs"])
    register_executor(connection, owner=owner, executor=executor)
    return {"receiver_id": receiver_id, "environment_ref": environment_ref,
            "executor_ref": executor["ref"]}


def receiver_ids(task_id, attempt):
    return f"task-{task_id}-a{attempt}", f"pod-environment-{task_id}-a{attempt}"


def admit_initial_intent(connection_factory, *, access, task, definition_lines, idempotency_key):
    unit = UnitOfWork(connection_factory)
    start_point = (definition_lines.get("start_points") or ["workspace:version.txt"])[0]
    if not isinstance(start_point, str) or not 1 <= len(start_point) <= 2048:
        raise DomainError("INVALID_REFERENCE", 422)
    client_ref = "".join(
        character if character.isalnum() or character in "-_" else "-"
        for character in start_point
    )[:64].strip("-") or "initial-read"
    question = (
        "Read the fixture workspace file for Task start point " + start_point
        + " once through the registered Kali workspace tool and cite the returned evidence."
    )
    if len(question) > 2048:
        raise DomainError("INVALID_SCHEMA", 422)
    return ClaimService(unit).propose_intent(
        access,
        task,
        {
            "client_ref": client_ref,
            "question": question,
            "basis_refs": [],
            "expected_output": "wuji.agent-payload.v2",
        },
        idempotency_key=idempotency_key,
    )


def activate(config, *, task_id, version, reason, base_url):
    payload = {
        "schema_version": "wuji.api.v2",
        "command": "start",
        "expected_version": str(version),
        "reason": reason,
    }
    token = _read_bytes(config["operator_token_file"], 16384).decode().strip()
    with httpx.Client(verify=config["ca_file"], trust_env=False, timeout=15.0) as peer:
        response = peer.post(
            f"{base_url}/api/v2/tasks/{task_id}/commands",
            json=payload,
            headers={"Authorization": "Bearer " + token,
                     "Idempotency-Key": f"task-launch-start-{task_id}"},
        )
    if response.status_code != 202:
        raise DomainError("CONTROL_REJECTED", response.status_code)
    return {"request": payload, "response": response.json()}


def runtime_config_document(binding):
    return {
        "tenant_id": binding["tenant_id"],
        "task_id": binding["task_id"],
        "namespace": binding["namespace"],
        "runtime_attempt": binding["runtime_attempt"],
        "execution_epoch": binding["execution_epoch"],
        "scope_digest": binding["scope_digest"],
        "config_digest": binding["config_digest"],
        "agent_image": binding["agent_image"],
        "kali_image": binding["kali_image"],
        "agent_resources": binding["agent_resources"],
        "kali_resources": binding["kali_resources"],
        "tmp_size_limit": binding["tmp_size_limit"],
        "pod_deadline_seconds": binding["pod_deadline_seconds"],
        "expose_pod_identity": binding["expose_pod_identity"],
        "kali_receipts_enabled": binding["kali_receipts_enabled"],
    }


def attempt_config(binding):
    from wuji_task_runtime.models import ContainerResources, TaskRuntimeConfig

    values = runtime_config_document(binding)
    return TaskRuntimeConfig(
        **{
            **values,
            "agent_resources": ContainerResources(**values["agent_resources"]),
            "kali_resources": ContainerResources(**values["kali_resources"]),
        }
    )


def requirement_material(config, *, agent_auth_dir, kali_auth_dir):
    agent = Path(agent_auth_dir)
    kali = Path(kali_auth_dir)
    return {
        "ca.crt": _read_bytes(config["ca_file"]),
        "identity.pub": _read_bytes(config["public_key_file"]),
        "receiver.token": _read_bytes(agent / "receiver.token", 16384),
        "collector.token": _read_bytes(kali / "collector.token", 16384),
        "task-agent.crt": _read_bytes(agent / "tls.crt", 65536),
        "task-agent.key": _read_bytes(agent / "tls.key", 65536),
        "task-kali.crt": _read_bytes(kali / "tls.crt", 65536),
        "task-kali.key": _read_bytes(kali / "tls.key", 65536),
    }


def task_objects(binding, material, *, namespace):
    config = attempt_config(binding)
    names = config.resource_names
    labels = config.identity_labels
    annotations = config.ownership_annotations
    metadata = {"namespace": namespace, "labels": labels, "annotations": annotations}
    supervisor = {
        "schema_version": "wuji.supervisor.deployment.v1",
        "controller_origin": binding["runtime_origin"],
        "receiver": {
            "receiver_id": binding["receiver_id"],
            "runtime_attempt": str(binding["runtime_attempt"]),
            "environment_ref": binding["environment_ref"],
        },
        "receiver_token_file": "/run/wuji/credentials/receiver.token",
        "profiles": binding["profiles"],
        "inbox_dir": "/var/lib/wuji/agent/inbox",
        "ca_file": "/config/ca.crt",
        "certificate_file": "/run/wuji/credentials/tls.crt",
        "private_key_file": "/run/wuji/credentials/tls.key",
        "port": 8443,
    }
    kali = {
        "schema_version": "wuji.kali.deployment.v1",
        "binding": {
            "tenant_id": binding["tenant_id"],
            "project_id": binding["project_id"],
            "task_id": binding["task_id"],
            "executor_ref": binding["executor_ref"],
            "receiver_id": binding["receiver_id"],
            "environment_ref": binding["environment_ref"],
            "collector_subject": "collector",
            "gate_subject": "gate",
        },
        "platform_url": binding["gate_url"],
        "ca_file": "/config/ca.crt",
        "collector_token_file": "/run/wuji/credentials/collector.token",
        "public_key_file": "/config/identity.pub",
        "issuer": binding["issuer"],
        "audience": binding["audience"],
        "root": "/workspace",
        "receipt_root": "/var/lib/wuji/kali-receipts",
    }
    objects = [
        {"apiVersion": "v1", "kind": "ConfigMap",
         "metadata": {"name": names["agent_config"], **metadata},
         "data": {"supervisor.json": canonical_json_bytes(supervisor).decode(),
                  "ca.crt": material["ca.crt"].decode(),
                  "identity.pub": material["identity.pub"].decode()}},
        {"apiVersion": "v1", "kind": "ConfigMap",
         "metadata": {"name": names["kali_config"], **metadata},
         "data": {"kali.json": canonical_json_bytes(kali).decode(),
                  "ca.crt": material["ca.crt"].decode(),
                  "identity.pub": material["identity.pub"].decode()}},
        {"apiVersion": "v1", "kind": "Secret",
         "metadata": {"name": names["agent_auth"], **metadata},
         "type": "Opaque",
         "data": {"receiver.token": _base64(material["receiver.token"]),
                  "tls.crt": _base64(material["task-agent.crt"]),
                  "tls.key": _base64(material["task-agent.key"])}},
        {"apiVersion": "v1", "kind": "Secret",
         "metadata": {"name": names["kali_auth"], **metadata},
         "type": "Opaque",
         "data": {"collector.token": _base64(material["collector.token"]),
                  "tls.crt": _base64(material["task-kali.crt"]),
                  "tls.key": _base64(material["task-kali.key"])}},
    ]
    objects += [
        {"apiVersion": "v1", "kind": "PersistentVolumeClaim",
         "metadata": {"name": names[key], **metadata},
         "spec": {"accessModes": ["ReadWriteOnce"],
                  "resources": {"requests": {"storage": "1Gi"}}}}
        for key in ("agent_state", "kali_work", "kali_receipts")
    ]
    return config, objects


def _base64(value):
    import base64

    return base64.b64encode(value).decode()


def initializer_job(binding, *, namespace, image):
    config = attempt_config(binding)
    labels = {key: value for key, value in config.identity_labels.items()
              if key != "app.kubernetes.io/managed-by"}
    labels["app.kubernetes.io/managed-by"] = "wuji-vnext-deployment"
    metadata = {"name": config.task_prefix + f"-a{binding['runtime_attempt']}-workspace-init",
                "namespace": namespace, "labels": labels,
                "annotations": config.ownership_annotations}
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": metadata,
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": 120,
            "template": {
                "metadata": {"labels": labels, "annotations": config.ownership_annotations},
                "spec": {
                    "automountServiceAccountToken": False,
                    "restartPolicy": "Never",
                    "securityContext": {"runAsNonRoot": True, "fsGroup": 10000,
                                        "seccompProfile": {"type": "RuntimeDefault"}},
                    "containers": [{
                        "name": "workspace-init",
                        "image": image,
                        "command": ["sh", "-c",
                                    "umask 077; printf 'wuji-vnext-fixture-v1\n' > /workspace/version.txt"],
                        "securityContext": {"runAsUser": 10002, "runAsGroup": 10000,
                                            "runAsNonRoot": True, "allowPrivilegeEscalation": False,
                                            "readOnlyRootFilesystem": True,
                                            "capabilities": {"drop": ["ALL"]}},
                        "volumeMounts": [{"name": "kali-work", "mountPath": "/workspace"},
                                         {"name": "tmp", "mountPath": "/tmp"}],
                        "resources": {"requests": {"cpu": "25m", "memory": "32Mi"},
                                      "limits": {"cpu": "250m", "memory": "128Mi"}},
                    }],
                    "volumes": [
                        {"name": "kali-work",
                         "persistentVolumeClaim": {"claimName": config.resource_names["kali_work"]}},
                        {"name": "tmp", "emptyDir": {"sizeLimit": "16Mi"}},
                    ],
                },
            },
        },
    }


def _canonical(document):
    return canonical_json_bytes(document)


def ensure_object(core, kind, body, *, namespace):
    """Create a Task-owned object or verify the existing one is identical."""

    name = body["metadata"]["name"]
    readers = {
        "ConfigMap": core.read_namespaced_config_map,
        "Secret": core.read_namespaced_secret,
        "PersistentVolumeClaim": core.read_namespaced_persistent_volume_claim,
    }
    creators = {
        "ConfigMap": core.create_namespaced_config_map,
        "Secret": core.create_namespaced_secret,
        "PersistentVolumeClaim": core.create_namespaced_persistent_volume_claim,
    }
    k8s = k8s_client()
    client = k8s.ApiClient()
    try:
        existing = client.sanitize_for_serialization(readers[kind](name, namespace))
    except k8s.exceptions.ApiException as error:
        if error.status != 404:
            raise
        creators[kind](namespace, body)
        return "created"
    comparable = ("data",) if kind != "PersistentVolumeClaim" else ("spec",)
    for field in comparable:
        if _canonical(existing.get(field)) != _canonical(body.get(field)):
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
    for key, value in body["metadata"]["labels"].items():
        if existing.get("metadata", {}).get("labels", {}).get(key) != value:
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
    return "unchanged"


def replace_service_selector(core, name, selector, *, namespace):
    client = k8s_client().ApiClient()
    service = client.sanitize_for_serialization(core.read_namespaced_service(name, namespace))
    if service["spec"].get("selector") == selector:
        return "unchanged"
    service["spec"]["selector"] = dict(selector)
    core.replace_namespaced_service(name, namespace, service)
    return "replaced"


def patch_deployment_json(core, name, update, *, namespace):
    client = k8s_client().ApiClient()
    configmap = client.sanitize_for_serialization(core.read_namespaced_config_map(name, namespace))
    document = json.loads(configmap["data"]["deployment.json"])
    if update(document) == "unchanged":
        return "unchanged"
    configmap["data"]["deployment.json"] = canonical_json_bytes(document).decode()
    core.replace_namespaced_config_map(name, namespace, configmap)
    return "replaced"


def rollout(apps, name, *, namespace, stamp):
    apps.patch_namespaced_deployment(
        name,
        namespace,
        {"spec": {"template": {"metadata": {"annotations": {
            "wuji.dev/task-binding": stamp}}}}},
    )


def wire(binding, *, config, namespace, agent_auth_dir, kali_auth_dir, image):
    from kubernetes import config as k8s_config

    k8s = k8s_client()
    k8s_config.load_incluster_config()
    core, apps, batch = k8s.CoreV1Api(), k8s.AppsV1Api(), k8s.BatchV1Api()
    material = requirement_material(config, agent_auth_dir=agent_auth_dir,
                                    kali_auth_dir=kali_auth_dir)
    task_config, objects = task_objects(binding, material, namespace=namespace)
    actions = {}
    for body in objects:
        actions[body["metadata"]["name"]] = ensure_object(
            core, body["kind"], body, namespace=namespace)
    job = initializer_job(binding, namespace=namespace, image=image)
    job_name = job["metadata"]["name"]
    try:
        batch.create_namespaced_job(namespace, job)
        actions[job_name] = "created"
    except k8s.exceptions.ApiException as error:
        if error.status != 409:
            raise
        actions[job_name] = "unchanged"
    deadline = time.monotonic() + 120
    while True:
        status = batch.read_namespaced_job_status(job_name, namespace).status
        if status.succeeded:
            break
        if status.failed or time.monotonic() > deadline:
            raise DomainError("WORKSPACE_INIT_FAILED", 500)
        time.sleep(2)
    for role, port in (("agent", 8443), ("kali", 8444)):
        actions[SERVICE_NAMES[role]] = replace_service_selector(
            core, SERVICE_NAMES[role], task_config.identity_labels, namespace=namespace)

    def runtime_update(document):
        pod_runtime = document.get("pod_runtime")
        if not isinstance(pod_runtime, dict):
            raise DomainError("INVALID_REFERENCE", 422)
        expected_task = runtime_config_document(binding)
        expected_receiver = {
            "receiver_id": binding["receiver_id"],
            "receiver_subject": "receiver",
            "environment_ref": binding["environment_ref"],
            "credential_template_ref": "deployment-worker-v1",
            "model_mode": "synthetic",
        }
        changed = (
            document.get("task_ids") != [binding["task_id"]]
            or pod_runtime.get("task_config") != expected_task
            or pod_runtime.get("receiver") != expected_receiver
        )
        document["task_ids"] = [binding["task_id"]]
        pod_runtime["task_config"] = expected_task
        pod_runtime["receiver"] = expected_receiver
        return "replaced" if changed else "unchanged"

    actions["runtime-config"] = patch_deployment_json(core, "runtime-config", runtime_update,
                                                      namespace=namespace)

    def gates_update(document):
        executors = document.get("executors")
        if not isinstance(executors, list) or len(executors) != 1:
            raise DomainError("INVALID_REFERENCE", 422)
        binding_document = executors[0].get("binding")
        if not isinstance(binding_document, dict):
            raise DomainError("INVALID_REFERENCE", 422)
        expected = {
            "tenant_id": binding["tenant_id"],
            "project_id": binding["project_id"],
            "task_id": binding["task_id"],
            "executor_ref": binding["executor_ref"],
            "receiver_id": binding["receiver_id"],
            "environment_ref": binding["environment_ref"],
        }
        changed = any(binding_document.get(key) != value for key, value in expected.items())
        binding_document.update(expected)
        return "replaced" if changed else "unchanged"

    actions["gates-config"] = patch_deployment_json(core, "gates-config", gates_update,
                                                    namespace=namespace)
    stamp = str(int(time.time()))
    rollout(apps, "runtime", namespace=namespace, stamp=stamp)
    rollout(apps, "gates", namespace=namespace, stamp=stamp)
    deadline = time.monotonic() + 300
    while True:
        try:
            pod = core.read_namespaced_pod(task_config.pod_name, namespace)
        except k8s.exceptions.ApiException as error:
            if error.status != 404:
                raise
            pod = None
        if pod is not None:
            statuses = pod.status.container_statuses or []
            ready = [item for item in statuses if item.ready is True]
            if pod.status.phase == "Running" and len(ready) == 2:
                break
            if pod.status.phase in {"Failed", "Succeeded"}:
                raise DomainError("POD_TERMINATED", 409)
        if time.monotonic() > deadline:
            raise DomainError("POD_NOT_READY", 504)
        time.sleep(3)
    return {
        "actions": actions,
        "pod_name": task_config.pod_name,
        "pod_uid": pod.metadata.uid,
        "resource_names": task_config.resource_names,
    }


def publish_capabilities(connection, *, config, binding):
    owner = (binding["tenant_id"], binding["project_id"], binding["task_id"])
    row = connection.execute(
        "SELECT document_json FROM vnext.admission_config"
        " WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
        owner,
    ).fetchone()
    if row is None:
        raise DomainError("INVALID_REFERENCE", 422)
    admission = TaskAdmissionConfig.model_validate(strict_json_loads(row[0]))
    client_snapshot = session_client_snapshot(admission)
    runtime_snapshot = admission.runtime.model_dump(mode="json")
    # A mechanism candidate binding must stay short-lived (<= 1 hour).  Rounding
    # the publication to a five-minute window keeps retries inside the window
    # idempotent while the record itself never lives longer than 55 minutes.
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    published_at = now.replace(minute=(now.minute // 5) * 5)
    published = []
    for kind, profile in binding["worker_profiles"].items():
        capability_ref = f"session-capability-{binding['task_id']}-a{binding['runtime_attempt']}-{kind}"
        register_session_capability(
            connection,
            tenant_id=binding["tenant_id"],
            capability={
                "ref": capability_ref,
                "revision": "1",
                "published_at": published_at,
                "validation_status": "mechanism_candidate",
                "candidate_binding": {
                    "tenant_id": binding["tenant_id"],
                    "project_id": binding["project_id"],
                    "task_id": binding["task_id"],
                    "receiver_id": binding["receiver_id"],
                    "runtime_attempt": str(binding["runtime_attempt"]),
                    "pod_uid": binding["pod_uid"],
                    "model_gateway_digest": model_gateway_digest(admission.model.gateway_url),
                    "expires_at": published_at + timedelta(minutes=55),
                },
                "profile_snapshot": profile,
                "profile_digest": profile["digest"],
                "client_snapshot": client_snapshot,
                "client_digest": configuration_digest(client_snapshot),
                "runtime_snapshot": runtime_snapshot,
                "runtime_digest": configuration_digest(runtime_snapshot),
                "framework_snapshot": dict(FRAMEWORK_SNAPSHOT),
                "framework_digest": configuration_digest(FRAMEWORK_SNAPSHOT),
                "lock_digest": admission.runtime.lock_digest,
                "limits": profile["body"]["session_limits"],
                "recovery_classes": ["settled_boundary", "approval_boundary"],
                "memory_mode": profile["body"]["memory_mode"],
                "approver_subjects": [config.get("operator_subject", "operator")],
                "approval_ttl_seconds": 300,
                "evidence_refs": [binding["evidence_ref"]],
            },
        )
        published.append(capability_ref)
    return {"capabilities": published}


def binding_document(config, task_id, *, agent_image, kali_image, prepared, extra):
    owner = (config["owner"][0], config["owner"][1], task_id)
    definition = prepared["definition"]
    attempt = prepared["runtime_attempt"]
    receiver_id, environment_ref = receiver_ids(task_id, attempt)
    return {
        "schema_version": SCHEMA_VERSION,
        "tenant_id": owner[0],
        "project_id": owner[1],
        "task_id": task_id,
        "definition_digest": prepared["definition_digest"],
        "scope_digest": sha256(
            canonical_json_bytes(definition["task"]["authorization_scope"])
        ).hexdigest(),
        "config_digest": prepared["definition_digest"],
        "runtime_attempt": attempt,
        "execution_epoch": prepared["execution_epoch"],
        "control_version": prepared["control_version"],
        "receiver_id": receiver_id,
        "environment_ref": environment_ref,
        "executor_ref": extra["executor_ref"],
        "agent_image": agent_image,
        "kali_image": kali_image,
        "profiles": {
            profile["ref"]: [kind]
            for kind, profile in published_session_profiles(config, definition).items()
        },
        "worker_profiles": published_session_profiles(config, definition),
        "issuer": config["identity"]["issuer"],
        "audience": config["identity"]["audience"],
        "runtime_origin": extra["runtime_origin"],
        "gate_url": extra["gate_url"],
        "namespace": extra["namespace"],
        "tmp_size_limit": extra.get("tmp_size_limit", "128Mi"),
        "pod_deadline_seconds": extra.get("pod_deadline_seconds", 1800),
        "expose_pod_identity": True,
        "kali_receipts_enabled": True,
        "agent_resources": extra.get(
            "agent_resources",
            {"cpu_request": "100m", "memory_request": "128Mi",
             "cpu_limit": "1", "memory_limit": "512Mi"},
        ),
        "kali_resources": extra.get(
            "kali_resources",
            {"cpu_request": "100m", "memory_request": "128Mi",
             "cpu_limit": "1", "memory_limit": "512Mi"},
        ),
        "evidence_ref": extra["evidence_ref"],
    }


def refreshed_binding(connection, binding):
    row = connection.execute(
        "SELECT definition_digest, execution_epoch, runtime_attempt, control_version, activated_at"
        " FROM vnext.task WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
        (binding["tenant_id"], binding["project_id"], binding["task_id"]),
    ).fetchone()
    if row is None or row[0] != binding["definition_digest"]:
        raise DomainError("INPUT_DIGEST_CONFLICT", 409)
    if row[4] is None:
        raise DomainError("INVALID_STATE", 409)
    return {
        **binding,
        "execution_epoch": int(row[1]),
        "runtime_attempt": int(row[2]),
        "control_version": str(row[3]),
    }


def run_phases(config, *, task_id, phases, options):
    connection = owner_connection(config)
    binding = options.get("binding_in") or None
    if binding is None and options.get("binding_path"):
        path = Path(options["binding_path"])
        if path.exists():
            candidate = _read_json(path)
            binding = candidate if candidate.get("task_id") == task_id else None
    if binding is None and "prepare" not in phases:
        raise DomainError("INVALID_REFERENCE", 422)
    result = {}
    try:
        if "prepare" in phases:
            prepared = finalise_definition(
                connection, owner=(config["owner"][0], config["owner"][1], task_id), config=config)
            ensure_operator_actor(
                connection, owner=(config["owner"][0], config["owner"][1], task_id),
                subject=config.get("operator_subject", "operator"))
            published = publish_admission(
                connection, owner=(config["owner"][0], config["owner"][1], task_id),
                config=config, definition=prepared["definition"],
                attempt=prepared["runtime_attempt"],
                pool_keys=deployment_pool_keys(connection, config))
            receipt = admit_initial_intent(
                partial(application_connection, config),
                access=operator_access(config, signing_key_file=options.get("signing_key_file")),
                task=task_id,
                definition_lines=prepared["definition"],
                idempotency_key=f"task-launch-intent-{task_id}")
            binding = binding_document(
                config, task_id,
                agent_image=options["agent_image"], kali_image=options["kali_image"],
                prepared=prepared,
                extra={
                    **published,
                    "runtime_origin": options["runtime_origin"],
                    "gate_url": options["gate_url"],
                    "namespace": options["namespace"],
                    "evidence_ref": options["evidence_ref"],
                },
            )
            result["prepare"] = {
                "definition_changed": prepared["definition_changed"],
                "definition_digest": prepared["definition_digest"],
                "receiver_id": published["receiver_id"],
                "executor_ref": published["executor_ref"],
                "intent_ref": receipt.canonical_ref.model_dump(mode="json")
                if receipt.canonical_ref is not None else None,
                "intent_disposition": receipt.disposition,
            }
        if "activate" in phases:
            result["activate"] = activate(
                config, task_id=task_id, version=binding["control_version"],
                reason="task launch: activate the created Task for its first runtime attempt",
                base_url=options["base_url"])
            binding = refreshed_binding(connection, binding)
            result["activate"]["execution_epoch"] = binding["execution_epoch"]
        if "wire" in phases:
            result["wire"] = wire(
                binding, config=config, namespace=options["namespace"],
                agent_auth_dir=options["agent_auth_dir"],
                kali_auth_dir=options["kali_auth_dir"],
                image=options["kali_image"])
            binding = {**binding, **result["wire"]}
        if "capability" in phases:
            result["capability"] = publish_capabilities(connection, config=config, binding=binding)
    finally:
        connection.close()
    if binding is not None and options.get("binding_path"):
        Path(options["binding_path"]).write_text(
            json.dumps(binding, sort_keys=True, indent=1, default=str) + "\n")
    return binding, result


def _job_manifest(*, name, namespace, image, args, service_account, configmap, secret,
                  agent_auth, kali_auth, signing_key_secret="runtime-credentials"):
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {"name": name, "namespace": namespace,
                     "labels": {"app.kubernetes.io/managed-by": "wuji-vnext-deployment",
                                "wuji.dev/environment": "local-test"}},
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": 900,
            "template": {
                "metadata": {"labels": {"app.kubernetes.io/managed-by": "wuji-vnext-deployment",
                                        "wuji.dev/environment": "local-test"}},
                "spec": {
                    "serviceAccountName": service_account,
                    "restartPolicy": "Never",
                    "securityContext": {"runAsNonRoot": True, "runAsUser": 10001,
                                        "runAsGroup": 10000, "fsGroup": 10000,
                                        "seccompProfile": {"type": "RuntimeDefault"}},
                    "containers": [{
                        "name": "task-launch",
                        "image": image,
                        "command": ["python", "/opt/wuji/ops/vnext/task_launch.py"],
                        "args": args,
                        "securityContext": {"runAsNonRoot": True, "runAsUser": 10001,
                                            "runAsGroup": 10000,
                                            "allowPrivilegeEscalation": False,
                                            "readOnlyRootFilesystem": True,
                                            "capabilities": {"drop": ["ALL"]}},
                        "volumeMounts": [
                            {"name": "public", "mountPath": "/config", "readOnly": True},
                            {"name": "input", "mountPath": "/run/wuji/bootstrap", "readOnly": True},
                            {"name": "agent-auth", "mountPath": "/run/wuji/task-agent-auth",
                             "readOnly": True},
                            {"name": "kali-auth", "mountPath": "/run/wuji/task-kali-auth",
                             "readOnly": True},
                            {"name": "signing-key", "mountPath": "/run/wuji/deployment-signing",
                             "readOnly": True},
                            {"name": "tmp", "mountPath": "/tmp"},
                        ],
                        "resources": {"requests": {"cpu": "100m", "memory": "128Mi"},
                                      "limits": {"cpu": "1", "memory": "512Mi"}},
                    }],
                    "volumes": [
                        {"name": "public", "configMap": {"name": configmap, "defaultMode": 0o444}},
                        {"name": "input", "secret": {"secretName": secret, "defaultMode": 0o440}},
                        {"name": "agent-auth", "secret": {"secretName": agent_auth,
                                                          "defaultMode": 0o440}},
                        {"name": "kali-auth", "secret": {"secretName": kali_auth,
                                                         "defaultMode": 0o440}},
                        {"name": "signing-key", "secret": {"secretName": signing_key_secret,
                                                           "defaultMode": 0o440}},
                        {"name": "tmp", "emptyDir": {"sizeLimit": "32Mi"}},
                    ],
                },
            },
        },
    }


def submit_job(*, args, namespace, job_name, job_args):
    import subprocess

    manifest = json.dumps(_job_manifest(
        name=job_name, namespace=namespace, image=args.image, args=job_args,
        service_account=args.service_account, configmap=args.public_configmap,
        secret=args.input_secret, agent_auth=args.agent_auth_secret,
        kali_auth=args.kali_auth_secret,
        signing_key_secret=args.signing_key_secret))
    context = ["--context", args.context] if args.context else []
    rbac = Path(__file__).parent / "kubernetes" / "task-owner-rbac.json"
    subprocess.run(["kubectl", *context, "apply", "-f", str(rbac)],
                   check=True, capture_output=True)
    subprocess.run(["kubectl", *context, "-n", namespace, "delete", "job", job_name,
                    "--ignore-not-found"], check=True, capture_output=True)
    subprocess.run(["kubectl", *context, "-n", namespace, "apply", "-f", "-"],
                   input=manifest, text=True, check=True, capture_output=True)
    subprocess.run(["kubectl", *context, "-n", namespace, "wait",
                    "--for=condition=complete", f"job/{job_name}", "--timeout=900s"],
                   check=False, capture_output=True)
    logs = subprocess.run(["kubectl", *context, "-n", namespace, "logs", f"job/{job_name}"],
                          check=True, capture_output=True, text=True).stdout
    print(logs.rstrip())


def main(argv=None):
    parser = argparse.ArgumentParser(description="owner command for P11 Task launch")
    parser.add_argument("--config", default="/run/wuji/bootstrap/config.json")
    parser.add_argument("--task", required=True)
    parser.add_argument("--phase", default="all",
                        choices=["all", "prepare", "activate", "wire", "capability"])
    parser.add_argument("--namespace", default="wuji-vnext-test")
    parser.add_argument("--agent-image", required=True)
    parser.add_argument("--kali-image", required=True)
    parser.add_argument("--base-url", default="https://api.wuji-vnext-test.svc:8443")
    parser.add_argument("--runtime-origin", default="https://runtime.wuji-vnext-test.svc:8443")
    parser.add_argument("--gate-url", default="https://gates.wuji-vnext-test.svc:8443")
    parser.add_argument("--agent-auth-dir", default="/run/wuji/task-agent-auth")
    parser.add_argument("--kali-auth-dir", default="/run/wuji/task-kali-auth")
    parser.add_argument("--operator-signing-key",
                        default="/run/wuji/deployment-signing/signing.key")
    parser.add_argument("--evidence-ref",
                        default="docs/vnext/evidence/P11/task-roundtrip-20260915/README.md")
    # submit mode (run from the operator workstation)
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--image", default="")
    parser.add_argument("--job-name", default="")
    parser.add_argument("--binding", default="/tmp/task-binding.json")
    parser.add_argument("--service-account", default="task-owner")
    parser.add_argument("--public-configmap", default="bootstrap-public-topo0915")
    parser.add_argument("--input-secret", default="bootstrap-input-topo0915")
    parser.add_argument("--signing-key-secret", default="runtime-credentials")
    parser.add_argument("--agent-auth-secret", default="")
    parser.add_argument("--kali-auth-secret", default="")
    parser.add_argument("--context", default="docker-desktop")
    parser.add_argument("--binding-in", default="")
    args = parser.parse_args(argv)
    if args.submit:
        job_args = [
            "--phase", args.phase,
            "--task", args.task,
            "--agent-image", args.agent_image,
            "--kali-image", args.kali_image,
            "--namespace", args.namespace,
            "--base-url", args.base_url,
            "--runtime-origin", args.runtime_origin,
            "--gate-url", args.gate_url,
            "--evidence-ref", args.evidence_ref,
            "--binding", args.binding,
        ]
        if args.operator_signing_key:
            job_args += ["--operator-signing-key", args.operator_signing_key]
        if args.binding_in:
            job_args += ["--binding-in", args.binding_in]
        submit_job(args=args, namespace=args.namespace, job_args=job_args,
                   job_name=args.job_name or f"p11c-launch-{args.task[:8]}")
        return 0
    config = _read_json(args.config)
    phases = ["prepare", "activate", "wire", "capability"] if args.phase == "all" else [args.phase]
    if not args.agent_image or not args.kali_image:
        raise SystemExit("--agent-image and --kali-image are required")
    if args.binding_in:
        options_binding = _read_json(args.binding_in)
        if options_binding.get("schema_version") != SCHEMA_VERSION:
            raise SystemExit("unknown binding document version")
    binding, result = run_phases(
        config, task_id=args.task, phases=phases,
        options={
            "binding_in": options_binding if args.binding_in else None,
            "binding_path": args.binding,
            "signing_key_file": args.operator_signing_key or None,
            "agent_image": args.agent_image,
            "kali_image": args.kali_image,
            "base_url": args.base_url,
            "runtime_origin": args.runtime_origin,
            "gate_url": args.gate_url,
            "namespace": args.namespace,
            "agent_auth_dir": args.agent_auth_dir,
            "kali_auth_dir": args.kali_auth_dir,
            "evidence_ref": args.evidence_ref,
        },
    )
    print(json.dumps({"event": "task_launch", "task_id": args.task,
                      "phases": phases, "result": result}, sort_keys=True, default=str))
    print("TASK_LAUNCH_BINDING " + json.dumps(binding, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
