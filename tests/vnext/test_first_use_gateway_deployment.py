"""Focused offline checks for the first-use LiteLLM Kubernetes owner."""

from __future__ import annotations

import base64
import copy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import pytest


def test_execute_refuses_unpublished_persistent_image_without_cluster_calls(monkeypatch, capsys):
    monkeypatch.setattr(gateway, "PERSISTENCE_IMAGE_READY", False)
    monkeypatch.setattr(gateway.GatewayDeployer, "reconcile", lambda self: pytest.fail("unpublished image touched the cluster"))
    assert gateway.main(["--execute"]) == 1
    assert json.loads(capsys.readouterr().out)["error"] == "persistent_image_not_published"


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "first_use_gateway_deployment",
    ROOT / "scripts" / "vnext" / "first_use_gateway.py",
)
gateway = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gateway
SPEC.loader.exec_module(gateway)


def _ca(directory: Path) -> None:
    directory.mkdir(parents=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Wuji fixture CA")])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=7))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(key, hashes.SHA256())
    )
    (directory / "ca.crt").write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    (directory / "ca.key").write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


class FakeClient:
    def __init__(self):
        password = "D" * 48
        private_data = {
            "master.key": base64.b64encode(("sk-" + "M" * 48).encode()).decode(),
            "database.password": base64.b64encode(password.encode()).decode(),
            "database.url": base64.b64encode(gateway.database_url(password).encode()).decode(),
        }
        self.objects = {
            (gateway.CORE_NAMESPACE, "Secret", gateway.PRIVATE_SECRET): {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {
                    "name": gateway.PRIVATE_SECRET,
                    "namespace": gateway.CORE_NAMESPACE,
                    "uid": "legacy-private-uid",
                    "resourceVersion": "legacy-private-rv",
                    "labels": {
                        gateway.OWNER_LABEL: gateway.OWNER,
                        "app.kubernetes.io/name": gateway.NAME,
                        "app.kubernetes.io/part-of": "wuji",
                    },
                },
                "type": "Opaque",
                "immutable": True,
                "data": private_data,
            },
            (gateway.CORE_NAMESPACE, "Secret", gateway.PROVIDER_SECRET): {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {
                    "name": gateway.PROVIDER_SECRET,
                    "namespace": gateway.CORE_NAMESPACE,
                    "uid": "legacy-provider-uid",
                    "resourceVersion": "legacy-provider-rv",
                    "labels": copy.deepcopy(gateway.PROVIDER_LABELS),
                },
                "type": "Opaque",
                "data": {
                    gateway.PROVIDER_KEY: base64.b64encode(b"provider-fixture-value").decode()
                },
            },
        }
        self.operations = []
        self.sql_inputs = []
        self.resource_version = 0

    def _get(self, namespace, kind, name):
        value = self.objects.get((namespace, kind, name))
        return copy.deepcopy(value) if value is not None else None

    def get_model(self, kind, name):
        return self._get(gateway.MODEL_NAMESPACE, kind, name)

    def get_core(self, kind, name):
        return self._get(gateway.CORE_NAMESPACE, kind, name)

    def get_namespace(self):
        return self._get(None, "Namespace", gateway.MODEL_NAMESPACE)

    def _store(self, resource):
        value = copy.deepcopy(resource)
        if value["kind"] == "Secret" and "stringData" in value:
            value["data"] = {
                key: base64.b64encode(item.encode()).decode()
                for key, item in value.pop("stringData").items()
            }
        self.resource_version += 1
        metadata = value.setdefault("metadata", {})
        metadata["resourceVersion"] = str(self.resource_version)
        metadata.setdefault("uid", f"fixture-{self.resource_version}")
        namespace = None if value["kind"] == "Namespace" else metadata["namespace"]
        self.objects[(namespace, value["kind"], metadata["name"])] = value

    def _create(self, resource):
        metadata = resource["metadata"]
        namespace = None if resource["kind"] == "Namespace" else metadata["namespace"]
        identity = (namespace, resource["kind"], metadata["name"])
        if identity in self.objects:
            raise gateway.DeploymentError("fixture_conflict", "resource create failed")
        self.operations.append(("create", resource["kind"], metadata["name"], namespace))
        self._store(resource)

    def create_model(self, resource):
        self._create(resource)

    def create_namespace(self, resource):
        self._create(resource)

    def _replace(self, resource):
        metadata = resource["metadata"]
        namespace = metadata["namespace"]
        self.operations.append(("replace", resource["kind"], metadata["name"], namespace))
        self._store(resource)

    def replace_model(self, resource):
        self._replace(resource)

    def replace_core(self, resource):
        self._replace(resource)

    def reconcile_database(self, password):
        self.operations.append(("exec", "PostgreSQL", "postgres"))
        self.sql_inputs.append(gateway.database_sql(password))

    def wait_for_rollout(self):
        self.operations.append(("read", "Deployment", gateway.NAME))

    def delete_core_provider_with_preconditions(self, *, uid, resource_version):
        provider = self.objects[(gateway.CORE_NAMESPACE, "Secret", gateway.PROVIDER_SECRET)]
        assert provider["metadata"]["uid"] == uid
        assert provider["metadata"]["resourceVersion"] == resource_version
        self.operations.append(("delete", "Secret", gateway.PROVIDER_SECRET, gateway.CORE_NAMESPACE))
        del self.objects[(gateway.CORE_NAMESPACE, "Secret", gateway.PROVIDER_SECRET)]


