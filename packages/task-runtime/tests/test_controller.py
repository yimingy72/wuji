from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from wuji_task_runtime import ExecutionPermit, TaskRuntimeController, build_task_pod
from wuji_task_runtime.errors import OwnershipError, PermitDenied, RuntimeConflict, RuntimeTransportError

NOW = datetime(2026, 9, 11, tzinfo=timezone.utc)


class Permits:
    def __init__(self, config, *, revoke_after=None):
        self.calls = 0
        self.revoke_after = revoke_after
        self.permit = ExecutionPermit(
            config.tenant_id, config.task_id, config.runtime_attempt, config.execution_epoch,
            config.scope_digest, config.config_digest,
            UUID("00000000-0000-4000-8000-000000000003"), NOW + timedelta(minutes=1),
        )

    def current(self, task_id):
        self.calls += 1
        return None if self.revoke_after is not None and self.calls > self.revoke_after else self.permit


class Pods:
    def __init__(self, config):
        self.config = config
        self.pod = None
        self.others = []
        self.created = []
        self.deleted = []
        self.read_error = None

    def read_pod(self, namespace, name):
        if self.read_error:
            raise self.read_error
        return deepcopy(self.pod)

    def list_task_pods(self, config):
        return deepcopy(self.others + ([self.pod] if self.pod else []))

    def read_resource(self, kind, namespace, name):
        return {"metadata": {"name": name, "namespace": namespace, "labels": self.config.identity_labels}}

    def create_pod(self, namespace, body):
        self.created.append(deepcopy(body))
        self.pod = deepcopy(body)
        self.pod["metadata"].update(uid="owned-uid", resourceVersion="7")
        return deepcopy(self.pod)

    def delete_pod(self, namespace, name, *, uid, resource_version):
        self.deleted.append((name, uid, resource_version))
        self.pod["metadata"]["deletionTimestamp"] = "2026-09-11T00:00:00Z"
        return True


def setup(config):
    pods, permits = Pods(config), Permits(config)
    return pods, permits, TaskRuntimeController(pods, permits, lambda: NOW)


def test_create_reuse_ready_and_confirmed_stop(config):
    pods, _, controller = setup(config)
    assert controller.ensure(config).state == "provisioning"
    pods.pod["status"] = {
        "phase": "Running", "conditions": [{"type": "Ready", "status": "True"}],
        "containerStatuses": [
            {"name": name, "ready": True, "state": {"running": {}}} for name in ("agent", "kali")
        ],
    }
    assert controller.ensure(config).state == "ready"
    assert len(pods.created) == 1
    assert controller.stop(config, "owned-uid").state == "stopping"
    assert pods.deleted == [(config.pod_name, "owned-uid", "7")]
    assert controller.stop(config, "owned-uid").state == "stopping"
    pods.pod = None
    assert controller.stop(config, "owned-uid").state == "stopped"
    assert len(pods.deleted) == 1


@pytest.mark.parametrize("invalid", ["missing", "expired", "epoch", "scope"])
def test_invalid_current_permission_never_creates(config, invalid):
    pods, permits, controller = setup(config)
    if invalid == "missing":
        permits.permit = None
    elif invalid == "expired":
        permits.permit = replace(permits.permit, expires_at=NOW)
    elif invalid == "epoch":
        permits.permit = replace(permits.permit, execution_epoch=3)
    else:
        permits.permit = replace(permits.permit, scope_digest="f" * 64)
    with pytest.raises(PermitDenied):
        controller.ensure(config)
    assert pods.created == []


def test_revocation_during_create_stops_only_returned_uid(config):
    pods = Pods(config)
    controller = TaskRuntimeController(pods, Permits(config, revoke_after=2), lambda: NOW)
    result = controller.ensure(config)
    assert result.state == "stopping" and result.reason == "permit_revoked"
    assert pods.deleted == [(config.pod_name, "owned-uid", "7")]


def test_foreign_owner_and_wrong_uid_are_never_deleted(config):
    pods, _, controller = setup(config)
    controller.ensure(config)
    with pytest.raises(OwnershipError):
        controller.stop(config, "different-uid")
    pods.pod["metadata"]["labels"]["wuji.dev/tenant-id"] = "another-tenant"
    with pytest.raises(OwnershipError):
        controller.ensure(config)
    assert len(pods.created) == 1 and pods.deleted == []


def test_previous_generation_blocks_creation(config):
    pods, _, controller = setup(config)
    previous = build_task_pod(replace(config, runtime_attempt=2))
    previous["metadata"].update(uid="other-uid", resourceVersion="4")
    pods.others = [previous]
    with pytest.raises(RuntimeConflict):
        controller.ensure(config)
    assert pods.created == [] and pods.deleted == []


def test_non_notfound_read_error_is_not_absence(config):
    pods, _, controller = setup(config)
    pods.read_error = RuntimeTransportError("read-pod", 403)
    with pytest.raises(RuntimeTransportError):
        controller.ensure(config)
    assert pods.created == []


def test_create_conflict_reuses_only_matching_object(config):
    pods, _, controller = setup(config)
    original_create = pods.create_pod

    def concurrent_create(namespace, body):
        original_create(namespace, body)
        raise RuntimeTransportError("create-pod", 409)

    pods.create_pod = concurrent_create
    result = controller.ensure(config)
    assert result.pod_uid == "owned-uid" and result.state == "provisioning"
    assert len(pods.created) == 1
