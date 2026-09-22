"""Human decisions and one-transaction consumption by the existing ToolAdmission."""

from datetime import datetime, timezone
from uuid import uuid4

from wuji_core.admission.common import current_run, digest
from wuji_core.contracts.execution import ApprovalDecision, CommandReceipt
from wuji_core.contracts.sessions import (
    ApprovalBinding, ApprovalDeliveryDecision, ApprovalReceipt, InputPayload,
    NativeCallBinding, PublishedNativeSessionV2,
)
from wuji_core.execution.inputs import current_input, locate, save_delivery
from wuji_core.execution.sessions import document, equal, row, rows, work_row
from wuji_core.http import strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text


class ApprovalService:
    def __init__(self, uow, *, sessions, registry):
        self.uow, self.sessions, self.registry = uow, sessions, registry

    def _row(self, tx, approval_ref, *, lock=False):
        value = row(tx.connection.execute(
            "SELECT * FROM vnext.approval_request WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND approval_ref=%s AND access_level<=%s"
            + (" FOR UPDATE" if lock else ""), (*tx.owner, approval_ref, tx.permissions["clearance"]),
        ))
        if not value:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        return value

    def _current(self, tx, value, work):
        definition = strict_json_loads(tx.task["definition_json"])
        if (work["desired_state"] == "cancel" or work["state"] in {"done", "failed", "cancelled"}
                or tx.task["desired_state"] in {"cancel", "finish"} or tx.task["observed_state"] == "closed"
                or value["expires_at"] <= datetime.now(timezone.utc)
                or digest(definition["task"]["authorization_scope"]) != value["scope_digest"]
                or datetime.fromisoformat(definition["task"]["authorization_expires_at"].replace("Z", "+00:00")) <= datetime.now(timezone.utc)
                or work["session_id"] != value["session_id"] or work["session_revision"] != value["session_revision"]
                or work["input_request_id"] != value["input_request_id"]):
            raise DomainError("STALE_EXECUTION", 409)
        waiting = current_input(tx, work)
        if waiting["status"] == "revoked" or tx.connection.execute(
            "SELECT 1 FROM vnext.work_suspension WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s AND cause_kind='scope_revoked'",
            (*tx.owner, work["work_item_id"]),
        ).fetchone():
            raise DomainError("STALE_EXECUTION", 409)
        published = self.sessions._load_in_transaction(tx, work)
        native_v2 = isinstance(published, PublishedNativeSessionV2)
        profile_digest = (
            published.dependencies.compatibility.profile_snapshot["digest"]
            if native_v2
            else published.history.compatibility.profile_snapshot["digest"]
        )
        if (published.receipt.manifest_ref != value["manifest_ref"]
                or profile_digest != value["profile_digest"]):
            raise DomainError("STALE_EXECUTION", 409)
        binding = NativeCallBinding.model_validate(strict_json_loads(value["binding_json"]))
        definition = self.registry.tool(tx, binding.tool_definition_ref)
        if digest(definition.model_dump(mode="json")) != value["tool_digest"]:
            raise DomainError("STALE_EXECUTION", 409)
        if native_v2:
            state = strict_json_loads(
                published.object_bytes[
                    published.manifest.native_state_ref.id
                    + "@"
                    + published.manifest.native_state_ref.version.root
                ]
            )
            original = [
                NativeCallBinding.model_validate(item)
                for item in state["call_bindings"]
                if item.get("tool_call_id") == value["tool_call_id"]
            ]
        else:
            original = [b for b in published.history.frontier.pending_approvals if b.tool_call_id == value["tool_call_id"]]
        if len(original) != 1 or not equal(original[0], binding):
            raise DomainError("INVALID_REFERENCE", 422)
        return waiting, binding

    def decide(self, access, approval_id, decision, *, idempotency_key):
        decision = ApprovalDecision.model_validate(decision)
        if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        task_id = locate(self.uow, access, "approval_request", "approval_ref", approval_id)
        request_digest = digest({"approval_id": approval_id, "decision": decision.model_dump(mode="json")})

        def replay(tx):
            self._row(tx, approval_id)
            old = row(tx.connection.execute("SELECT * FROM vnext.approval_command WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND idempotency_key=%s", (*tx.owner, idempotency_key)))
            if old:
                if old["input_digest"] != request_digest or old["approval_ref"] != approval_id:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                return CommandReceipt.model_validate(strict_json_loads(old["receipt_json"]))

        with self.uow.transaction(access, task_id) as tx:
            old = replay(tx)
            if old is not None:
                return old
        with self.uow.transaction(access, task_id, capability="control") as tx:
            old = replay(tx)
            if old is not None:
                return old
            value = self._row(tx, approval_id)
            work = work_row(tx, value["work_item_id"])
            value = self._row(tx, approval_id, lock=True)
            waiting, _binding = self._current(tx, value, work)
            if access.principal.subject not in strict_json_loads(value["qualifications_json"]):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            if value["decision_status"] != "pending" or value["version"] != int(decision.expected_version.root):
                raise DomainError("STALE_VERSION", 409)
            version = value["version"] + 1
            changed = tx.connection.execute(
                "UPDATE vnext.approval_request SET decision=%s,decision_status='decided',version=%s,decided_by=%s,decided_at=clock_timestamp(),decision_reason=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND approval_ref=%s AND version=%s AND decision_status='pending' RETURNING approval_ref",
                (decision.decision.value, version, access.principal.subject, decision.reason, *tx.owner, approval_id, value["version"]),
            ).fetchone()
            if not changed:
                raise DomainError("STALE_VERSION", 409)
            group = rows(tx.connection.execute("SELECT * FROM vnext.approval_request WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND input_request_id=%s ORDER BY approval_ref", (*tx.owner, value["input_request_id"])))
            if all(item["decision_status"] != "pending" for item in group):
                source = tx.connection.execute("SELECT receipt_json FROM vnext.input_source WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND input_request_id=%s", (*tx.owner, value["input_request_id"])).fetchone()
                if source is None:
                    raise DomainError("INVALID_REFERENCE", 422)
                original_order = strict_json_loads(source[0])["approval_refs"]
                if set(original_order) != {item["approval_ref"] for item in group}:
                    raise DomainError("INVALID_REFERENCE", 422)
                group.sort(key=lambda item: original_order.index(item["approval_ref"]))
                payload = InputPayload(kind="approval", decisions=tuple(ApprovalDeliveryDecision(
                    approval_ref=item["approval_ref"], decision_version=str(item["version"]), decision=item["decision"],
                    pending_content=strict_json_loads(item["content_json"]),
                    call_binding=NativeCallBinding.model_validate(strict_json_loads(item["binding_json"])),
                ) for item in group))
                save_delivery(tx, waiting, value["manifest_ref"], payload)
            receipt = CommandReceipt.model_validate({"command_id": str(uuid4()), "disposition": "accepted",
                "resource_ref": {"entity_type": "approval", "id": approval_id, "revision": str(version)},
                "resource_version": str(version), "request_id": access.request_id, "code": None})
            tx.connection.execute("INSERT INTO vnext.approval_command(tenant_id,project_id,task_id,idempotency_key,approval_ref,input_digest,receipt_json,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (*tx.owner, idempotency_key, approval_id, request_digest, json_text(receipt.model_dump(mode="json")), value["access_level"]))
            tx.semantic_event("approval.decided", {"approval_ref": approval_id, "version": str(version),
                "work_item_id": work["work_item_id"], "decision": decision.decision.value}, access_level=value["access_level"])
            return receipt

    def read(self, access, approval_id):
        task_id = locate(self.uow, access, "approval_request", "approval_ref", approval_id)
        with self.uow.transaction(access, task_id) as tx:
            value = self._row(tx, approval_id)
            work = work_row(tx, value["work_item_id"], lock=False)
            reason = None
            try:
                self._current(tx, value, work)
                if tx.task["desired_state"] != "run" or work["desired_state"] != "run" or tx.connection.execute(
                    "SELECT 1 FROM vnext.work_suspension WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s", (*tx.owner, work["work_item_id"]),
                ).fetchone():
                    reason = "STALE_EXECUTION"
            except DomainError as error:
                reason = error.code
            return ApprovalReceipt(approval_ref=approval_id, version=str(value["version"]), decision=value["decision"],
                decision_status=value["decision_status"], execution_block_reason=reason,
                tool_call_id=value["tool_call_id"], tool_attempt_id=value["consumed_attempt_id"])

    def bind_operation_in_transaction(self, tx, prepared, approval_ref):
        approval_ref = getattr(approval_ref, "root", approval_ref)
        if tx.purpose != "tool_request" or tx.run_binding is None or not approval_ref:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        run, work = current_run(tx, self.registry.config(tx))
        value = self._row(tx, approval_ref, lock=True)
        waiting, binding = self._current(tx, value, work)
        if (prepared.run["agent_run_id"] != run["agent_run_id"] or prepared.call["work_item_id"] != work["work_item_id"]
                or waiting["status"] != "resolved" or value["decision"] != "approve"
                or value["tool_call_id"] != prepared.call["tool_call_id"]
                or value["decision_status"] not in {"decided", "consumed"}
                or value["parameters_digest"] != digest(prepared.request.arguments)
                or tx.run_binding.session_lineage != prepared.request.session_lineage):
            raise DomainError("STALE_EXECUTION", 409)
        if (binding.message_id != prepared.request.message_id or binding.provider_call_id != prepared.request.provider_call_id
                or binding.sdk_content_id != getattr(prepared.request.sdk_content_id, "root", prepared.request.sdk_content_id)
                or binding.sdk_approval_id != getattr(prepared.request.sdk_approval_id, "root", prepared.request.sdk_approval_id)
                or binding.tool_definition_ref != prepared.request.tool_definition_ref):
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        holder = tx.connection.execute("SELECT 1 FROM vnext.session_holder WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND manifest_ref=%s AND session_lineage=%s", (*tx.owner, run["agent_run_id"], value["manifest_ref"], tx.run_binding.session_lineage)).fetchone()
        if not holder:
            raise DomainError("STALE_EXECUTION", 409)
        if value["decision_status"] == "consumed":
            if prepared.call["latest_attempt_id"] != value["consumed_attempt_id"]:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            return ApprovalBinding(approval_ref=approval_ref, decision_version=str(value["version"]),
                tool_call_id=value["tool_call_id"], tool_attempt_id=value["consumed_attempt_id"], replay=True)
        if prepared.call["latest_attempt_id"] is not None or prepared.call["status"] != "pending_approval":
            raise DomainError("OPERATION_UNKNOWN", 409)
        tx.connection.execute("UPDATE vnext.tool_call SET status='admitted' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_call_id=%s AND status='pending_approval' AND latest_attempt_id IS NULL", (*tx.owner, value["tool_call_id"]))
        return ApprovalBinding(approval_ref=approval_ref, decision_version=str(value["version"]), tool_call_id=value["tool_call_id"])

    def finish_binding_in_transaction(self, tx, binding, permit):
        binding = ApprovalBinding.model_validate(binding)
        if tx.purpose != "tool_request" or tx.run_binding is None or permit.tool_call_id != binding.tool_call_id or permit.tool_attempt_id is None:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        value = self._row(tx, binding.approval_ref, lock=True)
        if value["decision_status"] == "consumed":
            if (
                value["consumed_attempt_id"] != permit.tool_attempt_id
                or binding.decision_version != str(value["version"])
                or value["decision"] != "approve"
            ):
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            return binding.model_copy(update={"tool_attempt_id": permit.tool_attempt_id, "replay": True})
        attempt = tx.connection.execute("SELECT 1 FROM vnext.tool_attempt WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s AND tool_call_id=%s AND agent_run_id=%s AND status='admitted'", (*tx.owner, permit.tool_attempt_id, binding.tool_call_id, tx.run_binding.identity.agent_run_id)).fetchone()
        if not attempt or permit.identity != tx.run_binding.identity:
            raise DomainError("INVALID_REFERENCE", 422)
        if binding.decision_version != str(value["version"]):
            raise DomainError("STALE_VERSION", 409)
        updated = tx.connection.execute("UPDATE vnext.approval_request SET decision_status='consumed',consumed_attempt_id=%s,consumed_by_run=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND approval_ref=%s AND version=%s AND decision_status='decided' AND decision='approve' RETURNING approval_ref", (permit.tool_attempt_id, permit.identity.agent_run_id, *tx.owner, binding.approval_ref, binding.decision_version)).fetchone()
        if not updated:
            raise DomainError("STALE_VERSION", 409)
        return binding.model_copy(update={"tool_attempt_id": permit.tool_attempt_id})
