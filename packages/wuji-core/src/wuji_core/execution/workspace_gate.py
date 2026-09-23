"""Canonical ToolAttempt wrapper for native MCP workspace bundle operations."""

from starlette.concurrency import run_in_threadpool

from wuji_core.admission.common import audit, digest
from wuji_core.admission.tools import _attempt, _settlement, tool_kind
from wuji_core.contracts import generated as wire
from wuji_core.contracts.admission import ToolCallRequest, ToolCallReceipt
from wuji_core.http import strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text


class WorkspaceToolGate:
    def __init__(self, gate, service, *, refresh=None):
        self.gate, self.service = gate, service
        self.admission, self.registry = gate.admission, gate.registry
        self.refresh = refresh

    def _definition(self, access, ref, name):
        binding = self.registry.binding(access)
        with self.admission.uow.transaction(
            access, binding.identity.task_id
        ) as tx:
            definition = self.registry.tool(tx, ref)
            registration = self.registry.executor(tx, definition.executor_ref)
            if (
                definition.name != name
                or tool_kind(definition) != "workspace_bundle"
                or definition.ref not in registration.allowed_tool_refs
            ):
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            return definition, registration

    async def invoke(self, access, request, *, name, assignment):
        if self.refresh is not None:
            await run_in_threadpool(self.refresh)
        request = ToolCallRequest.model_validate(request)
        _definition, registration = await run_in_threadpool(
            self._definition, access, request.tool_definition_ref, name
        )
        permit = await run_in_threadpool(
            self.admission.authorize, access, request
        )
        if permit.replay:
            result = await run_in_threadpool(self.service.replay, permit, name)
            if result is None:
                result = await run_in_threadpool(self._saved, permit, name)
            await run_in_threadpool(self._complete, permit, result)
        else:
            try:
                await run_in_threadpool(
                    self.admission.check_execution,
                    permit,
                    receiver_id=registration.receiver_id,
                )
                result = (
                    await self.service.publish(permit, permit.arguments, assignment)
                    if name == "workspace_publish"
                    else await self.service.materialize(
                        permit, permit.arguments, assignment
                    )
                )
                await run_in_threadpool(self._complete, permit, result)
            except Exception:
                result = await run_in_threadpool(self.service.replay, permit, name)
                if result is None:
                    await run_in_threadpool(self._unknown, permit)
                    raise
                await run_in_threadpool(self._complete, permit, result)
        receipt = await run_in_threadpool(
            self.gate.ledger.tool_call, access, permit.tool_call_id
        )
        return result, receipt

    def _saved(self, permit, name):
        model = (
            wire.WorkspacePublishResultV1
            if name == "workspace_publish"
            else wire.WorkspaceMaterializeResultV1
        )
        with self.admission.uow.transaction(
            permit.access, permit.identity.task_id
        ) as tx:
            attempt = _attempt(tx, permit.tool_attempt_id)
            if attempt["receipt_json"] == "{}":
                raise DomainError("OPERATION_UNKNOWN", 409)
            return model.model_validate(
                strict_json_loads(attempt["receipt_json"])
            )

    def _complete(self, permit, result):
        result_value = result.model_dump(mode="json")
        manifest_ref = getattr(result, "manifest_ref", None)
        with self.admission.uow.transaction(
            permit.access, permit.identity.task_id, capability="tool_settle"
        ) as tx:
            attempt = _attempt(tx, permit.tool_attempt_id)
            if attempt["receipt_json"] != "{}":
                if digest(strict_json_loads(attempt["receipt_json"])) != digest(
                    result_value
                ):
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                return
            receipt = ToolCallReceipt.model_validate(
                {
                    "tool_call_id": permit.tool_call_id,
                    "operation_id": permit.tool_call_id,
                    "tool_attempt_id": permit.tool_attempt_id,
                    "status": "complete",
                    "evidence_receipt": None,
                    "result_ref": (
                        None
                        if manifest_ref is None
                        else manifest_ref.model_dump(mode="json")
                    ),
                    "reason_code": None,
                }
            )
            tx.connection.execute(
                """UPDATE vnext.tool_attempt SET status='complete',receipt_json=%s,
                result_receipt_json=%s WHERE tenant_id=%s AND project_id=%s
                AND task_id=%s AND tool_attempt_id=%s""",
                (
                    json_text(result_value),
                    json_text(receipt.model_dump(mode="json")),
                    *tx.owner,
                    permit.tool_attempt_id,
                ),
            )
            tx.connection.execute(
                "UPDATE vnext.tool_call SET status='complete' WHERE tenant_id=%s "
                "AND project_id=%s AND task_id=%s AND tool_call_id=%s",
                (*tx.owner, permit.tool_call_id),
            )
            _settlement(tx, permit.identity.agent_run_id)
            audit(
                tx,
                "workspace.action_complete",
                {"tool_attempt_id": permit.tool_attempt_id},
            )

    def _unknown(self, permit):
        with self.admission.uow.transaction(
            permit.access, permit.identity.task_id, capability="tool_settle"
        ) as tx:
            attempt = _attempt(tx, permit.tool_attempt_id)
            if attempt["status"] in {"complete", "failed", "cancelled"}:
                return
            tx.connection.execute(
                "UPDATE vnext.tool_attempt SET status='unknown' WHERE tenant_id=%s "
                "AND project_id=%s AND task_id=%s AND tool_attempt_id=%s",
                (*tx.owner, permit.tool_attempt_id),
            )
            tx.connection.execute(
                "UPDATE vnext.tool_call SET status='unknown' WHERE tenant_id=%s "
                "AND project_id=%s AND task_id=%s AND tool_call_id=%s",
                (*tx.owner, permit.tool_call_id),
            )
            _settlement(tx, permit.identity.agent_run_id)
