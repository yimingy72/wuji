"""Durable Task launch admission and its recoverable phase worker.

The public ``start`` command is admitted here, but it never runs an owner
script in the HTTP request.  ``LaunchWorker`` only calls a narrow deployment
adapter for prepare/wire/capability; activation is the existing Control
domain transition.  PostgreSQL rows and CAS functions in
``launch_schema_draft.sql`` are the source of truth for idempotency, leases,
and step recovery.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from threading import Event, Thread
from typing import Any, Mapping, Protocol

import psycopg

from wuji_core.contracts.execution import (
    CommandReceipt,
    TaskCommand,
    TaskCommandName,
)
from wuji_core.contracts.generated import LaunchView
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import AccessContext, DomainError


PHASES = ("prepare", "activate", "wire", "capability")
_ADAPTER_PHASES = ("prepare", "wire", "observe", "capability")
_PHASE_AFTER = {
    "prepare": "activate",
    "activate": "wire",
    "wire": "capability",
    "capability": "ready",
}
_TERMINAL_STATUSES = frozenset({"succeeded", "cancelled", "failed"})


class LaunchAdapter(Protocol):
    """The only deployment surface used by the launch worker."""

    def prepare(self, input: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def wire(self, input: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def observe(self, input: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def capability(self, input: Mapping[str, Any]) -> Mapping[str, Any]: ...


class LaunchUnknown(Exception):
    """The adapter cannot prove whether an external step happened."""

    def __init__(self, reason_code: str = "operation_unknown") -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


class LaunchLeaseLost(Exception):
    """A lease/CAS was lost; the external step must be reconciled."""

    reason_code = "launch_lease_lost"


@dataclass(frozen=True)
class LaunchAdmission:
    receipt: CommandReceipt
    operation_id: str
    definition_digest: str
    profile_digest: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(value: Any) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def _json_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    return dict(value)


def _runtime_uid(value: Mapping[str, Any]) -> str | None:
    direct = value.get("runtime_uid") or value.get("pod_uid")
    if isinstance(direct, str) and direct:
        return direct
    summary = value.get("summary")
    if isinstance(summary, Mapping):
        candidate = summary.get("runtime_uid") or summary.get("pod_uid")
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def _reason_code(value: Any) -> str:
    """Map domain/adapter errors to the generated lower-case wire pattern."""

    if not isinstance(value, str) or not value:
        return "launch_failed"
    normalized = "".join(
        char.lower() if char.isalnum() else "_" for char in value
    ).strip("_")
    return normalized[:128] or "launch_failed"


class _LeaseHeartbeat:
    def __init__(self, store, access, operation_id, lease_token, lease_seconds):
        self.store = store
        self.access = access
        self.operation_id = operation_id
        self.lease_token = lease_token
        self.lease_seconds = lease_seconds
        self.stop = Event()
        self.lost = Event()
        self.thread = Thread(target=self._run, name="wuji-launch-lease", daemon=True)

    def _run(self):
        interval = max(1.0, self.lease_seconds / 3)
        while not self.stop.wait(interval):
            try:
                if not self.store.renew(
                    self.access,
                    operation_id=self.operation_id,
                    lease_token=self.lease_token,
                    lease_seconds=self.lease_seconds,
                ):
                    self.lost.set()
                    return
            except Exception:
                self.lost.set()
                return

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop.set()
        self.thread.join(timeout=max(1.0, self.lease_seconds / 3))
        if self.lost.is_set():
            raise LaunchLeaseLost from exc_value
        return False


class LaunchStore:
    """Small adapter over migration-owned SECURITY DEFINER functions."""

    def __init__(self, uow) -> None:
        self.uow = uow

    @staticmethod
    def _settings(access: AccessContext) -> dict[str, str]:
        return {
            "tenant": access.principal.tenant_id,
            "subject": access.principal.subject,
            "token_id": access.principal.token_id,
            "project": "",
            "task": "",
            "clearance": "-1",
        }

    def _call(self, access: AccessContext, statement: str, args: tuple[Any, ...]):
        with self.uow.connection_factory() as connection:
            with connection.transaction():
                for name, value in self._settings(access).items():
                    connection.execute(
                        "SELECT set_config(%s,%s,true)", ("wuji." + name, value)
                    ).fetchone()
                try:
                    result = connection.execute(statement, args).fetchone()
                except psycopg.errors.UniqueViolation as error:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409) from error
                except psycopg.errors.CheckViolation as error:
                    raise DomainError("INVALID_SCHEMA", 422) from error
                except psycopg.errors.InvalidParameterValue as error:
                    raise DomainError("INVALID_SCHEMA", 422) from error
                except psycopg.errors.InsufficientPrivilege as error:
                    raise DomainError("NOT_FOUND_OR_FORBIDDEN") from error
                except psycopg.errors.ObjectNotInPrerequisiteState as error:
                    raise DomainError("STALE_EXECUTION", 409) from error
                except psycopg.errors.UndefinedFunction as error:
                    raise DomainError("CAPABILITY_UNAVAILABLE", 503) from error
        if not result or result[0] is None:
            return None
        if isinstance(result[0], Mapping):
            return dict(result[0])
        if isinstance(result[0], (bool, int, float)):
            return result[0]
        try:
            return strict_json_loads(result[0])
        except (TypeError, ValueError) as error:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503) from error

    def accept(
        self,
        access: AccessContext,
        *,
        project_id: str,
        task_id: str,
        operation_id: str,
        expected_version: str,
        input_digest: str,
        definition_digest: str,
        profile_digest: str,
        request: Mapping[str, Any],
        receipt: Mapping[str, Any],
    ):
        return self._call(
            access,
            """SELECT vnext.accept_task_launch(
                %s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)""",
            (
                project_id,
                task_id,
                operation_id,
                expected_version,
                input_digest,
                definition_digest,
                profile_digest,
                canonical_json_bytes(request).decode("utf-8"),
                canonical_json_bytes(receipt).decode("utf-8"),
            ),
        )

    def read(self, access: AccessContext, task_id: str):
        return self._call(
            access,
            "SELECT vnext.read_task_launch(%s)",
            (task_id,),
        )

    def claim(self, access: AccessContext, *, worker_id: str, lease_seconds: int):
        return self._call(
            access,
            "SELECT vnext.claim_task_launch(%s,%s,%s)",
            (worker_id, lease_seconds, access.principal.subject),
        )

    def record(
        self,
        access: AccessContext,
        *,
        operation_id: str,
        lease_token: str,
        phase: str,
        phase_status: str,
        patch: Mapping[str, Any],
    ):
        try:
            result = self._call(
                access,
                """SELECT vnext.record_task_launch_step(
                    %s,%s,%s,%s,%s::jsonb)""",
                (
                    operation_id,
                    lease_token,
                    phase,
                    phase_status,
                    canonical_json_bytes(patch).decode("utf-8"),
                ),
            )
        except (
            psycopg.errors.SerializationFailure,
            psycopg.errors.DeadlockDetected,
            psycopg.errors.OperationalError,
        ) as error:
            raise LaunchLeaseLost from error
        if result is None:
            raise LaunchLeaseLost
        return result

    def renew(
        self,
        access: AccessContext,
        *,
        operation_id: str,
        lease_token: str,
        lease_seconds: int,
    ) -> bool:
        result = self._call(
            access,
            "SELECT vnext.renew_task_launch_lease(%s,%s,%s)",
            (operation_id, lease_token, lease_seconds),
        )
        return result is True or result == {"renewed": True}


class LaunchService:
    """Accept and read durable Task starts; no external call is made here."""

    def __init__(self, uow, *, control) -> None:
        self.uow = uow
        self.control = control
        self.store = LaunchStore(uow)

    def accept_start(
        self,
        access: AccessContext,
        task_id: str,
        command: TaskCommand,
        *,
        idempotency_key: str,
    ) -> CommandReceipt:
        command = TaskCommand.model_validate(command)
        if command.command != TaskCommandName.start:
            raise DomainError("INVALID_SCHEMA", 422)
        if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        task = self.control.read_task(access, task_id)
        expected = command.expected_version.root
        raw_definition = task.get("definition_json")
        definition = strict_json_loads(raw_definition)
        definition_digest = task.get("definition_digest")
        if (
            not isinstance(raw_definition, str)
            or not isinstance(definition_digest, str)
            or sha256(raw_definition.encode("utf-8")).hexdigest() != definition_digest
        ):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        profile_digest = _digest(
            {
                "model_profile": definition.get("model_profile"),
                "runtime_profile": definition.get("runtime_profile"),
                "lock_digest": definition.get("lock_digest"),
            }
        )
        request = {
            "task_id": task_id,
            "command": command.model_dump(mode="json"),
            "definition_digest": definition_digest,
            "profile_digest": profile_digest,
        }
        # Derived configuration can be finalized after admission. Replay is
        # keyed to the original public command, not to the later live digest.
        input_digest = _digest({"task_id": task_id, "command": command.model_dump(mode="json")})
        receipt = CommandReceipt.model_validate(
            {
                "command_id": idempotency_key,
                "disposition": "accepted",
                "resource_ref": {
                    "entity_type": "task",
                    "id": task_id,
                    "revision": expected,
                },
                "resource_version": expected,
                "request_id": access.request_id,
            }
        )
        saved = self.store.accept(
            access,
            project_id=task["project_id"],
            task_id=task_id,
            operation_id=idempotency_key,
            expected_version=expected,
            input_digest=input_digest,
            definition_digest=definition_digest,
            profile_digest=profile_digest,
            request=request,
            receipt=receipt.model_dump(mode="json"),
        )
        if saved is not None:
            receipt = CommandReceipt.model_validate(saved)
        return receipt

    def read_launch(self, access: AccessContext, task_id: str) -> LaunchView:
        result = self.store.read(access, task_id)
        if result is None:
            # The SQL read function normally returns this object itself.  This
            # fallback keeps the HTTP contract stable if a compatible older
            # migration returns no row.
            task = self.control.read_task(access, task_id)
            return LaunchView.model_validate({
                "operation_id": None,
                "command_id": None,
                "task_id": task_id,
                "definition_digest": task["definition_digest"],
                "profile_digest": None,
                "runtime_attempt": None,
                "execution_epoch": None,
                "phase": "not_requested",
                "phase_status": "not_requested",
                "reason_code": None,
                "allowed_actions": [],
                "observed_at": _now(),
            })
        return LaunchView.model_validate(result)


class LaunchWorker:
    """Recoverable bounded worker; A0 attaches it to the host lifecycle."""

    def __init__(
        self,
        uow,
        *,
        access: AccessContext,
        control,
        adapter: LaunchAdapter,
        worker_id: str,
        lease_seconds: int = 30,
    ) -> None:
        if not isinstance(access, AccessContext):
            raise TypeError("authenticated worker access is required")
        if not isinstance(worker_id, str) or not 1 <= len(worker_id) <= 256:
            raise ValueError("bounded worker id is required")
        if type(lease_seconds) is not int or not 1 <= lease_seconds <= 300:
            raise ValueError("bounded launch lease is required")
        for name in _ADAPTER_PHASES:
            if not callable(getattr(adapter, name, None)):
                raise ValueError("launch adapter is missing " + name)
        self.store = LaunchStore(uow)
        self.control = control
        self.access = access
        self.adapter = adapter
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds

    def run_once(self, limit: int = 4) -> list[dict[str, Any]]:
        """Advance at most ``limit`` jobs and return bounded progress facts."""

        if type(limit) is not int or not 1 <= limit <= 32:
            raise ValueError("bounded launch tick limit is required")
        progress: list[dict[str, Any]] = []
        for _ in range(limit):
            job = self.store.claim(
                self.access,
                worker_id=self.worker_id,
                lease_seconds=self.lease_seconds,
            )
            if not job:
                break
            try:
                result = self._run(job)
                progress.append(self._progress(result))
            except LaunchLeaseLost:
                progress.append(
                    self._progress(
                        {
                            "task_id": job.get("task_id"),
                            "operation_id": job.get("operation_id"),
                            "phase": job.get("phase"),
                            "phase_status": "reconciling",
                            "reason_code": LaunchLeaseLost.reason_code,
                        }
                    )
                )
            except Exception:
                progress.append(
                    self._progress(
                        {
                            "task_id": job.get("task_id"),
                            "operation_id": job.get("operation_id"),
                            "phase": job.get("phase"),
                            "phase_status": "failed",
                            "reason_code": "launch_worker_failed",
                        }
                    )
                )
        return progress

    @staticmethod
    def _progress(job) -> dict[str, Any]:
        return {
            key: job.get(key)
            for key in (
                "task_id",
                "operation_id",
                "phase",
                "phase_status",
                "reason_code",
            )
        }

    def _guard(self, job):
        task = self.control.read_task(self.access, job["task_id"])
        phase = job.get("phase")
        if task["observed_state"] == "closed" or task["desired_state"] in {
            "cancel",
            "finish",
        }:
            return "cancelled", "task_cancelled"
        if phase == "prepare" and str(task["control_version"]) != str(
            job["expected_control_version"]
        ):
            return "blocked", "start_version_changed"
        if phase not in {"prepare", "activate"} and task["desired_state"] != "run":
            return "blocked", "task_paused"
        return None

    @staticmethod
    def _step(job, phase):
        steps = job.get("steps") or {}
        value = steps.get(phase)
        return value if isinstance(value, Mapping) else {}

    @staticmethod
    def _runtime_uid(job):
        value = LaunchWorker._step(job, "wire")
        return value.get("runtime_uid") or _runtime_uid(value)

    def _record(self, job, phase, status, **patch):
        return self.store.record(
            self.access,
            operation_id=job["operation_id"],
            lease_token=job["lease_token"],
            phase=phase,
            phase_status=status,
            patch={"observed_at": _now(), "lease_seconds": self.lease_seconds, **patch},
        )

    def _adapter_call(self, job, method, payload):
        """Run one bounded adapter call while retaining the durable lease."""

        with _LeaseHeartbeat(
            self.store,
            self.access,
            job["operation_id"],
            job["lease_token"],
            self.lease_seconds,
        ):
            return method(payload)

    def _run(self, job):
        for _ in range(len(PHASES) + 1):
            phase = job.get("phase")
            if phase == "ready" or job.get("phase_status") in _TERMINAL_STATUSES:
                return job
            if phase not in PHASES:
                return self._record(
                    job,
                    phase or "prepare",
                    "failed",
                    reason_code="invalid_launch_phase",
                )
            guard = self._guard(job)
            if guard:
                status, reason = guard
                step = self._step(job, phase)
                if (
                    phase in {"prepare", "wire", "capability"}
                    and step.get("phase_status") in {"pending", "running", "reconciling"}
                ):
                    try:
                        observed = _json_result(
                            self._adapter_call(
                                job,
                                self.adapter.observe,
                                {
                                    "task_id": job["task_id"],
                                    "operation_id": job["operation_id"],
                                    "attempt": job.get("runtime_attempt"),
                                    "epoch": job.get("execution_epoch"),
                                    "phase": phase,
                                    "definition_digest": job.get("definition_digest"),
                                    "profile_digest": job.get("profile_digest"),
                                    "external_ref": step.get("external_ref")
                                    or job["operation_id"],
                                },
                            )
                        )
                        observed_status = observed.get("status")
                        if observed_status == "unknown":
                            raise LaunchUnknown("operation_unknown")
                        if observed_status == "ready":
                            return self._record(
                                job,
                                phase,
                                "cancelled" if status == "cancelled" else "blocked",
                                external_ref=step.get("external_ref")
                                or job["operation_id"],
                                reason_code=(
                                    "task_cancelled_after_external"
                                    if status == "cancelled"
                                    else "task_paused_after_external"
                                ),
                            )
                        return self._record(
                            job,
                            phase,
                            "reconciling",
                            external_ref=step.get("external_ref")
                            or job["operation_id"],
                            reason_code="operation_pending_after_stop",
                        )
                    except LaunchLeaseLost:
                        raise
                    except LaunchUnknown as error:
                        return self._record(
                            job,
                            phase,
                            "reconciling",
                            external_ref=step.get("external_ref")
                            or job["operation_id"],
                            reason_code=_reason_code(error.reason_code),
                        )
                    except Exception:
                        return self._record(
                            job,
                            phase,
                            "reconciling",
                            external_ref=step.get("external_ref")
                            or job["operation_id"],
                            reason_code="operation_unknown",
                        )
                return self._record(
                    job,
                    phase,
                    status,
                    reason_code=reason,
                    allowed_actions=(
                        ["resume", "cancel"] if status == "blocked" else []
                    ),
                )
            step = self._step(job, phase)
            started_now = False
            if step.get("phase_status") not in {
                "succeeded",
                "pending",
                "running",
                "reconciling",
            }:
                # This write is deliberately before any adapter or Control
                # call.  A crash after this point resumes by observation or
                # the stable Control command key, never by blind re-submit.
                job = self._record(
                    job,
                    phase,
                    "running",
                    external_ref=job["operation_id"],
                    reason_code=None,
                )
                step = self._step(job, phase)
                started_now = True
            try:
                if step.get("phase_status") == "succeeded":
                    job = self._record(
                        job,
                        phase,
                        "succeeded",
                        next_phase=_PHASE_AFTER[phase],
                        runtime_attempt=job.get("runtime_attempt"),
                        execution_epoch=job.get("execution_epoch"),
                    )
                    continue
                if (
                    step.get("phase_status") in {"pending", "running", "reconciling"}
                    and phase != "activate"
                    and not started_now
                ):
                    response = self._adapter_call(
                        job,
                        self.adapter.observe,
                        {
                            "task_id": job["task_id"],
                            "operation_id": job["operation_id"],
                            "attempt": job.get("runtime_attempt"),
                            "epoch": job.get("execution_epoch"),
                            "phase": phase,
                            "definition_digest": job.get("definition_digest"),
                            "profile_digest": job.get("profile_digest"),
                            "external_ref": step.get("external_ref") or job["operation_id"],
                        },
                    )
                elif phase == "activate":
                    task = self.control.activate_task(
                        self.access,
                        job["task_id"],
                        operation_id=job["command_id"],
                        expected_version=str(job["expected_control_version"]),
                        reason="persistent launch activation",
                    )
                    response = {
                        "external_ref": f"control:{job['task_id']}",
                        "summary": {"activated": True},
                        "runtime_attempt": str(task["runtime_attempt"]),
                        "execution_epoch": str(task["execution_epoch"]),
                    }
                else:
                    if phase == "prepare":
                        response = self._adapter_call(
                            job,
                            self.adapter.prepare,
                            {
                                "task_id": job["task_id"],
                                "operation_id": job["operation_id"],
                                "definition_digest": job["definition_digest"],
                                "profile_digest": job["profile_digest"],
                                "attempt": job.get("runtime_attempt"),
                            },
                        )
                    elif phase == "wire":
                        response = self._adapter_call(
                            job,
                            self.adapter.wire,
                            {
                                "task_id": job["task_id"],
                                "operation_id": job["operation_id"],
                                "attempt": job["runtime_attempt"],
                                "epoch": job["execution_epoch"],
                                "definition_digest": job["definition_digest"],
                                "profile_digest": job["profile_digest"],
                            },
                        )
                    else:
                        runtime_uid = self._runtime_uid(job)
                        if not runtime_uid:
                            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                        response = self._adapter_call(
                            job,
                            self.adapter.capability,
                            {
                                "task_id": job["task_id"],
                                "operation_id": job["operation_id"],
                                "attempt": job["runtime_attempt"],
                                "epoch": job["execution_epoch"],
                                "observed_runtime_uid": runtime_uid,
                                "definition_digest": job["definition_digest"],
                                "profile_digest": job["profile_digest"],
                            },
                        )
                    response = _json_result(response)
                external_ref = response.get("external_ref") or job["operation_id"]
                if not isinstance(external_ref, str) or not external_ref:
                    raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                status = response.get("status")
                if phase == "activate":
                    status = "ready"
                if status not in {"ready", "pending", "unknown"}:
                    raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                if status == "unknown":
                    raise LaunchUnknown("operation_unknown")
                if status == "pending":
                    job = self._record(
                        job,
                        phase,
                        "pending",
                        external_ref=external_ref,
                        summary=response.get("summary") or {},
                        reason_code=(
                            "runtime_not_ready" if phase == "wire" else "step_pending"
                        ),
                    )
                    return job
                if phase == "wire" and not _runtime_uid(response):
                    raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                next_phase = _PHASE_AFTER[phase]
                job = self._record(
                    job,
                    phase,
                    "succeeded",
                    external_ref=external_ref,
                    summary=response.get("summary") or {},
                    runtime_uid=_runtime_uid(response),
                    definition_digest=response.get("definition_digest") if phase == "prepare" else job["definition_digest"],
                    runtime_attempt=response.get("runtime_attempt")
                    or job.get("runtime_attempt"),
                    execution_epoch=response.get("execution_epoch")
                    or job.get("execution_epoch"),
                    next_phase=next_phase,
                    allowed_actions=(
                        [] if next_phase != "ready" else ["pause", "cancel", "finish"]
                    ),
                )
            except LaunchUnknown as error:
                return self._record(
                    job,
                    phase,
                    "reconciling",
                    reason_code=_reason_code(error.reason_code),
                    external_ref=step.get("external_ref") or job["operation_id"],
                )
            except LaunchLeaseLost:
                raise
            except DomainError as error:
                return self._record(
                    job,
                    phase,
                    "reconciling"
                    if error.code == "OPERATION_UNKNOWN"
                    else (
                        "blocked"
                        if error.code in {"CAPABILITY_UNAVAILABLE", "STALE_EXECUTION"}
                        else "failed"
                    ),
                    reason_code=_reason_code(error.code),
                )
            except Exception:
                # Raw adapter text must not become a public launch message.
                return self._record(
                    job,
                    phase,
                    "failed",
                    reason_code="launch_adapter_failed",
                )
        return job


__all__ = [
    "LaunchAdapter",
    "LaunchAdmission",
    "LaunchService",
    "LaunchStore",
    "LaunchUnknown",
    "LaunchWorker",
    "PHASES",
]
