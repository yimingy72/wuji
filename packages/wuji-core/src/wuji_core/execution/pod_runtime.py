"""Trusted platform assembly of P05 permission, Task Pods and P09 receivers.

Keep one instance/session alive for the platform service's management lifetime::

    with VNextPodRuntime(config, connection=connection, access=controller_access,
                         control=control, pods=pods, receiver=receiver) as runtime:
        observation = runtime.ensure()

``ready`` describes infrastructure only. Scheduler admission and the P10/P06
execution checks still authorize every Run and operation. Node owns Run processes,
never the Pod. This module does not create credentials, ACLs, runtime attempts,
Kubernetes supporting resources, or deploy TLS endpoints.

The 0017 registration functions are installed by the platform migration owner.
They recheck the dedicated controller login/subject, current ACLs, Task state,
and this backend's actual advisory lock. There is no owner-connection fallback.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from threading import RLock
from typing import Literal

from psycopg.pq import TransactionStatus

from wuji_core.admission.registry import AdmissionRegistry
from wuji_core.execution.control import ControlService
from wuji_core.execution.states import task_can_run
from wuji_core.http.json_boundary import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import AccessContext, DomainError, UnitOfWork, row
from wuji_task_runtime.controller import PodClient, TaskRuntimeController
from wuji_task_runtime.errors import OwnershipError, PermitDenied, RuntimeConflict
from wuji_task_runtime.manifest import verify_pod_ownership
from wuji_task_runtime.models import (
    ExecutionPermit,
    RuntimeObservation,
    TaskRuntimeConfig,
    validate_execution_permit,
)


NAMESPACE = "wuji-vnext-test"
_LOCK_NAMESPACE = "wuji.vnext.task-pod"


@dataclass(frozen=True, slots=True, kw_only=True)
class PodReceiverRegistration:
    """Deployment-owned receiver metadata; Pod UID and profiles are not inputs."""

    receiver_id: str
    receiver_subject: str
    environment_ref: str
    credential_template_ref: str
    model_mode: Literal["synthetic", "real"]

    def __post_init__(self):
        for field in (
            "receiver_id", "receiver_subject", "environment_ref", "credential_template_ref"
        ):
            value = getattr(self, field)
            if (not isinstance(value, str) or not 1 <= len(value) <= 256
                    or any(ord(char) < 32 or ord(char) == 127 for char in value)):
                raise ValueError(f"{field} must be a bounded deployment identifier")
        if self.model_mode not in {"synthetic", "real"}:
            raise ValueError("a known deployed model mode is required")


class TaskPodLease:
    """Task-wide PG session ownership, bound locally to one immutable attempt.

