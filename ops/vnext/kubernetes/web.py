"""Render the isolated vNext web and optional local browser gateway.

This module has no dependency on the legacy API or Cairn. The optional gateway
is a fixed read-only adapter to the isolated vNext public API; Secret values are
supplied separately and never emitted by this renderer.
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any
from urllib.parse import urlsplit

NAMESPACE = "wuji-vnext-test"
SERVICE_NAME = "wuji-web"
IMAGE_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}$")
LOCAL_ACCESS_URL = "http://127.0.0.1:44180/"
SESSION_CLAIM_NAME = "wuji-web-session-state"
DNS_LABEL = re.compile(r"^[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?$")


def _local_http_origin(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme == "http" and parsed.hostname in {
        "localhost", "127.0.0.1", "::1"
    }


def _metadata(
    name: str, *, namespace: str, labels: dict[str, str]
) -> dict[str, Any]:
    return {
        "name": name,
        "namespace": namespace,
        "labels": dict(labels),
    }


def _validate_image(image: str) -> str:
    if not IMAGE_REFERENCE.fullmatch(image):
        raise ValueError("web image must be an immutable @sha256 digest reference")
    return image


def _runtime_config(
    api_base_url: str,
    auth_entrypoint: str,
    *,
    mode: str = "",
    auth_mode: str = "",
    tenant_id: str = "",
    project_id: str = "",
    task_id: str = "",
) -> str:
    document = {
        "apiBaseUrl": api_base_url.strip(),
        "authEntrypoint": auth_entrypoint.strip(),
    }
    if mode:
        document.update(
            mode=mode,
            authMode=auth_mode,
            tenantId=tenant_id,
            projectId=project_id,
            taskId=task_id,
        )
    encoded = json.dumps(document, ensure_ascii=False, separators=(",", ":"))
    return f"window.__WUJI_CONFIG__ = {encoded};\n"


def build_web_manifests(
    image: str,
    *,
    api_base_url: str = "",
    auth_entrypoint: str = "",
    gateway_image: str | None = None,
    gateway_api_base_url: str = "",
    gateway_secret_name: str = "wuji-web-gateway-credentials",
    gateway_ca_config_map: str = "api-config",
    gateway_auth_mode: str = "local_single_operator",
    identity_issuer: str = "",
    identity_audience: str = "",
    tenant_id: str = "",
    project_id: str = "",
    task_id: str = "",
    display_name: str = "Local test operator",
    allowed_origins: tuple[str, ...] = (),
    namespace: str = NAMESPACE,
    service_name: str = SERVICE_NAME,
    session_claim_name: str = SESSION_CLAIM_NAME,
    architecture: str = "arm64",
    service_port: int = 44180,
    deployment_labels: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Return the ConfigMaps, Deployment and Service for the isolated web."""

    image = _validate_image(image)
    if (
        not DNS_LABEL.fullmatch(namespace)
        or not DNS_LABEL.fullmatch(service_name)
        or not DNS_LABEL.fullmatch(session_claim_name)
        or architecture not in {"amd64", "arm64"}
        or type(service_port) is not int
        or not 1024 <= service_port <= 65535
    ):
        raise ValueError("web deployment identity is invalid")
    labels = {
        "app.kubernetes.io/part-of": "wuji-vnext",
        "app.kubernetes.io/component": "web",
        "app.kubernetes.io/managed-by": "wuji-vnext-deployment",
        "wuji.dev/environment": "local-test",
        **(deployment_labels or {}),
        "app.kubernetes.io/name": service_name,
        "wuji.dev/service": "web",
    }
    web_config_name = service_name + "-config"
    gateway_config_name = service_name + "-gateway-config"
    gateway_enabled = gateway_image is not None
    if gateway_enabled:
        gateway_image = _validate_image(gateway_image)
        required = {
            "gateway_api_base_url": gateway_api_base_url,
            "identity_issuer": identity_issuer,
            "identity_audience": identity_audience,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "gateway_secret_name": gateway_secret_name,
            "gateway_ca_config_map": gateway_ca_config_map,
        }
        if any(not value.strip() for value in required.values()) or not allowed_origins:
            raise ValueError("gateway deployment requires fixed identity and project bindings")
        if api_base_url or auth_entrypoint != "/auth/login":
            raise ValueError("read-only gateway uses same-origin API and fixed login path")
        if gateway_auth_mode not in {"local_single_operator", "local_password"}:
            raise ValueError("gateway authentication mode is unsupported")
        password_local_http = all(_local_http_origin(origin) for origin in allowed_origins)
        password_https = all(origin.startswith("https://") for origin in allowed_origins)
        if gateway_auth_mode == "local_password" and not (
            password_local_http or password_https
        ):
            raise ValueError(
                "local password gateway requires HTTPS or explicit loopback HTTP origins"
            )

    web_config = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": _metadata(web_config_name, namespace=namespace, labels=labels),
            "data": {"config.js": _runtime_config(
                api_base_url,
                auth_entrypoint,
                mode="vnext-readonly" if gateway_enabled else "",
                auth_mode=gateway_auth_mode if gateway_enabled else "",
                tenant_id=tenant_id,
                project_id=project_id,
                task_id=task_id,
            )},
        }
    pod_spec = {
        "nodeSelector": {"kubernetes.io/arch": architecture},
        "automountServiceAccountToken": False,
        "securityContext": {
            "runAsNonRoot": True,
            "seccompProfile": {"type": "RuntimeDefault"},
        },
        "containers": [
            {
                "name": "web",
                "image": image,
                "imagePullPolicy": "IfNotPresent",
                "ports": [{"name": "http", "containerPort": 8080}],
                "securityContext": {
                    "runAsUser": 101,
                    "runAsGroup": 101,
                    "allowPrivilegeEscalation": False,
                    "readOnlyRootFilesystem": True,
                    "capabilities": {"drop": ["ALL"]},
                },
                "resources": {
                    "requests": {"cpu": "25m", "memory": "64Mi"},
                    "limits": {"cpu": "250m", "memory": "256Mi"},
                },
                "readinessProbe": {"httpGet": {"path": "/healthz", "port": "http"}, "periodSeconds": 5},
                "livenessProbe": {"httpGet": {"path": "/healthz", "port": "http"}, "periodSeconds": 15},
                "volumeMounts": [
                    {"name": "tmp", "mountPath": "/tmp"},
                    {"name": "web-config", "mountPath": "/usr/share/nginx/html/config.js", "subPath": "config.js", "readOnly": True},
                ],
            },
        ],
        "volumes": [
            {"name": "tmp", "emptyDir": {"sizeLimit": "64Mi"}},
            {"name": "web-config", "configMap": {"name": web_config_name, "items": [{"key": "config.js", "path": "config.js"}]}},
        ],
    }
    documents = [web_config]
    if gateway_enabled:
        pod_spec["securityContext"]["fsGroup"] = 10000
        pod_spec["containers"][0]["securityContext"]["runAsGroup"] = 10000
        gateway_settings = {
            "schema_version": "wuji.web-gateway.v2",
            "mode": gateway_auth_mode,
            "api_base_url": gateway_api_base_url,
            "ca_file": "/config/api-ca.crt",
            "signing_key_file": "/run/wuji/web/identity.key",
            "session_key_file": "/run/wuji/web/session.key",
            "issuer": identity_issuer,
            "audience": identity_audience,
            "subject": "operator",
            "tenant_id": tenant_id,
            "project_id": project_id,
            "task_id": task_id or None,
            "roles": ["operator"],
            "display_name": display_name,
            "allowed_origins": list(allowed_origins),
            "session_ttl_seconds": 28_800 if gateway_auth_mode == "local_password" else 1800,
            "max_response_bytes": 2_097_152,
            "secure_cookie": all(origin.startswith("https://") for origin in allowed_origins),
        }
        if gateway_auth_mode == "local_password":
            gateway_settings.update(
                password_credential_file="/run/wuji/web/password.json",
                session_db_file="/var/lib/wuji/web/sessions.sqlite3",
            )
        else:
            gateway_settings["local_access_token_file"] = "/run/wuji/web/access.token"
        documents.append({
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": _metadata(gateway_config_name, namespace=namespace, labels=labels),
            "data": {"web-gateway.json": json.dumps(gateway_settings, ensure_ascii=False, separators=(",", ":"))},
        })
        pod_spec["containers"].append({
            "name": "gateway",
            "image": gateway_image,
            "imagePullPolicy": "IfNotPresent",
            "command": [
                "python", "/opt/wuji/services/wuji-web-gateway/main.py",
                "--config", "/config/web-gateway.json", "--host", "127.0.0.1", "--port", "8090",
            ],
            "securityContext": {
                "runAsUser": 10003,
                "runAsGroup": 10000,
                "allowPrivilegeEscalation": False,
                "readOnlyRootFilesystem": True,
                "capabilities": {"drop": ["ALL"]},
            },
            "resources": {
                "requests": {"cpu": "25m", "memory": "64Mi"},
                "limits": {"cpu": "250m", "memory": "256Mi"},
            },
            "readinessProbe": {
                # The probe starts an interpreter inside the container, so a 1 s
                # deadline flaps on a loaded node even while the gateway serves.
                "exec": {"command": [
                    "python", "-c",
                    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/healthz',timeout=3).read()",
                ]},
                "periodSeconds": 10,
                "timeoutSeconds": 5,
                "failureThreshold": 3,
                "successThreshold": 1,
            },
            "volumeMounts": [
                {"name": "tmp", "mountPath": "/tmp"},
                {"name": "gateway-config", "mountPath": "/config/web-gateway.json", "subPath": "web-gateway.json", "readOnly": True},
                {"name": "api-ca", "mountPath": "/config/api-ca.crt", "subPath": "ca.crt", "readOnly": True},
                {"name": "gateway-credentials", "mountPath": "/run/wuji/web", "readOnly": True},
            ],
        })
        pod_spec["volumes"].extend([
            {"name": "gateway-config", "configMap": {"name": gateway_config_name}},
            {"name": "api-ca", "configMap": {"name": gateway_ca_config_map, "items": [{"key": "ca.crt", "path": "ca.crt"}]}},
            {"name": "gateway-credentials", "secret": {"secretName": gateway_secret_name, "defaultMode": 288}},
        ])
        if gateway_auth_mode == "local_password":
            pod_spec["securityContext"]["fsGroupChangePolicy"] = "OnRootMismatch"
            pod_spec["containers"][-1]["volumeMounts"].append(
                {"name": "web-session-state", "mountPath": "/var/lib/wuji/web"}
            )
            pod_spec["volumes"].append(
                {
                    "name": "web-session-state",
                    "persistentVolumeClaim": {"claimName": session_claim_name},
                }
            )
            documents.append({
                "apiVersion": "v1",
                "kind": "PersistentVolumeClaim",
                "metadata": _metadata(
                    session_claim_name, namespace=namespace, labels=labels
                ),
                "spec": {
                    "accessModes": ["ReadWriteOnce"],
                    "resources": {"requests": {"storage": "64Mi"}},
                },
            })

    documents.extend([
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": _metadata(service_name, namespace=namespace, labels=labels),
            "spec": {
                "replicas": 1,
                "strategy": {"type": "Recreate"},
                "selector": {"matchLabels": labels},
                "template": {
                    "metadata": {"labels": labels},
                    "spec": pod_spec,
                },
            },
        },
        {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                **_metadata(service_name, namespace=namespace, labels=labels),
                "annotations": {
                    "wuji.dev/local-access": f"http://127.0.0.1:{service_port}/"
                },
            },
            "spec": {
                "type": "LoadBalancer",
                "selector": labels,
                "ports": [{"name": "http", "port": service_port, "targetPort": "http"}],
            },
        },
    ])
    return documents


