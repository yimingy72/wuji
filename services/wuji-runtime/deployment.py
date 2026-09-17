"""Production Runtime/Host composition from explicit mounted deployment files."""

import json

from deployment_common import Deployment, load_settings, read_file, token
from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.execution.dispatch_outbox import (
    SupervisorHttpTransport,
    TaskSupervisorTransport,
)
from wuji_core.execution.runtime_dispatcher import build_runtime_controller
from wuji_core.http import JsonBoundaryLimits
from wuji_core.projection.snapshots import ProjectionRepository
from wuji_core.worker_host import PlatformWorkerHost
from wuji_maf_worker.context import ContextLimits, ContextRelation, build_context_bundle


def build_context(*, records, read_set, snapshot_id, max_records, max_bytes, relations):
    return build_context_bundle(records, read_set, snapshot_id=snapshot_id,
        limits=ContextLimits(max_records=max_records, max_bytes=max_bytes),
        relations=tuple(ContextRelation(source=KnowledgeRef.model_validate(r["source"]),
            target=KnowledgeRef.model_validate(r["target"]), relation=r["relation"]) for r in relations))


def dispatch_audit(record):
    """Bounded operator signal for a Task-Service delivery attempt.

    Only the method, the HTTP status and the transport error class are emitted;
    the assignment, bearer, bodies and peer detail stay out of the log.
    """

    request, response = record.get("request", {}), record.get("response", {})
    detail = {"event": "runtime_dispatch_transport",
              "method": request.get("method")}
    status = response.get("status_code")
    if type(status) is int:
        detail["status"] = status
    error = response.get("error")
    if isinstance(error, str) and 0 < len(error) <= 64:
        detail["error"] = error
    print(json.dumps(detail, sort_keys=True), flush=True)


def _supervisor_transport(settings, deployment):
    """One supervisor origin per Task, with the deployment URL as fallback.

    A host that serves several Tasks must not deliver one Task's Assignment to
    another Task's Pod, so every published per-Task endpoint gets its own
    transport and only Tasks without one fall back to the fixed URL.
    """

    authorization = lambda: token(settings.receiver_token_file)
    common = dict(
        authorization=authorization,
        ssl_context=deployment.tls,
        max_response_bytes=min(settings.max_transport_bytes, 1048576),
        audit=dispatch_audit,
    )
    default = (
        SupervisorHttpTransport(settings.supervisor_url, **common)
        if settings.supervisor_url
        else None
    )
    by_task = {}
    pod_runtime = settings.pod_runtime or {}
    for entry in pod_runtime.get("tasks") or []:
        if not isinstance(entry, dict):
            continue
        values = entry.get("task_config")
        task_id = values.get("task_id") if isinstance(values, dict) else None
        url = entry.get("supervisor_url")
        if isinstance(task_id, str) and task_id and isinstance(url, str) and url:
            by_task[task_id] = SupervisorHttpTransport(url, **common)
    if not by_task:
        if default is None:
            raise ValueError("fixed runtime receiver endpoint required")
        return default
    return TaskSupervisorTransport(default=default, by_task=by_task)


def build_runtime():
    settings = load_settings("runtime")
    deployment = Deployment(settings)
    if not all((settings.supervisor_url, settings.receiver_token_file,
                settings.host_origin, settings.model_gate_url, settings.tool_gate_url,
                settings.task_ids)):
        raise ValueError("fixed runtime receiver/endpoints/Task discovery required")
    supervisor_transport = _supervisor_transport(settings, deployment)
    receiver_access = deployment.access(settings.receiver_token_file)

    def host_factory(access):
        return PlatformWorkerHost(uow=deployment.uow, registry=deployment.registry,
            access=access, artifacts=deployment.artifacts, committer=deployment.committer,
            profiles=deployment.profiles, lock_digest=deployment.lock_digest,
            sessions=deployment.sessions, inputs=deployment.inputs,
            receiver_access=lambda _: deployment.access(settings.receiver_token_file))

    def retained_factory(access, binding):
        return PlatformWorkerHost(uow=deployment.uow, registry=deployment.registry,
            access=access, artifacts=deployment.artifacts, committer=deployment.committer,
            profiles=deployment.profiles, lock_digest=deployment.lock_digest,
            retained_result=binding)

    controller = build_runtime_controller(deployment.uow, access=receiver_access,
        authorized_task_ids=settings.task_ids, work_kinds=settings.work_kinds,
        credentials=deployment.issuer(), registry=deployment.registry, control=deployment.control,
        supervisor_transport=supervisor_transport,
        host_factory=host_factory, retained_host_factory=retained_factory,
        session_transport=settings.session_transport, context_builder=build_context,
        ledger=deployment.ledger,
        child_config={"public_key_pem": read_file(settings.public_key_file).decode(),
            "issuer": settings.issuer, "audience": settings.audience,
            "host_origin": settings.host_origin, "model_gate_url": settings.model_gate_url,
            "tool_gate_url": settings.tool_gate_url, "wait_timeout_seconds": 120,
            "transport_timeout_seconds": 15, "max_transport_bytes": settings.max_transport_bytes},
        journal_path=settings.journal_path, spool_directory=settings.spool_directory,
        approval_service=deployment.approvals if settings.public_approvals else None,
        control_service=deployment.control if settings.public_commands else None,
        projection=ProjectionRepository(deployment.uow, ledger=deployment.ledger),
        json_limits=JsonBoundaryLimits(max_body_bytes=settings.max_transport_bytes))
    if settings.pod_runtime is not None:
        from pod_deployment import PodEnvironment
        controller.pod_environment = PodEnvironment(deployment, settings.pod_runtime)
    return controller