The key deliberately excludes attempt: two different generations must not both
manage the same Task. Every P05 transaction also checks the fixed attempt. A
lost/closed session is terminal for this object; no reconnect or time-based
takeover is attempted. The supplied connection is dedicated and closed on exit.
"""

    def __init__(self, connection, config: TaskRuntimeConfig):
        self.connection, self.config = connection, config
        self._pid = None
        self._key = None
        self._closed = False

    def acquire(self):
        if self._closed or self.connection.closed:
            raise DomainError("pod_runtime_ownership_lost", 503)
        if self._pid is not None:
            self.check()
            return
        if self.connection.info.transaction_status != TransactionStatus.IDLE:
            raise ValueError("Pod runtime requires an idle dedicated PG session")
        try:
            with self.connection.transaction():
                self.connection.execute(
                    "SELECT set_config('statement_timeout','5000',true),"
                    "set_config('lock_timeout','5000',true)"
                )
                privilege = self.connection.execute(
                    """SELECT r.rolsuper OR r.rolbypassrls
                    OR current_user=pg_get_userbyid(n.nspowner)
                    FROM pg_roles r CROSS JOIN pg_namespace n
                    WHERE r.rolname=current_user AND n.nspname='vnext'"""
                ).fetchone()
                if privilege != (False,):
                    raise DomainError("pod_runtime_requires_application_role", 503)
                self._key = self.connection.execute(
                    "SELECT hashtextextended(json_build_array(%s::text,%s::text,%s::text)::text,0)",
                    (_LOCK_NAMESPACE, str(self.config.tenant_id), str(self.config.task_id)),
                ).fetchone()[0]
                # Session locks are reentrant: reject another manager borrowing
                # the very same connection instead of acquiring a second count.
                if self._held():
                    raise DomainError("pod_runtime_session_already_in_use", 409)
                acquired, pid = self.connection.execute(
                    "SELECT pg_try_advisory_lock(%s::bigint),pg_backend_pid()",
                    (self._key,),
                ).fetchone()
                if not acquired:
                    raise DomainError("pod_runtime_owned_elsewhere", 409)
                self._pid = pid
        except BaseException:
            self.close()
            raise

    def _held(self):
        return self.connection.execute(
            """SELECT EXISTS(SELECT 1 FROM pg_locks
            WHERE locktype='advisory' AND pid=pg_backend_pid() AND granted
              AND mode='ExclusiveLock' AND objsubid=1
              AND classid::bigint=((%s::bigint >> 32) & 4294967295)
              AND objid::bigint=(%s::bigint & 4294967295)
              AND database=(SELECT oid FROM pg_database WHERE datname=current_database()))""",
            (self._key, self._key),
        ).fetchone() == (True,)

    def assert_owned(self):
        if self._closed or self.connection.closed or self._pid is None:
            raise DomainError("pod_runtime_ownership_lost", 503)
        try:
            if self.connection.execute("SELECT pg_backend_pid()").fetchone() != (self._pid,) or not self._held():
                raise DomainError("pod_runtime_ownership_lost", 503)
        except BaseException:
            self.close()
            raise

    def check(self):
        if self._closed or self.connection.closed or self._pid is None:
            raise DomainError("pod_runtime_ownership_lost", 503)
        with self.connection.transaction():
            self.connection.execute("SELECT set_config('statement_timeout','5000',true)")
            self.assert_owned()

    @contextmanager
    def borrow(self):
        if self._closed or self.connection.closed or self._pid is None:
            raise DomainError("pod_runtime_ownership_lost", 503)
        yield self.connection

    def close(self):
        self._closed = True
        self._pid = None
        # Closing the actual session releases even an ambiguously acquired lock.
        # It can never be returned to a pool with a live session lock attached.
        self.connection.close()


class P05PermitSource:
    """Current persisted permission through the existing UoW and ControlService."""

    def __init__(self, *, config, lease, access, control):
        self.config, self.lease, self.access, self.control = config, lease, access, control
        self.uow = UnitOfWork(lease.borrow)
        self.registry = AdmissionRegistry(self.uow)

    @contextmanager
    def transaction(self):
        with self.uow.transaction(
            self.access, str(self.config.task_id), capability="admit"
        ) as tx:
            self.lease.assert_owned()
            roles = self.access.principal.roles
            if ("controller" not in roles or roles & {"agent", "worker", "supervisor"}
                    or not tx.permissions.get("can_observe")
                    or not tx.permissions.get("can_admit")
                    or tx.owner[0] != str(self.config.tenant_id)):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            yield tx
            self.lease.assert_owned()

    def in_transaction(self, tx):
        if not task_can_run(tx.task):
            raise PermitDenied("Task is not currently activated and runnable")
        definition = self.control._definition(tx)
        admission = self.registry.config(tx)
        expires = min(
            datetime.fromisoformat(definition["task"]["authorization_expires_at"].replace("Z", "+00:00")),
            tx.task["activated_at"] + timedelta(seconds=admission.runtime.limits.max_elapsed_seconds),
        )
        # The immutable P05 start event and its accepted task-command receipt
        # supply provenance. Never manufacture a UUID or treat queued as start.
        start = row(tx.connection.execute(
            """SELECT event_seq,payload_json FROM vnext.outbox
            WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND kind='task.started'
            ORDER BY event_seq LIMIT 1""", tx.owner,
        ))
        if start is None:
            raise PermitDenied("a persisted explicit Task start is required")
        started = strict_json_loads(start["payload_json"])
        if (started.get("task_id") != tx.owner[2]
                or started.get("definition_digest") != tx.task["definition_digest"]):
            raise PermitDenied("Task start definition binding differs")
        command = tx.connection.execute(
            """SELECT c.operation_id FROM vnext.outbox o
            JOIN vnext.control_receipt c ON
              (c.tenant_id,c.project_id,c.task_id)=(o.tenant_id,o.project_id,o.task_id)
              AND c.operation_id=o.payload_json::jsonb->>'command_id'
              AND c.operation_kind='task_command'
            WHERE o.tenant_id=%s AND o.project_id=%s AND o.task_id=%s
              AND o.kind='control.applied' AND o.event_seq>%s
              AND c.receipt_json::jsonb->>'disposition'='accepted'
              AND c.receipt_json::jsonb->'resource_ref'->>'entity_type'='task'
              AND c.receipt_json::jsonb->'resource_ref'->>'id'=%s
            ORDER BY o.event_seq LIMIT 1""",
            (*tx.owner, start["event_seq"], tx.owner[2]),
        ).fetchone()
        if command is None:
            raise PermitDenied("the accepted Task start command is unavailable")
        if self.config.pod_deadline_seconds > admission.runtime.limits.max_elapsed_seconds:
            raise PermitDenied("Pod deadline exceeds the fixed Task runtime limit")
        permit = ExecutionPermit(
            tenant_id=self.config.tenant_id,
            task_id=self.config.task_id,
            runtime_attempt=int(tx.task["runtime_attempt"]),
            execution_epoch=int(tx.task["execution_epoch"]),
            scope_digest=sha256(canonical_json_bytes(definition["task"]["authorization_scope"])).hexdigest(),
            config_digest=tx.task["definition_digest"],
            start_command_id=command[0],
            expires_at=expires,
        )
        validate_execution_permit(self.config, permit, datetime.now(timezone.utc))
        return permit, definition

    def current(self, task_id):
        if task_id != self.config.task_id:
            return None
        try:
            with self.transaction() as tx:
                permit, _ = self.in_transaction(tx)
                return permit
        except (DomainError, PermitDenied):
            return None


class _LeasedPodClient:
    """Fence each Kubernetes call on the same live management session."""

    def __init__(self, runtime, pods):
        self.runtime, self.pods = runtime, pods

    def _call(self, method, *args, **kwargs):
        self.runtime.lease.check()
        value = method(*args, **kwargs)
        self.runtime.lease.check()
        return value

    def read_pod(self, namespace, name):
        return self._call(self.pods.read_pod, namespace, name)

    def list_task_pods(self, config):
        return self._call(self.pods.list_task_pods, config)

    def read_resource(self, kind, namespace, name):
        return self._call(self.pods.read_resource, kind, namespace, name)

    def create_pod(self, namespace, body):
        return self._call(self.pods.create_pod, namespace, body)

    def delete_pod(self, namespace, name, *, uid, resource_version):
        self.runtime._disable(uid)
        return self._call(
            self.pods.delete_pod, namespace, name, uid=uid, resource_version=resource_version
        )


class VNextPodRuntime:
    """One platform-owned Task/attempt; no Run executor or replacement loop.

