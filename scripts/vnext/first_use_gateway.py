"""Provision the isolated first-use LiteLLM gateway without printing secrets.

The default CLI path is an offline, deterministic render.  ``--execute`` is
required before this module reads or writes the fixed docker-desktop namespace.
Secret values are sent to Kubernetes and PostgreSQL only over stdin; command
arguments, successful output, and sanitized failures contain metadata only.
"""

from __future__ import annotations

import argparse
import base64
import copy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import secrets
import subprocess
from typing import Any, Callable, Sequence
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[2]
CONTEXT = "docker-desktop"
NAMESPACE = "wuji-vnext-test"
OWNER_LABEL = "wuji.dev/credential-owner"
OWNER = "first-use-gateway-v1"

NAME = "first-use-litellm"
CONFIG_NAME = NAME + "-config"
PRIVATE_SECRET = NAME + "-private"
TLS_SECRET = NAME + "-tls"
PROVIDER_SECRET = "deepseek-provider-first-use"
PROVIDER_KEY = "DEEPSEEK_API_KEY"

PRIVATE_KEYS = frozenset({"master.key", "database.password", "database.url"})
TLS_KEYS = frozenset({"tls.crt", "tls.key", "ca.crt"})
DATABASE_ROLE = "wuji_first_use_litellm"
DATABASE_NAME = "wuji_first_use_litellm_20260919"
DATABASE_HOST = f"postgres.{NAMESPACE}.svc"
GATEWAY_HOST = f"{NAME}.{NAMESPACE}.svc"
IMAGE = (
    "127.0.0.1:56615/wuji-first-use-litellm@"
    "sha256:ff399bcda3d2b0ed0afd1f57ffd3af82ce45645775506507c553c8ed93fd206d"
)
# The original fixed image lacks the persistent Prisma client. Its replacement
# has been built locally, but registry publication failed when the host filled.
# Replace IMAGE with its verified RepoDigest before enabling this operator CLI.
PERSISTENCE_IMAGE_READY = False
CONFIG_TEMPLATE = ROOT / "templates" / "LITELLM_GATEWAY_DEEPSEEK.example.yaml"
LAST_APPLIED = "kubectl.kubernetes.io/last-applied-configuration"


