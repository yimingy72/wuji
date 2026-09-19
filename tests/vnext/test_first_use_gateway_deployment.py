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
        self.objects = {
            ("Namespace", gateway.NAMESPACE): {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {"name": gateway.NAMESPACE},
            },
            ("Secret", gateway.PROVIDER_SECRET): {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": gateway.PROVIDER_SECRET, "namespace": gateway.NAMESPACE},
                "data": {
                    gateway.PROVIDER_KEY: base64.b64encode(b"provider-fixture-value").decode()
                },
            },
        }
        self.operations = []
        self.sql_inputs = []
        self.resource_version = 0

    def get(self, kind, name):
        value = self.objects.get((kind, name))
        return copy.deepcopy(value) if value is not None else None

    def _store(self, resource):
        value = copy.deepcopy(resource)
        if value["kind"] == "Secret" and "stringData" in value:
            value["data"] = {
                key: base64.b64encode(item.encode()).decode()
                for key, item in value.pop("stringData").items()
            }
        self.resource_version += 1
        value.setdefault("metadata", {})["resourceVersion"] = str(self.resource_version)
        value["metadata"].setdefault("uid", f"fixture-{self.resource_version}")
        self.objects[(value["kind"], value["metadata"]["name"])] = value

    def create(self, resource):
        identity = (resource["kind"], resource["metadata"]["name"])
        if identity in self.objects:
            raise gateway.DeploymentError("fixture_conflict", "resource create failed")
        self.operations.append(("create", *identity))
        self._store(resource)

    def replace(self, resource):
        identity = (resource["kind"], resource["metadata"]["name"])
        self.operations.append(("replace", *identity))
        self._store(resource)

    def reconcile_database(self, password):
        self.operations.append(("exec", "PostgreSQL", "postgres"))
        self.sql_inputs.append(gateway.database_sql(password))

    def wait_for_rollout(self):
        self.operations.append(("read", "Deployment", gateway.NAME))


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
    assert result["endpoint"] == "https://first-use-litellm.wuji-vnext-test.svc:4000"
    assert "provider-fixture-value" not in output.out
    assert "database.password" not in output.out
    assert "master.key" not in output.out


def test_reconcile_creates_stable_secrets_database_and_tls_without_rotating_ca(tmp_path):
    ca_directory = tmp_path / "tls"
    _ca(ca_directory)
    ca_before = {
        name: sha256((ca_directory / name).read_bytes()).hexdigest()
        for name in ("ca.crt", "ca.key")
    }
    client = FakeClient()
    deployer = gateway.GatewayDeployer(client, ca_directory)

    first = deployer.reconcile()
    private_before = copy.deepcopy(client.objects[("Secret", gateway.PRIVATE_SECRET)])
    tls_before = copy.deepcopy(client.objects[("Secret", gateway.TLS_SECRET)])
    second = deployer.reconcile()

    assert first["secrets"][:2] == [
        {"name": gateway.PRIVATE_SECRET, "action": "created"},
        {"name": gateway.TLS_SECRET, "action": "created"},
    ]
    assert second["secrets"][:2] == [
        {"name": gateway.PRIVATE_SECRET, "action": "reused"},
        {"name": gateway.TLS_SECRET, "action": "reused"},
    ]
    assert client.objects[("Secret", gateway.PRIVATE_SECRET)]["data"] == private_before["data"]
    assert client.objects[("Secret", gateway.TLS_SECRET)]["data"] == tls_before["data"]
    assert not any(action == "replace" and kind == "Secret" for action, kind, _ in client.operations)
    assert not any(action == "apply" for action, *_ in client.operations)
    assert all(
        gateway.LAST_APPLIED not in value.get("metadata", {}).get("annotations", {})
        for (kind, _), value in client.objects.items()
        if kind == "Secret"
    )

    private = client.objects[("Secret", gateway.PRIVATE_SECRET)]
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

    tls = client.objects[("Secret", gateway.TLS_SECRET)]
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
    assert client.objects[("Secret", gateway.PROVIDER_SECRET)]["data"] == {
        gateway.PROVIDER_KEY: base64.b64encode(b"provider-fixture-value").decode()
    }


def test_unknown_same_name_object_is_never_overwritten(tmp_path):
    ca_directory = tmp_path / "tls"
    _ca(ca_directory)
    client = FakeClient()
    client.objects[("ConfigMap", gateway.CONFIG_NAME)] = {
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
        gateway.GatewayDeployer(client, ca_directory).reconcile()
    assert caught.value.code == "owner_conflict"
    assert client.objects[("ConfigMap", gateway.CONFIG_NAME)]["data"] == {
        "config.yaml": "foreign"
    }
    assert not any(action == "replace" for action, *_ in client.operations)
    assert not any(action in {"create", "exec"} for action, *_ in client.operations)


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