def _container(manifests):
    deployment = next(item for item in manifests if item["kind"] == "Deployment")
    return deployment, deployment["spec"]["template"]["spec"]["containers"][0]


def test_manifest_is_reproducible_tls_only_and_provider_isolated():
    first = gateway.render_manifests()
    second = gateway.render_manifests()
    assert gateway.manifest_digest(first) == gateway.manifest_digest(second)
    assert gateway.render_json_documents(first) == gateway.render_json_documents(second)
    assert [item["kind"] for item in first] == ["ConfigMap", "Deployment", "Service"]
    assert all(item["metadata"]["labels"][gateway.OWNER_LABEL] == gateway.OWNER for item in first)
    assert all(item["metadata"]["namespace"] == gateway.MODEL_NAMESPACE for item in first)
    assert gateway.CORE_NAMESPACE not in gateway.render_json_documents(first)
    assert gateway.DATABASE_HOST == "postgres.wuji-vnext-test.svc"
    postgres_command = gateway.postgres_exec_command()
    assert postgres_command[postgres_command.index("--namespace") + 1] == gateway.CORE_NAMESPACE

    deployment, container = _container(first)
    pod = deployment["spec"]["template"]["spec"]
    assert container["image"] == gateway.IMAGE
    assert "command" not in container  # retain the image's sole litellm entrypoint
    assert container["securityContext"] == {
        "runAsUser": 10001,
        "runAsGroup": 10000,
        "runAsNonRoot": True,
        "allowPrivilegeEscalation": False,
        "readOnlyRootFilesystem": True,
        "capabilities": {"drop": ["ALL"]},
    }
    assert pod["securityContext"]["fsGroup"] == 10000
    assert pod["automountServiceAccountToken"] is False
    assert len(pod["containers"]) == 1
    assert container["readinessProbe"]["httpGet"] == {
        "scheme": "HTTPS",
        "path": "/health/readiness",
        "port": "https",
    }
    assert container["startupProbe"] == {
        "httpGet": {
            "scheme": "HTTPS",
            "path": "/health/liveliness",
            "port": "https",
        },
        "periodSeconds": 5,
        "timeoutSeconds": 3,
        "failureThreshold": 120,
    }
    assert container["livenessProbe"]["httpGet"] == {
        "scheme": "HTTPS",
        "path": "/health/liveliness",
        "port": "https",
    }

    env = {item["name"]: item for item in container["env"]}
    assert env["DEEPSEEK_API_KEY"]["valueFrom"]["secretKeyRef"] == {
        "name": gateway.PROVIDER_SECRET,
        "key": gateway.PROVIDER_KEY,
    }
    assert env["LITELLM_MASTER_KEY"]["valueFrom"]["secretKeyRef"] == {
        "name": gateway.PRIVATE_SECRET,
        "key": "master.key",
    }
    assert env["WUJI_LITELLM_DATABASE_URL"]["valueFrom"]["secretKeyRef"] == {
        "name": gateway.PRIVATE_SECRET,
        "key": "database.url",
    }
    assert env["DATABASE_URL"]["value"] == "$(WUJI_LITELLM_DATABASE_URL)&sslcert=/run/wuji/tls/ca.crt"
    names = [item["name"] for item in container["env"]]
    assert names.index("WUJI_LITELLM_DATABASE_URL") < names.index("DATABASE_URL")
    assert not any(item.get("value") == "database.password" for item in container["env"])
    mounted_secrets = {
        item["secret"]["secretName"]
        for item in pod["volumes"]
        if "secret" in item
    }
    assert mounted_secrets == {gateway.TLS_SECRET}
    assert gateway.PROVIDER_SECRET not in mounted_secrets
    assert gateway.PRIVATE_SECRET not in mounted_secrets

    service = next(item for item in first if item["kind"] == "Service")
    assert service["spec"]["type"] == "ClusterIP"
    assert service["spec"]["ports"] == [
        {"name": "https", "port": 4000, "targetPort": "https", "protocol": "TCP"}
    ]
    config = next(item for item in first if item["kind"] == "ConfigMap")["data"]["config.yaml"]
    assert "ops.vnext.litellm_hooks.proxy_handler_instance" in config
    assert "thinking disabled" in config


