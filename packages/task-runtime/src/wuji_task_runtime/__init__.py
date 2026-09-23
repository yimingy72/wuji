"""Task infrastructure primitives; importing this package does not contact a cluster."""

from .controller import PodClient, PermitSource, TaskRuntimeController
from .capture_client import CaptureControlClient
from .process_cleanup import ProcessCleanupClient
from .kubernetes_client import KubernetesPodClient
from .manifest import build_task_pod, verify_pod_ownership, verify_resource_ownership
from .models import (
    CapturePolicy, ContainerResources, ExecutionPermit, RuntimeObservation,
    TaskRuntimeConfig, validate_execution_permit,
)

__all__ = [
    "CaptureControlClient", "ProcessCleanupClient", "CapturePolicy", "ContainerResources", "ExecutionPermit", "RuntimeObservation", "TaskRuntimeConfig",
    "TaskRuntimeController", "KubernetesPodClient", "PodClient", "PermitSource",
    "validate_execution_permit", "build_task_pod", "verify_pod_ownership", "verify_resource_ownership",
]
