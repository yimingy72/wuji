"""Durable attempt receipts, cumulative counters, and bounded response chunks."""

from dataclasses import dataclass
from hmac import compare_digest

from wuji_core.contracts.admission import ModelAttemptReceipt, ToolCallReceipt
from wuji_core.http import strict_json_loads
from wuji_core.persistence.uow import DomainError, row, json_text
from wuji_core.admission.common import allocate_output, audit


@dataclass(frozen=True)
class LedgerSnapshot:
    task_id: str
    model_attempts: int = 0
    tool_attempts: int = 0
    output_bytes: int = 0
    received_bytes: int = 0
    retained_bytes: int = 0
    forwarded_bytes: int = 0


def model_receipt(record):
    return ModelAttemptReceipt.model_validate({
        **{k: record[k] for k in ("model_attempt_id", "input_digest", "logical_request_id", "send_state", "response_state", "billing_state", "local_state", "inflight", "upstream_status", "response_available", "gateway_usage_ref", "gateway_spend_ref")},
        "grouping_state": "known", "admission_state": "admitted",
        **{k: str(record[k]) for k in ("received_bytes", "retained_bytes", "forwarded_bytes", "output_bytes")},
    })


def tool_receipt(tx, call):
    attempt = None
    if call["latest_attempt_id"]:
        attempt = row(tx.connection.execute("SELECT * FROM vnext.tool_attempt WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s", (*tx.owner, call["latest_attempt_id"])))
    if attempt and attempt["result_receipt_json"]:
        result = strict_json_loads(attempt["result_receipt_json"])
        result["status"] = call["status"]
        return ToolCallReceipt.model_validate(result)
    reason = "OPERATION_UNKNOWN" if call["status"] == "unknown" else None
    if attempt and attempt.get("limit_reason") == "LIMIT_BLOCKED":
        reason = "LIMIT_BLOCKED"
    return ToolCallReceipt.model_validate({"tool_call_id": call["tool_call_id"], "operation_id": call["tool_call_id"], "tool_attempt_id": call["latest_attempt_id"], "status": call["status"], "evidence_receipt": None, "result_ref": None, "reason_code": reason})


