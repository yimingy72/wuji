"""Explicit fixture values are examples, never product resource defaults."""
from uuid import UUID

import pytest

from wuji_task_runtime.models import ContainerResources, TaskRuntimeConfig


@pytest.fixture
def config():
    return TaskRuntimeConfig(
        tenant_id=UUID("00000000-0000-4000-8000-000000000001"),
        task_id=UUID("00000000-0000-4000-8000-000000000002"),
        namespace="wuji-test", runtime_attempt=1, execution_epoch=2,
        scope_digest="a" * 64, config_digest="b" * 64,
        agent_image="example.invalid/agent@sha256:" + "c" * 64,
        kali_image="example.invalid/kali@sha256:" + "d" * 64,
        agent_resources=ContainerResources("100m", "128Mi", "1", "512Mi"),
        kali_resources=ContainerResources("200m", "256Mi", "2", "1Gi"),
        tmp_size_limit="128Mi", pod_deadline_seconds=600,
    )