def test_default_cli_is_offline_dry_run_and_emits_no_secret(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("dry-run invoked a process")

    monkeypatch.setattr(gateway.subprocess, "run", forbidden)
    assert gateway.main([]) == 0
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert output.err == ""
    assert result["mode"] == "dry-run"
    assert result["mutations"] is False
    assert result["endpoint"] == "https://first-use-litellm.wuji-first-use-model.svc:4000"
    assert result["core_namespace"] == gateway.CORE_NAMESPACE
    assert "provider-fixture-value" not in output.out
    assert "database.password" not in output.out
    assert "master.key" not in output.out

    assert gateway.main(["--isolate-provider"]) == 1
    refused = json.loads(capsys.readouterr().out)
    assert refused["error"] == "execute_required"


def test_reconcile_creates_stable_secrets_database_and_tls_without_rotating_ca(tmp_path):
    ca_directory = tmp_path / "tls"
    _ca(ca_directory)
    ca_before = {
        name: sha256((ca_directory / name).read_bytes()).hexdigest()
        for name in ("ca.crt", "ca.key")
    }
    client = FakeClient()
    deployer = gateway.GatewayDeployer(client, ca_directory)

    legacy_private = copy.deepcopy(
        client.objects[(gateway.CORE_NAMESPACE, "Secret", gateway.PRIVATE_SECRET)]
    )
    first = deployer.reconcile(isolate_provider=True)
    private_key = (gateway.MODEL_NAMESPACE, "Secret", gateway.PRIVATE_SECRET)
    tls_key = (gateway.MODEL_NAMESPACE, "Secret", gateway.TLS_SECRET)
    provider_key = (gateway.MODEL_NAMESPACE, "Secret", gateway.PROVIDER_SECRET)
    private_before = copy.deepcopy(client.objects[private_key])
    tls_before = copy.deepcopy(client.objects[tls_key])
    second = deployer.reconcile()

    assert first["namespace_action"] == "created"
    assert first["secrets"][:2] == [
        {"name": gateway.PRIVATE_SECRET, "action": "created"},
        {"name": gateway.TLS_SECRET, "action": "created"},
    ]
    assert second["secrets"][:2] == [
        {"name": gateway.PRIVATE_SECRET, "action": "reused"},
        {"name": gateway.TLS_SECRET, "action": "reused"},
    ]
    assert first["secrets"][2] == {"name": gateway.PROVIDER_SECRET, "action": "created"}
    assert client.objects[private_key]["data"] == private_before["data"]
    assert client.objects[private_key]["data"] == legacy_private["data"]
    assert client.objects[tls_key]["data"] == tls_before["data"]
    assert not any(action == "replace" and kind == "Secret" for action, kind, *_ in client.operations)
    assert not any(action == "apply" for action, *_ in client.operations)
    assert all(
        gateway.LAST_APPLIED not in value.get("metadata", {}).get("annotations", {})
        for (_, kind, _), value in client.objects.items()
        if kind == "Secret"
    )

    private = client.objects[private_key]
    assert set(private["data"]) == gateway.PRIVATE_KEYS
    db_password = base64.b64decode(private["data"]["database.password"]).decode()
    db_url = base64.b64decode(private["data"]["database.url"]).decode()
    assert db_url == gateway.database_url(db_password)
    assert "sslmode=require" in db_url
    assert "sslaccept=strict" in db_url
    assert "sslrootcert=/run/wuji/tls/ca.crt" in db_url
    assert len(client.sql_inputs) == 2
    assert all(b"NOSUPERUSER" in sql and b"CREATE DATABASE" in sql for sql in client.sql_inputs)
    assert all(b"LiteLLM_VerificationToken" not in sql for sql in client.sql_inputs)

    tls = client.objects[tls_key]
    leaf = x509.load_pem_x509_certificate(base64.b64decode(tls["data"]["tls.crt"]))
    assert leaf.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value.digest
    assert leaf.extensions.get_extension_for_class(x509.AuthorityKeyIdentifier).value.key_identifier
    sans = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert gateway.GATEWAY_HOST in sans.get_values_for_type(x509.DNSName)
    assert {
        name: sha256((ca_directory / name).read_bytes()).hexdigest()
        for name in ("ca.crt", "ca.key")
    } == ca_before
    assert "ca.key" not in tls["data"]

    serialized_results = json.dumps([first, second], sort_keys=True)
    assert db_password not in serialized_results
    assert base64.b64decode(private["data"]["master.key"]).decode() not in serialized_results
    assert client.objects[provider_key]["metadata"]["labels"] == gateway.PROVIDER_LABELS
    assert client.objects[provider_key]["data"] == {
        gateway.PROVIDER_KEY: base64.b64encode(b"provider-fixture-value").decode()
    }
    assert client.objects[(gateway.CORE_NAMESPACE, "Secret", gateway.PROVIDER_SECRET)]["data"] == client.objects[provider_key]["data"]


def test_unknown_same_name_object_is_never_overwritten(tmp_path):
    ca_directory = tmp_path / "tls"
    _ca(ca_directory)
    client = FakeClient()
    client.objects[(None, "Namespace", gateway.MODEL_NAMESPACE)] = gateway._namespace_manifest()
    client.objects[(gateway.MODEL_NAMESPACE, "ConfigMap", gateway.CONFIG_NAME)] = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": gateway.CONFIG_NAME,
            "namespace": gateway.NAMESPACE,
            "resourceVersion": "foreign",
            "labels": {gateway.OWNER_LABEL: "someone-else"},
        },
        "data": {"config.yaml": "foreign"},
    }

    with pytest.raises(gateway.DeploymentError, match="unknown same-name") as caught:
        gateway.GatewayDeployer(client, ca_directory).reconcile(isolate_provider=True)
    assert caught.value.code == "owner_conflict"
    assert client.objects[(gateway.MODEL_NAMESPACE, "ConfigMap", gateway.CONFIG_NAME)]["data"] == {
        "config.yaml": "foreign"
    }
    assert not any(action == "replace" for action, *_ in client.operations)
    assert not any(action in {"create", "exec"} for action, *_ in client.operations)


