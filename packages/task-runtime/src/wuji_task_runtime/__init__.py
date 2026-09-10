"""Task infrastructure primitives; importing this package does not contact a cluster."""

from .controller import PodClient, PermitSource, TaskRuntimeController
from .kubernetes_client import KubernetesPodClient
from .manifest import build_task_pod, verify_pod_ownership, verify_resource_ownership
from .models import ContainerResources, ExecutionPermit, RuntimeObservation, TaskRuntimeConfig, validate_execution_permit

__all__ = [
    "ContainerResources", "ExecutionPermit", "RuntimeObservation", "TaskRuntimeConfig",
    "TaskRuntimeController", "KubernetesPodClient", "PodClient", "PermitSource",
    "validate_execution_permit", "build_task_pod", "verify_pod_ownership", "verify_resource_ownership",
]
