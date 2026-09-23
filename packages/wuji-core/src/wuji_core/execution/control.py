"""Production S05 controls over canonical rows and trusted stored observations.

No HTTP Task creation, scheduler loop, process spawn, Session publishing or Goal
assessment lives here. Missing producers leave explicit blocking conditions.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Annotated, Literal

from psycopg import sql
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    AwareDatetime,
    StrictInt,
    ValidationError,
    model_validator,
)

from wuji_core.contracts.execution import (
    TaskCommand,
    WorkCommand,
    CommandReceipt,
    TaskCreate,
    SessionManifest,
)
from wuji_core.contracts.envelopes import RunIdentity
from wuji_core.persistence.uow import AccessContext, DomainError, row, json_text
from wuji_core.http.json_boundary import strict_json_loads, canonical_json_bytes
from wuji_core.execution.states import (
    TERMINAL,
    ACTIVE,
    require_transition,
    task_can_run,
    can_settle_done,
)
from wuji_core.execution.capacity import CapacityService, operations_settled
from wuji_core.admission.tools import (
    operation_axes_closed,
    settle_operation_set,
)
from wuji_core.execution.dependencies import dependencies_satisfied, result_accepted
from wuji_core.execution.dependencies import intent_current, intent_record
from wuji_core.blackboard.result_state import mark_missing_output


def require_runtime_terminal(tx):
    """Core Tasks close only after the current environment's external exit.

    Run settlement cannot prove that a root command left no background process.
    This reads trusted persisted observations inside the caller's Task lock.
    """
    definition = strict_json_loads(tx.task["definition_json"])
    if (
        tx.task["activated_at"] is None
        or definition.get("runtime_profile", {}).get("capture_policy") is None
    ):
        return
    bindings = tx.connection.execute(
        """SELECT DISTINCT execution_epoch,pod_uid
        FROM vnext.runtime_terminal_observation WHERE tenant_id=%s
          AND project_id=%s AND task_id=%s AND runtime_attempt=%s""",
        (*tx.owner, tx.task["runtime_attempt"]),
    ).fetchall()
    if len(bindings) != 1:
        raise DomainError("OPERATION_UNKNOWN", 409)
    execution_epoch, pod_uid = bindings[0]
    receiver = tx.connection.execute(
        """SELECT pod_uid FROM vnext.scheduler_receiver WHERE tenant_id=%s
          AND project_id=%s AND task_id=%s AND runtime_attempt=%s""",
        (*tx.owner, tx.task["runtime_attempt"]),
    ).fetchone()
    if receiver is not None and receiver[0] != pod_uid:
        raise DomainError("OPERATION_UNKNOWN", 409)
    from wuji_core.evidence.runtime_capture import terminal_container_states

    if terminal_container_states(
        tx, runtime_attempt=tx.task["runtime_attempt"],
        execution_epoch=execution_epoch, pod_uid=pod_uid,
    ) is None:
        raise DomainError("OPERATION_UNKNOWN", 409)


@dataclass(frozen=True)
class ControlCommandContext:
    access: AccessContext
    task_id: str
    operation_id: str
    command: TaskCommand | WorkCommand
    work_item_id: str | None = None


class ProcessObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pid: Annotated[StrictInt, Field(gt=0)]
    birth_id: Annotated[str, Field(min_length=1)]
    started_at: AwareDatetime
    exited_at: AwareDatetime | None = None
    exit_code: StrictInt | None = None


class ExecutionObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    receipt_id: Annotated[str, Field(min_length=1, max_length=256)]
    identity: RunIdentity
    operation_id: Annotated[str, Field(min_length=1, max_length=256)]
    environment_ref: Annotated[str, Field(min_length=1, max_length=256)]
    pod_uid: Annotated[str, Field(min_length=1, max_length=256)]
    kind: Literal["not_started", "started", "exited", "environment_stopped", "unknown"]
    observed_at: AwareDatetime
    process: ProcessObservation | None = None
    reason: Annotated[str, Field(min_length=1, max_length=8192)]
    source_receipt: Annotated[str, Field(min_length=1, max_length=65536)]
    source_digest: Annotated[str, Field(pattern="^[a-f0-9]{64}$")]

    @model_validator(mode="after")
    def source_matches(self):
        if sha256(self.source_receipt.encode()).hexdigest() != self.source_digest:
            raise ValueError("source digest mismatch")
        source = strict_json_loads(self.source_receipt)
        # Parse the original source through the same typed shape to normalize timestamps only.
        own = self.model_dump(mode="json", exclude={"source_receipt", "source_digest"})
        if not isinstance(source, dict):
            raise ValueError("source receipt must be an object")
        normalized = dict(source)
        for key in ["observed_at"]:
            if key in normalized:
                normalized[key] = (
                    datetime.fromisoformat(normalized[key].replace("Z", "+00:00"))
                    .isoformat()
                    .replace("+00:00", "Z")
                )
        if isinstance(normalized.get("process"), dict):
            normalized["process"] = ProcessObservation.model_validate(
                normalized["process"]
            ).model_dump(mode="json")
        if canonical_json_bytes(normalized) != canonical_json_bytes(own):
            raise ValueError("normalized fields differ from source receipt")
        if self.kind in {"started", "exited"} and self.process is None:
            raise ValueError("process birth identity required")
        if self.kind == "exited" and (
            self.process.exited_at is None
            or self.process.exit_code is None
            or self.process.exited_at < self.process.started_at
        ):
            raise ValueError("complete exit receipt required")
        if self.kind == "started" and self.process.exited_at is not None:
            raise ValueError("started receipt cannot assert exit")
        if self.kind == "not_started" and self.process is not None:
            raise ValueError("not-started receipt cannot name a process")
        return self


def _rows(cursor):
    values = []
    while (value := row(cursor)) is not None:
        values.append(value)
    return values


def _work(tx, work_id, *, lock=True):
    work = row(
        tx.connection.execute(
            "SELECT * FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s"
            + (" FOR UPDATE" if lock else ""),
            (*tx.owner, work_id),
        )
    )
    if work is None:
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")
    return work


def _runs(tx, work_id):
    return _rows(
        tx.connection.execute(
            "SELECT * FROM vnext.agent_run WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s ORDER BY agent_run_id",
            (*tx.owner, work_id),
        )
    )


def _causes(tx, work_id):
    return _rows(
        tx.connection.execute(
            "SELECT cause_kind,cause_ref FROM vnext.work_suspension WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s ORDER BY cause_kind,cause_ref",
            (*tx.owner, work_id),
        )
    )


def _input(tx, work):
    if not work["input_request_id"]:
        return None
    value = row(
        tx.connection.execute(
            "SELECT * FROM vnext.input_request WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND input_request_id=%s AND work_item_id=%s",
            (*tx.owner, work["input_request_id"], work["work_item_id"]),
        )
    )
    if not value:
        raise DomainError("INVALID_WAIT", 409)
    return value


def _update_work(tx, work, **changes):
    allowed = {
        "state",
        "desired_state",
        "run_epoch",
        "current_run_id",
        "blocked_reason",
        "terminal_reason",
        "input_request_id",
        "session_id",
        "session_revision",
    }
    if not set(changes) <= allowed:
        raise ValueError("unsupported Work update")
    if "state" in changes:
        require_transition(work["state"], changes["state"])
    changes = {k: v for k, v in changes.items() if work.get(k) != v}
    if not changes:
        return
    assignments = sql.SQL(",").join(
        sql.SQL("{}=%s").format(sql.Identifier(k)) for k in changes
    )
    tx.connection.execute(
        sql.SQL(
            "UPDATE vnext.work_item SET {},revision=revision+1 WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s"
        ).format(assignments),
        (*changes.values(), *tx.owner, work["work_item_id"]),
    )
    work.update(changes)
    work["revision"] += 1


def _known_fresh(tx, work):
    runs = _runs(tx, work["work_item_id"])
    if not runs:
        return True
    if any(run["stop_kind"] != "not_started" for run in runs):
        return False
    return not tx.connection.execute(
        """SELECT 1 FROM vnext.tool_attempt a JOIN vnext.agent_run r USING(tenant_id,project_id,task_id,agent_run_id)
        WHERE r.tenant_id=%s AND r.project_id=%s AND r.task_id=%s AND r.work_item_id=%s AND a.started_at IS NOT NULL LIMIT 1""",
        (*tx.owner, work["work_item_id"]),
    ).fetchone()


def _environment_stopped_without_evidence(tx, run):
    """The attempt's environment ended before this Run produced any evidence.

    Only the platform's own ``environment_stopped`` observation qualifies, and
    only while the Run holds no process identity, no admitted tool attempt, no
    in-flight model request, no unreleased reservation and no result submission.
    This is not proof that no process ever ran; it is the statement that the
    platform can obtain no further evidence from that environment, so the Run
    settles instead of holding its Work item forever.
    """

    if run["stop_kind"] != "environment_stopped" or run["last_observation_id"] is None:
        return False
    observation = tx.connection.execute(
        "SELECT kind FROM vnext.execution_observation WHERE tenant_id=%s AND project_id=%s"
        " AND task_id=%s AND agent_run_id=%s AND receipt_id=%s",
        (*tx.owner, run["agent_run_id"], run["last_observation_id"]),
    ).fetchone()
    if not observation or observation[0] != "environment_stopped":
        return False
    if run["process_identity_json"]:
        return False
    if tx.connection.execute(
        "SELECT 1 FROM vnext.tool_attempt WHERE tenant_id=%s AND project_id=%s AND task_id=%s"
        " AND agent_run_id=%s AND (status IS NOT NULL OR started_at IS NOT NULL) LIMIT 1",
        (*tx.owner, run["agent_run_id"]),
    ).fetchone():
        return False
    if tx.connection.execute(
        "SELECT 1 FROM vnext.model_call WHERE tenant_id=%s AND project_id=%s AND task_id=%s"
        " AND agent_run_id=%s AND inflight LIMIT 1",
        (*tx.owner, run["agent_run_id"]),
    ).fetchone():
        return False
    if tx.connection.execute(
        "SELECT 1 FROM vnext.result_submission WHERE tenant_id=%s AND project_id=%s AND task_id=%s"
        " AND agent_run_id=%s LIMIT 1",
        (*tx.owner, run["agent_run_id"]),
    ).fetchone():
        return False
    return not tx.connection.execute(
        "SELECT 1 FROM vnext.resource_reservation WHERE tenant_id=%s AND project_id=%s AND task_id=%s"
        " AND agent_run_id=%s AND state<>'released' LIMIT 1",
        (*tx.owner, run["agent_run_id"]),
    ).fetchone()


def _possibly_running(tx, work):
    return any(run["stop_kind"] is None for run in _runs(tx, work["work_item_id"]))


class ControlService:
    def __init__(self, uow, *, artifacts=None, sessions=None):
        self.uow, self.artifacts, self.sessions = uow, artifacts, sessions

    def read_task(self, access, task_id):
        with self.uow.transaction(access, task_id) as tx:
            return tx.task

    def activate_task(
        self,
        access,
        task_id,
        *,
        operation_id,
        expected_version,
        reason,
    ):
        """Atomically perform the launcher's internal ``start`` transition.

        This is intentionally a domain method, not an HTTP re-entry.  The
        public launch command's stable operation id is written to the normal
        control receipt in the same transaction as the state transition, so a
        worker crash can replay the exact activation without creating a second
        execution epoch.
        """

        if not isinstance(operation_id, str) or not 1 <= len(operation_id) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        try:
            command = TaskCommand.model_validate(
                {
                    "schema_version": "wuji.api.v2",
                    "command": "start",
                    "expected_version": str(expected_version),
                    "reason": reason,
                }
            )
        except ValidationError as error:
            raise DomainError("INVALID_SCHEMA", 422) from error
        digest = sha256(
            canonical_json_bytes(
                {
                    "task_id": task_id,
                    "work_item_id": None,
                    "command": command.model_dump(mode="python"),
                }
            )
        ).hexdigest()
        with self.uow.transaction(access, task_id, capability="control") as tx:
            old = row(
                tx.connection.execute(
                    "SELECT * FROM vnext.control_receipt WHERE tenant_id=%s AND task_id=%s AND operation_kind='task_command' AND operation_id=%s",
                    (tx.owner[0], task_id, operation_id),
                )
            )
            if old:
                if old["input_digest"] != digest:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                return tx.task
            if str(tx.task["control_version"]) != str(expected_version):
                raise DomainError("STALE_VERSION", 409)
            if tx.task["activated_at"] is not None:
                # No receipt plus an already activated Task means the previous
                # external outcome is not attributable to this operation.
                raise DomainError("OPERATION_UNKNOWN", 409)
            self._task_command(tx, "start", reason)
            receipt = CommandReceipt.model_validate(
                {
                    "command_id": operation_id,
                    "disposition": "accepted",
                    "resource_ref": {
                        "entity_type": "task",
                        "id": task_id,
                        "revision": str(tx.task["control_version"]),
                    },
                    "resource_version": str(tx.task["control_version"]),
                    "request_id": access.request_id,
                }
            )
            tx.connection.execute(
                "INSERT INTO vnext.control_receipt(tenant_id,project_id,task_id,operation_kind,operation_id,input_digest,receipt_json) VALUES(%s,%s,%s,'task_command',%s,%s,%s)",
                (
                    *tx.owner,
                    operation_id,
                    digest,
                    json_text(receipt.model_dump(mode="python")),
                ),
            )
            # Pod permits correlate task.started with this accepted receipt
            # through the same event emitted by the public command path.
            tx.semantic_event("control.applied", receipt.model_dump(mode="python"))
            return tx.task

    def read_work(self, access, task_id, work_id):
        with self.uow.transaction(access, task_id) as tx:
            value = _work(tx, work_id, lock=False)
            value["suspension_causes"] = _causes(tx, work_id)
            value["input_request"] = _input(tx, value)
            run = next(
                (
                    r
                    for r in _runs(tx, work_id)
                    if r["agent_run_id"] == value["current_run_id"]
                ),
                None,
            )
            value["result_state"] = run["result_state"] if run else "none"
            return value

    def _definition(self, tx):
        try:
            raw = tx.task["definition_json"]
            if (
                not raw
                or sha256(raw.encode()).hexdigest() != tx.task["definition_digest"]
            ):
                raise ValueError("definition absent or changed")
            doc = strict_json_loads(raw)
            saved = TaskCreate.model_validate(doc["task"])
            if saved.project_id != tx.owner[
                1
            ] or saved.authorization_expires_at <= datetime.now(timezone.utc):
                raise ValueError("authorization expired")
            if (
                not isinstance(doc["start_points"], list)
                or not doc["start_points"]
                or any(not isinstance(v, str) or not v for v in doc["start_points"])
            ):
                raise ValueError("explicit starting inputs required")
            for name in ["model_profile", "runtime_profile"]:
                profile = doc[name]
                if (
                    profile["ref"] != getattr(saved, name + "_ref")
                    or int(profile["revision"]) < 1
                    or datetime.fromisoformat(
                        profile["published_at"].replace("Z", "+00:00")
                    )
                    > datetime.now(timezone.utc)
                ):
                    raise ValueError("published profile snapshot required")
            if not isinstance(doc["lock_digest"], str) or len(doc["lock_digest"]) != 64:
                raise ValueError("fixed lock digest required")
            return doc
        except (ValueError, KeyError, TypeError, ValidationError) as error:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503) from error

    def _recoverable(self, tx, work):
        if _known_fresh(tx, work):
            return True
        if self.sessions is None or not work["session_id"]:
            return False
        # The Session producer owns full pins/compatibility/frontier validation.
        # There is deliberately no root-only or empty-pending fallback.
        return self.sessions.validate_recovery_in_transaction(tx, work).resumable

    def dispatchable(self, access, task_id, work_id):
        # Informational only. P09 must repeat this in the locked admission transaction.
        with self.uow.transaction(access, task_id, capability="read") as tx:
            work = _work(tx, work_id, lock=False)
            return self.can_dispatch(tx, work)

    def can_dispatch(self, tx, work):
        if (
            not task_can_run(tx.task)
            or work["state"] != "ready"
            or work["desired_state"] != "run"
            or _causes(tx, work["work_item_id"])
            or _possibly_running(tx, work)
        ):
            return False
        waiting = _input(tx, work)
        if waiting and waiting["status"] != "resolved":
            return False
        try:
            self._definition(tx)
            return (
                intent_current(tx, work)
                and dependencies_satisfied(tx, work["work_item_id"])
                and self._recoverable(tx, work)
            )
        except DomainError:
            return False

    def apply(self, context: ControlCommandContext):
        if not isinstance(context, ControlCommandContext) or not context.operation_id:
            raise ValueError("trusted ControlCommandContext required")
        work_id = context.work_item_id
        dto = (WorkCommand if work_id else TaskCommand).model_validate(context.command)
        kind = "work_command" if work_id else "task_command"
        digest = sha256(
            canonical_json_bytes(
                {
                    "task_id": context.task_id,
                    "work_item_id": work_id,
                    "command": dto.model_dump(mode="python"),
                }
            )
        ).hexdigest()

        def replay(tx):
            old = row(
                tx.connection.execute(
                    "SELECT * FROM vnext.control_receipt WHERE tenant_id=%s AND task_id=%s AND operation_kind=%s AND operation_id=%s",
                    (tx.owner[0], context.task_id, kind, context.operation_id),
                )
            )
            if old:
                if old["input_digest"] != digest:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                return CommandReceipt.model_validate(
                    strict_json_loads(old["receipt_json"])
                )

        with self.uow.transaction(context.access, context.task_id) as tx:
            if (old := replay(tx)) is not None:
                return old
        with self.uow.transaction(
            context.access, context.task_id, capability="control"
        ) as tx:
            if (old := replay(tx)) is not None:
                return old
            target = _work(tx, work_id) if work_id else tx.task
            version = target["revision" if work_id else "control_version"]
            if int(dto.expected_version.root) != version:
                raise DomainError("STALE_VERSION", 409)
            if work_id:
                self._work_command(tx, target, dto.command.value, dto.reason)
            else:
                self._task_command(tx, dto.command.value, dto.reason)
            version = target["revision" if work_id else "control_version"]
            receipt = CommandReceipt.model_validate(
                dict(
                    command_id=context.operation_id,
                    disposition="accepted",
                    resource_ref={
                        "entity_type": "work_item" if work_id else "task",
                        "id": work_id or context.task_id,
                        "revision": str(version),
                    },
                    resource_version=str(version),
                    request_id=context.access.request_id,
                )
            )
            tx.connection.execute(
                "INSERT INTO vnext.control_receipt(tenant_id,project_id,task_id,operation_kind,operation_id,input_digest,receipt_json) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (
                    *tx.owner,
                    kind,
                    context.operation_id,
                    digest,
                    json_text(receipt.model_dump(mode="python")),
                ),
            )
            tx.semantic_event("control.applied", receipt.model_dump(mode="python"))
            return receipt

    def _cause(self, tx, work, kind, ref, *, remove=False):
        if remove:
            changed = tx.connection.execute(
                "DELETE FROM vnext.work_suspension WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s AND cause_kind=%s AND cause_ref=%s",
                (*tx.owner, work["work_item_id"], kind, ref),
            ).rowcount
        else:
            changed = tx.connection.execute(
                "INSERT INTO vnext.work_suspension(tenant_id,project_id,task_id,work_item_id,cause_kind,cause_ref) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (*tx.owner, work["work_item_id"], kind, ref),
            ).rowcount
        if changed:
            tx.connection.execute(
                "UPDATE vnext.work_item SET revision=revision+1 WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
                (*tx.owner, work["work_item_id"]),
            )
            work["revision"] += 1

    def _stop(self, tx, work, reason):
        tx.connection.execute(
            "UPDATE vnext.agent_run SET execution_allowed=false WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
            (*tx.owner, work["work_item_id"]),
        )
        if work["desired_state"] == "cancel":
            tx.connection.execute(
                "UPDATE vnext.input_request SET status='revoked' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s AND status<>'revoked'",
                (*tx.owner, work["work_item_id"]),
            )
        running = _possibly_running(tx, work)
        if running:
            if work["state"] in {"leased", "running"}:
                _update_work(tx, work, state="stopping")
            elif work["state"] == "ready":
                _update_work(
                    tx, work, state="blocked", blocked_reason="execution_unknown"
                )
            tx.semantic_event(
                "work.stop_requested",
                {
                    "work_item_id": work["work_item_id"],
                    "reason": reason,
                    "run_epoch": str(work["run_epoch"]),
                },
            )
            return
        if any(
            r["stop_kind"] != "not_started"
            and not operations_settled(tx, r["agent_run_id"])
            for r in _runs(tx, work["work_item_id"])
        ):
            if work["state"] in {"leased", "running", "stopping"}:
                _update_work(
                    tx, work, state="reconciling", blocked_reason="operations_unsettled"
                )
            return
        if work["desired_state"] == "cancel":
            if work["state"] in {"running", "leased"}:
                _update_work(tx, work, state="stopping")
            _update_work(
                tx, work, state="cancelled", terminal_reason=reason, blocked_reason=None
            )
            tx.connection.execute(
                "UPDATE vnext.input_request SET status='revoked' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s AND status<>'revoked'",
                (*tx.owner, work["work_item_id"]),
            )
        elif _causes(tx, work["work_item_id"]):
            if work["state"] in {"running", "leased"}:
                _update_work(tx, work, state="stopping")
            _update_work(
                tx,
                work,
                state="suspended",
                blocked_reason=(
                    None
                    if work["blocked_reason"] == "operations_unsettled"
                    else work["blocked_reason"]
                ),
            )

    def _restore(self, tx, work):
        if work["state"] in TERMINAL or _causes(tx, work["work_item_id"]):
            return
        if _possibly_running(tx, work) or work["state"] in {"stopping", "reconciling"}:
            return
        waiting = _input(tx, work)
        if waiting and waiting["status"] == "pending":
            if work["state"] == "suspended":
                _update_work(tx, work, state="waiting_input", blocked_reason=None)
            return
        if not task_can_run(tx.task) or work["desired_state"] != "run":
            return
        valid = (
            intent_current(tx, work)
            and dependencies_satisfied(tx, work["work_item_id"])
            and self._recoverable(tx, work)
        )
        if valid and (not waiting or waiting["status"] == "resolved"):
            _update_work(tx, work, state="ready", blocked_reason=None)
        elif work["state"] in {"suspended", "ready"}:
            _update_work(
                tx,
                work,
                state="blocked",
                blocked_reason="dependency_or_recovery_unavailable",
            )

    def _work_command(self, tx, work, command, reason):
        if work["state"] in TERMINAL:
            raise DomainError("STALE_EXECUTION", 409)
        if command == "resume":
            if work["desired_state"] == "cancel":
                raise DomainError("STALE_EXECUTION", 409)
            self._definition(tx)
            _update_work(tx, work, desired_state="run")
            self._cause(tx, work, "user_hold", work["work_item_id"], remove=True)
            self._restore(tx, work)
        else:
            _update_work(
                tx,
                work,
                desired_state="hold" if command == "hold" else "cancel",
                run_epoch=work["run_epoch"] + 1,
                terminal_reason=(
                    reason if command == "cancel" else work["terminal_reason"]
                ),
            )
            if command == "hold":
                self._cause(tx, work, "user_hold", work["work_item_id"])
            self._stop(tx, work, reason)

    def _task_command(self, tx, command, reason):
        task = tx.task
        if task["observed_state"] == "closed" or task["desired_state"] in {
            "cancel",
            "finish",
        }:
            raise DomainError("STALE_EXECUTION", 409)
        if command in {"start", "resume"}:
            if not {"global", "tenant"} <= {pool["tier"] for pool in tx.capacity_pools}:
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            self._definition(tx)
            if (command == "start") != (task["activated_at"] is None) or task[
                "completion_epoch_id"
            ]:
                raise DomainError("STALE_EXECUTION", 409)
            task.update(
                desired_state="run", observed_state="running", execution_allowed=True
            )
            if command == "start":
                task["activated_at"] = datetime.now(timezone.utc)
                task["execution_epoch"] += 1
                tx.semantic_event(
                    "task.started",
                    {
                        "task_id": tx.owner[2],
                        "definition_digest": task["definition_digest"],
                        "execution_epoch": str(task["execution_epoch"]),
                    },
                )
        else:
            task["execution_epoch"] += 1
            task.update(
                execution_allowed=False,
                desired_state="pause" if command == "pause" else command,
                observed_state=(
                    "quiescing" if command in {"cancel", "finish"} else "paused"
                ),
            )
            if command in {"cancel", "finish"}:
                task["close_trigger"] = (
                    "user_cancel" if command == "cancel" else "operator_finish"
                )
        task["control_version"] += 1
        tx.connection.execute(
            "UPDATE vnext.task SET desired_state=%s,observed_state=%s,execution_allowed=%s,execution_epoch=%s,activated_at=%s,close_trigger=%s,control_version=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
            (
                task["desired_state"],
                task["observed_state"],
                task["execution_allowed"],
                task["execution_epoch"],
                task["activated_at"],
                task["close_trigger"],
                task["control_version"],
                *tx.owner,
            ),
        )
        works = _rows(
            tx.connection.execute(
                "SELECT * FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s ORDER BY work_item_id FOR UPDATE",
                tx.owner,
            )
        )
        for work in works:
            if work["state"] in TERMINAL:
                continue
            if command == "pause":
                self._cause(tx, work, "task_pause", tx.owner[2])
                self._stop(tx, work, reason)
            elif command == "resume":
                self._cause(tx, work, "task_pause", tx.owner[2], remove=True)
                self._restore(tx, work)
            elif command == "cancel":
                _update_work(
                    tx,
                    work,
                    desired_state="cancel",
                    terminal_reason=task["close_trigger"],
                )
                self._stop(tx, work, task["close_trigger"])
            elif command == "finish":
                # P12 will attach a concrete CompletionEpoch; this is only ending intent.
                if work["state"] in {"leased", "running"}:
                    _update_work(tx, work, state="stopping")
                tx.connection.execute(
                    "UPDATE vnext.agent_run SET execution_allowed=false WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
                    (*tx.owner, work["work_item_id"]),
                )
                tx.semantic_event(
                    "work.stop_requested",
                    {"work_item_id": work["work_item_id"], "reason": reason},
                )
        self._observe_task(tx)

    def _observe_task(self, tx):
        if tx.task["observed_state"] == "closed" or tx.task["desired_state"] == "run":
            return
        unresolved = tx.connection.execute(
            """SELECT 1 FROM vnext.agent_run r WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND (
            stop_kind IS NULL OR (stop_kind<>'not_started' AND NOT EXISTS(
              SELECT 1 FROM vnext.run_operation_settlement s WHERE (s.tenant_id,s.project_id,s.task_id,s.agent_run_id)=(r.tenant_id,r.project_id,r.task_id,r.agent_run_id) AND s.status='settled')) OR EXISTS(
              SELECT 1 FROM vnext.resource_reservation s WHERE (s.tenant_id,s.project_id,s.task_id,s.agent_run_id)=(r.tenant_id,r.project_id,r.task_id,r.agent_run_id) AND s.state<>'released')) LIMIT 1""",
            tx.owner,
        ).fetchone()
        state = (
            "reconciling"
            if unresolved
            else ("paused" if tx.task["desired_state"] == "pause" else "quiescing")
        )
        if state != tx.task["observed_state"]:
            tx.connection.execute(
                "UPDATE vnext.task SET observed_state=%s,control_version=control_version+1 WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                (state, *tx.owner),
            )
            tx.task["observed_state"] = state
            tx.task["control_version"] += 1

    def record_observation(self, access, observation):
        observation = ExecutionObservation.model_validate(observation)
        with self.uow.transaction(
            access, observation.identity.task_id, capability="observe"
        ) as tx:
            work = _work(tx, observation.identity.work_item_id)
            run = next(
                (
                    r
                    for r in _runs(tx, work["work_item_id"])
                    if r["agent_run_id"] == observation.identity.agent_run_id
                ),
                None,
            )
            if (
                not run
                or any(
                    str(run[k]) != str(v)
                    for k, v in observation.identity.model_dump(mode="json").items()
                )
                or run["environment_ref"] != observation.environment_ref
                or run["pod_uid"] != observation.pod_uid
                or run["start_operation_id"] != observation.operation_id
            ):
                raise DomainError("STALE_EXECUTION", 409)
            old = row(
                tx.connection.execute(
                    "SELECT * FROM vnext.execution_observation WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND receipt_id=%s",
                    (*tx.owner, observation.receipt_id),
                )
            )
            if old:
                if old["source_digest"] != observation.source_digest:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                return observation.receipt_id
            if run["stop_kind"] is not None and observation.kind in {
                "started",
                "unknown",
                "not_started",
            }:
                raise DomainError("STALE_EXECUTION", 409)
            process = observation.process
            if run["process_identity_json"] and process:
                previous = strict_json_loads(run["process_identity_json"])
                if any(
                    previous[k] != process.model_dump(mode="json")[k]
                    for k in ["pid", "birth_id", "started_at"]
                ):
                    raise DomainError("STALE_EXECUTION", 409)
            if observation.kind == "not_started" and (
                run["process_identity_json"]
                or tx.connection.execute(
                    "SELECT 1 FROM vnext.tool_attempt WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND started_at IS NOT NULL LIMIT 1",
                    (*tx.owner, run["agent_run_id"]),
                ).fetchone()
            ):
                raise DomainError("STALE_EXECUTION", 409)
            tx.connection.execute(
                "INSERT INTO vnext.execution_observation(tenant_id,project_id,task_id,receipt_id,agent_run_id,kind,source_receipt,source_digest,subject,observed_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    *tx.owner,
                    observation.receipt_id,
                    run["agent_run_id"],
                    observation.kind,
                    observation.source_receipt,
                    observation.source_digest,
                    access.principal.subject,
                    observation.observed_at,
                ),
            )
            stopped = observation.kind in {
                "not_started",
                "exited",
                "environment_stopped",
            }
            state = (
                "exited"
                if stopped
                else ("unknown" if observation.kind == "unknown" else "running")
            )
            tx.connection.execute(
                "UPDATE vnext.agent_run SET process_state=%s,process_identity_json=%s,started_at=%s,exited_at=%s,stop_kind=%s,last_observation_id=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s",
                (
                    state,
                    (
                        json_text(process.model_dump(mode="json"))
                        if process
                        else run["process_identity_json"]
                    ),
                    process.started_at if process else run["started_at"],
                    observation.observed_at if stopped else None,
                    observation.kind if stopped else None,
                    observation.receipt_id,
                    *tx.owner,
                    run["agent_run_id"],
                ),
            )
            run = next(
                r
                for r in _runs(tx, work["work_item_id"])
                if r["agent_run_id"] == run["agent_run_id"]
            )
            CapacityService.observe(tx, run)
            if (
                observation.kind in {"exited", "not_started"}
                and work["current_run_id"] == run["agent_run_id"]
                and operation_axes_closed(tx, run["agent_run_id"])
            ):
                # A Run that died before publishing its own settlement (the M2
                # and E08 trials both lost one to a transport failure) would pin
                # its Work at operations_unsettled or OPERATION_UNKNOWN forever.
                # The process is observed exited and every durable axis is
                # closed, so the platform publishes the settlement the Run
                # itself could no longer write.
                settle_operation_set(
                    tx, run["agent_run_id"], basis="observed_exit_recomputed"
                )
            if work["current_run_id"] == run["agent_run_id"]:
                if state == "running" and work["state"] == "leased":
                    if (
                        task_can_run(tx.task)
                        and run["execution_allowed"]
                        and not _causes(tx, work["work_item_id"])
                    ):
                        _update_work(tx, work, state="running")
                    else:
                        _update_work(tx, work, state="stopping")
                elif state == "unknown" and work["state"] in {
                    "leased",
                    "running",
                    "stopping",
                }:
                    _update_work(
                        tx,
                        work,
                        state="reconciling",
                        blocked_reason="execution_unknown",
                    )
                self._settle(tx, work, run)
            tx.semantic_event(
                "execution.observed",
                {
                    "receipt_id": observation.receipt_id,
                    "agent_run_id": run["agent_run_id"],
                    "kind": observation.kind,
                },
            )
            self._observe_task(tx)
            return observation.receipt_id

    def reconcile(self, access, task_id, work_id):
        with self.uow.transaction(access, task_id, capability="observe") as tx:
            work = _work(tx, work_id)
            run = next(
                (
                    r
                    for r in _runs(tx, work_id)
                    if r["agent_run_id"] == work["current_run_id"]
                ),
                None,
            )
            if run:
                before = work["revision"]
                self._settle(tx, work, run)
                if work["revision"] != before:
                    tx.semantic_event(
                        "work.reconciled",
                        {"work_item_id": work_id, "state": work["state"]},
                    )
            self._observe_task(tx)
            return work

    def refresh(self, access, task_id, work_id):
        """P08/P09 notification consumer: re-read durable predicates, never clear on tick."""
        with self.uow.transaction(access, task_id, capability="observe") as tx:
            work = _work(tx, work_id)
            before = work["revision"]
            intent = intent_record(tx, work)
            if (
                work["state"] not in TERMINAL
                and intent
                and intent["acceptance_state"] == "superseded"
            ):
                self._work_command(tx, work, "cancel", "intent_superseded")
            else:
                self._restore(tx, work)
            if before != work["revision"]:
                tx.semantic_event(
                    "work.condition_changed",
                    {"work_item_id": work_id, "state": work["state"]},
                )
            return work

    def apply_completion(self, access, task_id, receipt_id, *, basis_check=None):
        """Consume a P12-owned canonical decision, not a caller's close/Goal assertion.

        ``basis_check`` is the one thing this state machine cannot judge by itself:
        the completion service recomputes the persisted review inside this same
        control transaction, so a decision whose evidence moved is refused here
        instead of being applied under stale assumptions.
        """
        if (
            not {"controller", "operator"}.intersection(access.principal.roles)
            or "agent" in access.principal.roles
        ):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        with self.uow.transaction(access, task_id, capability="control") as tx:
            decision = row(
                tx.connection.execute(
                    "SELECT * FROM vnext.completion_decision WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND receipt_id=%s",
                    (*tx.owner, receipt_id),
                )
            )
            if not decision:
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            old = row(
                tx.connection.execute(
                    "SELECT receipt_json FROM vnext.control_receipt WHERE tenant_id=%s AND task_id=%s AND operation_kind='completion_command' AND operation_id=%s",
                    (tx.owner[0], task_id, receipt_id),
                )
            )
            if old:
                return CommandReceipt.model_validate(
                    strict_json_loads(old["receipt_json"])
                )
            task = tx.task
            if (
                task["control_version"] != decision["expected_control_version"]
                or task["board_revision"] != decision["board_revision"]
                or task["observed_state"] == "closed"
            ):
                raise DomainError("STALE_VERSION", 409)
            if basis_check is not None:
                basis_check(tx, decision)
            action, epoch = decision["action"], decision["epoch_id"]
            if action == "quiesce":
                if (
                    not task["activated_at"]
                    or task["completion_epoch_id"]
                    or decision["deadline"] <= datetime.now(timezone.utc)
                ):
                    raise DomainError("STALE_EXECUTION", 409)
                task.update(
                    completion_epoch_id=epoch,
                    execution_allowed=False,
                    observed_state="quiescing",
                    close_trigger=decision["close_trigger"],
                )
                task["execution_epoch"] += 1
            elif task["completion_epoch_id"] != epoch:
                raise DomainError("STALE_EXECUTION", 409)
            elif action == "abort":
                if (
                    task["desired_state"] == "cancel"
                    or task["close_trigger"] == "user_cancel"
                ):
                    raise DomainError("STALE_EXECUTION", 409)
                self._definition(tx)
                paused = task["desired_state"] == "pause"
                task.update(
                    completion_epoch_id=None,
                    execution_allowed=not paused,
                    desired_state="pause" if paused else "run",
                    observed_state="paused" if paused else "running",
                    close_trigger=None,
                )
            elif action == "close":
                require_runtime_terminal(tx)
                runs = _rows(
                    tx.connection.execute(
                        "SELECT * FROM vnext.agent_run WHERE tenant_id=%s AND project_id=%s AND task_id=%s ORDER BY agent_run_id",
                        tx.owner,
                    )
                )
                if any(
                    r["stop_kind"] is None
                    or (
                        r["stop_kind"] != "not_started"
                        and not operations_settled(tx, r["agent_run_id"])
                    )
                    for r in runs
                ):
                    raise DomainError("OPERATION_UNKNOWN", 409)
                from wuji_core.contracts.execution import CloseTrigger, ResultOutcome

                try:
                    trigger = CloseTrigger(decision["close_trigger"]).value
                    outcome = ResultOutcome(decision["result_outcome"]).value
                except ValueError as error:
                    raise DomainError("INVALID_SCHEMA", 422) from error
                task.update(
                    observed_state="closed",
                    execution_allowed=False,
                    close_trigger=trigger,
                    result_outcome=outcome,
                )
            works = _rows(
                tx.connection.execute(
                    "SELECT * FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s ORDER BY work_item_id FOR UPDATE",
                    tx.owner,
                )
            )
            for work in works:
                if work["state"] in TERMINAL:
                    continue
                if action == "quiesce":
                    self._cause(tx, work, "completion_epoch", epoch)
                    self._stop(tx, work, decision["close_trigger"] or "completion")
                elif action == "abort":
                    self._cause(tx, work, "completion_epoch", epoch, remove=True)
                    self._restore(tx, work)
                else:
                    _update_work(
                        tx,
                        work,
                        desired_state="cancel",
                        terminal_reason=task["close_trigger"],
                    )
                    self._stop(tx, work, task["close_trigger"])
            task["control_version"] += 1
            tx.connection.execute(
                "UPDATE vnext.task SET completion_epoch_id=%s,execution_allowed=%s,execution_epoch=%s,desired_state=%s,observed_state=%s,close_trigger=%s,result_outcome=%s,control_version=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                (
                    task["completion_epoch_id"],
                    task["execution_allowed"],
                    task["execution_epoch"],
                    task["desired_state"],
                    task["observed_state"],
                    task["close_trigger"],
                    task["result_outcome"],
                    task["control_version"],
                    *tx.owner,
                ),
            )
            receipt = CommandReceipt.model_validate(
                dict(
                    command_id=receipt_id,
                    disposition="accepted",
                    resource_ref={
                        "entity_type": "task",
                        "id": task_id,
                        "revision": str(task["control_version"]),
                    },
                    resource_version=str(task["control_version"]),
                    request_id=access.request_id,
                )
            )
            raw = json_text(receipt.model_dump(mode="python"))
            tx.connection.execute(
                "INSERT INTO vnext.control_receipt(tenant_id,project_id,task_id,operation_kind,operation_id,input_digest,receipt_json) VALUES(%s,%s,%s,'completion_command',%s,%s,%s)",
                (
                    *tx.owner,
                    receipt_id,
                    sha256(decision["source_receipt_json"].encode()).hexdigest(),
                    raw,
                ),
            )
            tx.semantic_event(
                "completion.control_applied",
                {"receipt_id": receipt_id, "epoch_id": epoch, "action": action},
            )
            return receipt

    def _settle(self, tx, work, run):
        initial_state = work["state"]

        def publish_terminal_transition():
            if initial_state not in TERMINAL and work["state"] in TERMINAL:
                tx.semantic_event(
                    "work.settled",
                    {
                        "work_item_id": work["work_item_id"],
                        "agent_run_id": run["agent_run_id"],
                        "state": work["state"],
                        "terminal_reason": work["terminal_reason"],
                    },
                )

        if (
            work["state"] in TERMINAL
            or run["process_state"] != "exited"
            or not run["last_observation_id"]
        ):
            return
        stopped = tx.connection.execute(
            "SELECT kind FROM vnext.execution_observation WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND receipt_id=%s",
            (*tx.owner, run["agent_run_id"], run["last_observation_id"]),
        ).fetchone()
        if not stopped or stopped[0] not in {
            "not_started",
            "exited",
            "environment_stopped",
        }:
            return
        settled = operations_settled(tx, run["agent_run_id"])
        empty_evidence = _environment_stopped_without_evidence(tx, run)
        if not settled and run["stop_kind"] != "not_started" and not empty_evidence:
            if work["state"] in {"running", "leased", "stopping"}:
                _update_work(
                    tx, work, state="reconciling", blocked_reason="operations_unsettled"
                )
            return
        if work["desired_state"] == "cancel" or _causes(tx, work["work_item_id"]):
            self._stop(tx, work, work["terminal_reason"] or "control_stop")
            publish_terminal_transition()
            return
        native_process = (
            strict_json_loads(run["process_identity_json"])
            if run["process_identity_json"]
            else {}
        )
        if native_process.get("exit_code") not in {None, 0}:
            mark_missing_output(tx, run["agent_run_id"])
            if work["state"] in {"leased", "stopping"}:
                _update_work(tx, work, state="reconciling")
            if work["state"] in {"running", "reconciling"}:
                _update_work(
                    tx, work, state="failed", terminal_reason="process_failure"
                )
            publish_terminal_transition()
            return
        if can_settle_done(
            result_accepted(tx, run["agent_run_id"]),
            run["stop_kind"] != "not_started",
            settled,
        ):
            if work["state"] in {"leased", "stopping"}:
                _update_work(tx, work, state="reconciling")
            _update_work(tx, work, state="done", blocked_reason=None)
            publish_terminal_transition()
            return
        waiting = _input(tx, work)
        if (
            waiting
            and waiting["status"] in {"pending", "resolved"}
            and self._recoverable(tx, work)
            and work["state"] in {"running", "reconciling"}
        ):
            if work["state"] == "reconciling":
                # Both legal edges commit under the existing Task/Work locks.
                # Restore rechecks suspension causes and the persisted wait.
                _update_work(tx, work, state="suspended", blocked_reason=None)
                self._restore(tx, work)
            else:
                _update_work(tx, work, state="waiting_input", blocked_reason=None)
                if waiting["status"] == "resolved":
                    self._restore(tx, work)
            return
        if empty_evidence:
            # The environment is gone and the platform holds no execution
            # evidence: record the actual outcome instead of inventing output or
            # holding the Work item. Nothing is claimed about a process.
            mark_missing_output(tx, run["agent_run_id"])
            if work["state"] in {"leased", "stopping"}:
                _update_work(tx, work, state="reconciling")
            if work["state"] in {"running", "reconciling"}:
                _update_work(
                    tx,
                    work,
                    state="failed",
                    terminal_reason="environment_stopped_before_observation",
                )
            publish_terminal_transition()
            return
        state = mark_missing_output(tx, run["agent_run_id"])
        source = (
            strict_json_loads(run["process_identity_json"])
            if run["process_identity_json"]
            else {}
        )
        if state in {"incomplete", "rejected"} or (
            source.get("exit_code") is not None and source["exit_code"] != 0
        ):
            if work["state"] in {"leased", "stopping"}:
                _update_work(tx, work, state="reconciling")
            if work["state"] in {"running", "reconciling"}:
                _update_work(
                    tx,
                    work,
                    state="failed",
                    terminal_reason=(
                        "missing_or_rejected_output"
                        if state in {"incomplete", "rejected"}
                        else "process_failure"
                    ),
                )
        elif work["state"] in {"running", "leased", "stopping"}:
            _update_work(
                tx,
                work,
                state="reconciling",
                blocked_reason="result_or_boundary_pending",
            )
        publish_terminal_transition()