def test_migration_provider_collision_and_regular_missing_provider_are_zero_write(tmp_path):
    ca_directory = tmp_path / "tls"
    _ca(ca_directory)

    regular = FakeClient()
    regular.objects[(None, "Namespace", gateway.MODEL_NAMESPACE)] = gateway._namespace_manifest()
    with pytest.raises(gateway.DeploymentError) as absent:
        gateway.GatewayDeployer(regular, ca_directory).reconcile()
    assert absent.value.code == "provider_secret_absent"
    assert regular.operations == []

    collision = FakeClient()
    collision.objects[(None, "Namespace", gateway.MODEL_NAMESPACE)] = gateway._namespace_manifest()
    collision.objects[(gateway.MODEL_NAMESPACE, "Secret", gateway.PROVIDER_SECRET)] = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": gateway.PROVIDER_SECRET,
            "namespace": gateway.MODEL_NAMESPACE,
            "labels": {"app.kubernetes.io/component": "unknown"},
        },
        "data": {
            gateway.PROVIDER_KEY: base64.b64encode(b"unknown-provider").decode()
        },
    }
    with pytest.raises(gateway.DeploymentError) as conflict:
        gateway.GatewayDeployer(collision, ca_directory).reconcile(
            isolate_provider=True
        )
    assert conflict.value.code == "provider_secret_invalid"
    assert collision.operations == []


