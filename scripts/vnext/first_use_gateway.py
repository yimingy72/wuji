"""Provision the isolated first-use LiteLLM gateway without printing secrets.

The default CLI path is an offline, deterministic render.  ``--execute`` is
required before this module reads or writes the fixed docker-desktop namespace.
Secret values are sent to Kubernetes and PostgreSQL only over stdin; command
arguments, successful output, and sanitized failures contain metadata only.
Provider migration and legacy cleanup are separate, explicit actions.
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
import selectors
import subprocess
from typing import Any, Callable, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
CONTEXT = "docker-desktop"
CORE_NAMESPACE = "wuji-vnext-test"
MODEL_NAMESPACE = "wuji-first-use-model"
# Retain the public constant for focused consumers while making its meaning the
# isolated workload namespace. Database administration always uses CORE_NAMESPACE.
NAMESPACE = MODEL_NAMESPACE
OWNER_LABEL = "wuji.dev/credential-owner"
OWNER = "first-use-gateway-v1"
MANIFEST_DIGEST_ANNOTATION = "wuji.dev/manifest-sha256"

NAME = "first-use-litellm"
CONFIG_NAME = NAME + "-config"
PRIVATE_SECRET = NAME + "-private"
TLS_SECRET = NAME + "-tls-v2"
PROVIDER_SECRET = "deepseek-provider-first-use"
PROVIDER_KEY = "DEEPSEEK_API_KEY"
PROVIDER_LABELS = {
    "app.kubernetes.io/component": "model-gateway",
    "app.kubernetes.io/part-of": "wuji-first-use",
}

PRIVATE_KEYS = frozenset({"master.key", "database.password", "database.url"})
TLS_KEYS = frozenset({"tls.crt", "tls.key", "ca.crt"})
DATABASE_ROLE = "wuji_first_use_litellm"
DATABASE_NAME = "wuji_first_use_litellm_20260919"
DATABASE_HOST = f"postgres.{CORE_NAMESPACE}.svc"
GATEWAY_HOST = f"{NAME}.{NAMESPACE}.svc"
IMAGE = (
    "127.0.0.1:55529/wuji-first-use-litellm@"
    "sha256:11c59c67f03f4012d9000d210147ace1e0058144962d2301db916517c4494c1d"
)
# Published and image-ID checked after the approved Docker cache recovery.
# Registry publication is not evidence of database or provider acceptance.
PERSISTENCE_IMAGE_READY = True
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
            "app.kubernetes.io/part-of": "wuji-first-use",
        },
    }


def _namespace_manifest() -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": MODEL_NAMESPACE,
            "labels": {
                OWNER_LABEL: OWNER,
                "app.kubernetes.io/part-of": "wuji-first-use",
            },
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
                "name": "WUJI_LITELLM_DATABASE_URL",
                "valueFrom": {
                    "secretKeyRef": {"name": PRIVATE_SECRET, "key": "database.url"}
                },
            },
            # Prisma uses sslcert for the trust root; libpq's sslrootcert is
            # ignored by its connector. Keep the immutable stored credential
            # bytes and strict verification, adding only the connector option.
            {"name": "DATABASE_URL", "value": "$(WUJI_LITELLM_DATABASE_URL)&sslcert=/run/wuji/tls/ca.crt"},
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
            # Proxy startup was OOMKilled at 2 GiB in the first actual run;
            # keep a bounded ceiling without changing TLS/DB enforcement.
            "limits": {"cpu": "2", "memory": "4Gi"},
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
    manifests = [config, deployment, service]
    digest = manifest_digest(manifests)
    deployment["metadata"]["annotations"] = {MANIFEST_DIGEST_ANNOTATION: digest}
    deployment["spec"]["template"]["metadata"]["annotations"] = {
        MANIFEST_DIGEST_ANNOTATION: digest
    }
    return manifests


def manifest_digest(manifests: Sequence[dict[str, Any]]) -> str:
    normalized = copy.deepcopy(list(manifests))
    for item in normalized:
        annotations = item.get("metadata", {}).get("annotations", {})
        annotations.pop(MANIFEST_DIGEST_ANNOTATION, None)
        if not annotations:
            item.get("metadata", {}).pop("annotations", None)
        template = item.get("spec", {}).get("template", {})
        pod_annotations = template.get("metadata", {}).get("annotations", {})
        pod_annotations.pop(MANIFEST_DIGEST_ANNOTATION, None)
        if not pod_annotations:
            template.get("metadata", {}).pop("annotations", None)
    return sha256(_canonical(normalized)).hexdigest()


def render_json_documents(manifests: Sequence[dict[str, Any]]) -> str:
    return "\n---\n".join(json.dumps(item, sort_keys=True, indent=2) for item in manifests) + "\n"


def postgres_exec_command() -> list[str]:
    """The admin password stays in the existing container environment."""

    return [
        "kubectl",
        "--context",
        CONTEXT,
        "--namespace",
        CORE_NAMESPACE,
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
    (database_marker IS NOT NULL AND database_marker IS DISTINCT FROM '{marker}')
  ) THEN
    RAISE EXCEPTION 'first-use LiteLLM database ownership conflict';
  END IF;
END
$wuji$;
SELECT format('CREATE DATABASE %I OWNER %I', '{DATABASE_NAME}', '{DATABASE_ROLE}')
  WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '{DATABASE_NAME}')\\gexec
-- A lost response between CREATE DATABASE and COMMENT is recoverable only
-- for this exact database and the already owner/privilege-checked role above.
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


def _check_namespace(resource: dict[str, Any]) -> None:
    if resource.get("kind") not in (None, "Namespace") or not _owned(resource):
        raise DeploymentError(
            "namespace_owner_conflict",
            "refusing to use an unknown same-name model namespace",
        )


def _provider_value(resource: dict[str, Any]) -> bytes:
    metadata = resource.get("metadata", {})
    if (
        metadata.get("labels") != PROVIDER_LABELS
        or set(resource.get("data", {})) != {PROVIDER_KEY}
        or LAST_APPLIED in metadata.get("annotations", {})
    ):
        raise DeploymentError(
            "provider_secret_invalid",
            "provider Secret identity or shape is invalid",
        )
    value = _decode_secret(resource["data"], PROVIDER_KEY)
    if not value:
        raise DeploymentError(
            "provider_secret_invalid", "provider Secret field is absent or empty"
        )
    return value


def _private_values(resource: dict[str, Any]) -> dict[str, str]:
    _check_owned(resource, secret=True)
    if set(resource.get("data", {})) != PRIVATE_KEYS or resource.get("immutable") is not True:
        raise DeploymentError(
            "private_secret_invalid",
            "gateway private Secret has an unexpected shape",
        )
    try:
        values = {
            key: _decode_secret(resource["data"], key).decode("ascii")
            for key in PRIVATE_KEYS
        }
    except UnicodeDecodeError:
        raise DeploymentError(
            "private_secret_invalid", "gateway private Secret is malformed"
        ) from None
    if not re.fullmatch(r"sk-[A-Za-z0-9_-]{32,256}", values["master.key"]):
        raise DeploymentError(
            "private_secret_invalid", "gateway private Secret is malformed"
        )
    if values["database.url"] != database_url(values["database.password"]):
        raise DeploymentError(
            "private_secret_invalid", "gateway private Secret is malformed"
        )
    return values


def _private_secret(encoded_data: dict[str, str]) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": _metadata(PRIVATE_SECRET),
        "type": "Opaque",
        "immutable": True,
        "data": copy.deepcopy(encoded_data),
    }


def _provider_secret(encoded_data: dict[str, str]) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": PROVIDER_SECRET,
            "namespace": MODEL_NAMESPACE,
            "labels": copy.deepcopy(PROVIDER_LABELS),
        },
        "type": "Opaque",
        "data": copy.deepcopy(encoded_data),
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
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(leaf_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca.public_key()), critical=False)
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
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID

    if set(resource.get("data", {})) != TLS_KEYS or resource.get("immutable") is not True:
        raise DeploymentError("tls_secret_invalid", "gateway TLS Secret has an unexpected shape")
    try:
        expected_ca = x509.load_pem_x509_certificate((ca_directory / "ca.crt").read_bytes())
        mounted_ca = x509.load_pem_x509_certificate(_decode_secret(resource["data"], "ca.crt"))
        leaf = x509.load_pem_x509_certificate(_decode_secret(resource["data"], "tls.crt"))
        leaf_key = serialization.load_pem_private_key(_decode_secret(resource["data"], "tls.key"), password=None)
        now = datetime.now(timezone.utc)
        if not (expected_ca.not_valid_before_utc <= now < expected_ca.not_valid_after_utc
                and leaf.not_valid_before_utc <= now < leaf.not_valid_after_utc - timedelta(minutes=5)):
            raise ValueError
        if leaf.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo) != leaf_key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo):
            raise ValueError
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
ProxyFactory = Callable[..., subprocess.Popen[bytes]]


class KubernetesClient:
    """Small kubectl adapter that never exposes subprocess output in errors."""

    def __init__(
        self,
        runner: Runner = subprocess.run,
        proxy_factory: ProxyFactory = subprocess.Popen,
    ):
        self.runner = runner
        self.proxy_factory = proxy_factory

    def _run(
        self,
        arguments: Sequence[str],
        *,
        input_bytes: bytes | None = None,
        timeout: int = 120,
        operation: str,
    ) -> bytes:
        command = ["kubectl", "--context", CONTEXT, *arguments]
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

    def _get(
        self, namespace_arguments: Sequence[str], kind: str, name: str
    ) -> dict[str, Any] | None:
        raw = self._run(
            [*namespace_arguments, "get", kind, name, "--ignore-not-found", "-o", "json"],
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

    def get_model(self, kind: str, name: str) -> dict[str, Any] | None:
        return self._get(["--namespace", MODEL_NAMESPACE], kind, name)

    def get_core(self, kind: str, name: str) -> dict[str, Any] | None:
        return self._get(["--namespace", CORE_NAMESPACE], kind, name)

    def get_namespace(self) -> dict[str, Any] | None:
        return self._get([], "Namespace", MODEL_NAMESPACE)

    def _create(self, namespace_arguments: Sequence[str], resource: dict[str, Any]) -> None:
        self._run(
            [*namespace_arguments, "create", "-f", "-", "-o", "name"],
            input_bytes=_canonical(resource),
            operation="resource create",
        )

    def create_model(self, resource: dict[str, Any]) -> None:
        self._create(["--namespace", MODEL_NAMESPACE], resource)

    def create_namespace(self, resource: dict[str, Any]) -> None:
        self._create([], resource)

    def _replace(self, namespace_arguments: Sequence[str], resource: dict[str, Any]) -> None:
        self._run(
            [*namespace_arguments, "replace", "-f", "-", "-o", "name"],
            input_bytes=_canonical(resource),
            operation="resource replace",
        )

    def replace_model(self, resource: dict[str, Any]) -> None:
        self._replace(["--namespace", MODEL_NAMESPACE], resource)

    def replace_core(self, resource: dict[str, Any]) -> None:
        self._replace(["--namespace", CORE_NAMESPACE], resource)

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
            [
                "--namespace",
                MODEL_NAMESPACE,
                "rollout",
                "status",
                f"deployment/{NAME}",
                "--timeout=300s",
            ],
            timeout=330,
            operation="gateway rollout",
        )

    def delete_core_provider_with_preconditions(
        self, *, uid: str, resource_version: str
    ) -> None:
        """DELETE the legacy provider with API-server UID/RV preconditions."""

        command = [
            "kubectl",
            "--context",
            CONTEXT,
            "proxy",
            "--port=0",
            "--accept-hosts=^127[.]0[.]0[.]1$",
        ]
        process: subprocess.Popen[bytes] | None = None
        selector: selectors.BaseSelector | None = None
        try:
            process = self.proxy_factory(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if process.stdout is None:
                raise OSError
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout=15):
                raise TimeoutError
            line = process.stdout.readline()
            match = re.search(rb"Starting to serve on 127[.]0[.]0[.]1:([0-9]+)", line)
            if match is None:
                raise OSError
            port = int(match.group(1))
            path = (
                f"/api/v1/namespaces/{quote(CORE_NAMESPACE, safe='')}/secrets/"
                f"{quote(PROVIDER_SECRET, safe='')}"
            )
            body = _canonical(
                {
                    "apiVersion": "v1",
                    "kind": "DeleteOptions",
                    "preconditions": {
                        "uid": uid,
                        "resourceVersion": resource_version,
                    },
                    "propagationPolicy": "Background",
                }
            )
            request = Request(
                f"http://127.0.0.1:{port}{path}",
                data=body,
                headers={"Content-Type": "application/json"},
                method="DELETE",
            )
            with urlopen(request, timeout=30) as response:
                if not 200 <= response.status < 300:
                    raise OSError
        except (OSError, TimeoutError, HTTPError, URLError, subprocess.SubprocessError):
            raise DeploymentError(
                "provider_delete_failed", "legacy provider Secret deletion failed"
            ) from None
        finally:
            if selector is not None:
                selector.close()
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


@dataclass
class GatewayDeployer:
    client: KubernetesClient
    ca_directory: Path

    def _create_or_recover_secret(
        self,
        desired: dict[str, Any],
        validator: Callable[[dict[str, Any]], Any],
    ) -> tuple[dict[str, Any], str]:
        name = desired["metadata"]["name"]
        existing = self.client.get_model("Secret", name)
        if existing is not None:
            validator(existing)
            return existing, "reused"
        try:
            self.client.create_model(desired)
            return desired, "created"
        except DeploymentError:
            # A concurrent creator or a lost success response is resolved only
            # by a fresh identity/shape checked read.
            existing = self.client.get_model("Secret", name)
            if existing is None:
                raise
            validator(existing)
            return existing, "reused"

    def _require_namespace(self) -> None:
        namespace = self.client.get_namespace()
        if namespace is None:
            raise DeploymentError(
                "namespace_absent", "the isolated model namespace is absent"
            )
        _check_namespace(namespace)

    def _ensure_migration_namespace(self) -> str:
        namespace = self.client.get_namespace()
        if namespace is not None:
            _check_namespace(namespace)
            return "reused"
        desired = _namespace_manifest()
        try:
            self.client.create_namespace(desired)
            return "created"
        except DeploymentError:
            namespace = self.client.get_namespace()
            if namespace is None:
                raise
            _check_namespace(namespace)
            return "reused"

    def _read_private(self) -> tuple[dict[str, Any], dict[str, str]]:
        private = self.client.get_model("Secret", PRIVATE_SECRET)
        if private is None:
            raise DeploymentError(
                "private_secret_absent",
                "isolated gateway private Secret is absent; explicit migration is required",
            )
        return private, _private_values(private)

    def _provider_preflight(self) -> dict[str, Any]:
        provider = self.client.get_model("Secret", PROVIDER_SECRET)
        if provider is None:
            raise DeploymentError(
                "provider_secret_absent",
                "isolated provider Secret is absent; explicit migration is required",
            )
        _provider_value(provider)
        return provider

    def _preflight_model_objects(
        self,
        manifests: Sequence[dict[str, Any]],
        *,
        source_private: dict[str, Any] | None = None,
        source_provider: dict[str, Any] | None = None,
    ) -> None:
        private = self.client.get_model("Secret", PRIVATE_SECRET)
        if private is not None:
            _private_values(private)
            if source_private is not None and private.get("data") != source_private.get("data"):
                raise DeploymentError(
                    "migration_secret_conflict",
                    "isolated private Secret does not match the verified legacy source",
                )
        provider = self.client.get_model("Secret", PROVIDER_SECRET)
        if provider is not None:
            target_value = _provider_value(provider)
            if source_provider is not None and target_value != _provider_value(source_provider):
                raise DeploymentError(
                    "migration_secret_conflict",
                    "isolated provider Secret does not match the verified legacy source",
                )
        tls = self.client.get_model("Secret", TLS_SECRET)
        if tls is not None:
            _check_owned(tls, secret=True)
            validate_existing_tls(tls, self.ca_directory)
        for desired in manifests:
            existing = self.client.get_model(
                desired["kind"], desired["metadata"]["name"]
            )
            if existing is not None:
                _check_owned(existing)

    def _migrate_secrets(self, manifests: Sequence[dict[str, Any]]) -> tuple[str, str, str]:
        source_private = self.client.get_core("Secret", PRIVATE_SECRET)
        if source_private is None:
            raise DeploymentError(
                "migration_source_absent", "legacy gateway private Secret is absent"
            )
        _private_values(source_private)
        source_provider = self.client.get_core("Secret", PROVIDER_SECRET)
        if source_provider is None:
            raise DeploymentError(
                "migration_source_absent", "legacy provider Secret is absent"
            )
        _provider_value(source_provider)

        # If the target namespace already exists, all same-name targets are
        # checked before the first write. Unknown ownership therefore produces
        # a zero-write refusal in the ordinary (non-racing) case.
        namespace = self.client.get_namespace()
        if namespace is not None:
            _check_namespace(namespace)
            self._preflight_model_objects(
                manifests,
                source_private=source_private,
                source_provider=source_provider,
            )
        namespace_action = self._ensure_migration_namespace()

        migrated_private, private_action = self._create_or_recover_secret(
            _private_secret(source_private["data"]), _private_values
        )
        if migrated_private.get("data") != source_private.get("data"):
            raise DeploymentError(
                "migration_secret_conflict",
                "isolated private Secret does not match the verified legacy source",
            )
        migrated_provider, provider_action = self._create_or_recover_secret(
            _provider_secret(source_provider["data"]), _provider_value
        )
        if _provider_value(migrated_provider) != _provider_value(source_provider):
            raise DeploymentError(
                "migration_secret_conflict",
                "isolated provider Secret does not match the verified legacy source",
            )
        return namespace_action, private_action, provider_action

    def _ensure_tls(self) -> str:
        existing = self.client.get_model("Secret", TLS_SECRET)
        if existing is not None:
            _check_owned(existing, secret=True)
            validate_existing_tls(existing, self.ca_directory)
            return "reused"
        certificate, key, ca_certificate = sign_gateway_leaf(self.ca_directory)
        resource, action = self._create_or_recover_secret(
            _tls_secret(certificate, key, ca_certificate),
            lambda value: (
                _check_owned(value, secret=True),
                validate_existing_tls(value, self.ca_directory),
            ),
        )
        if action == "reused":
            validate_existing_tls(resource, self.ca_directory)
        return action

    def _write_manifest(self, desired: dict[str, Any]) -> str:
        kind, name = desired["kind"], desired["metadata"]["name"]
        existing = self.client.get_model(kind, name)
        if existing is None:
            self.client.create_model(desired)
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
        self.client.replace_model(replacement)
        return "matched"

    def reconcile(self, *, isolate_provider: bool = False) -> dict[str, Any]:
        manifests = render_manifests()
        namespace_action = "reused"
        provider_action = "referenced"
        if isolate_provider:
            namespace_action, private_action, provider_action = self._migrate_secrets(
                manifests
            )
        else:
            self._require_namespace()
            self._preflight_model_objects(manifests)
            self._provider_preflight()
            private_action = "reused"
        _, private = self._read_private()
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
            "namespace_action": namespace_action,
            "secrets": [
                {"name": PRIVATE_SECRET, "action": private_action},
                {"name": TLS_SECRET, "action": tls_action},
                {"name": PROVIDER_SECRET, "action": provider_action},
            ],
            "resources": actions,
            "manifest_sha256": manifest_digest(manifests),
        }


def _require_metadata(
    resource: dict[str, Any], *, uid: str, resource_version: str, kind: str
) -> None:
    metadata = resource.get("metadata", {})
    if metadata.get("uid") != uid or metadata.get("resourceVersion") != resource_version:
        raise DeploymentError(
            "legacy_metadata_changed", f"legacy {kind} metadata no longer matches confirmation"
        )


def _ready_with_digest(deployment: dict[str, Any], expected_digest: str) -> bool:
    metadata = deployment.get("metadata", {})
    spec = deployment.get("spec", {})
    status = deployment.get("status", {})
    template = spec.get("template", {})
    containers = template.get("spec", {}).get("containers", [])
    conditions = status.get("conditions", [])
    return bool(
        re.fullmatch(r"[0-9a-f]{64}", expected_digest)
        and expected_digest == manifest_digest(render_manifests())
        and metadata.get("annotations", {}).get(MANIFEST_DIGEST_ANNOTATION)
        == expected_digest
        and template.get("metadata", {}).get("annotations", {}).get(
            MANIFEST_DIGEST_ANNOTATION
        )
        == expected_digest
        and spec.get("replicas") == 1
        and status.get("observedGeneration") == metadata.get("generation")
        and status.get("availableReplicas", 0) >= 1
        and len(containers) == 1
        and containers[0].get("image") == IMAGE
        and any(
            item.get("type") == "Available" and item.get("status") == "True"
            for item in conditions
        )
    )


def _contains_desired(actual: Any, desired: Any) -> bool:
    """Compare desired fields while allowing API-server defaulted fields."""

    if isinstance(desired, dict):
        return isinstance(actual, dict) and all(
            key in actual and _contains_desired(actual[key], value)
            for key, value in desired.items()
        )
    if isinstance(desired, list):
        return isinstance(actual, list) and len(actual) == len(desired) and all(
            _contains_desired(actual_item, desired_item)
            for actual_item, desired_item in zip(actual, desired)
        )
    return actual == desired


@dataclass
class IsolationFinalizer:
    client: KubernetesClient
    ca_directory: Path

    def finalize(
        self,
        *,
        expected_manifest_sha256: str,
        legacy_deployment_uid: str,
        legacy_deployment_resource_version: str,
        legacy_provider_uid: str,
        legacy_provider_resource_version: str,
    ) -> dict[str, Any]:
        namespace = self.client.get_namespace()
        if namespace is None:
            raise DeploymentError("namespace_absent", "the isolated model namespace is absent")
        _check_namespace(namespace)

        private = self.client.get_model("Secret", PRIVATE_SECRET)
        provider = self.client.get_model("Secret", PROVIDER_SECRET)
        tls = self.client.get_model("Secret", TLS_SECRET)
        deployment = self.client.get_model("Deployment", NAME)
        config = self.client.get_model("ConfigMap", CONFIG_NAME)
        service = self.client.get_model("Service", NAME)
        if None in (private, provider, tls, deployment, config, service):
            raise DeploymentError(
                "isolation_not_ready", "isolated gateway resources are incomplete"
            )
        assert private is not None and provider is not None and tls is not None
        assert deployment is not None and config is not None and service is not None
        _private_values(private)
        target_provider_value = _provider_value(provider)
        _check_owned(tls, secret=True)
        validate_existing_tls(tls, self.ca_directory)
        desired_by_identity = {
            (item["kind"], item["metadata"]["name"]): item
            for item in render_manifests()
        }
        live_resources = (config, deployment, service)
        for resource in live_resources:
            _check_owned(resource)
        if (
            not _ready_with_digest(deployment, expected_manifest_sha256)
            or not all(
                _contains_desired(
                    resource,
                    desired_by_identity[(
                        resource["kind"],
                        resource["metadata"]["name"],
                    )],
                )
                for resource in live_resources
            )
        ):
            raise DeploymentError(
                "isolation_not_ready",
                "isolated gateway is not Ready with the confirmed manifest digest",
            )

        legacy_deployment = self.client.get_core("Deployment", NAME)
        legacy_private = self.client.get_core("Secret", PRIVATE_SECRET)
        legacy_provider = self.client.get_core("Secret", PROVIDER_SECRET)
        if (
            legacy_deployment is None
            or legacy_private is None
            or legacy_provider is None
        ):
            raise DeploymentError(
                "legacy_resource_absent", "legacy gateway resources are absent"
            )
        _check_owned(legacy_deployment)
        _private_values(legacy_private)
        if legacy_private.get("data") != private.get("data"):
            raise DeploymentError(
                "migration_secret_conflict",
                "isolated private Secret does not match the verified legacy source",
            )
        legacy_provider_value = _provider_value(legacy_provider)
        if legacy_provider_value != target_provider_value:
            raise DeploymentError(
                "migration_secret_conflict",
                "isolated provider Secret does not match the verified legacy source",
            )
        _require_metadata(
            legacy_deployment,
            uid=legacy_deployment_uid,
            resource_version=legacy_deployment_resource_version,
            kind="Deployment",
        )
        _require_metadata(
            legacy_provider,
            uid=legacy_provider_uid,
            resource_version=legacy_provider_resource_version,
            kind="provider Secret",
        )

        scaled = copy.deepcopy(legacy_deployment)
        scaled.pop("status", None)
        scaled.get("metadata", {}).pop("managedFields", None)
        scaled.setdefault("spec", {})["replicas"] = 0
        self.client.replace_core(scaled)
        self.client.delete_core_provider_with_preconditions(
            uid=legacy_provider_uid,
            resource_version=legacy_provider_resource_version,
        )
        return {
            "ok": True,
            "mode": "finalize-isolation",
            "context": CONTEXT,
            "model_namespace": MODEL_NAMESPACE,
            "legacy_namespace": CORE_NAMESPACE,
            "manifest_sha256": expected_manifest_sha256,
            "actions": [
                {"kind": "Deployment", "name": NAME, "action": "scaled-to-zero"},
                {"kind": "Secret", "name": PROVIDER_SECRET, "action": "deleted"},
            ],
            "retained": [
                {"kind": "Secret", "name": PRIVATE_SECRET, "namespace": CORE_NAMESPACE}
            ],
        }


def dry_run_plan() -> dict[str, Any]:
    manifests = render_manifests()
    return {
        "ok": True,
        "mode": "dry-run",
        "mutations": False,
        "context": CONTEXT,
        "namespace": NAMESPACE,
        "core_namespace": CORE_NAMESPACE,
        "owner": OWNER,
        "endpoint": f"https://{GATEWAY_HOST}:4000",
        "database": {
            "name": DATABASE_NAME,
            "role": DATABASE_ROLE,
            "host": DATABASE_HOST,
        },
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
        help="perform owner-checked writes in the fixed isolated model namespace",
    )
    parser.add_argument(
        "--isolate-provider",
        action="store_true",
        help="explicitly copy the verified legacy private/provider Secrets before deployment",
    )
    parser.add_argument(
        "--finalize-isolation",
        action="store_true",
        help="after isolated readiness, scale the confirmed legacy gateway to zero and delete its provider Secret",
    )
    parser.add_argument(
        "--ca-directory",
        type=Path,
        help="existing CA directory; defaults to the main worktree deployment state",
    )
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--legacy-deployment-uid")
    parser.add_argument("--legacy-deployment-resource-version")
    parser.add_argument("--legacy-provider-uid")
    parser.add_argument("--legacy-provider-resource-version")
    args = parser.parse_args(argv)
    try:
        if (args.isolate_provider or args.finalize_isolation) and not args.execute:
            raise DeploymentError(
                "execute_required", "isolation mutations require the explicit --execute flag"
            )
        if args.isolate_provider and args.finalize_isolation:
            raise DeploymentError(
                "action_conflict", "provider migration and isolation finalization are separate actions"
            )
        if args.execute and not PERSISTENCE_IMAGE_READY:
            raise DeploymentError("persistent_image_not_published",
                                  "the persistent gateway image is built but not published; deployment is blocked")
        if args.finalize_isolation:
            required = {
                "expected manifest digest": args.expected_manifest_sha256,
                "legacy Deployment UID": args.legacy_deployment_uid,
                "legacy Deployment resourceVersion": args.legacy_deployment_resource_version,
                "legacy provider UID": args.legacy_provider_uid,
                "legacy provider resourceVersion": args.legacy_provider_resource_version,
            }
            if any(not value for value in required.values()):
                raise DeploymentError(
                    "confirmation_required",
                    "finalization requires confirmed legacy metadata and manifest digest",
                )
            result = IsolationFinalizer(
                KubernetesClient(), args.ca_directory or default_ca_directory()
            ).finalize(
                expected_manifest_sha256=args.expected_manifest_sha256,
                legacy_deployment_uid=args.legacy_deployment_uid,
                legacy_deployment_resource_version=args.legacy_deployment_resource_version,
                legacy_provider_uid=args.legacy_provider_uid,
                legacy_provider_resource_version=args.legacy_provider_resource_version,
            )
        elif args.execute:
            result = GatewayDeployer(
                KubernetesClient(), args.ca_directory or default_ca_directory()
            ).reconcile(isolate_provider=args.isolate_provider)
        else:
            result = dry_run_plan()
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