Deployment resolves the receiver's TLS Service to this actual Pod identity;
``environment_ref`` is that fixed deployment binding, never a request URL.
    Prerequisites (0017 controller binding, current ACLs, identity template, frozen
definition/admission config, ConfigMaps/Secrets/PVCs) are owner-provisioned.
The Task Pod only receives its own restricted runtime/TLS credentials.
"""

    def __init__(
        self, config: TaskRuntimeConfig, *, connection, access: AccessContext,
        control: ControlService, pods: PodClient, receiver: PodReceiverRegistration,
    ):
        if not isinstance(config, TaskRuntimeConfig) or config.namespace != NAMESPACE:
            raise ValueError("vNext Task Pods require the fixed wuji-vnext-test deployment")
        if not config.expose_pod_identity:
            raise ValueError("vNext Task Pods require Downward API identity")
        if not config.kali_receipts_enabled:
            raise ValueError("vNext Task Pods require durable Kali executor receipts")
        if not isinstance(access, AccessContext) or not isinstance(control, ControlService):
            raise ValueError("trusted AccessContext and existing ControlService required")
        if not isinstance(receiver, PodReceiverRegistration):
            raise ValueError("fixed deployment receiver registration required")
        if (access.principal.tenant_id != str(config.tenant_id)
                or "controller" not in access.principal.roles
                or access.principal.roles & {"agent", "worker", "supervisor"}):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        self.config, self.access, self.receiver = config, access, receiver
        self.lease = TaskPodLease(connection, config)
        self.permits = P05PermitSource(config=config, lease=self.lease, access=access, control=control)
        self.pods = _LeasedPodClient(self, pods)
        self.controller = TaskRuntimeController(self.pods, self.permits)
        self._mutex = RLock()
        self._entered = False
        self._closed = False
        self._registered_uid = None
        self._observed_uid = None

    def __enter__(self):
        with self._mutex:
            if self._entered or self._closed:
                raise DomainError("pod_runtime_lifecycle_conflict", 409)
            self.lease.acquire()
            self._entered = True
            return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            self.close()
        except Exception:
            if exc is None:
                raise
        return False

    def _require_open(self):
        if not self._entered or self._closed:
            raise DomainError("pod_runtime_ownership_lost", 503)
        self.lease.check()

    def _registered(self, tx):
        return row(tx.connection.execute(
            """SELECT * FROM vnext.scheduler_receiver
            WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND runtime_attempt=%s""",
            (*tx.owner, self.config.runtime_attempt),
        ))

    def _match_registered(self, record, *, uid=None):
        if any(record[name] != getattr(self.receiver, name) for name in (
            "receiver_id", "receiver_subject", "environment_ref", "credential_template_ref", "model_mode"
        )) or not record["pod_uid"] or (uid is not None and record["pod_uid"] != uid):
            raise OwnershipError("registered receiver/Pod identity cannot be replaced within an attempt")
        self._registered_uid = record["pod_uid"]

    def _disable(self, uid):
        with self.permits.transaction() as tx:
            existing = self._registered(tx)
            if existing is None:
                return
            self._match_registered(existing, uid=uid)
            disabled = tx.connection.execute(
                "SELECT vnext.disable_task_pod_receiver(%s,%s,%s,%s,%s,%s)",
                (*tx.owner, self.config.runtime_attempt, self.receiver.receiver_id, uid),
            ).fetchone()
            if disabled != (True,):
                raise DomainError("pod_receiver_disable_unconfirmed", 503)

    def ensure(self) -> RuntimeObservation:
        with self._mutex:
            self._require_open()
            try:
                revoked_uid = None
                with self.permits.transaction() as tx:
                    # Read the durable receiver binding before checking that the
                    # Task is still runnable.  A cancelled/revoked Task must be
                    # able to stop its exact previously registered Pod; failing
                    # closed at this point must not leak the environment.
                    existing = self._registered(tx)
                    if existing is not None:
                        self._match_registered(existing)
                    try:
                        self.permits.in_transaction(tx)
                    except PermitDenied:
                        if existing is None or not existing["pod_uid"]:
                            raise
                        revoked_uid = existing["pod_uid"]
                if revoked_uid is not None:
                    stopped = self.stop(pod_uid=revoked_uid)
                    self._registered_uid = None
                    self._observed_uid = None
                    return RuntimeObservation(
                        stopped.state, stopped.pod_name, stopped.pod_uid,
                        "permit_revoked",
                    )
                # Once P09 has observed a UID, absence means reconcile the old
                # generation; it is never permission to create a replacement.
                if self._registered_uid is not None:
                    previous = self.pods.read_pod(self.config.namespace, self.config.pod_name)
                    if previous is None:
                        self._disable(self._registered_uid)
                        raise RuntimeConflict("registered Pod is absent; explicit runtime reconciliation required")
                    verify_pod_ownership(previous, self.config, expected_uid=self._registered_uid)
                observation = self.controller.ensure(self.config)
                self._observed_uid = observation.pod_uid
                if observation.state != "ready":
                    if self._registered_uid is not None:
                        self._disable(self._registered_uid)
                    return observation
                # Do not trust a create response, Downward API report, or a
                # supplied UID. Re-read through the trusted Kubernetes client.
                pod = self.pods.read_pod(self.config.namespace, self.config.pod_name)
                if pod is None:
                    raise RuntimeConflict("Pod disappeared before receiver registration")
                verify_pod_ownership(pod, self.config, expected_uid=observation.pod_uid)
                if not _ready(pod):
                    if self._registered_uid is not None:
                        self._disable(self._registered_uid)
                    return RuntimeObservation("provisioning", self.config.pod_name, observation.pod_uid)
                uid = pod["metadata"]["uid"]
                with self.permits.transaction() as tx:
                    permit, definition = self.permits.in_transaction(tx)
                    profiles = definition.get("worker_profiles")
                    if not isinstance(profiles, dict) or not profiles:
                        raise DomainError("worker_profile_unavailable", 503)
                    existing = self._registered(tx)
                    if existing is not None:
                        self._match_registered(existing, uid=uid)
                    registered = tx.connection.execute(
                        "SELECT vnext.register_task_pod_receiver("
                        "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (*tx.owner, self.config.runtime_attempt, self.config.execution_epoch,
                         permit.config_digest, permit.scope_digest, self.receiver.receiver_id,
                         self.receiver.receiver_subject, self.receiver.environment_ref,
                         self.receiver.credential_template_ref, self.receiver.model_mode, uid,
                         canonical_json_bytes(profiles).decode()),
                    ).fetchone()
                    if registered != (True,):
                        raise DomainError("pod_receiver_registration_unconfirmed", 503)
                self._registered_uid = uid
                return observation
            except (PermitDenied, DomainError, OwnershipError, RuntimeConflict):
                # No speculative replacement or Task/Run state edits on failure.
                # Disable an exact known binding while its management authority
                # is available. Permission/connection failures themselves fail
                # closed; they never fall back to a different DB session.
                if self._registered_uid is not None:
                    self._disable(self._registered_uid)
                raise

    def stop(self, *, pod_uid: str) -> RuntimeObservation:
        with self._mutex:
            self._require_open()
            if not isinstance(pod_uid, str) or not pod_uid:
                raise OwnershipError("previously observed Pod UID required")
            with self.permits.transaction() as tx:
                existing = self._registered(tx)
                if existing is not None:
                    self._match_registered(existing, uid=pod_uid)
            # Ownership and UID are rechecked by TaskRuntimeController; stop is
            # valid after epoch revocation and does not claim Run process exit.
            self._disable(pod_uid)
            return self.controller.stop(self.config, pod_uid)

    def close(self):
        with self._mutex:
            if self._closed:
                return
            try:
                if self._entered and self._registered_uid is not None:
                    self._disable(self._registered_uid)
            finally:
                self._closed = True
                self._entered = False
                self.lease.close()


def _ready(pod):
    if pod.get("metadata", {}).get("deletionTimestamp"):
        return False
    status = pod.get("status") or {}
    running = {
        item.get("name") for item in status.get("containerStatuses", [])
        if item.get("ready") is True and item.get("state", {}).get("running") is not None
    }
    return (status.get("phase") == "Running" and running == {"agent", "kali"}
            and any(item.get("type") == "Ready" and item.get("status") == "True"
                    for item in status.get("conditions", [])))
