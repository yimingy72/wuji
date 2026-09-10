"""Bounded calls through the upstream Kubernetes client, without kubeconfig discovery."""

from __future__ import annotations

import math
from typing import Callable

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from .errors import RuntimeStateUnknown, RuntimeTransportError
from .models import LABEL_ATTEMPT, TaskRuntimeConfig


class KubernetesPodClient:
    def __init__(self, core_v1_api: client.CoreV1Api, request_timeout_seconds: float = 10):
        if not isinstance(request_timeout_seconds, (float, int)) or isinstance(request_timeout_seconds, bool):
            raise ValueError("request timeout must be positive and finite")
        if not math.isfinite(request_timeout_seconds) or request_timeout_seconds <= 0:
            raise ValueError("request timeout must be positive and finite")
        # Configure before constructing ApiClient, so its connection pool also has
        # retries disabled. We do not change another service's shared configuration.
        if core_v1_api.api_client.configuration.retries != 0:
            raise ValueError("construct the Kubernetes ApiClient with configuration.retries=0")
        self.api = core_v1_api
        self.timeout = (request_timeout_seconds, request_timeout_seconds)

    def _call(self, operation: str, method: Callable, *, write: bool = False, missing_ok: bool = False, **kwargs):
        try:
            return method(_request_timeout=self.timeout, **kwargs)
        except ApiException as exc:
            if missing_ok and exc.status == 404:
                return None
            if write and (not exc.status or exc.status >= 500):
                raise RuntimeStateUnknown(operation, exc.status or None) from None
            raise RuntimeTransportError(operation, exc.status or None) from None
        except Exception:
            # Do not expose upstream URLs, response bodies, headers or Secret data.
            error = RuntimeStateUnknown if write else RuntimeTransportError
            raise error(operation) from None

    def _pod_dict(self, value) -> dict:
        result = self.api.api_client.sanitize_for_serialization(value)
        if not isinstance(result, dict):
            raise RuntimeStateUnknown("decode-pod")
        return result

    def read_pod(self, namespace: str, name: str) -> dict | None:
        pod = self._call("read-pod", self.api.read_namespaced_pod, namespace=namespace, name=name, missing_ok=True)
        return None if pod is None else self._pod_dict(pod)

    def list_task_pods(self, config: TaskRuntimeConfig) -> list[dict]:
        labels = {key: value for key, value in config.identity_labels.items() if key != LABEL_ATTEMPT}
        selector = ",".join(f"{key}={value}" for key, value in sorted(labels.items()))
        pods: list[dict] = []
        cursor = None
        for _ in range(10):
            result = self._call(
                "list-task-pods", self.api.list_namespaced_pod,
                namespace=config.namespace, label_selector=selector, limit=100, _continue=cursor,
            )
            pods.extend(self._pod_dict(pod) for pod in result.items)
            cursor = getattr(result.metadata, "_continue", None) if result.metadata is not None else None
            if not cursor:
                return pods
        raise RuntimeTransportError("list-task-pods-pagination-limit")

    def read_resource(self, kind: str, namespace: str, name: str) -> dict | None:
        methods = {
            "ConfigMap": self.api.read_namespaced_config_map,
            "Secret": self.api.read_namespaced_secret,
            "PersistentVolumeClaim": self.api.read_namespaced_persistent_volume_claim,
        }
        if kind not in methods:
            raise ValueError("unsupported task resource kind")
        obj = self._call(f"read-{kind}", methods[kind], namespace=namespace, name=name, missing_ok=True)
        if obj is None:
            return None
        # Deliberately never serialize the resource's data, including Secret values.
        return {"metadata": self.api.api_client.sanitize_for_serialization(obj.metadata)}

    def create_pod(self, namespace: str, body: dict) -> dict:
        return self._pod_dict(self._call("create-pod", self.api.create_namespaced_pod, namespace=namespace, body=body, write=True))

    def delete_pod(self, namespace: str, name: str, *, uid: str, resource_version: str) -> bool:
        body = client.V1DeleteOptions(preconditions=client.V1Preconditions(uid=uid, resource_version=resource_version))
        result = self._call(
            "delete-pod", self.api.delete_namespaced_pod,
            namespace=namespace, name=name, body=body, write=True, missing_ok=True,
        )
        return result is not None