class DeploymentError(RuntimeError):
    """A bounded error whose message is safe to return to an operator."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _metadata(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "namespace": NAMESPACE,
        "labels": {
            OWNER_LABEL: OWNER,
            "app.kubernetes.io/name": NAME,
            "app.kubernetes.io/part-of": "wuji",
        },
    }


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def database_url(password: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", password):
        raise DeploymentError("private_secret_invalid", "gateway private Secret is malformed")
    return (
        f"postgresql://{DATABASE_ROLE}:{quote(password, safe='')}@{DATABASE_HOST}:5432/"
        f"{DATABASE_NAME}?schema=public&sslmode=require&sslaccept=strict&"
        "sslrootcert=/run/wuji/tls/ca.crt"
    )


def render_manifests(config_text: str | None = None) -> list[dict[str, Any]]:
    """Return deterministic non-Secret objects for the fixed gateway."""

    if config_text is None:
        config_text = CONFIG_TEMPLATE.read_text(encoding="utf-8")
    if "ops.vnext.litellm_hooks.proxy_handler_instance" not in config_text:
        raise DeploymentError("config_invalid", "LiteLLM hook is absent from the fixed template")
    if "os.environ/DEEPSEEK_API_KEY" not in config_text:
        raise DeploymentError("config_invalid", "provider environment reference is absent")

    selector = {
        OWNER_LABEL: OWNER,
        "app.kubernetes.io/name": NAME,
    }
    container = {
        "name": "litellm",
        "image": IMAGE,
        "imagePullPolicy": "IfNotPresent",
        # Do not replace the image ENTRYPOINT: the only entrypoint remains litellm.
        "args": [
            "--ssl_certfile_path",
            "/run/wuji/tls/tls.crt",
            "--ssl_keyfile_path",
            "/run/wuji/tls/tls.key",
            "--enforce_prisma_migration_check",
            "--use_v2_migration_resolver",
        ],
        "env": [
            {
                "name": "DEEPSEEK_API_KEY",
                "valueFrom": {
                    "secretKeyRef": {"name": PROVIDER_SECRET, "key": PROVIDER_KEY}
                },
            },
            {
                "name": "LITELLM_MASTER_KEY",
                "valueFrom": {
                    "secretKeyRef": {"name": PRIVATE_SECRET, "key": "master.key"}
                },
            },
            {
                "name": "DATABASE_URL",
                "valueFrom": {
                    "secretKeyRef": {"name": PRIVATE_SECRET, "key": "database.url"}
                },
            },
            {"name": "TMPDIR", "value": "/tmp"},
            {"name": "LITELLM_TELEMETRY", "value": "False"},
            {"name": "DO_NOT_TRACK", "value": "1"},
        ],
        "ports": [{"name": "https", "containerPort": 4000, "protocol": "TCP"}],
        "securityContext": {
            "runAsUser": 10001,
            "runAsGroup": 10000,
            "runAsNonRoot": True,
            "allowPrivilegeEscalation": False,
            "readOnlyRootFilesystem": True,
            "capabilities": {"drop": ["ALL"]},
        },
        "volumeMounts": [
            {
                "name": "config",
                "mountPath": "/opt/litellm/config.yaml",
                "subPath": "config.yaml",
                "readOnly": True,
            },
            {"name": "tls", "mountPath": "/run/wuji/tls", "readOnly": True},
            {"name": "tmp", "mountPath": "/tmp"},
        ],
        # These endpoints do not send provider inference requests.  Readiness is
        # LiteLLM's database-aware readiness path; liveliness is process-only.
        "readinessProbe": {
            "httpGet": {"scheme": "HTTPS", "path": "/health/readiness", "port": "https"},
            "initialDelaySeconds": 10,
            "periodSeconds": 5,
            "timeoutSeconds": 3,
            "failureThreshold": 12,
        },
        "livenessProbe": {
            "httpGet": {"scheme": "HTTPS", "path": "/health/liveliness", "port": "https"},
            "initialDelaySeconds": 60,
            "periodSeconds": 15,
            "timeoutSeconds": 3,
            "failureThreshold": 4,
        },
        "resources": {
            "requests": {"cpu": "100m", "memory": "512Mi"},
            "limits": {"cpu": "2", "memory": "2Gi"},
        },
    }
    config = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": _metadata(CONFIG_NAME),
        "data": {"config.yaml": config_text},
    }
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": _metadata(NAME),
        "spec": {
            "replicas": 1,
            "strategy": {"type": "Recreate"},
            "selector": {"matchLabels": selector},
            "template": {
                "metadata": {"labels": {**_metadata(NAME)["labels"]}},
                "spec": {
                    "nodeSelector": {"kubernetes.io/arch": "arm64"},
                    "automountServiceAccountToken": False,
                    "terminationGracePeriodSeconds": 30,
                    "securityContext": {
                        "runAsNonRoot": True,
                        "runAsUser": 10001,
                        "runAsGroup": 10000,
                        "fsGroup": 10000,
                        "seccompProfile": {"type": "RuntimeDefault"},
                    },
                    "containers": [container],
                    "volumes": [
                        {"name": "config", "configMap": {"name": CONFIG_NAME}},
                        {
                            "name": "tls",
                            "secret": {"secretName": TLS_SECRET, "defaultMode": 0o440},
                        },
                        {"name": "tmp", "emptyDir": {"sizeLimit": "256Mi"}},
                    ],
                },
            },
        },
    }
    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": _metadata(NAME),
        "spec": {
            "type": "ClusterIP",
            "selector": selector,
            "ports": [
                {"name": "https", "port": 4000, "targetPort": "https", "protocol": "TCP"}
            ],
        },
    }
    return [config, deployment, service]


def manifest_digest(manifests: Sequence[dict[str, Any]]) -> str:
    return sha256(_canonical(list(manifests))).hexdigest()


def render_json_documents(manifests: Sequence[dict[str, Any]]) -> str:
    return "\n---\n".join(json.dumps(item, sort_keys=True, indent=2) for item in manifests) + "\n"


def postgres_exec_command() -> list[str]:
    """The admin password stays in the existing container environment."""

    return [
        "kubectl",
        "--context",
        CONTEXT,
        "--namespace",
        NAMESPACE,
        "exec",
        "-i",
        "deployment/postgres",
        "-c",
        "postgres",
        "--",
        "sh",
        "-ceu",
        'exec env PGPASSWORD="$POSTGRES_PASSWORD" psql --no-psqlrc --quiet '
        '--set=ON_ERROR_STOP=1 --dbname="$POSTGRES_DB" --username="$POSTGRES_USER"',
    ]


def database_sql(password: str) -> bytes:
    """Return idempotent owner-checked SQL; the password appears only in stdin."""

    if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", password):
        raise DeploymentError("private_secret_invalid", "gateway private Secret is malformed")
    marker = OWNER
    # The fixed identifiers and constrained password make the literals bounded;
    # doubling remains explicit so this helper stays safe if the alphabet widens.
    password_literal = password.replace("'", "''")
    return f"""\
