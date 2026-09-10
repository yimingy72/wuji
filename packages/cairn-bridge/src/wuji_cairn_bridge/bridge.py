from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from cairn.server.models import ConcludeResponse, ProjectDetail, ProjectSummary
from wuji_task_runtime import validate_execution_permit

from .client import CairnPlatformClient
from .errors import BindingUnavailable, CairnUnavailable, DispatchDenied, OperationConflict
from .journal import SQLAlchemyJournal
from .models import AgentResult, BindingRecord, ControlSource, DispatchContext, ExplorationInput, ResultRecord, TaskKey, native_id

_REJECTED = {400, 401, 403, 404, 422}


class CairnTaskBridge:
    def __init__(self, client: CairnPlatformClient, journal: SQLAlchemyJournal, controls: ControlSource,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.client, self.journal, self.controls, self.clock = client, journal, controls, clock

    def _binding(self, key: TaskKey) -> BindingRecord:
        record = self.journal.get_binding(key)
        if record is None or record.state != "bound" or record.server_id != self.client.server_id or not record.project_id:
            raise BindingUnavailable("Task has no confirmed binding on this Cairn instance")
        native_id(record.project_id)
        return record

    def ensure_project(self, task: ExplorationInput) -> BindingRecord:
        request = task.to_native()
        record = self.journal.prepare_binding(task.key, self.client.server_id, task.request_digest)
        if record.state != "pending":
            # A crash after claiming cannot be distinguished from a lost response.
            # Never issue a second create based on a name or a similar goal.
            return record
        if not self.journal.claim_binding(task.key):
            return self.journal.get_binding(task.key)
        try:
            response = self.client.create_project(request)
        except Exception:
            return self.journal.set_binding_state(task.key, "unknown")
        if response.status_code in _REJECTED:
            return self.journal.set_binding_state(task.key, "rejected")
        if response.status_code != 201:
            return self.journal.set_binding_state(task.key, "unknown")
        try:
            detail = ProjectDetail.model_validate(response.data)
            native_id(detail.project.id)
            facts = {item.id: item.description for item in detail.facts}
            if detail.project.title != request.title or facts.get("origin") != request.origin or facts.get("goal") != request.goal:
                raise ValueError("unexpected project response")
        except Exception:
            return self.journal.set_binding_state(task.key, "unknown")
        # If this durable write fails, the sent record remains conservative.
        return self.journal.finish_binding(task.key, detail.project.id)

    def get_project(self, key: TaskKey) -> ProjectDetail:
        binding = self._binding(key)
        try:
            detail = self.client.get_project(binding.project_id)
            if detail.project.id != binding.project_id:
                raise ValueError("different project")
            return detail
        except Exception:
            raise CairnUnavailable("native project read failed") from None

    def _context(self, key: TaskKey) -> DispatchContext:
        try:
            context = self.controls.current(key)
            if not isinstance(context, DispatchContext) or context.key != key:
                raise ValueError("missing task context")
            config = context.runtime_config
            if config.tenant_id != key.tenant_id or config.task_id != key.task_id:
                raise ValueError("different task")
            if context.control_state != "running" or context.execution_ready is not True:
                raise ValueError("execution not admitted")
            validate_execution_permit(config, context.permit, self.clock())
            observed = context.observation
            if observed is None or observed.state != "ready" or observed.pod_name != config.pod_name or not observed.pod_uid:
                raise ValueError("runtime not ready")
            return context
        except Exception:
            raise DispatchDenied("Task has no current dispatch admission") from None

    def eligible_projects(self) -> list[ProjectSummary]:
        bindings = {record.project_id: record for record in self.journal.list_bindings(self.client.server_id) if record.state == "bound"}
        try:
            projects = self.client.list_projects()
        except Exception:
            raise CairnUnavailable("native project listing failed") from None
        result = []
        for project in projects:
            binding = bindings.get(project.id)
            if binding is None or project.status != "active":
                continue
            try:
                self._context(binding.key)
            except DispatchDenied:
                continue
            result.append(project)
        return result

    def authorize_dispatch(self, key: TaskKey) -> DispatchContext:
        context = self._context(key)
        if self.get_project(key).project.status != "active":
            raise DispatchDenied("Cairn exploration is not active")
        # Recheck after native I/O rather than retaining a preselection grant.
        return self._context(context.key)

    def _result_state(self, result: AgentResult, state: str) -> ResultRecord:
        try:
            return self.journal.set_result_state(result.key, result.operation_id, state)
        except OperationConflict:
            record = self.journal.get_result(result.key, result.operation_id)
            if record is not None and record.state == "applied":
                return record
            raise

    def submit_result(self, result: AgentResult) -> ResultRecord:
        binding = self._binding(result.key)
        record = self.journal.prepare_result(result, self.client.server_id, binding.project_id,
                                             result.request_digest(self.client.server_id, binding.project_id))
        if record.state in {"applied", "rejected", "conflict"}:
            return record
        if record.state in {"sent", "unknown"}:
            return self.reconcile_result(result.key, result.operation_id)
        try:
            context = self.authorize_dispatch(result.key)
            if result.agent_run_id not in context.active_agent_run_ids:
                raise DispatchDenied("AgentRun is not registered as active")
            for field in ("runtime_attempt", "execution_epoch", "scope_digest", "config_digest"):
                if getattr(result, field) != getattr(context.runtime_config, field):
                    raise DispatchDenied("result execution binding changed")
        except DispatchDenied:
            return self.journal.reject_pending_result(result.key, result.operation_id)
        if not self.journal.claim_result(result.key, result.operation_id):
            return self.journal.get_result(result.key, result.operation_id)
        try:
            response = self.client.conclude(binding.project_id, result.intent_id, str(result.agent_run_id), result.description)
        except Exception:
            return self._result_state(result, "unknown")
        if response.status_code in _REJECTED:
            return self._result_state(result, "rejected")
        if response.status_code != 200:
            return self._result_state(result, "unknown")
        try:
            concluded = ConcludeResponse.model_validate(response.data)
            if (concluded.intent.id != result.intent_id or concluded.intent.to != concluded.fact.id or
                concluded.intent.worker != str(result.agent_run_id) or concluded.fact.description != result.description):
                raise ValueError("unexpected conclusion")
            native_id(concluded.fact.id)
        except Exception:
            return self._result_state(result, "unknown")
        return self.journal.finish_result(result.key, result.operation_id, concluded.fact.id)

    def reconcile_result(self, key: TaskKey, operation_id) -> ResultRecord:
        record = self.journal.get_result(key, operation_id)
        if record is None:
            raise BindingUnavailable("no recorded result operation")
        if record.state in {"applied", "rejected", "conflict", "pending"}:
            return record
        binding = self._binding(key)
        if record.server_id != binding.server_id or record.project_id != binding.project_id:
            raise OperationConflict("result binding changed")
        detail = self.get_project(key)
        intent = next((item for item in detail.intents if item.id == record.result.intent_id), None)
        if intent is None or intent.to is None:
            return self._result_state(record.result, "unknown")
        fact = next((item for item in detail.facts if item.id == intent.to), None)
        if fact is not None and intent.worker == str(record.result.agent_run_id) and fact.description == record.result.description:
            native_id(fact.id)
            return self.journal.finish_result(key, operation_id, fact.id)
        return self._result_state(record.result, "conflict")