class AdmissionLedger:
    def __init__(self, uow):
        self.uow = uow

    def snapshot(self, access, task_id):
        with self.uow.transaction(access, task_id) as tx:
            item = row(tx.connection.execute("SELECT * FROM vnext.admission_counter WHERE tenant_id=%s AND project_id=%s AND task_id=%s", tx.owner))
            if item is None:
                return LedgerSnapshot(task_id)
            return LedgerSnapshot(task_id, **{k: int(item[k]) for k in ("model_attempts", "tool_attempts", "output_bytes", "received_bytes", "retained_bytes", "forwarded_bytes")})

    def model_attempt(self, access, model_attempt_id):
        task_id = self.uow.locate_model_attempt(access, model_attempt_id)
        with self.uow.transaction(access, task_id) as tx:
            record = self.model_row(tx, model_attempt_id)
            return model_receipt(record)

    def reconcile_not_sent(self, access, model_attempt_id):
        """End a durably admitted attempt that never crossed the send fence."""
        task_id = self.uow.locate_model_attempt(access, model_attempt_id)
        with self.uow.transaction(access, task_id, capability="model_settle") as tx:
            record = self.model_row(tx, model_attempt_id)
            binding = tx.run_binding
            if (
                record["agent_run_id"] != binding.identity.agent_run_id
                or record["subject"] != access.principal.subject
                or record["token_id"] != access.principal.token_id
            ):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            if record["send_state"] != "not_sent" or not record["inflight"]:
                return model_receipt(record)
            settlement = {
                "source": "trusted_not_sent_reconcile",
                "reason": "admission_committed_before_send",
                "model_attempt_id": model_attempt_id,
                "local_ended": True,
            }
            updated = tx.connection.execute(
                "UPDATE vnext.model_call SET local_state='ended',inflight=false,response_state='unknown',response_available=false,settlement_json=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND model_attempt_id=%s AND send_state='not_sent' AND local_state='inflight' AND inflight RETURNING model_attempt_id",
                (json_text(settlement), *tx.owner, model_attempt_id),
            ).fetchone()
            if updated:
                audit(
                    tx,
                    "model.not_sent_reconciled",
                    {"model_attempt_id": model_attempt_id},
                )
            return model_receipt(self.model_row(tx, model_attempt_id))

    def model_row(self, tx, attempt_id):
        record = row(tx.connection.execute("SELECT * FROM vnext.model_call WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND model_attempt_id=%s", (*tx.owner, attempt_id)))
        if not record:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        return record

    def _permit_row(self, tx, permit):
        record = self.model_row(tx, permit.model_attempt_id)
        if record["agent_run_id"] != permit.identity.agent_run_id or record["subject"] != tx.access.principal.subject or record["token_id"] != tx.access.principal.token_id or not compare_digest(record["settlement_token"], permit.settlement_token):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        return record

    def tool_call(self, access, tool_call_id):
        # Run reads are located from their registered Task, not a client Task ID.
        binding = self.uow.locate_run_credential(access)
        with self.uow.transaction(access, binding.identity.task_id) as tx:
            call = row(tx.connection.execute("SELECT * FROM vnext.tool_call WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_call_id=%s AND access_level<=%s", (*tx.owner, tool_call_id, tx.permissions["clearance"])))
            if not call:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            return tool_receipt(tx, call)

    def response_started(self, access, permit, *, status, content_type, usage_ref=None, spend_ref=None):
        with self.uow.transaction(access, permit.identity.task_id, capability="model_settle") as tx:
            self._permit_row(tx, permit)
            tx.connection.execute("UPDATE vnext.model_call SET send_state='sent',upstream_status=%s,content_type=%s,gateway_usage_ref=%s,gateway_spend_ref=%s,billing_state=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND model_attempt_id=%s", (status, content_type, usage_ref, spend_ref, "reported" if usage_ref or spend_ref else "pending", *tx.owner, permit.model_attempt_id))

    def retain(self, access, permit, data):
        with self.uow.transaction(access, permit.identity.task_id, capability="model_settle") as tx:
            record = self._permit_row(tx, permit)
            if not record["inflight"]:
                raise DomainError("STALE_EXECUTION", 409)
            accepted = allocate_output(tx, len(data), already=record["output_bytes"], runtime=permit.config.runtime)
            tx.connection.execute("UPDATE vnext.model_call SET received_bytes=received_bytes+%s,retained_bytes=retained_bytes+%s,output_bytes=output_bytes+%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND model_attempt_id=%s", (len(data), len(data) if accepted else 0, len(data) if accepted else 0, *tx.owner, permit.model_attempt_id))
            if accepted:
                tx.connection.execute("INSERT INTO vnext.model_response_chunk(tenant_id,project_id,task_id,model_attempt_id,ordinal,data,access_level) SELECT %s,%s,%s,%s,COALESCE(MAX(ordinal),-1)+1,%s,%s FROM vnext.model_response_chunk WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND model_attempt_id=%s", (*tx.owner, permit.model_attempt_id, data, record["access_level"], *tx.owner, permit.model_attempt_id))
            return accepted

    def forwarded(self, access, permit, size):
        with self.uow.transaction(access, permit.identity.task_id, capability="model_settle") as tx:
            self._permit_row(tx, permit)
            tx.connection.execute("UPDATE vnext.model_call SET forwarded_bytes=forwarded_bytes+%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND model_attempt_id=%s", (size, *tx.owner, permit.model_attempt_id))
            tx.connection.execute("UPDATE vnext.admission_counter SET forwarded_bytes=forwarded_bytes+%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s", (size, *tx.owner))

    def settle_local(self, access, permit, *, response_state, local_ended, reason):
        # This port is invoked by the Gate's actual transport finalizer, never an HTTP DTO.
        with self.uow.transaction(access, permit.identity.task_id, capability="model_settle") as tx:
            record = self._permit_row(tx, permit)
            if record["local_state"] == "ended":
                return model_receipt(record)
            settlement = {"source": "gate_transport_finalizer", "reason": reason, "model_attempt_id": permit.model_attempt_id, "local_ended": local_ended}
            tx.connection.execute("UPDATE vnext.model_call SET local_state=%s,inflight=%s,response_state=%s,response_available=%s,settlement_json=%s,send_state=CASE WHEN send_state='sending' THEN 'unknown' ELSE send_state END WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND model_attempt_id=%s", ("ended" if local_ended else "unknown", not local_ended, response_state, response_state == "complete" and record["upstream_status"] == 200, json_text(settlement), *tx.owner, permit.model_attempt_id))
            audit(tx, "model.local_settlement", {"model_attempt_id": permit.model_attempt_id, "response_state": response_state, "local_state": "ended" if local_ended else "unknown"})
            return model_receipt(self.model_row(tx, permit.model_attempt_id))

    def response_chunks(self, access, permit):
        ordinal = -1
        while True:
            with self.uow.transaction(access, permit.identity.task_id) as tx:
                self._permit_row(tx, permit)
                item = tx.connection.execute("SELECT ordinal,data FROM vnext.model_response_chunk WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND model_attempt_id=%s AND ordinal>%s ORDER BY ordinal LIMIT 1", (*tx.owner, permit.model_attempt_id, ordinal)).fetchone()
            if not item:
                return
            ordinal, data = item
            yield bytes(data)

    def rejected(self, access, task_id, purpose, code):
        try:
            with self.uow.transaction(access, task_id, capability=purpose.replace("_request", "_settle")) as tx:
                audit(tx, "request.rejected", {"purpose": purpose, "code": code})
        except DomainError:
            # No scoped access means no disclosure or manufactured Task audit row.
            pass