SELECT pg_advisory_lock(hashtextextended('{marker}', 0));
DO $wuji$
DECLARE role_marker text;
BEGIN
  SELECT shobj_description(oid, 'pg_authid') INTO role_marker
    FROM pg_roles WHERE rolname = '{DATABASE_ROLE}';
  IF NOT FOUND THEN
    CREATE ROLE {DATABASE_ROLE} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB
      NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '{password_literal}';
    COMMENT ON ROLE {DATABASE_ROLE} IS '{marker}';
  ELSIF role_marker IS DISTINCT FROM '{marker}' OR EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = '{DATABASE_ROLE}' AND
      (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls OR rolinherit)
  ) OR EXISTS (
    SELECT 1 FROM pg_auth_members
      WHERE member = (SELECT oid FROM pg_roles WHERE rolname = '{DATABASE_ROLE}')
  ) THEN
    RAISE EXCEPTION 'first-use LiteLLM role ownership or privilege conflict';
  END IF;
END
$wuji$;
DO $wuji$
DECLARE database_owner text; database_marker text;
BEGIN
  SELECT pg_get_userbyid(datdba), shobj_description(oid, 'pg_database')
    INTO database_owner, database_marker
    FROM pg_database WHERE datname = '{DATABASE_NAME}';
  IF FOUND AND (
    database_owner IS DISTINCT FROM '{DATABASE_ROLE}' OR
    database_marker IS DISTINCT FROM '{marker}'
  ) THEN
    RAISE EXCEPTION 'first-use LiteLLM database ownership conflict';
  END IF;
END
$wuji$;
SELECT format('CREATE DATABASE %I OWNER %I', '{DATABASE_NAME}', '{DATABASE_ROLE}')
  WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '{DATABASE_NAME}')\\gexec
