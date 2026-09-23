"""Render one private, empty Core CTF platform in its own namespace.

This writes manifests only. It never runs kubectl, creates a Task, starts a
Task, or calls a model/target.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import sys
from uuid import uuid4

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from joserfc import jwt
from joserfc.jwk import RSAKey


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops/vnext"))
from core_ctf_catalog import owner_template  # noqa: E402
from task_launch import shipped_worker_lock_digest  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


render_helpers = _load("core_ctf_render_helpers", "ops/vnext/kubernetes/render.py")
k8s_helpers = _load("core_ctf_k8s_helpers", "scripts/vnext/k8s.py")
web_helpers = _load("core_ctf_web_helpers", "ops/vnext/kubernetes/web.py")
gateway = _load("core_ctf_gateway", "services/wuji-web-gateway/main.py")

IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[a-f0-9]{64}$")
SOURCE_REVISION = re.compile(r"(?:[a-f0-9]{40}|[a-f0-9]{64})\Z")
NAMESPACE = re.compile(r"^[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?$")
ROLES = ("platform", "agent", "kali", "capture", "postgres", "web")
BUSINESS_ROLES = ("platform", "agent", "kali", "capture", "web")
LABELS = {
    "app.kubernetes.io/managed-by": "wuji-core-ctf-deployment",
    "wuji.dev/environment": "local-core-ctf",
}


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)


def _json(path, value):
    _write(path, json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def _image(value):
    value = value.get("reference") if isinstance(value, dict) else value
    if not isinstance(value, str) or not IMAGE.fullmatch(value):
        raise ValueError("every Core CTF image must be an immutable digest reference")
    return value


def _image_source_revisions(inventory):
    revisions = {}
    for role in BUSINESS_ROLES:
        entry = inventory.get(role)
        revision = entry.get("source_revision") if isinstance(entry, dict) else None
        if not isinstance(revision, str) or not SOURCE_REVISION.fullmatch(revision):
            raise ValueError(f"Core CTF {role} image requires its full source SHA")
        revisions[role] = revision
    return revisions


def _metadata(name, namespace):
    return {"name": name, "namespace": namespace, "labels": dict(LABELS)}


def _configmap(name, namespace, data):
    return {
        "apiVersion": "v1", "kind": "ConfigMap",
        "metadata": _metadata(name, namespace), "data": data,
    }


def _secret(name, namespace, data):
    return {
        "apiVersion": "v1", "kind": "Secret", "type": "Opaque",
        "metadata": _metadata(name, namespace),
        "data": {key: base64.b64encode(value).decode() for key, value in data.items()},
    }


def _token(private_key, *, issuer, audience, tenant, subject, roles, now):
    value = jwt.encode(
        {"alg": "RS256", "kid": "deployment-key"},
        {
            "iss": issuer, "aud": audience, "sub": subject,
            "tenant_id": tenant, "roles": roles,
            "iat": int(now.timestamp()) - 30,
            "nbf": int(now.timestamp()) - 30,
            "exp": int((now + timedelta(hours=8)).timestamp()),
            "jti": str(uuid4()),
        },
        RSAKey.import_key(private_key),
        algorithms=["RS256"],
    )
    return value.encode() if isinstance(value, str) else value


def _client_certificate(ca_directory):
    ca = x509.load_pem_x509_certificate((ca_directory / "ca.crt").read_bytes())
    ca_key = serialization.load_pem_private_key(
        (ca_directory / "ca.key").read_bytes(), password=None
    )
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "core-ctf-runtime")]))
        .issuer_name(ca.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=7))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca.public_key()), critical=False)
        .add_extension(x509.KeyUsage(
            digital_signature=True, key_encipherment=False,
            content_commitment=False, data_encipherment=False,
            key_agreement=False, key_cert_sign=False, crl_sign=False,
            encipher_only=None, decipher_only=None,
        ), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    return (
        certificate.public_bytes(serialization.Encoding.PEM),
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )


def _job(name, namespace, image, command, mounts, volumes, *, architecture):
    return {
        "apiVersion": "batch/v1", "kind": "Job",
        "metadata": _metadata(name, namespace),
        "spec": {
            "backoffLimit": 0, "activeDeadlineSeconds": 180,
            "template": {
                "metadata": {"labels": dict(LABELS)},
                "spec": {
                    "restartPolicy": "Never", "automountServiceAccountToken": False,
                    "nodeSelector": {"kubernetes.io/arch": architecture},
                    "securityContext": {
                        "runAsNonRoot": True, "runAsUser": 10001,
                        "runAsGroup": 10000, "fsGroup": 10000,
                        "seccompProfile": {"type": "RuntimeDefault"},
                    },
                    "containers": [{
                        "name": name, "image": image, "command": command,
                        "securityContext": render_helpers.security(10001),
                        "volumeMounts": mounts,
                    }],
                    "volumes": volumes,
                },
            },
        },
    }


def _rbac(namespace):
    runtime_rules = [
        {"apiGroups": [""], "resources": ["pods"], "verbs": ["get", "list", "create", "delete", "patch"]},
        {"apiGroups": [""], "resources": ["configmaps", "secrets", "persistentvolumeclaims", "services"], "verbs": ["get"]},
        {"apiGroups": ["discovery.k8s.io"], "resources": ["endpointslices"], "verbs": ["list"]},
    ]
    launch_rules = [
        {"apiGroups": [""], "resources": ["pods"], "verbs": ["get", "list"]},
        {"apiGroups": [""], "resources": ["configmaps", "persistentvolumeclaims", "services"], "verbs": ["get", "list", "create", "update", "patch"]},
        {"apiGroups": [""], "resources": ["secrets"], "verbs": ["get", "create", "patch"]},
        {"apiGroups": ["batch"], "resources": ["jobs", "jobs/status"], "verbs": ["get", "list", "create"]},
    ]
    result = []
    for name, rules in (("runtime", runtime_rules), ("core-launch", launch_rules)):
        result.extend([
            {"apiVersion": "v1", "kind": "ServiceAccount", "metadata": _metadata(name, namespace)},
            {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "Role", "metadata": _metadata(name, namespace), "rules": rules},
            {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "RoleBinding", "metadata": _metadata(name, namespace),
             "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": name},
             "subjects": [{"kind": "ServiceAccount", "name": name, "namespace": namespace}]},
        ])
    return result


def render(
    state, inventory, *, namespace, password_credential,
    explore_limit, pool_capacity, architecture="amd64", web_port=44181,
):
    state = Path(state).resolve()
    if (
        ROOT / "work" not in state.parents
        or not NAMESPACE.fullmatch(namespace)
        or namespace == "wuji-vnext-test"
    ):
        raise ValueError("Core CTF state must be an ignored work directory and namespace a DNS label")
    credential_path = Path(password_credential).resolve()
    gateway.PasswordCredential(str(credential_path))
    password_document = credential_path.read_bytes()
    if type(web_port) is not int or not 1024 <= web_port <= 65535:
        raise ValueError("an explicit local web port is required")
    output = state / "configuration"
    if output.exists():
        raise ValueError("configuration already exists; preserve its private identity")
    images = {role: _image(inventory.get(role)) for role in ROLES}
    source_revisions = _image_source_revisions(inventory)
    output.mkdir(parents=True, mode=0o700)
    tls = state / "tls"
    k8s_helpers.certificates(
        tls,
        namespace_name=namespace,
        services=("runtime", "api", "gates", "postgres", "task-agent"),
    )
    tls_bytes = {
        path.name: path.read_bytes()
        for path in tls.iterdir()
        if path.suffix in {".crt", ".key"}
    }
    client_cert, client_key = _client_certificate(tls)

    now = datetime.now(timezone.utc)
    tenant, project = str(uuid4()), str(uuid4())
    issuer = "https://identity." + namespace + ".invalid"
    audience = "wuji-core-ctf"
    signing = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    private = signing.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public = signing.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    tokens = {
        subject: _token(
            private, issuer=issuer, audience=audience, tenant=tenant,
            subject=subject, roles=roles, now=now,
        )
        for subject, roles in {
            "operator": ["operator"], "scheduler": ["scheduler"],
            "receiver": ["controller"], "pod-controller": ["controller"],
            "collector": ["runtime", "collector"], "gate": ["gate"],
            "launch": ["controller"],
        }.items()
    }
    roles = {
        name: secrets.token_urlsafe(36)
        for name in ("wuji_migration", "wuji_app", "wuji_pod")
    }
    bootstrap_password = secrets.token_urlsafe(36)
    database = {
        "host": f"postgres.{namespace}.svc", "port": 5432, "dbname": "wuji_vnext"
    }
    lock = shipped_worker_lock_digest()
    published_at = now.isoformat().replace("+00:00", "Z")
    owner = owner_template(
        {
            "database": database,
            "roles": roles,
            "owner": [tenant, project, "catalog-only"],
            "identity": {"issuer": issuer, "audience": audience},
            "ca_file": "/config/ca.crt",
            "public_key_file": "/config/identity.pub",
            "operator_token_file": "/run/wuji/bootstrap/operator.token",
            "operator_subject": "operator",
            "pod_controller_subject": "pod-controller",
        },
        mode="mechanism_synthetic",
        published_at=published_at,
        lock_digest=lock,
        namespace=namespace,
        model_gateway_url="http://127.0.0.1:8081/v1/chat/completions",
        client_model="synthetic-core-ctf",
        upstream_model="synthetic-core-ctf",
        task_key_ref="core-model-key",
        model_capability_ref="synthetic-core-ctf-v1",
        kali_image_digest=images["kali"].rsplit("@sha256:", 1)[1],
        architecture=architecture,
        action_signing_key_ref="signing-key",
        action_signing_kid="deployment-key",
        explore_limit=explore_limit,
        pool_capacity=pool_capacity,
    )
    bootstrap = {
        "schema_version": "wuji.core-ctf-bootstrap.v1",
        "database": {**database, "user": "bootstrap", "password": bootstrap_password},
        "roles": roles, "ca_file": "/config/ca.crt",
        "tenant_id": tenant, "project_id": project, "operator_subject": "operator",
    }
    capture_client = {
        "ca.crt": tls_bytes["ca.crt"], "tls.crt": client_cert,
        "tls.key": client_key, "collector.token": tokens["collector"],
    }
    objects = [
        {
            "apiVersion": "v1", "kind": "Namespace",
            "metadata": {
                "name": namespace, "labels": {
                    **LABELS,
                    "pod-security.kubernetes.io/enforce": "privileged",
                    "pod-security.kubernetes.io/audit": "restricted",
                },
            },
        },
        *render_helpers.postgres(
            images["postgres"], tls_bytes, bootstrap_password.encode(),
            namespace=namespace, architecture=architecture,
        ),
        *render_helpers.platform_storage(namespace=namespace),
    ]
    for item in objects:
        if item["kind"] != "Namespace":
            item["metadata"]["labels"] = dict(LABELS)
            template = item.get("spec", {}).get("template")
            if isinstance(template, dict):
                template.setdefault("metadata", {}).setdefault("labels", {}).update(LABELS)

    public_data = {"ca.crt": tls_bytes["ca.crt"].decode(), "identity.pub": public.decode()}
    bootstrap_secret = _secret(
        "core-bootstrap-input", namespace,
        {"config.json": json.dumps(bootstrap, sort_keys=True).encode()},
    )
    owner_secret = _secret(
        "core-owner", namespace,
        {
            "config.json": json.dumps(owner, sort_keys=True).encode(),
            "operator.token": tokens["operator"],
        },
    )
    bootstrap_job = _job(
        "core-bootstrap", namespace, images["platform"],
        ["python", "/opt/wuji/ops/vnext/core_ctf_bootstrap.py"],
        [
            {"name": "input", "mountPath": "/run/wuji/bootstrap", "readOnly": True},
            {"name": "public", "mountPath": "/config", "readOnly": True},
        ],
        [
            {"name": "input", "secret": {"secretName": "core-bootstrap-input", "defaultMode": 0o440}},
            {"name": "public", "configMap": {"name": "core-public"}},
        ],
        architecture=architecture,
    )
    catalog_job = _job(
        "core-catalog", namespace, images["platform"],
        ["python", "/opt/wuji/ops/vnext/core_ctf_catalog.py"],
        [
            {"name": "input", "mountPath": "/run/wuji/bootstrap", "readOnly": True},
            {"name": "public", "mountPath": "/config", "readOnly": True},
        ],
        [
            {"name": "input", "secret": {"secretName": "core-owner", "defaultMode": 0o440}},
            {"name": "public", "configMap": {"name": "core-public"}},
        ],
        architecture=architecture,
    )
    catalog_job["spec"]["template"]["spec"]["containers"][0]["env"] = [{
        "name": "WUJI_CORE_CTF_OWNER_CONFIG", "value": "/run/wuji/bootstrap/config.json"
    }]
    foundation = {
        "apiVersion": "v1", "kind": "List",
        "items": [*objects, _configmap("core-public", namespace, public_data), bootstrap_secret, owner_secret],
    }

    base = {
        "schema_version": "wuji.deployment.v1",
        "database_file": "/run/wuji/credentials/database.json",
        "public_key_file": "/config/identity.pub",
        "issuer": issuer, "audience": audience,
        "service_token_file": "/run/wuji/credentials/service.token",
        "ca_file": "/config/ca.crt", "profiles_file": "/config/profiles.json",
        "worker_lock_digest": lock, "artifact_max_bytes": 67_108_864,
    }
    platform_objects = _rbac(namespace)
    credential_encryption = secrets.token_bytes(32)
    role_specs = (
        ("runtime", "pod-controller", "wuji_pod"),
        ("api", "operator", "wuji_app"),
        ("scheduler", "scheduler", "wuji_app"),
        ("gates", "gate", "wuji_app"),
    )
    for name, subject, database_role in role_specs:
        settings = {**base, "role": name}
        credentials = {
            "service.token": tokens[subject],
            "database.json": json.dumps({
                **database, "user": database_role, "password": roles[database_role]
            }, sort_keys=True).encode(),
        }
        if name != "scheduler":
            credentials.update({"tls.crt": tls_bytes[name + ".crt"], "tls.key": tls_bytes[name + ".key"]})
        if name in {"runtime", "scheduler"}:
            credentials.update({"signing.key": private, "encryption.key": credential_encryption})
            settings["secret_refs"] = {
                "signing-key": "/run/wuji/credentials/signing.key",
                "encryption-key": "/run/wuji/credentials/encryption.key",
            }
        if name == "runtime":
            credentials["receiver.token"] = tokens["receiver"]
            settings.update(
                max_transport_bytes=8_388_608,
                task_ids=[], work_kinds=["reason", "explore", "report"],
                receiver_token_file="/run/wuji/credentials/receiver.token",
                host_origin=f"https://runtime.{namespace}.svc:8443",
                model_gate_url=f"https://gates.{namespace}.svc:8443/internal/v2/model",
                tool_gate_url=f"https://gates.{namespace}.svc:8443/internal/v2/tool-calls",
                session_transport=True, public_commands=True, public_approvals=True,
                journal_path="/var/lib/wuji/platform/state/dispatch.sqlite3",
                spool_directory="/var/lib/wuji/platform/state/intake",
                pod_runtime={
                    "tasks": [],
                    "service_names": {"agent": "task-agent", "kali": "task-kali"},
                    "capture_client": {
                        "ca_file": "/run/wuji/capture-runtime-client/ca.crt",
                        "certificate_file": "/run/wuji/capture-runtime-client/tls.crt",
                        "private_key_file": "/run/wuji/capture-runtime-client/tls.key",
                        "collector_token_file": "/run/wuji/capture-runtime-client/collector.token",
                    },
                    "kubernetes_url": "https://kubernetes.default.svc",
                    "kubernetes_ca_file": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
                    "kubernetes_token_file": "/var/run/secrets/kubernetes.io/serviceaccount/token",
                },
            )
        if name == "gates":
            credentials.update({
                "collector.token": tokens["collector"],
                "signing.key": private,
                "model.key": b"synthetic-local-only",
            })
            settings.update(
                tool_gate_url=f"https://gates.{namespace}.svc:8443/internal/v2/tool-calls",
                secret_refs={
                    "signing-key": "/run/wuji/credentials/signing.key",
                    "core-model-key": "/run/wuji/credentials/model.key",
                },
                executors=[],
            )
        platform_objects.extend([
            _configmap(name + "-config", namespace, {
                "deployment.json": json.dumps(settings, sort_keys=True),
                "profiles.json": "[]", **public_data,
            }),
            _secret(name + "-credentials", namespace, credentials),
        ])
        command = (
            ["python", f"/opt/wuji/services/wuji-{name}/main.py", "--factory", f"deployment:build_{name}"]
            if name in {"runtime", "api", "scheduler"}
            else ["python", "-m", "uvicorn", "gate_deployment:build_gates", "--factory", "--host", "0.0.0.0"]
        )
        if name != "scheduler":
            command += ["--port", "8443", "--ssl-certfile", "/run/wuji/credentials/tls.crt", "--ssl-keyfile", "/run/wuji/credentials/tls.key"]
        deployment = render_helpers.platform(
            name, images["platform"], command,
            synthetic_model_image=images["platform"] if name == "gates" else None,
            namespace=namespace, architecture=architecture,
        )
        deployment["metadata"]["labels"] = dict(LABELS)
        deployment["spec"]["template"]["metadata"]["labels"].update(LABELS)
        if name == "runtime":
            pod = deployment["spec"]["template"]["spec"]
            pod["containers"][0]["volumeMounts"].append({
                "name": "capture-runtime-client", "mountPath": "/run/wuji/capture-runtime-client", "readOnly": True
            })
            pod["volumes"].append({
                "name": "capture-runtime-client", "secret": {"secretName": "core-capture-runtime", "defaultMode": 0o440}
            })
        platform_objects.append(deployment)
        if name != "scheduler":
            service = render_helpers.service(name, 8443, namespace=namespace)
            service["metadata"]["labels"] = dict(LABELS)
            platform_objects.append(service)

    platform_objects.extend([
        _secret("core-capture-runtime", namespace, capture_client),
        _secret("core-ca-private", namespace, {"ca.crt": tls_bytes["ca.crt"], "ca.key": tls_bytes["ca.key"]}),
        _secret("task-agent-auth", namespace, {"tls.crt": tls_bytes["task-agent.crt"], "tls.key": tls_bytes["task-agent.key"]}),
        _secret("core-launch-credentials", namespace, {
            "service.token": tokens["launch"],
            "signing.key": private,
            "receiver.token": tokens["receiver"],
        }),
        _secret("core-gates-auth", namespace, {"collector.token": tokens["collector"]}),
    ])
    launch_settings = {
        "schema_version": "wuji.launch-deployment.v1",
        "owner_config_file": "/run/wuji/bootstrap/config.json",
        "service_token_file": "/run/wuji/deployment-signing/service.token",
        "namespace": namespace,
        "agent_image": images["agent"], "kali_image": images["kali"],
        "capture_image": images["capture"],
        "capture_ca_cert_file": "/run/wuji/capture-runtime-client/ca.crt",
        "runtime_origin": f"https://runtime.{namespace}.svc:8443",
        "gate_url": f"https://gates.{namespace}.svc:8443",
        "evidence_ref": "core-ctf-local-mechanism",
    }
    platform_objects.append(_configmap("core-launch-config", namespace, {
        "launch.json": json.dumps(launch_settings, sort_keys=True), **public_data,
    }))
    launch_mounts = [
        ("config", "core-launch-config", "/config"),
        ("owner", "core-owner", "/run/wuji/bootstrap"),
        ("deployment", "core-launch-credentials", "/run/wuji/deployment-signing"),
        ("agent-auth", "task-agent-auth", "/run/wuji/task-agent-auth"),
        ("gates-auth", "core-gates-auth", "/run/wuji/gates-credentials"),
        ("capture-ca", "core-ca-private", "/run/wuji/capture-ca"),
        ("capture-runtime", "core-capture-runtime", "/run/wuji/capture-runtime-client"),
    ]
    platform_objects.append({
        "apiVersion": "apps/v1", "kind": "Deployment", "metadata": _metadata("core-launch", namespace),
        "spec": {
            "replicas": 1, "strategy": {"type": "Recreate"},
            "selector": {"matchLabels": {**LABELS, "wuji.dev/service": "core-launch"}},
            "template": {"metadata": {"labels": {**LABELS, "wuji.dev/service": "core-launch"}}, "spec": {
                "serviceAccountName": "core-launch", "automountServiceAccountToken": True,
                "nodeSelector": {"kubernetes.io/arch": architecture},
                "securityContext": {"runAsNonRoot": True, "fsGroup": 10000, "seccompProfile": {"type": "RuntimeDefault"}},
                "containers": [{
                    "name": "launch", "image": images["platform"],
                    "command": ["python", "/opt/wuji/services/wuji-launch/main.py", "--batch-limit", "1"],
                    "env": [{"name": "WUJI_LAUNCH_CONFIG", "value": "/config/launch.json"},
                            {"name": "POD_UID", "valueFrom": {"fieldRef": {"fieldPath": "metadata.uid"}}}],
                    "securityContext": render_helpers.security(10001),
                    "volumeMounts": [
                        {"name": name, "mountPath": path, "readOnly": True}
                        for name, _secret_name, path in launch_mounts
                    ] + [{"name": "tmp", "mountPath": "/tmp"}],
                }],
                "volumes": [
                    {"name": name, "configMap": {"name": secret_name}}
                    if name == "config" else
                    {"name": name, "secret": {"secretName": secret_name, "defaultMode": 0o440}}
                    for name, secret_name, _path in launch_mounts
                ] + [{"name": "tmp", "emptyDir": {"sizeLimit": "64Mi"}}],
            }},
        },
    })
    target_labels = {**LABELS, "wuji.dev/service": "core-target"}
    platform_objects.extend([
        _configmap("core-target-data", namespace, {"answer.json": json.dumps({"answer": "core-mechanism-ok"})}),
        {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": _metadata("core-target", namespace),
         "spec": {"replicas": 1, "selector": {"matchLabels": target_labels},
                  "template": {"metadata": {"labels": target_labels}, "spec": {
                      "automountServiceAccountToken": False,
                      "nodeSelector": {"kubernetes.io/arch": architecture},
                      "containers": [{"name": "target", "image": images["platform"],
                          "command": ["python", "-m", "http.server", "8080", "--directory", "/fixture"],
                          "securityContext": render_helpers.security(10001),
                          "volumeMounts": [{"name": "data", "mountPath": "/fixture", "readOnly": True}]}],
                      "volumes": [{"name": "data", "configMap": {"name": "core-target-data"}}],
                  }}}},
        {"apiVersion": "v1", "kind": "Service", "metadata": _metadata("core-target", namespace),
         "spec": {"selector": target_labels, "ports": [{"name": "http", "port": 8080, "targetPort": 8080}]}},
    ])

    platform_objects.append(_secret("core-web-credentials", namespace, {
        "identity.key": private,
        "session.key": secrets.token_bytes(32),
        "password.json": password_document,
    }))
    platform_objects.extend(web_helpers.build_web_manifests(
        images["web"],
        auth_entrypoint="/auth/login",
        gateway_image=images["platform"],
        gateway_api_base_url=f"https://api.{namespace}.svc:8443",
        gateway_secret_name="core-web-credentials",
        gateway_ca_config_map="core-public",
        gateway_auth_mode="local_password",
        identity_issuer=issuer,
        identity_audience=audience,
        tenant_id=tenant,
        project_id=project,
        display_name="Wuji 开发者",
        allowed_origins=(f"http://127.0.0.1:{web_port}", f"http://localhost:{web_port}"),
        namespace=namespace,
        service_name="core-web",
        session_claim_name="core-web-sessions",
        architecture=architecture,
        service_port=web_port,
        deployment_labels=LABELS,
    ))

    _json(output / "foundation.json", foundation)
    _json(output / "bootstrap-job.json", {"apiVersion": "v1", "kind": "List", "items": [bootstrap_job]})
    _json(output / "catalog-job.json", {"apiVersion": "v1", "kind": "List", "items": [catalog_job]})
    _json(output / "platform.json", {"apiVersion": "v1", "kind": "List", "items": platform_objects})
    _json(output / "images.json", {
        "images": images,
        "source_revision": source_revisions["platform"],
        "image_source_revisions": source_revisions,
    })
    _json(output / "public.json", {
        "namespace": namespace, "tenant_id": tenant, "project_id": project,
        "mode": "mechanism_synthetic", "task_count": 0,
        "apply_order": [
            "foundation.json", "bootstrap-job.json", "catalog-job.json", "platform.json"
        ],
        "start_url": f"http://core-target.{namespace}.svc:8080/answer.json",
        "web_url": f"http://127.0.0.1:{web_port}/",
        "ca_sha256": sha256(tls_bytes["ca.crt"]).hexdigest(),
    })
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-directory", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--namespace", default="wuji-core-ctf")
    parser.add_argument("--architecture", choices=("amd64", "arm64"), default="amd64")
    parser.add_argument("--password-credential", type=Path, required=True)
    parser.add_argument("--web-port", type=int, default=44181)
    parser.add_argument("--explore-limit", type=int, required=True)
    parser.add_argument("--pool-capacity", type=int, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    inventory = json.loads(args.images.read_bytes())
    output = render(
        args.state_directory, inventory,
        namespace=args.namespace, architecture=args.architecture,
        password_credential=args.password_credential, web_port=args.web_port,
        explore_limit=args.explore_limit, pool_capacity=args.pool_capacity,
    )
    print(json.dumps({"event": "core_ctf_platform_rendered", "configuration": str(output)}))


if __name__ == "__main__":
    main()
