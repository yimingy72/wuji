"""Render the isolated vNext static web deployment.

This module deliberately has no dependency on the legacy API, Cairn, runtime,
scheduler, gates, or Task Pod renderers. It only emits the web Deployment,
Service, and its explicit public runtime configuration.
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

NAMESPACE = "wuji-vnext-test"
SERVICE_NAME = "wuji-web"
IMAGE_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}$")
LOCAL_ACCESS_COMMAND = "kubectl -n wuji-vnext-test port-forward svc/wuji-web 4180:80"


def _metadata(name: str, *, labels: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "namespace": NAMESPACE,
        "labels": {"app.kubernetes.io/part-of": "wuji-vnext", "app.kubernetes.io/component": "web", **(labels or {})},
    }


def _validate_image(image: str) -> str:
    if not IMAGE_REFERENCE.fullmatch(image):
        raise ValueError("web image must be an immutable @sha256 digest reference")
    return image


def _runtime_config(api_base_url: str, auth_entrypoint: str) -> str:
    document = {
        "apiBaseUrl": api_base_url.strip(),
        "authEntrypoint": auth_entrypoint.strip(),
    }
    encoded = json.dumps(document, ensure_ascii=False, separators=(",", ":"))
    return f"window.__WUJI_CONFIG__ = {encoded};\n"


def build_web_manifests(
    image: str,
    *,
    api_base_url: str = "",
    auth_entrypoint: str = "",
) -> list[dict[str, Any]]:
    """Return ConfigMap, Deployment, and Service for the isolated web shell."""

    image = _validate_image(image)
    labels = {"app.kubernetes.io/name": SERVICE_NAME, "wuji.dev/service": "web"}
    return [
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": _metadata("wuji-web-config", labels=labels),
            "data": {"config.js": _runtime_config(api_base_url, auth_entrypoint)},
        },
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": _metadata(SERVICE_NAME, labels=labels),
            "spec": {
                "replicas": 1,
                "strategy": {"type": "Recreate"},
                "selector": {"matchLabels": labels},
                "template": {
                    "metadata": {"labels": labels},
                    "spec": {
                        "nodeSelector": {"kubernetes.io/arch": "arm64"},
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
                            {"name": "web-config", "configMap": {"name": "wuji-web-config", "items": [{"key": "config.js", "path": "config.js"}]}},
                        ],
                    },
                },
            },
        },
        {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                **_metadata(SERVICE_NAME, labels=labels),
                "annotations": {"wuji.dev/local-access": LOCAL_ACCESS_COMMAND},
            },
            "spec": {
                "type": "ClusterIP",
                "selector": labels,
                "ports": [{"name": "http", "port": 80, "targetPort": "http"}],
            },
        },
    ]


def render_json_documents(manifests: list[dict[str, Any]]) -> str:
    return "\n---\n".join(json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True) for item in manifests) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render wuji-vnext-test static web manifests")
    parser.add_argument("--image", required=True)
    parser.add_argument("--api-base-url", default="")
    parser.add_argument("--auth-entrypoint", default="")
    args = parser.parse_args()
    print(render_json_documents(build_web_manifests(args.image, api_base_url=args.api_base_url, auth_entrypoint=args.auth_entrypoint)), end="")


if __name__ == "__main__":
    main()
