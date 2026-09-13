"""Production composition for P09 outbox delivery and P10 Worker reconciliation.

The deployment supplies authenticated service access, fixed task discovery,
network transports and storage roots.  This module never creates an Assignment,
derives an operation from caller input, or keeps PostgreSQL open during I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

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
    ) -> None:
        work_kinds = tuple(work_kinds)
        if (
            not isinstance(access, AccessContext)
            or "agent" in access.principal.roles
            or not access.principal.roles.intersection({"controller", "reconciler"})
            or type(max_configured_tasks) is not int
            or not 1 <= max_configured_tasks <= 100_000
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
                ORDER BY o.event_seq,d.operation_id LIMIT %s""",
                (
                    *tx.owner,
                    self.access.principal.subject,
                    list(self.work_kinds),
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
            return tuple(pending)

    def pending(self, *, limit: int = 16) -> tuple[PendingDispatch, ...]:
        if self._closed or type(limit) is not int or not 1 <= limit <= 256:
            raise ValueError("a live dispatcher and bounded limit are required")
        pending = []
        for task_id in self._tasks():
            remaining = limit - len(pending)
            if not remaining:
                break
            pending.extend(self._pending_for(task_id, remaining))
        return tuple(pending)

    def deliver_pending(self, *, limit: int = 16) -> tuple[ObservedExecution, ...]:
        """Deliver registered operations after all discovery transactions close."""
        records = self.pending(limit=limit)
        return tuple(
            self.outbox.deliver(record.task_id, record.operation_id)
            for record in records
        )

    def reconcile(self, run: RegisteredRun) -> ObservedExecution:
        return self.reconciler.reconcile(run)

    def run_once(self, *, limit: int = 16) -> tuple[ObservedExecution, ...]:
        """One bounded service cycle; retained results precede P05 observation."""
        delivered = self.deliver_pending(limit=limit)
        return tuple(self.reconcile(item.run) for item in delivered)

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