COMMENT ON DATABASE {DATABASE_NAME} IS '{marker}';
REVOKE ALL ON DATABASE {DATABASE_NAME} FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE {DATABASE_NAME} TO {DATABASE_ROLE};
SELECT pg_advisory_unlock(hashtextextended('{marker}', 0));
""".encode()


def _decode_secret(data: dict[str, Any], key: str) -> bytes:
    try:
        encoded = data[key]
        if not isinstance(encoded, str):
            raise ValueError
        return base64.b64decode(encoded, validate=True)
    except (KeyError, ValueError):
        raise DeploymentError("secret_invalid", "Kubernetes Secret is malformed") from None


def _owned(resource: dict[str, Any]) -> bool:
    return resource.get("metadata", {}).get("labels", {}).get(OWNER_LABEL) == OWNER


def _check_owned(resource: dict[str, Any], *, secret: bool = False) -> None:
    if not _owned(resource):
        raise DeploymentError("owner_conflict", "refusing to overwrite an unknown same-name object")
    if secret and LAST_APPLIED in resource.get("metadata", {}).get("annotations", {}):
        raise DeploymentError(
            "secret_annotation_conflict",
            "owned Secret contains a forbidden last-applied annotation",
        )


def _private_secret(values: dict[str, str]) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": _metadata(PRIVATE_SECRET),
        "type": "Opaque",
        "immutable": True,
        "stringData": values,
    }


def _tls_secret(certificate: bytes, key: bytes, ca_certificate: bytes) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": _metadata(TLS_SECRET),
        "type": "kubernetes.io/tls",
        "immutable": True,
        "data": {
            "tls.crt": base64.b64encode(certificate).decode(),
            "tls.key": base64.b64encode(key).decode(),
            "ca.crt": base64.b64encode(ca_certificate).decode(),
        },
    }


def sign_gateway_leaf(ca_directory: Path) -> tuple[bytes, bytes, bytes]:
    """Sign only the gateway leaf with the existing CA; never rewrite CA files."""

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    try:
        ca_bytes = (ca_directory / "ca.crt").read_bytes()
        ca_key_bytes = (ca_directory / "ca.key").read_bytes()
        ca = x509.load_pem_x509_certificate(ca_bytes)
        ca_key = serialization.load_pem_private_key(ca_key_bytes, password=None)
        constraints = ca.extensions.get_extension_for_class(x509.BasicConstraints).value
    except (OSError, ValueError, TypeError, x509.ExtensionNotFound):
        raise DeploymentError("ca_invalid", "the existing deployment CA is unavailable or invalid") from None
    if not constraints.ca:
        raise DeploymentError("ca_invalid", "the existing certificate is not a CA")
    ca_public = ca.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    key_public = ca_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    if ca_public != key_public:
        raise DeploymentError("ca_invalid", "the existing CA key does not match its certificate")

    now = datetime.now(timezone.utc)
    ca_expires = (
        ca.not_valid_after_utc
        if hasattr(ca, "not_valid_after_utc")
        else ca.not_valid_after.replace(tzinfo=timezone.utc)
    )
    expires = min(now + timedelta(days=30), ca_expires - timedelta(minutes=1))
    if expires <= now + timedelta(minutes=5):
        raise DeploymentError("ca_expiring", "the existing CA lifetime is too short for a new leaf")
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    dns_names = [NAME, f"{NAME}.{NAMESPACE}", GATEWAY_HOST, f"{GATEWAY_HOST}.cluster.local"]
    leaf = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, GATEWAY_HOST)]))
        .issuer_name(ca.subject)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(expires)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(name) for name in dns_names]), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=None,
                decipher_only=None,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )
    return (
        leaf.public_bytes(serialization.Encoding.PEM),
        leaf_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        ca_bytes,
    )


def validate_existing_tls(resource: dict[str, Any], ca_directory: Path) -> None:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID

    if set(resource.get("data", {})) != TLS_KEYS or resource.get("immutable") is not True:
        raise DeploymentError("tls_secret_invalid", "gateway TLS Secret has an unexpected shape")
    try:
        expected_ca = x509.load_pem_x509_certificate((ca_directory / "ca.crt").read_bytes())
        mounted_ca = x509.load_pem_x509_certificate(_decode_secret(resource["data"], "ca.crt"))
        leaf = x509.load_pem_x509_certificate(_decode_secret(resource["data"], "tls.crt"))
        sans = set(leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName))
        usages = leaf.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        if expected_ca.fingerprint(hashes.SHA256()) != mounted_ca.fingerprint(hashes.SHA256()):
            raise ValueError
        if GATEWAY_HOST not in sans or ExtendedKeyUsageOID.SERVER_AUTH not in usages:
            raise ValueError
        public_key = expected_ca.public_key()
        if not isinstance(public_key, rsa.RSAPublicKey):
            raise ValueError
        public_key.verify(leaf.signature, leaf.tbs_certificate_bytes, padding.PKCS1v15(), leaf.signature_hash_algorithm)
    except (OSError, ValueError, TypeError, KeyError, x509.ExtensionNotFound):
        raise DeploymentError("tls_secret_invalid", "gateway TLS Secret is not signed by the existing CA") from None


Runner = Callable[..., subprocess.CompletedProcess[bytes]]


class KubernetesClient:
    """Small kubectl adapter that never exposes subprocess output in errors."""

    def __init__(self, runner: Runner = subprocess.run):
        self.runner = runner

    def _run(
        self,
        arguments: Sequence[str],
        *,
        input_bytes: bytes | None = None,
        timeout: int = 120,
        operation: str,
    ) -> bytes:
        command = ["kubectl", "--context", CONTEXT, "--namespace", NAMESPACE, *arguments]
        try:
            result = self.runner(
                command,
                input=input_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise DeploymentError("kubectl_unavailable", f"{operation} failed") from None
        if result.returncode != 0:
            raise DeploymentError("kubectl_failed", f"{operation} failed")
        return bytes(result.stdout)

    def get(self, kind: str, name: str) -> dict[str, Any] | None:
        raw = self._run(
            ["get", kind, name, "--ignore-not-found", "-o", "json"],
            timeout=30,
            operation="resource read",
        )
        if not raw.strip():
            return None
        try:
            value = json.loads(raw)
        except (TypeError, ValueError):
            raise DeploymentError("kubectl_invalid", "resource read returned invalid metadata") from None
        if not isinstance(value, dict):
            raise DeploymentError("kubectl_invalid", "resource read returned invalid metadata")
        return value

    def create(self, resource: dict[str, Any]) -> None:
        self._run(
            ["create", "-f", "-", "-o", "name"],
            input_bytes=_canonical(resource),
            operation="resource create",
        )

    def replace(self, resource: dict[str, Any]) -> None:
        self._run(
            ["replace", "-f", "-", "-o", "name"],
            input_bytes=_canonical(resource),
            operation="resource replace",
        )

    def reconcile_database(self, password: str) -> None:
        # Use the explicit command instead of _run because it is already fully
        # scoped; SQL (including the password) is stdin, never an argv element.
        try:
            result = self.runner(
                postgres_exec_command(),
                input=database_sql(password),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=180,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise DeploymentError("database_unavailable", "database reconciliation failed") from None
        if result.returncode != 0:
            raise DeploymentError("database_failed", "database reconciliation failed")

    def wait_for_rollout(self) -> None:
        self._run(
            ["rollout", "status", f"deployment/{NAME}", "--timeout=300s"],
            timeout=330,
            operation="gateway rollout",
        )


@dataclass
class GatewayDeployer:
    client: KubernetesClient
    ca_directory: Path

    def _create_or_recover_secret(self, desired: dict[str, Any]) -> tuple[dict[str, Any], str]:
        name = desired["metadata"]["name"]
        existing = self.client.get("Secret", name)
        if existing is not None:
            _check_owned(existing, secret=True)
            return existing, "reused"
        try:
            self.client.create(desired)
            return desired, "created"
        except DeploymentError:
            # A concurrent creator or a lost success response is resolved by an
            # ownership-checked read.  No second credential is generated.
            existing = self.client.get("Secret", name)
            if existing is None:
                raise
            _check_owned(existing, secret=True)
            return existing, "reused"

    def _private_values(self) -> tuple[dict[str, str], str]:
        existing = self.client.get("Secret", PRIVATE_SECRET)
        if existing is None:
            password = secrets.token_urlsafe(48)
            values = {
                "master.key": "sk-" + secrets.token_urlsafe(48),
                "database.password": password,
                "database.url": database_url(password),
            }
            resource, action = self._create_or_recover_secret(_private_secret(values))
            if action == "created":
                return values, action
            existing = resource
        _check_owned(existing, secret=True)
        if (
            set(existing.get("data", {})) != PRIVATE_KEYS
            or existing.get("immutable") is not True
        ):
            raise DeploymentError("private_secret_invalid", "gateway private Secret has an unexpected shape")
        try:
            values = {
                key: _decode_secret(existing["data"], key).decode("ascii")
                for key in PRIVATE_KEYS
            }
        except UnicodeDecodeError:
            raise DeploymentError("private_secret_invalid", "gateway private Secret is malformed") from None
        if not re.fullmatch(r"sk-[A-Za-z0-9_-]{32,256}", values["master.key"]):
            raise DeploymentError("private_secret_invalid", "gateway private Secret is malformed")
        if values["database.url"] != database_url(values["database.password"]):
            raise DeploymentError("private_secret_invalid", "gateway private Secret is malformed")
        return values, "reused"

    def _ensure_tls(self) -> str:
        existing = self.client.get("Secret", TLS_SECRET)
        if existing is not None:
            _check_owned(existing, secret=True)
            validate_existing_tls(existing, self.ca_directory)
            return "reused"
        certificate, key, ca_certificate = sign_gateway_leaf(self.ca_directory)
        resource, action = self._create_or_recover_secret(
            _tls_secret(certificate, key, ca_certificate)
        )
        if action == "reused":
            validate_existing_tls(resource, self.ca_directory)
        return action

    def _provider_preflight(self) -> None:
        provider = self.client.get("Secret", PROVIDER_SECRET)
        if provider is None:
            raise DeploymentError("provider_secret_absent", "provider Secret is absent")
        try:
            if not _decode_secret(provider.get("data", {}), PROVIDER_KEY):
                raise ValueError
        except (DeploymentError, ValueError):
            raise DeploymentError("provider_secret_invalid", "provider Secret field is absent or empty") from None

    def _write_manifest(self, desired: dict[str, Any]) -> str:
        kind, name = desired["kind"], desired["metadata"]["name"]
        existing = self.client.get(kind, name)
        if existing is None:
            self.client.create(desired)
            return "created"
        _check_owned(existing)
        replacement = copy.deepcopy(desired)
        resource_version = existing.get("metadata", {}).get("resourceVersion")
        if not resource_version:
            raise DeploymentError("resource_invalid", "owned resource has no resourceVersion")
        replacement["metadata"]["resourceVersion"] = resource_version
        if kind == "Service":
            for field in ("clusterIP", "clusterIPs", "ipFamilies", "ipFamilyPolicy"):
                if field in existing.get("spec", {}):
                    replacement["spec"][field] = existing["spec"][field]
        self.client.replace(replacement)
        return "matched"

    def reconcile(self) -> dict[str, Any]:
        if self.client.get("Namespace", NAMESPACE) is None:
            raise DeploymentError("namespace_absent", "the fixed namespace is absent")
        self._provider_preflight()
        manifests = render_manifests()
        # Resolve all known same-name collisions before creating a credential,
        # role, database, or workload. Reads are repeated at write time for races.
        for kind, name in (
            ("Secret", PRIVATE_SECRET),
            ("Secret", TLS_SECRET),
            *((item["kind"], item["metadata"]["name"]) for item in manifests),
        ):
            existing = self.client.get(kind, name)
            if existing is not None:
                _check_owned(existing, secret=kind == "Secret")
        private, private_action = self._private_values()
        self.client.reconcile_database(private["database.password"])
        tls_action = self._ensure_tls()
        actions = [
            {"kind": item["kind"], "name": item["metadata"]["name"], "action": self._write_manifest(item)}
            for item in manifests
        ]
        self.client.wait_for_rollout()
        return {
            "ok": True,
            "mode": "execute",
            "context": CONTEXT,
            "namespace": NAMESPACE,
            "owner": OWNER,
            "endpoint": f"https://{GATEWAY_HOST}:4000",
            "database": {"name": DATABASE_NAME, "role": DATABASE_ROLE, "action": "reconciled"},
            "secrets": [
                {"name": PRIVATE_SECRET, "action": private_action},
                {"name": TLS_SECRET, "action": tls_action},
                {"name": PROVIDER_SECRET, "action": "referenced"},
            ],
            "resources": actions,
            "manifest_sha256": manifest_digest(manifests),
        }


def dry_run_plan() -> dict[str, Any]:
    manifests = render_manifests()
    return {
        "ok": True,
        "mode": "dry-run",
        "mutations": False,
        "context": CONTEXT,
        "namespace": NAMESPACE,
        "owner": OWNER,
        "endpoint": f"https://{GATEWAY_HOST}:4000",
        "database": {"name": DATABASE_NAME, "role": DATABASE_ROLE},
        "secrets": [PRIVATE_SECRET, TLS_SECRET, PROVIDER_SECRET],
        "resources": [
            {"kind": item["kind"], "name": item["metadata"]["name"]}
            for item in manifests
        ],
        "manifest_sha256": manifest_digest(manifests),
    }


def default_ca_directory() -> Path:
    local_state = ROOT / "work" / "vnext" / "k8s" / "tls"
    if (local_state / "ca.crt").is_file() and (local_state / "ca.key").is_file():
        return local_state
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        return local_state
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve().parent / "work" / "vnext" / "k8s" / "tls"
    return local_state


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="perform owner-checked writes in the fixed local namespace",
    )
    parser.add_argument(
        "--ca-directory",
        type=Path,
        help="existing CA directory; defaults to the main worktree deployment state",
    )
    args = parser.parse_args(argv)
    try:
        if args.execute and not PERSISTENCE_IMAGE_READY:
            raise DeploymentError("persistent_image_not_published",
                                  "the persistent gateway image is built but not published; deployment is blocked")
        result = (
            GatewayDeployer(
                KubernetesClient(), args.ca_directory or default_ca_directory()
            ).reconcile()
            if args.execute
            else dry_run_plan()
        )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except DeploymentError as error:
        print(
            json.dumps(
                {"ok": False, "error": error.code, "message": str(error)},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    except Exception:
        # Never serialize repr(error): subprocess and parser failures can carry
        # Secret stdin or environment values in their diagnostic payloads.
        print('{"error":"internal_error","message":"gateway deployment failed","ok":false}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
