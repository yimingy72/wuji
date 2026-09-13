"""C0 PG-backed Pod permission/receiver tests with a recording PodClient.

These tests prove the platform permission, session lease, ownership checks and
P09 receiver row. The PodClient records the Kubernetes contract; Bacon's C2 run
is the separate proof that a real Kubernetes API and Pod satisfy it.
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "packages" / "task-runtime" / "src"))

from support.p03 import access
from support.p06 import OWNER, TASK, task_admission_config
from test_work_state_guards import command, control_case
from wuji_core.admission.registry import register_task_config
from wuji_core.execution.pod_runtime import (
    NAMESPACE,
    PodReceiverRegistration,
    VNextPodRuntime,
)
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError
from wuji_task_runtime.errors import OwnershipError
from wuji_task_runtime.manifest import build_task_pod
from wuji_task_runtime.models import ContainerResources, TaskRuntimeConfig


CONTROLLER_SUBJECT = "pod-controller-fixture"
RECEIVER_SUBJECT = "observer-fixture"
TEMPLATE_REF = "pod-worker-template-v1"
POD_UID = "actual-observed-pod-uid"


class RecordingPodClient:
    """Record trusted API inputs while returning complete API-shaped objects."""

    def __init__(self, config: TaskRuntimeConfig, *, pod=None):
        self.config = config
        self.pod = deepcopy(pod)
        self.created = []
        self.deleted = []
        self.resource_reads = []

    def read_pod(self, namespace, name):
        assert (namespace, name) == (self.config.namespace, self.config.pod_name)
        return deepcopy(self.pod)

    def list_task_pods(self, config):
        assert config == self.config
        return [] if self.pod is None else [deepcopy(self.pod)]

    def read_resource(self, kind, namespace, name):
        self.resource_reads.append((kind, namespace, name))
        return {
            "metadata": {
                "name": name,
                "namespace": namespace,
                "labels": self.config.identity_labels,
                "annotations": self.config.ownership_annotations,
            }
        }

    def create_pod(self, namespace, body):
        assert namespace == self.config.namespace
        self.created.append(deepcopy(body))
        self.pod = _ready_pod(self.config, POD_UID)
        return deepcopy(self.pod)

    def delete_pod(self, namespace, name, *, uid, resource_version):
        self.deleted.append((namespace, name, uid, resource_version))
        if self.pod is None:
            return False
        self.pod["metadata"]["deletionTimestamp"] = "2026-09-13T14:00:00Z"
        return True


def _ready_pod(config: TaskRuntimeConfig, uid: str):
    pod = build_task_pod(config)
    pod["metadata"].update(uid=uid, resourceVersion="7")
    pod["status"] = {
        "phase": "Running",
        "conditions": [{"type": "Ready", "status": "True"}],
        "containerStatuses": [
            {"name": name, "ready": True, "state": {"running": {}}}
            for name in ("agent", "kali")
        ],
    }
    return pod


@contextmanager
def _pod_case(environment, tmp_path, audit_directory):
    profiles = {"explore": {"ref": "harness.explore.c0.v1", "revision": "1"}}
    controller_access = access(CONTROLLER_SUBJECT, role="controller")
    receiver = PodReceiverRegistration(
        receiver_id="receiver-fixture",
        receiver_subject=RECEIVER_SUBJECT,
        environment_ref="environment-fixture",
        credential_template_ref=TEMPLATE_REF,
        model_mode="synthetic",
    )
    with control_case(environment, tmp_path, audit_directory) as case:
        with environment.migration_connection() as connection:
            definition = strict_json_loads(
                connection.execute(
                    "SELECT definition_json FROM vnext.task WHERE task_id=%s", (TASK,)
                ).fetchone()[0]
            )
            definition["worker_profiles"] = profiles
            encoded = canonical_json_bytes(definition).decode("utf-8")
            definition_digest = sha256(encoded.encode("utf-8")).hexdigest()
            connection.execute(
                "UPDATE vnext.task SET definition_json=%s,definition_digest=%s WHERE task_id=%s",
                (encoded, definition_digest, TASK),
            )
            config = task_admission_config(
                __import__("wuji_core.admission.registry", fromlist=["TaskAdmissionConfig"]),
                gateway_url="https://model.fixture.invalid/v1",
                allowed_tool_refs=[],
            )
            register_task_config(connection, owner=OWNER, config=config)
            connection.execute(
                """INSERT INTO vnext.task_access(
                tenant_id,project_id,task_id,subject,can_read,can_observe,can_admit,clearance)
                VALUES(%s,%s,%s,%s,true,true,true,1)""",
                (*OWNER, CONTROLLER_SUBJECT),
            )
            connection.execute(
                """INSERT INTO vnext.scheduler_identity_template(
                tenant_id,project_id,task_id,template_ref,issuer,audience,
                signing_key_ref,signing_kid,encryption_key_ref,clearance,enabled)
                VALUES(%s,%s,%s,%s,'https://pod.identity.fixture.invalid',
                'wuji-c0-pod','pod-signing-key','pod-kid','pod-encryption-key',1,true)""",
                (*OWNER, TEMPLATE_REF),
            )
            connection.execute(
                """INSERT INTO vnext.task_pod_controller(
                tenant_id,project_id,task_id,controller_subject,login_role,enabled)
                VALUES(%s,%s,%s,%s,%s,true)""",
                (*OWNER, CONTROLLER_SUBJECT, environment.application_role),
            )
        command(case, "start", key="c0-pod-start")
        with environment.migration_connection() as connection:
            task = connection.execute(
                """SELECT runtime_attempt,execution_epoch,definition_digest,definition_json
                FROM vnext.task WHERE tenant_id=%s AND project_id=%s AND task_id=%s""",
                OWNER,
            ).fetchone()
        saved_definition = strict_json_loads(task[3])
        runtime_config = TaskRuntimeConfig(
            tenant_id=OWNER[0],
            task_id=OWNER[2],
            namespace=NAMESPACE,
            runtime_attempt=int(task[0]),
            execution_epoch=int(task[1]),
            scope_digest=sha256(
                canonical_json_bytes(saved_definition["task"]["authorization_scope"])
            ).hexdigest(),
            config_digest=task[2],
            agent_image="example.invalid/wuji-agent@sha256:" + "a" * 64,
            kali_image="example.invalid/wuji-kali@sha256:" + "b" * 64,
            agent_resources=ContainerResources("100m", "128Mi", "1", "512Mi"),
            kali_resources=ContainerResources("200m", "256Mi", "2", "1Gi"),
            tmp_size_limit="128Mi",
            pod_deadline_seconds=300,
            expose_pod_identity=True,
            kali_receipts_enabled=True,
        )
        yield SimpleNamespace(
            case=case,
            config=runtime_config,
            access=controller_access,
            receiver=receiver,
            profiles=profiles,
        )


def _runtime(case, connection, pods):
    return VNextPodRuntime(
        case.config,
        connection=connection,
        access=case.access,
        control=case.case.control,
        pods=pods,
        receiver=case.receiver,
    )


def test_current_p05_permit_session_lease_verified_uid_and_receiver_registration(
    db_environment, tmp_path, audit_directory
):
    with _pod_case(db_environment, tmp_path, audit_directory) as case:
        pods = RecordingPodClient(case.config)
        with db_environment.additional_app_connection() as connection:
            with _runtime(case, connection, pods) as runtime:
                permit = runtime.permits.current(TASK)
                assert permit is not None
                assert permit.runtime_attempt == case.config.runtime_attempt
                assert permit.execution_epoch == case.config.execution_epoch
                assert permit.scope_digest == case.config.scope_digest
                observation = runtime.ensure()
                assert (observation.state, observation.pod_uid) == ("ready", POD_UID)

                with db_environment.migration_connection() as owner:
                    registered = owner.execute(
                        """SELECT receiver_id,receiver_subject,environment_ref,
                        credential_template_ref,model_mode,pod_uid,enabled
                        FROM vnext.scheduler_receiver
                        WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                          AND runtime_attempt=%s""",
                        (*OWNER, case.config.runtime_attempt),
                    ).fetchone()
                assert registered == (
                    case.receiver.receiver_id,
                    case.receiver.receiver_subject,
                    case.receiver.environment_ref,
                    case.receiver.credential_template_ref,
                    case.receiver.model_mode,
                    POD_UID,
                    True,
                )

                second_pods = RecordingPodClient(case.config)
                with db_environment.additional_app_connection() as second_connection:
                    with pytest.raises(DomainError) as conflict:
                        with _runtime(case, second_connection, second_pods):
                            pass
                assert conflict.value.code == "pod_runtime_owned_elsewhere"
                assert second_pods.created == []

                manifest = pods.created[0]
                volumes = {item["name"]: item for item in manifest["spec"]["volumes"]}
                assert volumes["kali-receipts"]["persistentVolumeClaim"]["claimName"] == (
                    case.config.resource_names["kali_receipts"]
                )
                containers = {
                    item["name"]: item for item in manifest["spec"]["containers"]
                }
                agent_mounts = {item["mountPath"] for item in containers["agent"]["volumeMounts"]}
                kali_mounts = {
                    item["mountPath"]: item for item in containers["kali"]["volumeMounts"]
                }
                assert "/var/lib/wuji/kali-receipts" not in agent_mounts
                assert kali_mounts["/var/lib/wuji/kali-receipts"]["name"] == "kali-receipts"
                assert containers["kali"]["securityContext"]["runAsUser"] == 10002
                assert manifest["spec"]["securityContext"]["fsGroup"] == 10000
                assert (
                    "PersistentVolumeClaim",
                    NAMESPACE,
                    case.config.resource_names["kali_receipts"],
                ) in pods.resource_reads

        with db_environment.migration_connection() as owner:
            assert owner.execute(
                "SELECT enabled FROM vnext.scheduler_receiver WHERE task_id=%s",
                (TASK,),
            ).fetchone() == (False,)

        replacement_pods = RecordingPodClient(
            case.config, pod=_ready_pod(case.config, "replacement-pod-uid")
        )
        with db_environment.additional_app_connection() as replacement_connection:
            with _runtime(case, replacement_connection, replacement_pods) as replacement:
                with pytest.raises(OwnershipError, match="Pod UID"):
                    replacement.ensure()
        assert replacement_pods.created == []
        assert replacement_pods.deleted == []


def test_foreign_pod_owner_cannot_register_receiver(
    db_environment, tmp_path, audit_directory
):
    with _pod_case(db_environment, tmp_path, audit_directory) as case:
        pod = _ready_pod(case.config, "foreign-pod-uid")
        pod["metadata"]["labels"]["wuji.dev/tenant-id"] = "another-tenant"
        pods = RecordingPodClient(case.config, pod=pod)
        with db_environment.additional_app_connection() as connection:
            with _runtime(case, connection, pods) as runtime:
                with pytest.raises(OwnershipError, match="ownership"):
                    runtime.ensure()
        assert pods.created == [] and pods.deleted == []
        with db_environment.migration_connection() as owner:
            assert owner.execute(
                "SELECT count(*) FROM vnext.scheduler_receiver WHERE task_id=%s",
                (TASK,),
            ).fetchone() == (0,)
