"""Task infrastructure primitives; importing this package does not contact a cluster."""

from .controller import PodClient, PermitSource, TaskRuntimeController
from .kubernetes_client import KubernetesPodClient
from .manifest import build_task_pod, verify_pod_ownership, verify_resource_ownership
from .models import ContainerResources, ExecutionPermit, RuntimeObservation, TaskRuntimeConfig

__all__ = [
    "ContainerResources", "ExecutionPermit", "RuntimeObservation", "TaskRuntimeConfig",
    "TaskRuntimeController", "KubernetesPodClient", "PodClient", "PermitSource",
    "build_task_pod", "verify_pod_ownership", "verify_resource_ownership",
]