def render_json_documents(manifests: list[dict[str, Any]]) -> str:
    return "\n---\n".join(json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True) for item in manifests) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render wuji-vnext-test static web manifests")
    parser.add_argument("--image", required=True)
    parser.add_argument("--api-base-url", default="")
    parser.add_argument("--auth-entrypoint", default="")
    parser.add_argument("--gateway-image")
    parser.add_argument("--gateway-api-base-url", default="")
    parser.add_argument(
        "--gateway-auth-mode",
        choices=("local_password", "local_single_operator"),
        default="local_password",
    )
    parser.add_argument("--identity-issuer", default="")
    parser.add_argument("--identity-audience", default="")
    parser.add_argument("--tenant-id", default="")
    parser.add_argument("--project-id", default="")
    parser.add_argument("--task-id", default="")
    parser.add_argument("--display-name", default="Local test operator")
    parser.add_argument("--allowed-origin", action="append", default=[])
    parser.add_argument("--namespace", default=NAMESPACE)
    parser.add_argument("--service-name", default=SERVICE_NAME)
    parser.add_argument("--session-claim-name", default=SESSION_CLAIM_NAME)
    parser.add_argument("--architecture", choices=("amd64", "arm64"), default="arm64")
    parser.add_argument("--service-port", type=int, default=44180)
    args = parser.parse_args()
    print(render_json_documents(build_web_manifests(
        args.image,
        api_base_url=args.api_base_url,
        auth_entrypoint=args.auth_entrypoint,
        gateway_image=args.gateway_image,
        gateway_api_base_url=args.gateway_api_base_url,
        gateway_auth_mode=args.gateway_auth_mode,
        identity_issuer=args.identity_issuer,
        identity_audience=args.identity_audience,
        tenant_id=args.tenant_id,
        project_id=args.project_id,
        task_id=args.task_id,
        display_name=args.display_name,
        allowed_origins=tuple(args.allowed_origin),
        namespace=args.namespace,
        service_name=args.service_name,
        session_claim_name=args.session_claim_name,
        architecture=args.architecture,
        service_port=args.service_port,
    )), end="")


if __name__ == "__main__":
    main()