def test_finalize_requires_ready_verified_digest_and_exact_legacy_metadata(tmp_path):
    ca_directory = tmp_path / "tls"
    _ca(ca_directory)
    client = FakeClient()
    result = gateway.GatewayDeployer(client, ca_directory).reconcile(
        isolate_provider=True
    )
    digest = result["manifest_sha256"]

    target_key = (gateway.MODEL_NAMESPACE, "Deployment", gateway.NAME)
    target = client.objects[target_key]
    target["metadata"]["generation"] = 7
    target["status"] = {
        "observedGeneration": 7,
        "availableReplicas": 0,
        "conditions": [{"type": "Available", "status": "False"}],
    }
    legacy = copy.deepcopy(
        next(
            item
            for item in gateway.render_manifests()
            if item["kind"] == "Deployment"
        )
    )
    legacy["metadata"].update(
        {
            "namespace": gateway.CORE_NAMESPACE,
            "uid": "legacy-deployment-uid",
            "resourceVersion": "legacy-deployment-rv",
            "generation": 4,
        }
    )
    client.objects[(gateway.CORE_NAMESPACE, "Deployment", gateway.NAME)] = legacy
    finalizer = gateway.IsolationFinalizer(client, ca_directory)
    arguments = {
        "expected_manifest_sha256": digest,
        "legacy_deployment_uid": "legacy-deployment-uid",
        "legacy_deployment_resource_version": "legacy-deployment-rv",
        "legacy_provider_uid": "legacy-provider-uid",
        "legacy_provider_resource_version": "legacy-provider-rv",
    }

    before = list(client.operations)
    with pytest.raises(gateway.DeploymentError) as not_ready:
        finalizer.finalize(**arguments)
    assert not_ready.value.code == "isolation_not_ready"
    assert client.operations == before

    target["status"] = {
        "observedGeneration": 7,
        "availableReplicas": 1,
        "conditions": [{"type": "Available", "status": "True"}],
    }
    with pytest.raises(gateway.DeploymentError) as wrong_digest:
        finalizer.finalize(**{**arguments, "expected_manifest_sha256": "0" * 64})
    assert wrong_digest.value.code == "isolation_not_ready"
    assert client.operations == before

    finalized = finalizer.finalize(**arguments)
    assert finalized["mode"] == "finalize-isolation"
    assert client.objects[(gateway.CORE_NAMESPACE, "Deployment", gateway.NAME)]["spec"]["replicas"] == 0
    assert (gateway.CORE_NAMESPACE, "Secret", gateway.PROVIDER_SECRET) not in client.objects
    assert (gateway.CORE_NAMESPACE, "Secret", gateway.PRIVATE_SECRET) in client.objects
    assert client.objects[(gateway.MODEL_NAMESPACE, "Secret", gateway.PROVIDER_SECRET)]["data"] == {
        gateway.PROVIDER_KEY: base64.b64encode(b"provider-fixture-value").decode()
    }


def test_database_password_is_stdin_only_and_subprocess_errors_are_sanitized():
    password = "A" * 48
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            1,
            stdout=("unsafe-" + password).encode(),
            stderr=("unsafe-" + password).encode(),
        )

    client = gateway.KubernetesClient(runner=runner)
    with pytest.raises(gateway.DeploymentError) as caught:
        client.reconcile_database(password)
    command, kwargs = calls[0]
    assert password not in " ".join(command)
    assert password.encode() in kwargs["input"]
    assert password not in str(caught.value)
    assert "unsafe" not in str(caught.value)
    assert "POSTGRES_PASSWORD" in " ".join(command)
    assert "DATABASE_URL" not in " ".join(command)


def test_reused_tls_rejects_expiry_and_mismatched_private_key(tmp_path, monkeypatch):
    directory = tmp_path / "ca"
    _ca(directory)
    cert, key, ca = gateway.sign_gateway_leaf(directory)
    resource = gateway._tls_secret(cert, key, ca)
    gateway.validate_existing_tls(resource, directory)
    _, another_key, _ = gateway.sign_gateway_leaf(directory)
    wrong_key = copy.deepcopy(resource)
    wrong_key["data"]["tls.key"] = base64.b64encode(another_key).decode()
    with pytest.raises(gateway.DeploymentError):
        gateway.validate_existing_tls(wrong_key, directory)

    class FutureDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz) + timedelta(days=8)

    monkeypatch.setattr(gateway, "datetime", FutureDatetime)
    with pytest.raises(gateway.DeploymentError):
        gateway.validate_existing_tls(resource, directory)


def test_database_replay_accepts_only_unmarked_database_with_exact_owned_role():
    sql = gateway.database_sql("A" * 48).decode()
    assert "database_owner IS DISTINCT FROM 'wuji_first_use_litellm'" in sql
    assert "database_marker IS NOT NULL AND database_marker IS DISTINCT FROM 'first-use-gateway-v1'" in sql
    assert "role_marker IS DISTINCT FROM 'first-use-gateway-v1'" in sql
    assert sql.index("role_marker IS DISTINCT") < sql.index("COMMENT ON DATABASE")
