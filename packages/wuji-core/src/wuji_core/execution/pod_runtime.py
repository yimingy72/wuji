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
import json
import time
from typing import Callable, Literal

from psycopg.pq import TransactionStatus

from wuji_core.admission.registry import AdmissionRegistry
from wuji_core.contracts import generated as wire
from wuji_core.contracts.execution import TaskCommand
from wuji_core.evidence.runtime_capture import RuntimeCaptureService
from wuji_core.execution.control import ControlCommandContext, ControlService
from wuji_core.execution.states import task_can_run
from wuji_core.http.json_boundary import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import AccessContext, DomainError, UnitOfWork, row
from wuji_task_runtime.capture_client import CaptureControlClient
from wuji_task_runtime.controller import PodClient, TaskRuntimeController
from wuji_task_runtime.errors import (
    OwnershipError, PermitDenied, RuntimeConflict, RuntimeStateUnknown,
    RuntimeTransportError,
)
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


@dataclass(frozen=True, slots=True, kw_only=True)
class PodCaptureRegistration:
    collector_ref: str
    evidence_origin: Literal["live_capture", "fixture_capture"]
    capture_layer: str

    def __post_init__(self):
        for field in ("collector_ref", "capture_layer"):
            value = getattr(self, field)
            if (
                not isinstance(value, str)
                or not 1 <= len(value) <= 256
                or any(ord(char) < 32 or ord(char) == 127 for char in value)
            ):
                raise ValueError(f"{field} must be a bounded deployment identifier")
        if self.evidence_origin not in {"live_capture", "fixture_capture"}:
            raise ValueError("capture evidence origin is invalid")


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
            raise PermitDenied("Task is not currently activated and runnable", code="task_not_runnable")
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
            raise PermitDenied("a persisted explicit Task start is required", code="start_event_missing")
        started = strict_json_loads(start["payload_json"])
        if (started.get("task_id") != tx.owner[2]
                or started.get("definition_digest") != tx.task["definition_digest"]):
            raise PermitDenied("Task start definition binding differs", code="start_definition_changed")
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
            raise PermitDenied("the accepted Task start command is unavailable", code="start_command_unavailable")
        if self.config.pod_deadline_seconds > admission.runtime.limits.max_elapsed_seconds:
            raise PermitDenied("Pod deadline exceeds the fixed Task runtime limit", code="pod_deadline_exceeds_limit")
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

    def patch_pod_deadline(
        self, namespace, name, *, uid, resource_version, active_deadline_seconds,
    ):
        self.runtime._disable(uid)
        return self._call(
            self.pods.patch_pod_deadline,
            namespace,
            name,
            uid=uid,
            resource_version=resource_version,
            active_deadline_seconds=active_deadline_seconds,
        )

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
        artifacts=None, capture_client: CaptureControlClient | None = None,
        capture_registration: PodCaptureRegistration | None = None,
        capture_ingest_service: RuntimeCaptureService | None = None,
        capture_collector_access: AccessContext | None = None,
        process_shutdown: Callable[..., dict] | None = None,
    ):
        if not isinstance(config, TaskRuntimeConfig):
            raise ValueError("a Task runtime configuration is required")
        if config.template_version == "legacy-v1" and config.namespace != NAMESPACE:
            raise ValueError("legacy vNext Task Pods require the fixed wuji-vnext-test deployment")
        if not config.expose_pod_identity:
            raise ValueError("vNext Task Pods require Downward API identity")
        if not config.kali_receipts_enabled:
            raise ValueError("vNext Task Pods require durable Kali executor receipts")
        if not isinstance(access, AccessContext) or not isinstance(control, ControlService):
            raise ValueError("trusted AccessContext and existing ControlService required")
        if not isinstance(receiver, PodReceiverRegistration):
            raise ValueError("fixed deployment receiver registration required")
        if config.template_version == "core-ctf-v1" and not (
            artifacts is not None
            and isinstance(capture_client, CaptureControlClient)
            and isinstance(capture_registration, PodCaptureRegistration)
            and isinstance(capture_ingest_service, RuntimeCaptureService)
            and isinstance(capture_collector_access, AccessContext)
            and callable(process_shutdown)
        ):
            raise ValueError("core-ctf-v1 requires trusted capture runtime wiring")
        if config.template_version == "core-ctf-v1" and (
            capture_collector_access.principal.subject != capture_registration.collector_ref
            or not {"runtime", "collector"} <= capture_collector_access.principal.roles
            or "agent" in capture_collector_access.principal.roles
        ):
            raise ValueError("capture collector identity does not match registration")
        if (access.principal.tenant_id != str(config.tenant_id)
                or "controller" not in access.principal.roles
                or access.principal.roles & {"agent", "worker", "supervisor"}):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        self.config, self.access, self.receiver = config, access, receiver
        self.control = control
        self.lease = TaskPodLease(connection, config)
        self.permits = P05PermitSource(config=config, lease=self.lease, access=access, control=control)
        self.pods = _LeasedPodClient(self, pods)
        self.controller = TaskRuntimeController(self.pods, self.permits)
        self.capture_client = capture_client
        self.capture_registration = capture_registration
        self.capture_ingest_service = capture_ingest_service
        self.capture_collector_access = capture_collector_access
        self.process_shutdown = process_shutdown
        self.capture_service = (
            RuntimeCaptureService(UnitOfWork(self.lease.borrow), artifacts=artifacts)
            if config.template_version == "core-ctf-v1"
            else None
        )
        self._mutex = RLock()
        self._entered = False
        self._closed = False
        self._registered_uid = None
        self._observed_uid = None
        self._capture_session = None
        self._capture_cursor = 0
        self._capture_drained = False
        self._process_shutdown_confirmed = False
        self._process_shutdown_unknown = False
        self._capture_sealed = False
        self._capture_final_seq = None
        self._capture_seal_status = None
        self._capture_last_status = None
        self._capture_window_incomplete = False

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

    def _capture_binding(self, pod_uid):
        return {
            "task_id": str(self.config.task_id),
            "runtime_attempt": str(self.config.runtime_attempt),
            "execution_epoch": str(self.config.execution_epoch),
            "pod_uid": pod_uid,
        }

    def _capture_status_document(self, local):
        states = {
            "ready": "ready",
            "draining": "draining",
            "sealing": "draining",
            "sealed-complete": "sealed",
            "sealed-incomplete": "failed",
            "failed": "failed",
        }
        state = states.get(local.get("state"))
        if state is None:
            raise DomainError("capture_registration_pending", 503)
        value = {
            "schema_version": "wuji.runtime-capture-status.v1",
            "binding": self._capture_binding(local["binding"]["pod_uid"]),
            "collector_ref": self.capture_registration.collector_ref,
            "environment_ref": self.receiver.environment_ref,
            "evidence_origin": self.capture_registration.evidence_origin,
            "capture_layer": self.capture_registration.capture_layer,
            "state": state,
            "started_at": local["started_at"],
        }
        value["status_digest"] = "0" * 64
        candidate = wire.RuntimeCaptureStatusV1.model_validate(value)
        normalized = candidate.model_dump(mode="json", exclude={"status_digest"})
        value["status_digest"] = sha256(canonical_json_bytes(normalized)).hexdigest()
        return wire.RuntimeCaptureStatusV1.model_validate(value)

    def _register_capture(self, pod_uid):
        self.capture_client.bind_pod_uid(pod_uid)
        local = self.capture_client.status()
        if local.get("binding") != {
            "task_id": str(self.config.task_id),
            "runtime_attempt": self.config.runtime_attempt,
            "execution_epoch": self.config.execution_epoch,
            "pod_uid": pod_uid,
        }:
            raise OwnershipError("capture status identity does not match the observed Pod")
        if local.get("state") != "ready" or local.get("ready") is not True:
            code = (
                "capture_failed"
                if local.get("state") in {"failed", "draining", "sealing", "sealed-complete", "sealed-incomplete"}
                else "capture_registration_pending"
            )
            if code == "capture_failed":
                self._capture_last_status = local
                self._remember_capture_status(local, state="failed")
            raise DomainError(code, 503)
        self._capture_last_status = local
        return self._remember_capture_status(local)

    def _remember_capture_status(self, local, *, state=None):
        source = dict(local)
        if state is not None:
            source.update(state=state, ready=False)
        session = self.capture_service.register_session(
            self.access, self._capture_status_document(source)
        )
        self._capture_session = session
        self._capture_cursor = self.capture_ingest_service.latest_contiguous_item_seq(
            self.capture_collector_access,
            str(self.config.task_id),
            session.capture_session_id,
        )
        return session

    def _restore_capture_session(self, pod_uid):
        if self._capture_session is not None:
            return
        page = self.capture_service.list_sessions(
            self.access, str(self.config.task_id)
        )
        matches = [
            session for session in page.sessions
            if session.binding.runtime_attempt.root == str(self.config.runtime_attempt)
            and session.binding.execution_epoch.root == str(self.config.execution_epoch)
            and session.binding.pod_uid == pod_uid
        ]
        if len(matches) > 1:
            raise DomainError("capture_session_conflict", 409)
        if matches:
            self._capture_session = matches[0]
            state = getattr(matches[0].state, "value", matches[0].state)
            self._capture_last_status = {
                "binding": {"pod_uid": pod_uid},
                "state": state,
                "ready": state == "ready",
                "started_at": matches[0].started_at,
            }
            self._capture_cursor = (
                self.capture_ingest_service.latest_contiguous_item_seq(
                    self.capture_collector_access,
                    str(self.config.task_id),
                    matches[0].capture_session_id,
                )
            )

    def _mark_capture_incomplete(self):
        self._capture_window_incomplete = True
        session_state = getattr(
            getattr(self._capture_session, "state", None), "value",
            getattr(self._capture_session, "state", None),
        )
        if self._capture_last_status is not None and (
            self._capture_session is None or session_state in {"ready", "draining"}
        ):
            try:
                self._remember_capture_status(self._capture_last_status, state="failed")
            except DomainError:
                # Persisting the failure is best effort when Task admission was
                # already revoked; external Pod termination still proceeds.
                pass

    def _ingest_capture_items(self, *, deadline: float, limit: int = 1):
        if self._capture_session is None:
            return False
        if time.monotonic() >= deadline:
            return False
        page = self.capture_client.items(
            after=self._capture_cursor,
            limit=limit,
            timeout_seconds=deadline - time.monotonic(),
        )
        items = page.get("items")
        if not isinstance(items, list):
            raise DomainError("capture_index_invalid", 503)
        for item in items:
            if time.monotonic() >= deadline:
                return False
            if item.get("item_seq") != self._capture_cursor + 1:
                raise DomainError("capture_index_gap", 503)
            parts = {}
            for descriptor in item["parts"]:
                if descriptor["length"] == 0:
                    parts[descriptor["part"]] = b""
                    continue
                body = bytearray()
                while len(body) < descriptor["length"]:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return False
                    body.extend(self.capture_client.read_part(
                        item["item_seq"], descriptor, offset=len(body),
                        timeout_seconds=remaining,
                    ))
                if (
                    len(body) != descriptor["length"]
                    or sha256(body).hexdigest() != descriptor["sha256"]
                ):
                    raise DomainError("capture_part_mismatch", 503)
                parts[descriptor["part"]] = bytes(body)
            envelope = {
                "schema_version": "wuji.runtime-capture-envelope.v1",
                "capture_session_id": self._capture_session.capture_session_id,
                "binding": self._capture_binding(self._observed_uid),
                "collector_ref": self.capture_registration.collector_ref,
                "item_seq": item["item_seq"],
                "kind": item["kind"],
                "completeness": item["completeness"],
                "observed_at": item["observed_at"],
                "parts": item["parts"],
                "metadata": item["metadata"],
                "conditions": item["conditions"],
            }
            envelope["item_digest"] = "0" * 64
            candidate = wire.RuntimeCaptureEnvelopeV1.model_validate(envelope)
            normalized = candidate.model_dump(mode="json", exclude={"item_digest"})
            envelope["item_digest"] = sha256(
                canonical_json_bytes(normalized)
            ).hexdigest()
            parsed = wire.RuntimeCaptureEnvelopeV1.model_validate(envelope)
            self.capture_ingest_service.ingest_item(
                self.capture_collector_access, parsed, parts
            )
            self._capture_cursor = item["item_seq"]
        return bool(items)

    def _revoke_runtime_failure(self, pod_uid, code):
        task = self.control.read_task(self.access, str(self.config.task_id))
        if task["desired_state"] != "run" or not task["execution_allowed"]:
            return
        command = TaskCommand.model_validate({
            "schema_version": "wuji.api.v2",
            "command": "cancel",
            "expected_version": str(task["control_version"]),
            "reason": "Task runtime failure: " + code,
        })
        try:
            self.control.apply(ControlCommandContext(
                access=self.access,
                task_id=str(self.config.task_id),
                operation_id=(
                    f"runtime-failure-a{self.config.runtime_attempt}-"
                    + sha256((pod_uid + code).encode()).hexdigest()[:24]
                ),
                command=command,
                cancel_source="system_failure",
            ))
        except DomainError as error:
            current = self.control.read_task(self.access, str(self.config.task_id))
            if error.code != "STALE_VERSION" or (
                current["desired_state"] == "run" and current["execution_allowed"]
            ):
                raise

    @staticmethod
    def _container_terminated(pod, name):
        return any(
            item.get("name") == name
            and item.get("state", {}).get("terminated") is not None
            for item in (pod.get("status") or {}).get("containerStatuses", [])
        )

    def _cleanup_deadline(self, tx):
        """Map the persisted Task revocation time to this process's monotonic clock."""

        value = tx.connection.execute(
            """WITH activation AS (
              SELECT event_seq FROM vnext.outbox
              WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                AND kind='task.started'
                AND payload_json::jsonb->>'execution_epoch'=%s
              ORDER BY event_seq DESC LIMIT 1
            ), task_commands AS (
              SELECT o.created_at,row_number() OVER (ORDER BY o.event_seq) AS ordinal
              FROM vnext.outbox o,activation WHERE o.tenant_id=%s AND o.project_id=%s
                AND o.task_id=%s AND o.event_seq>activation.event_seq
                AND o.kind='control.applied'
                AND o.payload_json::jsonb->'resource_ref'->>'entity_type'='task'
                AND o.payload_json::jsonb->'resource_ref'->>'id'=%s
            ), revocations AS (
              SELECT created_at FROM task_commands WHERE ordinal=2
              UNION ALL
              SELECT o.created_at FROM vnext.outbox o,activation
              WHERE o.tenant_id=%s AND o.project_id=%s AND o.task_id=%s
                AND o.event_seq>activation.event_seq
                AND o.kind='completion.control_applied'
                AND o.payload_json::jsonb->>'action'='quiesce'
            ) SELECT min(created_at) FROM revocations""",
            (
                *tx.owner, str(self.config.execution_epoch),
                *tx.owner, tx.owner[2], *tx.owner,
            ),
        ).fetchone()
        anchor = value[0] if value is not None and value[0] is not None else tx.task["activated_at"]
        if not isinstance(anchor, datetime) or anchor.utcoffset() is None:
            raise DomainError("task_cleanup_anchor_unavailable", 503)
        window = (
            self.config.capture_policy.drain_timeout_seconds
            + self.config.capture_policy.seal_timeout_seconds
        )
        remaining = (
            anchor + timedelta(seconds=window) - datetime.now(timezone.utc)
        ).total_seconds()
        return time.monotonic() + max(0.0, remaining)

    def _drain_processes_and_capture(self, pod_uid, *, deadline):
        self.capture_client.bind_pod_uid(pod_uid)
        self._restore_capture_session(pod_uid)
        if time.monotonic() >= deadline:
            if not self._process_shutdown_confirmed:
                self._process_shutdown_unknown = True
            self._mark_capture_incomplete()
            return True
        if not self._capture_drained:
            try:
                local = self.capture_client.drain(
                    timeout_seconds=deadline - time.monotonic()
                )
                self._capture_last_status = local
                self._capture_drained = True
                session_state = getattr(
                    getattr(self._capture_session, "state", None), "value",
                    getattr(self._capture_session, "state", None),
                )
                if self._capture_session is not None and session_state != "sealed":
                    self._remember_capture_status(local, state="draining")
            except (RuntimeStateUnknown, RuntimeTransportError):
                # Capture failure must not prevent the external Task stop.
                self._capture_drained = False
        if time.monotonic() >= deadline:
            if not self._process_shutdown_confirmed:
                self._process_shutdown_unknown = True
            self._mark_capture_incomplete()
            return True
        if not self._process_shutdown_confirmed and not self._process_shutdown_unknown:
            try:
                reply = self.process_shutdown(
                    task_id=str(self.config.task_id),
                    execution_epoch=self.config.execution_epoch,
                    runtime_attempt=self.config.runtime_attempt,
                    reason="task runtime cleanup",
                    timeout_seconds=deadline - time.monotonic(),
                )
                if (
                    reply.get("status") != "accepted"
                    or reply.get("task_id") != str(self.config.task_id)
                    or str(reply.get("execution_epoch"))
                    != str(self.config.execution_epoch)
                    or str(reply.get("runtime_attempt")) != str(self.config.runtime_attempt)
                ):
                    raise RuntimeStateUnknown("process-shutdown-ack")
                if reply.get("archive_status") == "complete":
                    self._process_shutdown_confirmed = True
                else:
                    self._process_shutdown_unknown = True
            except (DomainError, RuntimeStateUnknown, RuntimeTransportError):
                self._process_shutdown_unknown = True
        pod = self.pods.read_pod(self.config.namespace, self.config.pod_name)
        if (
            self._process_shutdown_confirmed
            and pod is not None
            and not self._container_terminated(pod, "kali")
            and time.monotonic() < deadline
        ):
            return False
        if (
            self._process_shutdown_confirmed
            and pod is not None
            and not self._container_terminated(pod, "kali")
        ):
            self._mark_capture_incomplete()
        if not self._capture_sealed:
            try:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._mark_capture_incomplete()
                    return True
                local = self.capture_client.seal(timeout_seconds=remaining)
                self._capture_sealed = local.get("state") in {
                    "sealed-complete", "sealed-incomplete"
                }
                final = local.get("latest_item_seq")
                if (
                    not self._capture_sealed
                    or type(final) is not int
                    or final < self._capture_cursor
                ):
                    raise RuntimeStateUnknown("capture-seal-watermark")
                self._capture_final_seq = final
                self._capture_seal_status = local
                self._capture_last_status = local
                if self._capture_session is None:
                    self._remember_capture_status(local, state="draining")
            except (DomainError, RuntimeStateUnknown, RuntimeTransportError):
                self._capture_sealed = False
                self._mark_capture_incomplete()
                return True
        try:
            while self._capture_cursor < self._capture_final_seq:
                previous = self._capture_cursor
                if not self._ingest_capture_items(deadline=deadline, limit=1):
                    self._mark_capture_incomplete()
                    return True
                if self._capture_cursor <= previous:
                    self._mark_capture_incomplete()
                    return True
            if self._capture_session is not None:
                self._remember_capture_status(self._capture_seal_status)
        except (DomainError, RuntimeStateUnknown, RuntimeTransportError):
            self._mark_capture_incomplete()
        return True

    def _record_terminal_observations(self, pod, pod_uid):
        states = TaskRuntimeController.core_terminal_states(pod)
        if states is None:
            raise RuntimeStateUnknown("container-terminal-unconfirmed")
        statuses = {
            item["name"]: item
            for item in [
                *((pod.get("status") or {}).get("initContainerStatuses", [])),
                *((pod.get("status") or {}).get("containerStatuses", [])),
            ]
        }
        states = {"task-network-init": "terminated", **states}
        observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        for name, state in states.items():
            status = statuses[name]
            terminated = status.get("state", {}).get("terminated") or {}
            waiting = status.get("state", {}).get("waiting") or {}
            value = {
                "schema_version": "wuji.runtime-terminal-observation.v1",
                "capture_session_id": (
                    None if self._capture_session is None
                    else self._capture_session.capture_session_id
                ),
                "binding": self._capture_binding(pod_uid),
                "controller_ref": self.access.principal.subject,
                "container_name": name,
                "state": state,
                "container_id": (
                    status.get("containerID") if state == "terminated" else None
                ),
                "exit_code": (
                    terminated.get("exitCode") if state == "terminated" else None
                ),
                "signal": (
                    terminated.get("signal")
                    if state == "terminated" and terminated.get("signal", 0) > 0
                    else None
                ),
                "reason": (terminated.get("reason") or waiting.get("reason") or None),
                "started_at": (
                    terminated.get("startedAt") if state == "terminated" else None
                ),
                "finished_at": (
                    terminated.get("finishedAt") if state == "terminated" else None
                ),
                "observed_at": observed_at,
            }
            value["source_digest"] = "0" * 64
            candidate = wire.RuntimeTerminalObservationV1.model_validate(value)
            source = candidate.model_dump(
                mode="json",
                exclude={
                    "capture_session_id", "controller_ref", "observed_at", "source_digest"
                },
            )
            value["source_digest"] = sha256(canonical_json_bytes(source)).hexdigest()
            observation = wire.RuntimeTerminalObservationV1.model_validate(value)
            self.capture_service.record_terminal_observation(self.access, observation)

    def _terminal_observations_complete(self, pod_uid):
        states = self.capture_service.terminal_container_states(
            self.access,
            str(self.config.task_id),
            runtime_attempt=self.config.runtime_attempt,
            execution_epoch=self.config.execution_epoch,
            pod_uid=pod_uid,
        )
        return (
            isinstance(states, dict)
            and states.get("task-network-init") == "terminated"
            and set(states) == {"task-network-init", "agent", "kali", "capture"}
            and all(
                states[name] in {"terminated", "not_started"}
                for name in ("agent", "kali", "capture")
            )
        )

    def ensure(self) -> RuntimeObservation:
        with self._mutex:
            self._require_open()
            try:
                revoked_uid = None
                revoked_code = None
                revoked_without_receiver = False
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
                    except PermitDenied as denied:
                        if existing is None or not existing["pod_uid"]:
                            if self.config.template_version != "core-ctf-v1":
                                raise
                            revoked_without_receiver = True
                        else:
                            revoked_uid = existing["pod_uid"]
                        # Only the bounded predicate code travels with the
                        # observation; the message stays internal.
                        revoked_code = denied.code
                if revoked_without_receiver:
                    pod = self.pods.read_pod(
                        self.config.namespace, self.config.pod_name
                    )
                    if pod is None:
                        with self.permits.transaction() as tx:
                            bindings = tx.connection.execute(
                                """SELECT DISTINCT pod_uid FROM vnext.runtime_terminal_observation
                                WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                                  AND runtime_attempt=%s AND execution_epoch=%s""",
                                (*tx.owner, self.config.runtime_attempt, self.config.execution_epoch),
                            ).fetchall()
                        if len(bindings) == 1 and self._terminal_observations_complete(
                            bindings[0][0]
                        ):
                            return RuntimeObservation(
                                "stopped", self.config.pod_name, bindings[0][0],
                                "terminal_observation_persisted",
                            )
                        return RuntimeObservation(
                            "stopping", self.config.pod_name, None,
                            "permit_revoked_before_Pod_identity_was_observed",
                            "pod_terminal_unconfirmed",
                        )
                    verify_pod_ownership(
                        pod, self.config, allow_shortened_deadline=True
                    )
                    revoked_uid = pod["metadata"]["uid"]
                if revoked_uid is not None:
                    stopped = self.stop(pod_uid=revoked_uid)
                    self._registered_uid = None
                    self._observed_uid = None
                    return RuntimeObservation(
                        stopped.state, stopped.pod_name, stopped.pod_uid,
                        "permit_revoked", revoked_code,
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
                local_capture_ready = (
                    self.config.template_version == "core-ctf-v1"
                    and observation.reason == "capture_registration_pending"
                )
                if observation.state == "stopping" and self.config.template_version == "core-ctf-v1":
                    self._revoke_runtime_failure(
                        observation.pod_uid, observation.code or "runtime_failure"
                    )
                    return self.stop(pod_uid=observation.pod_uid)
                if observation.state != "ready" and not local_capture_ready:
                    if self._registered_uid is not None:
                        self._disable(self._registered_uid)
                    return observation
                # Do not trust a create response, Downward API report, or a
                # supplied UID. Re-read through the trusted Kubernetes client.
                pod = self.pods.read_pod(self.config.namespace, self.config.pod_name)
                if pod is None:
                    raise RuntimeConflict("Pod disappeared before receiver registration")
                verify_pod_ownership(pod, self.config, expected_uid=observation.pod_uid)
                if not _ready(pod, self.config):
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
                if self.config.template_version == "core-ctf-v1":
                    try:
                        self._register_capture(uid)
                    except DomainError as error:
                        if error.code == "capture_registration_pending":
                            return RuntimeObservation(
                                "provisioning", self.config.pod_name, uid,
                                "capture_registration_pending", error.code,
                            )
                        if error.code != "capture_failed":
                            raise
                        self._revoke_runtime_failure(uid, error.code)
                        return self.stop(pod_uid=uid)
                    except (OwnershipError, RuntimeStateUnknown, RuntimeTransportError) as error:
                        detail = {
                            "event": "capture_enforcement_unavailable",
                            "task_id": str(self.config.task_id),
                            "error": type(error).__name__,
                        }
                        if isinstance(error, RuntimeTransportError):
                            detail["operation"] = error.operation
                            if error.status is not None:
                                detail["status"] = error.status
                        print(json.dumps(detail, sort_keys=True), flush=True)
                        self._revoke_runtime_failure(uid, "capture_enforcement_unavailable")
                        return self.stop(pod_uid=uid)
                    self._ingest_capture_items(
                        deadline=time.monotonic() + min(
                            10.0, self.config.capture_policy.seal_timeout_seconds
                        )
                    )
                    return RuntimeObservation("ready", self.config.pod_name, uid)
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
                deadline = (
                    self._cleanup_deadline(tx)
                    if self.config.template_version == "core-ctf-v1"
                    else None
                )
            # Ownership and UID are rechecked by TaskRuntimeController; stop is
            # valid after epoch revocation and does not claim Run process exit.
            self._disable(pod_uid)
            if self.config.template_version != "core-ctf-v1":
                return self.controller.stop(self.config, pod_uid)
            if deadline is None:
                raise DomainError("task_cleanup_anchor_unavailable", 503)
            if not self._drain_processes_and_capture(pod_uid, deadline=deadline):
                return RuntimeObservation(
                    "stopping", self.config.pod_name, pod_uid,
                    "process_shutdown_pending",
                    "process_shutdown_pending",
                )
            result = self.controller.stop(self.config, pod_uid)
            if result.state != "stopped":
                if (
                    result.code == "pod_terminal_unconfirmed"
                    and self._terminal_observations_complete(pod_uid)
                ):
                    return RuntimeObservation(
                        "stopped", self.config.pod_name, pod_uid,
                        "terminal_observation_persisted",
                    )
                return result
            pod = self.pods.read_pod(self.config.namespace, self.config.pod_name)
            if pod is None:
                return RuntimeObservation(
                    "stopping", self.config.pod_name, pod_uid,
                    "terminal_observation_pending", "pod_terminal_unconfirmed",
                )
            verify_pod_ownership(
                pod, self.config, require_template=False, expected_uid=pod_uid
            )
            self._record_terminal_observations(pod, pod_uid)
            deleted = self.controller.delete_terminal(self.config, pod_uid)
            if self._capture_window_incomplete:
                return RuntimeObservation(
                    deleted.state, deleted.pod_name, deleted.pod_uid,
                    "capture_window_incomplete", "capture_window_incomplete",
                )
            if self._process_shutdown_unknown:
                return RuntimeObservation(
                    deleted.state, deleted.pod_name, deleted.pod_uid,
                    "process_archive_incomplete", "process_archive_incomplete",
                )
            return deleted

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


def _ready(pod, config):
    if pod.get("metadata", {}).get("deletionTimestamp"):
        return False
    status = pod.get("status") or {}
    running = {
        item.get("name") for item in status.get("containerStatuses", [])
        if item.get("ready") is True and item.get("state", {}).get("running") is not None
    }
    expected = {"agent", "kali"}
    init_ready = True
    if config.template_version == "core-ctf-v1":
        expected.add("capture")
        init_values = status.get("initContainerStatuses", [])
        init_ready = (
            {item.get("name") for item in init_values} == {"task-network-init"}
            and all(
                item.get("state", {}).get("terminated", {}).get("exitCode") == 0
                for item in init_values
            )
        )
    return (
        status.get("phase") == "Running"
        and {item.get("name") for item in status.get("containerStatuses", [])} == expected
        and running == expected
        and init_ready
        and any(item.get("type") == "Ready" and item.get("status") == "True"
                for item in status.get("conditions", []))
    )
