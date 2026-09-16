"""Production composition for P09 outbox delivery and P10 Worker reconciliation.

The deployment supplies authenticated service access, fixed task discovery,
network transports and storage roots.  This module never creates an Assignment,
derives an operation from caller input, or keeps PostgreSQL open during I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Callable, Iterable, Mapping

from wuji_core.execution.dispatch_outbox import DispatchOutbox
from wuji_core.execution.reconcile import (
    ObservedExecution,
    Reconciler,
    RegisteredRun,
    read_registered_run,
)
from wuji_core.execution.retained_results import RetainedResultService
from wuji_core.execution.worker_bridge import WorkerHostBridge
from wuji_core.http import DEFAULT_JSON_LIMITS, JsonBoundaryLimits, create_app, strict_json_loads
from wuji_core.http.worker_host import create_worker_host_router
from wuji_core.persistence.uow import AccessContext, DomainError


@dataclass(frozen=True)
class PendingDispatch:
    task_id: str
    operation_id: str
    assignment_digest: str
    event_seq: str


@dataclass(frozen=True)
class PendingReconcile:
    """An existing Run that still needs reconciliation, never a new dispatch."""

    task_id: str
    operation_id: str
    run: RegisteredRun
    receiver_enabled: bool
    process_state: str
    work_state: str


def _bounded_failure(error) -> str:
    """Bounded, loggable classification; raw peer text never leaves here."""

    code = getattr(error, "code", None)
    if isinstance(code, str) and 1 <= len(code) <= 64:
        return code
    return type(error).__name__


@dataclass
class RuntimeController:
    """The assembled private Host app and its one outbox consumer."""

    app: object
    dispatcher: "RuntimeDispatcher"
    outbox: DispatchOutbox
    reconciler: Reconciler
    bridge: WorkerHostBridge
    session_bridge: object | None
    session_codec: object | None

    def close(self) -> None:
        self.dispatcher.close()


class RuntimeDispatcher:
    """Bounded receiver-owned consumer for existing dispatch notifications."""

    def __init__(
        self,
        uow,
        *,
        access: AccessContext,
        authorized_task_ids: Iterable[str] | Callable[[], Iterable[str]],
        work_kinds: Iterable[str],
        outbox: DispatchOutbox,
        reconciler: Reconciler,
        max_configured_tasks: int = 10_000,
        max_reconcile_per_cycle: int = 16,
    ) -> None:
        work_kinds = tuple(work_kinds)
        if (
            not isinstance(access, AccessContext)
            or "agent" in access.principal.roles
            or not access.principal.roles.intersection({"controller", "reconciler"})
            or type(max_configured_tasks) is not int
            or not 1 <= max_configured_tasks <= 100_000
            or type(max_reconcile_per_cycle) is not int
            or not 1 <= max_reconcile_per_cycle <= 256
            or not work_kinds
            or len(set(work_kinds)) != len(work_kinds)
            or any(kind not in {"reason", "explore", "report"} for kind in work_kinds)
        ):
            raise ValueError("a bounded authenticated receiver is required")
        self.uow = uow
        self.access = access
        self._task_source = (
            authorized_task_ids
            if callable(authorized_task_ids)
            else lambda: tuple(authorized_task_ids)
        )
        self.work_kinds = work_kinds
        self.outbox = outbox
        self.reconciler = reconciler
        self.max_configured_tasks = max_configured_tasks
        self.max_reconcile_per_cycle = max_reconcile_per_cycle
        # Fairness cursors are in-memory hints only: PostgreSQL stays the
        # authority for what is pending, and a restart simply rescans.
        self._task_cursor = 0
        self._dispatch_cursor: dict[str, str] = {}
        self._reconcile_cursor: dict[str, str] = {}
        self.failures: dict[str, str] = {}
        self._start_restriction: frozenset[str] | None = None
        self._ended_environments: dict[str, str] = {}
        self._closed = False

    def _tasks(self) -> tuple[str, ...]:
        tasks = tuple(self._task_source())
        if (
            len(tasks) > self.max_configured_tasks
            or len(set(tasks)) != len(tasks)
            or any(not isinstance(task_id, str) or not task_id for task_id in tasks)
        ):
            raise ValueError("invalid authorized task source")
        return tasks

    def _ordered_tasks(self) -> tuple[str, ...]:
        """Round-robin start offset: no Task can own the head of every batch."""

        tasks = list(self._tasks())
        if not tasks:
            return ()
        offset = self._task_cursor % len(tasks)
        self._task_cursor = (self._task_cursor + 1) % len(tasks)
        return tuple(tasks[offset:] + tasks[:offset])

    def _pending_for(self, task_id: str, limit: int) -> tuple[PendingDispatch, ...]:
        with self.uow.transaction(self.access, task_id, capability="observe") as tx:
            cursor = tx.connection.execute(
                """SELECT o.event_seq,o.payload_json,d.operation_id,d.assignment_digest
                FROM vnext.outbox o
                JOIN vnext.scheduler_assignment d
                  ON (d.tenant_id,d.project_id,d.task_id,d.event_seq)=
                     (o.tenant_id,o.project_id,o.task_id,o.event_seq)
                JOIN vnext.agent_run a
                  ON (a.tenant_id,a.project_id,a.task_id,a.agent_run_id,a.work_item_id,
                      a.start_operation_id)=
                     (d.tenant_id,d.project_id,d.task_id,d.agent_run_id,d.work_item_id,
                      d.operation_id)
                JOIN vnext.work_item w
                  ON (w.tenant_id,w.project_id,w.task_id,w.work_item_id)=
                     (a.tenant_id,a.project_id,a.task_id,a.work_item_id)
                JOIN vnext.scheduler_receiver r
                  ON (r.tenant_id,r.project_id,r.task_id,r.runtime_attempt,r.receiver_id)=
                     (a.tenant_id,a.project_id,a.task_id,a.runtime_attempt,a.receiver_id)
                WHERE o.tenant_id=%s AND o.project_id=%s AND o.task_id=%s
                  AND o.kind='run.dispatch_requested'
                  AND r.receiver_subject=%s AND r.enabled
                  AND w.kind=ANY(%s)
                  AND a.process_state<>'exited'
                ORDER BY CASE WHEN o.event_seq>%s THEN 0 ELSE 1 END,
                         o.event_seq,d.operation_id LIMIT %s""",
                (
                    *tx.owner,
                    self.access.principal.subject,
                    list(self.work_kinds),
                    int(self._dispatch_cursor.get(task_id, "0") or 0),
                    limit,
                ),
            )
            columns = tuple(column.name for column in cursor.description)
            rows = tuple(dict(zip(columns, values)) for values in cursor.fetchall())
            pending = []
            for record in rows:
                payload = strict_json_loads(record["payload_json"])
                if (
                    not isinstance(payload, dict)
                    or set(payload)
                    != {"agent_run_id", "operation_id", "assignment_digest"}
                    or payload["operation_id"] != record["operation_id"]
                    or payload["assignment_digest"] != record["assignment_digest"]
                ):
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                run, assignment, _credential_ref = read_registered_run(
                    tx, record["operation_id"]
                )
                if (
                    run.assignment_digest != record["assignment_digest"]
                    or assignment.identity.agent_run_id != payload["agent_run_id"]
                ):
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                pending.append(
                    PendingDispatch(
                        task_id=task_id,
                        operation_id=record["operation_id"],
                        assignment_digest=record["assignment_digest"],
                        event_seq=str(record["event_seq"]),
                    )
                )
            if pending:
                self._dispatch_cursor[task_id] = pending[-1].event_seq
            if len(pending) < limit:
                # Scan exhausted: wrap so the next cycle reconsiders the head
                # instead of rescanning the same stable prefix forever.
                self._dispatch_cursor[task_id] = "0"
            return tuple(pending)

    def restrict_starts(self, task_ids: Iterable[str] | None) -> None:
        """Bound which Tasks may deliver a *new* start this cycle.

        `None` restores the configured authorization. Reconciliation is never
        restricted: a Task whose environment is not ready must still have its
        existing Runs queried and settled, or a stop can strand them. Only
        identifiers the deployment already authorized are accepted.
        """

        if task_ids is None:
            self._start_restriction = None
            return
        requested = tuple(task_ids)
        authorized = self._tasks()
        if (
            len(set(requested)) != len(requested)
            or any(not isinstance(task_id, str) or not task_id for task_id in requested)
            or not set(requested) <= set(authorized)
        ):
            raise ValueError("invalid start restriction")
        self._start_restriction = frozenset(requested)

    def note_ended_environments(self, evidence: Mapping | None) -> None:
        """Record which Tasks have no runtime environment left this cycle.

        The runtime sets this from the Pod controller's own observation: it
        reports ``stopped`` only once the Task Pod object is absent, never for a
        transient Kubernetes failure. A Task listed here gets no new delivery and
        its never-observed Runs are settled instead of being queried forever.
        """

        if evidence is None:
            self._ended_environments = {}
            return
        if not isinstance(evidence, dict):
            raise ValueError("bounded per-Task environment evidence required")
        authorized = self._tasks()
        checked = {}
        for task_id, reason in evidence.items():
            if (
                not isinstance(task_id, str)
                or task_id not in authorized
                or not isinstance(reason, str)
                or not 0 < len(reason) <= 512
            ):
                raise ValueError("invalid environment evidence")
            checked[task_id] = reason
        self._ended_environments = checked

    def start_allowed(self, task_id: str) -> bool:
        return self._start_restriction is None or task_id in self._start_restriction

    def pending(self, *, limit: int = 16) -> tuple[PendingDispatch, ...]:
        if self._closed or type(limit) is not int or not 1 <= limit <= 256:
            raise ValueError("a live dispatcher and bounded limit are required")
        pending = []
        for task_id in self._ordered_tasks():
            if not self.start_allowed(task_id) or task_id in self._ended_environments:
                continue
            remaining = limit - len(pending)
            if not remaining:
                break
            pending.extend(self._pending_for(task_id, remaining))
        return tuple(pending)

    def _note_failure(self, key: str, error) -> None:
        self.failures[key] = _bounded_failure(error)

    def deliver_pending(self, *, limit: int = 16) -> tuple[ObservedExecution, ...]:
        """Deliver registered operations after all discovery transactions close.

        One refused or unreachable operation must not cancel the rest of the
        batch: each delivery is isolated and its bounded classification is kept
        for the next cycle instead of silently disappearing.
        """

        records = self.pending(limit=limit)
        delivered = []
        for record in records:
            try:
                delivered.append(
                    self.outbox.deliver(record.task_id, record.operation_id)
                )
            except (DomainError, OSError, TimeoutError, ValueError) as error:
                self._note_failure(record.operation_id, error)
        return tuple(delivered)

    def _reconcile_candidates(self, task_id: str, limit: int) -> tuple[PendingReconcile, ...]:
        """Existing Runs that still need reconciliation, enabled or not.

        A disabled receiver or a non-ready Pod only stops *new* starts.  Runs
        whose work item is not terminal must keep being queried and settled, or
        a cancel/stop can strand them without any automatic path back.
        """

        with self.uow.transaction(self.access, task_id, capability="observe") as tx:
            cursor = tx.connection.execute(
                """SELECT a.start_operation_id,a.process_state,
                          COALESCE(r.enabled,false) AS receiver_enabled,w.state AS work_state
                FROM vnext.agent_run a
                JOIN vnext.work_item w
                  ON (w.tenant_id,w.project_id,w.task_id,w.work_item_id)=
                     (a.tenant_id,a.project_id,a.task_id,a.work_item_id)
                LEFT JOIN vnext.scheduler_receiver r
                  ON (r.tenant_id,r.project_id,r.task_id,r.runtime_attempt,r.receiver_id)=
                     (a.tenant_id,a.project_id,a.task_id,a.runtime_attempt,a.receiver_id)
                WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s
                  AND a.start_operation_id IS NOT NULL
                  AND w.state NOT IN ('done','cancelled','failed','superseded')
                ORDER BY CASE WHEN a.agent_run_id>%s THEN 0 ELSE 1 END,
                         a.agent_run_id LIMIT %s""",
                (
                    *tx.owner,
                    self._reconcile_cursor.get(task_id, ""),
                    limit,
                ),
            )
            columns = tuple(column.name for column in cursor.description)
            rows = tuple(dict(zip(columns, values)) for values in cursor.fetchall())
            candidates = []
            for record in rows:
                run, _assignment, _ref = read_registered_run(
                    tx, record["start_operation_id"]
                )
                candidates.append(
                    PendingReconcile(
                        task_id=task_id,
                        operation_id=record["start_operation_id"],
                        run=run,
                        receiver_enabled=bool(record["receiver_enabled"]),
                        process_state=str(record["process_state"]),
                        work_state=str(record["work_state"]),
                    )
                )
            if candidates:
                self._reconcile_cursor[task_id] = candidates[-1].run.identity.agent_run_id
            if len(candidates) < limit:
                self._reconcile_cursor[task_id] = ""
            return tuple(candidates)

    def reconcile_pending(self, *, limit: int | None = None) -> tuple[ObservedExecution, ...]:
        """Query and settle existing Runs; never creates a Run or a new start."""

        budget = self.max_reconcile_per_cycle if limit is None else limit
        if type(budget) is not int or not 1 <= budget <= 256:
            raise ValueError("a bounded reconcile limit is required")
        observed = []
        for task_id in self._ordered_tasks():
            remaining = budget - len(observed)
            if not remaining:
                break
            try:
                candidates = self._reconcile_candidates(task_id, remaining)
            except (DomainError, OSError, TimeoutError, ValueError) as error:
                self._note_failure(task_id, error)
                continue
            ended = self._ended_environments.get(task_id)
            for candidate in candidates:
                try:
                    if ended is not None and candidate.process_state == "registered":
                        # The environment is gone and this Run never produced a
                        # receipt, so no query can settle it.
                        observed.append(
                            self.reconciler.settle_ended_environment(
                                candidate.run, reason=ended
                            )
                        )
                        continue
                    observed.append(self.reconciler.reconcile(candidate.run))
                except (DomainError, OSError, TimeoutError, ValueError) as error:
                    self._note_failure(candidate.operation_id, error)
        return tuple(observed)

    def reconcile(self, run: RegisteredRun) -> ObservedExecution:
        return self.reconciler.reconcile(run)

    def run_once(self, *, limit: int = 16) -> tuple[ObservedExecution, ...]:
        """One bounded service cycle; retained results precede P05 observation."""

        observed = []
        for item in self.deliver_pending(limit=limit):
            try:
                observed.append(self.reconcile(item.run))
            except (DomainError, OSError, TimeoutError, ValueError) as error:
                self._note_failure(item.run.identity.agent_run_id, error)
        observed.extend(self.reconcile_pending(limit=self.max_reconcile_per_cycle))
        return tuple(observed)

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self.outbox.close()


def build_runtime_controller(
    uow,
    *,
    access: AccessContext,
    authorized_task_ids: Iterable[str] | Callable[[], Iterable[str]],
    work_kinds: Iterable[str],
    credentials,
    registry,
    control,
    supervisor_transport,
    host_factory,
    retained_host_factory,
    session_transport: bool,
    context_builder,
    ledger,
    child_config,
    journal_path,
    spool_directory,
    approval_service=None,
    control_service=None,
    projection=None,
    json_limits: JsonBoundaryLimits = DEFAULT_JSON_LIMITS,
    max_configured_tasks: int = 10_000,
) -> RuntimeController:
    """Build the private Host/router and the matching P09 delivery consumer."""
    if type(session_transport) is not bool:
        raise ValueError("Session transport deployment selection is required")
    def receiver_access(value) -> AccessContext:
        identity = value.identity
        if identity.tenant_id != access.principal.tenant_id:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        # WorkerHostBridge and DispatchRepository re-read the exact Task,
        # operation, receiver subject and Assignment under this access.
        return access

    retained_results = RetainedResultService(retained_host_factory)
    session_codec = None
    session_bridge = None
    session_resolve_encoder = None
    if session_transport:
        from wuji_core.execution.session_bridge import (
            SessionHostBridge,
            SessionTransportCodec,
        )

        session_codec = SessionTransportCodec(
            max_transport_bytes=child_config["max_transport_bytes"]
        )
        session_resolve_encoder = session_codec.encode_resolved
    bridge = WorkerHostBridge(
        uow,
        registry=registry,
        credentials=credentials,
        receiver_access=receiver_access,
        host_factory=host_factory,
        context_builder=context_builder,
        ledger=ledger,
        retained_results=retained_results,
        child_config=child_config,
        spool_directory=spool_directory,
        session_resolve_encoder=session_resolve_encoder,
    )
    routers = [create_worker_host_router(bridge)]
    if approval_service is not None:
        if not callable(getattr(approval_service, "decide", None)):
            raise ValueError("a real ApprovalService decision port is required")
        from wuji_core.http.approvals import create_approval_router

        routers.append(create_approval_router(approval_service))
    if control_service is not None:
        if control_service is not control:
            raise ValueError("the command API must use the Runtime ControlService")
        from wuji_core.execution.control_api import ControlAPI
        from wuji_core.http.commands import create_command_router

        routers.append(create_command_router(ControlAPI(control_service)))
    if projection is not None:
        if getattr(projection, "uow", None) is not uow or not callable(
            getattr(projection, "topology", None)
        ):
            raise ValueError("projection must use the runtime UnitOfWork")
        from wuji_core.http.topology import create_topology_router

        routers.append(create_topology_router(projection))
    if session_transport:
        from wuji_core.http.session_host import create_session_host_router

        session_bridge = SessionHostBridge(bridge, codec=session_codec)
        routers.append(create_session_host_router(session_bridge))
    outbox = DispatchOutbox(
        uow,
        access=access,
        transport=supervisor_transport,
        journal_path=journal_path,
    )
    reconciler = Reconciler(
        uow,
        access=access,
        control=control,
        transport=supervisor_transport,
        persist_results=bridge.reconcile_results,
    )
    dispatcher = RuntimeDispatcher(
        uow,
        access=access,
        authorized_task_ids=authorized_task_ids,
        work_kinds=work_kinds,
        outbox=outbox,
        reconciler=reconciler,
        max_configured_tasks=max_configured_tasks,
    )
    app = create_app(
        token_verifier=bridge.verifier,
        routers=routers,
        json_limits=json_limits,
    )
    return RuntimeController(
        app, dispatcher, outbox, reconciler, bridge, session_bridge, session_codec
    )
