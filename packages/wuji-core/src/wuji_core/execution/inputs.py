"""Trusted native intake and durable input delivery, without process authority."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from psycopg import sql

from wuji_core.admission.common import current_run, digest
from wuji_core.contracts.envelopes import WorkerAssignment
from wuji_core.contracts.sessions import (
    DeliveryReceipt, HumanInput, InputPayload, InputReceipt, NativeApprovalObservation,
)
from wuji_core.contracts import generated as wire
from wuji_core.execution.sessions import document, equal, row, rows, work_row
from wuji_core.http import strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text


def locate(uow, access, table, column, identifier):
    if (table, column) not in {("approval_request", "approval_ref"), ("input_request", "input_request_id")}:
        raise ValueError("unsupported internal locator")
    with uow.connection_factory() as connection:
        with connection.transaction():
            for key, value in {"tenant": access.principal.tenant_id, "subject": access.principal.subject,
                    "task": "", "project": "", "clearance": "-1"}.items():
                connection.execute("SELECT set_config(%s,%s,true)", ("wuji." + key, value)).fetchone()
            item = connection.execute(sql.SQL("SELECT task_id FROM vnext.{} WHERE {}=%s").format(
                sql.Identifier(table), sql.Identifier(column)), (identifier,)).fetchone()
            if not item:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            return item[0]


def current_input(tx, work):
    result = row(tx.connection.execute(
        "SELECT * FROM vnext.input_request WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND input_request_id=%s AND work_item_id=%s",
        (*tx.owner, work["input_request_id"], work["work_item_id"]),
    ))
    if not result:
        raise DomainError("INVALID_WAIT", 409)
    return result


def save_delivery(tx, input_row, manifest_ref, payload):
    payload = InputPayload.model_validate(payload)
    raw = json_text(document(payload))
    old = row(tx.connection.execute(
        "SELECT * FROM vnext.input_delivery WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND input_request_id=%s",
        (*tx.owner, input_row["input_request_id"]),
    ))
    if old:
        if old["payload_digest"] != digest(document(payload)) or old["manifest_ref"] != manifest_ref:
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        return old["delivery_id"]
    delivery_id = str(uuid4())
    tx.connection.execute(
        "INSERT INTO vnext.input_delivery(tenant_id,project_id,task_id,delivery_id,input_request_id,manifest_ref,payload_json,payload_digest,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (*tx.owner, delivery_id, input_row["input_request_id"], manifest_ref, raw, digest(document(payload)), input_row["access_level"]),
    )
    changed = tx.connection.execute(
        "UPDATE vnext.input_request SET status='resolved' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND input_request_id=%s AND status='pending' RETURNING input_request_id",
        (*tx.owner, input_row["input_request_id"]),
    ).fetchone()
    if not changed:
        raise DomainError("STALE_EXECUTION", 409)
    tx.semantic_event("input.resolved", {"input_request_id": input_row["input_request_id"],
        "work_item_id": input_row["work_item_id"], "delivery_id": delivery_id}, access_level=input_row["access_level"])
    return delivery_id


class InputService:
    def __init__(self, uow, *, sessions, registry):
        self.uow, self.sessions, self.registry = uow, sessions, registry

    def list_pending(self, access, task_id):
        with self.uow.transaction(access, task_id) as tx:
            items = []
            for value in rows(tx.connection.execute(
                "SELECT * FROM vnext.input_request WHERE tenant_id=%s AND project_id=%s "
                "AND task_id=%s AND status='pending' ORDER BY input_request_id LIMIT 256",
                tx.owner,
            )):
                wait = strict_json_loads(value["wait_ref_json"])
                kind = wait.get("kind")
                if kind == "question":
                    question = tx.connection.execute(
                        "SELECT question_text FROM vnext.human_question WHERE tenant_id=%s AND project_id=%s "
                        "AND task_id=%s AND question_ref=%s AND work_item_id=%s",
                        (*tx.owner, wait.get("question_ref"), value["work_item_id"]),
                    ).fetchone()
                    if question is None:
                        raise DomainError("INVALID_REFERENCE", 422)
                    prompt = question[0]
                elif kind == "native_approval":
                    kind, prompt = "approval", "该工作有一个受控工具调用等待审批"
                else:
                    raise DomainError("INVALID_REFERENCE", 422)
                items.append({
                    "input_request_id": value["input_request_id"],
                    "work_item_id": value["work_item_id"],
                    "kind": kind,
                    "status": value["status"],
                    "prompt": prompt,
                    "manifest_ref": value["source_receipt_json"]
                    and strict_json_loads(value["source_receipt_json"])["manifest_ref"],
                })
        return wire.TaskInputListV1.model_validate({
            "schema_version": "wuji.task-inputs.v1", "task_id": task_id,
            "items": items,
        })

    def register_native(self, access, assignment, observation):
        assignment = WorkerAssignment.model_validate(assignment)
        observation = NativeApprovalObservation.model_validate(observation)
        with self.uow.transaction(access, assignment.identity.task_id, capability="observe") as tx:
            run = self.sessions.receiver(tx, assignment)
            work = work_row(tx, assignment.identity.work_item_id)
            published = self.sessions._load_in_transaction(tx, work)
            if (published.receipt.manifest_ref != observation.manifest_ref
                    or published.manifest.owner_run_id != run["agent_run_id"]
                    or published.manifest.recovery_class.value != "approval_boundary"
                    or not equal(published.provider_state.pending_contents, observation.contents)
                    or not equal(published.provider_state.call_bindings, observation.call_bindings)):
                raise DomainError("INVALID_REFERENCE", 422)
            native_digest = digest(list(observation.contents))
            old = row(tx.connection.execute(
                "SELECT * FROM vnext.input_source WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND manifest_ref=%s AND native_digest=%s",
                (*tx.owner, observation.manifest_ref, native_digest),
            ))
            if old:
                return InputReceipt.model_validate(strict_json_loads(old["receipt_json"]))
            self.sessions._current_writer(tx, work, run)
            self.sessions.require_current_root_writer(tx, published.manifest)
            self.sessions._frontier(
                tx,
                published.history,
                published.provider_state,
                published.memory,
                allow_pending=True,
            )
            if work["input_request_id"]:
                prior = current_input(tx, work)
                if prior["status"] == "pending":
                    raise DomainError("INVALID_WAIT", 409)
            capability = self.sessions.capability(tx, published.history)
            definition = strict_json_loads(tx.task["definition_json"])
            now = tx.connection.execute("SELECT clock_timestamp()").fetchone()[0]
            expires = min(now + timedelta(seconds=capability["approval_ttl_seconds"]),
                datetime.fromisoformat(definition["task"]["authorization_expires_at"].replace("Z", "+00:00")))
            source_id, input_id = str(uuid4()), str(uuid4())
            source = {"source_receipt_id": source_id, "kind": "native_approval", "manifest_ref": observation.manifest_ref,
                "native_digest": native_digest, "receiver_subject": access.principal.subject,
                "owner_run_id": run["agent_run_id"], "received_at": now.isoformat(),
                "worker_observed_at": observation.observed_at.isoformat() if observation.observed_at else None}
            level = max(self.sessions.artifacts.record(tx, ref)["access_level"] for ref in (
                published.manifest.history_root, published.manifest.provider_state_ref, published.manifest.memory_manifest_ref))
            tx.connection.execute(
                "INSERT INTO vnext.input_request(tenant_id,project_id,task_id,input_request_id,work_item_id,wait_ref_json,status,session_id,session_revision,source_receipt_json,access_level) VALUES(%s,%s,%s,%s,%s,%s,'pending',%s,%s,%s,%s)",
                (*tx.owner, input_id, work["work_item_id"], json_text({"kind": "native_approval", "source_receipt_id": source_id}),
                 published.manifest.session_id, published.manifest.checkpoint_revision.root, json_text(source), level),
            )
            pending = {b.sdk_approval_id: b for b in published.history.frontier.pending_approvals}
            approval_refs = []
            for content in observation.contents:
                binding = pending[content["id"]]
                ref = str(uuid4())
                approval_refs.append(ref)
                tool = self.registry.tool(tx, binding.tool_definition_ref)
                if not tool.approval_required:
                    raise DomainError("INVALID_REFERENCE", 422)
                tx.connection.execute(
                    "INSERT INTO vnext.approval_request(tenant_id,project_id,task_id,approval_ref,input_request_id,work_item_id,session_id,session_revision,manifest_ref,tool_call_id,content_json,binding_json,parameters_digest,tool_digest,scope_json,scope_digest,profile_digest,qualifications_json,expires_at,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (*tx.owner, ref, input_id, work["work_item_id"], published.manifest.session_id, published.manifest.checkpoint_revision.root,
                     observation.manifest_ref, binding.tool_call_id, json_text(content), json_text(document(binding)), binding.arguments_digest,
                     digest(tool.model_dump(mode="json")), json_text(definition["task"]["authorization_scope"]),
                     digest(definition["task"]["authorization_scope"]),
                     published.history.compatibility.profile_snapshot["digest"], json_text(list(capability["approver_subjects"])), expires, level),
                )
            receipt = InputReceipt(input_request_id=input_id, work_item_id=work["work_item_id"], manifest_ref=observation.manifest_ref,
                status="pending", approval_refs=tuple(approval_refs), source_receipt_id=source_id)
            tx.connection.execute(
                "INSERT INTO vnext.input_source(tenant_id,project_id,task_id,source_receipt_id,input_request_id,manifest_ref,native_digest,source_json,receipt_json,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (*tx.owner, source_id, input_id, observation.manifest_ref, native_digest, json_text(source), json_text(document(receipt)), level),
            )
            tx.connection.execute("UPDATE vnext.work_item SET input_request_id=%s,revision=revision+1 WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s", (input_id, *tx.owner, work["work_item_id"]))
            tx.connection.execute(
                "SELECT vnext.settle_session_input_boundary(%s,%s,%s,%s,%s,%s)",
                (
                    *tx.owner,
                    run["agent_run_id"],
                    input_id,
                    observation.manifest_ref,
                ),
            ).fetchone()
            tx.semantic_event("input.registered", {"input_request_id": input_id, "work_item_id": work["work_item_id"], "source_receipt_id": source_id}, access_level=level)
            return receipt

    def record_question(self, access, task_id, work_item_id, *, question, manifest_ref, idempotency_key):
        """Human/controller registration; no model payload or question UUID grants authority."""
        if not isinstance(question, str) or not 1 <= len(question) <= 32768 or not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        with self.uow.transaction(access, task_id, capability="control") as tx:
            work = work_row(tx, work_item_id)
            published = self.sessions._load_in_transaction(tx, work)
            if published.receipt.manifest_ref != manifest_ref or published.manifest.recovery_class.value != "settled_boundary":
                raise DomainError("INVALID_REFERENCE", 422)
            old = row(tx.connection.execute("SELECT * FROM vnext.human_question WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND idempotency_key=%s", (*tx.owner, idempotency_key)))
            content_digest = digest({"question": question, "work_item_id": work_item_id, "manifest_ref": manifest_ref})
            if old:
                if old["input_digest"] != content_digest:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                return old["question_ref"]
            question_ref = str(uuid4())
            tx.connection.execute("INSERT INTO vnext.human_question(tenant_id,project_id,task_id,question_ref,work_item_id,manifest_ref,question_text,subject,idempotency_key,input_digest,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (*tx.owner, question_ref, work_item_id, manifest_ref, question, access.principal.subject, idempotency_key, content_digest, tx.permissions["clearance"]))
            return question_ref

    def register_question(self, access, assignment, *, question_ref, manifest_ref):
        assignment = WorkerAssignment.model_validate(assignment)
        with self.uow.transaction(access, assignment.identity.task_id, capability="observe") as tx:
            run = self.sessions.receiver(tx, assignment)
            work = work_row(tx, assignment.identity.work_item_id)
            published = self.sessions._load_in_transaction(tx, work)
            question = row(tx.connection.execute("SELECT * FROM vnext.human_question WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND question_ref=%s AND work_item_id=%s AND manifest_ref=%s", (*tx.owner, question_ref, work["work_item_id"], manifest_ref)))
            if not question or published.receipt.manifest_ref != manifest_ref or published.manifest.recovery_class.value != "settled_boundary":
                raise DomainError("INVALID_REFERENCE", 422)
            old = row(tx.connection.execute("SELECT * FROM vnext.input_source WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND manifest_ref=%s AND native_digest=%s", (*tx.owner, manifest_ref, question["input_digest"])))
            if old:
                return InputReceipt.model_validate(strict_json_loads(old["receipt_json"]))
            self.sessions._current_writer(tx, work, run)
            self.sessions.require_current_root_writer(tx, published.manifest)
            if work["input_request_id"] and current_input(tx, work)["status"] == "pending":
                raise DomainError("INVALID_WAIT", 409)
            source_id, input_id = str(uuid4()), str(uuid4())
            source = {"source_receipt_id": source_id, "kind": "question", "question_ref": question_ref,
                "manifest_ref": manifest_ref, "received_at": tx.connection.execute("SELECT clock_timestamp()").fetchone()[0].isoformat()}
            receipt = InputReceipt(input_request_id=input_id, work_item_id=work["work_item_id"], manifest_ref=manifest_ref,
                status="pending", approval_refs=(), source_receipt_id=source_id)
            tx.connection.execute("INSERT INTO vnext.input_request(tenant_id,project_id,task_id,input_request_id,work_item_id,wait_ref_json,status,session_id,session_revision,source_receipt_json,access_level) VALUES(%s,%s,%s,%s,%s,%s,'pending',%s,%s,%s,%s)",
                (*tx.owner, input_id, work["work_item_id"], json_text({"kind": "question", "question_ref": question_ref}), published.manifest.session_id, published.manifest.checkpoint_revision.root, json_text(source), question["access_level"]))
            tx.connection.execute("INSERT INTO vnext.input_source(tenant_id,project_id,task_id,source_receipt_id,input_request_id,manifest_ref,native_digest,source_json,receipt_json,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (*tx.owner, source_id, input_id, manifest_ref, question["input_digest"], json_text(source), json_text(document(receipt)), question["access_level"]))
            tx.connection.execute("UPDATE vnext.work_item SET input_request_id=%s,revision=revision+1 WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s", (input_id, *tx.owner, work["work_item_id"]))
            tx.semantic_event("input.registered", {"input_request_id": input_id, "work_item_id": work["work_item_id"]}, access_level=question["access_level"])
            return receipt

    def answer_question(self, access, input_request_id, *, text, idempotency_key):
        payload = InputPayload(kind="question", text=text)
        task_id = locate(self.uow, access, "input_request", "input_request_id", input_request_id)
        with self.uow.transaction(access, task_id, capability="control") as tx:
            value = row(tx.connection.execute("SELECT * FROM vnext.input_request WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND input_request_id=%s", (*tx.owner, input_request_id)))
            if not value or strict_json_loads(value["wait_ref_json"]).get("kind") != "question":
                raise DomainError("INVALID_REFERENCE", 422)
            work = work_row(tx, value["work_item_id"])
            if value["status"] == "revoked" or work["desired_state"] == "cancel" or tx.task["desired_state"] in {"cancel", "finish"}:
                raise DomainError("STALE_EXECUTION", 409)
            published = self.sessions._load_in_transaction(tx, work)
            if work["input_request_id"] != input_request_id or str(value["session_revision"]) != published.manifest.checkpoint_revision.root:
                raise DomainError("STALE_EXECUTION", 409)
            old = tx.connection.execute("SELECT idempotency_key,payload_digest FROM vnext.input_answer WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND input_request_id=%s", (*tx.owner, input_request_id)).fetchone()
            if old and old != (idempotency_key, digest(document(payload))):
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            if not old:
                if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 256:
                    raise DomainError("INVALID_SCHEMA", 422)
                tx.connection.execute("INSERT INTO vnext.input_answer(tenant_id,project_id,task_id,input_request_id,idempotency_key,payload_digest) VALUES(%s,%s,%s,%s,%s,%s)", (*tx.owner, input_request_id, idempotency_key, digest(document(payload))))
            return save_delivery(tx, value, published.receipt.manifest_ref, payload)

    def _delivery(self, tx, assignment, delivery_id):
        if tx.run_binding is None or tx.run_binding.identity != assignment.identity:
            raise DomainError("STALE_EXECUTION", 409)
        current_run(tx, self.registry.config(tx))
        value = row(tx.connection.execute("SELECT d.*,i.status AS input_status,i.work_item_id,i.session_id AS input_session_id,i.session_revision AS input_session_revision FROM vnext.input_delivery d JOIN vnext.input_request i USING(tenant_id,project_id,task_id,input_request_id) WHERE d.tenant_id=%s AND d.project_id=%s AND d.task_id=%s AND d.delivery_id=%s AND d.access_level<=%s", (*tx.owner, delivery_id, tx.permissions["clearance"])))
        work = work_row(tx, assignment.identity.work_item_id)
        if (value is None or value["work_item_id"] != assignment.identity.work_item_id or value["input_status"] != "resolved"
                or assignment.session_manifest_ref is None or assignment.session_manifest_ref.root != value["manifest_ref"]):
            raise DomainError("INVALID_REFERENCE", 422)
        if (
            work["input_request_id"] != value["input_request_id"]
            or work["session_id"] != value["input_session_id"]
            or str(work["session_revision"]) != str(value["input_session_revision"])
        ):
            raise DomainError("STALE_EXECUTION", 409)
        holder = tx.connection.execute("SELECT 1 FROM vnext.session_holder WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND manifest_ref=%s AND session_lineage=%s", (*tx.owner, assignment.identity.agent_run_id, value["manifest_ref"], tx.run_binding.session_lineage)).fetchone()
        if holder is None:
            raise DomainError("STALE_EXECUTION", 409)
        return value

    def load_delivery(self, access, assignment, *, delivery_id):
        assignment = WorkerAssignment.model_validate(assignment)
        with self.uow.transaction(access, assignment.identity.task_id, capability="tool_request") as tx:
            value = self._delivery(tx, assignment, delivery_id)
            payload = InputPayload.model_validate(strict_json_loads(value["payload_json"]))
            if digest(document(payload)) != value["payload_digest"]:
                raise DomainError("INVALID_REFERENCE", 422)
            for decision in payload.decisions:
                if decision.decision == "reject":
                    # This closes a never-executed proposal through the existing
                    # tool_request authority. It does not invoke a function or
                    # manufacture a result; MAF produces its native denial.
                    tx.connection.execute(
                        "UPDATE vnext.tool_call c SET status='cancelled' WHERE c.tenant_id=%s AND c.project_id=%s AND c.task_id=%s AND c.tool_call_id=%s AND c.status='pending_approval' AND c.latest_attempt_id IS NULL AND EXISTS(SELECT 1 FROM vnext.approval_request a WHERE (a.tenant_id,a.project_id,a.task_id,a.tool_call_id)=(c.tenant_id,c.project_id,c.task_id,c.tool_call_id) AND a.approval_ref=%s AND a.decision='reject' AND a.decision_status='decided' AND a.input_request_id=%s)",
                        (*tx.owner, decision.call_binding.tool_call_id, decision.approval_ref, value["input_request_id"]),
                    )
            return HumanInput(delivery_id=value["delivery_id"], input_request_id=value["input_request_id"],
                manifest_ref=value["manifest_ref"], payload_digest=value["payload_digest"], payload=payload)

    def acknowledge_delivery(self, access, assignment, *, delivery_id, payload_digest):
        assignment = WorkerAssignment.model_validate(assignment)
        with self.uow.transaction(access, assignment.identity.task_id, capability="tool_request") as tx:
            value = self._delivery(tx, assignment, delivery_id)
            if value["payload_digest"] != payload_digest:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            if value["status"] == "pending":
                tx.connection.execute("UPDATE vnext.input_delivery SET status='delivered',receiving_run_id=%s,delivered_at=clock_timestamp() WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND delivery_id=%s AND status='pending'", (assignment.identity.agent_run_id, *tx.owner, delivery_id))
            return DeliveryReceipt(delivery_id=delivery_id, input_request_id=value["input_request_id"], status="delivered",
                payload_digest=payload_digest, receiving_run_id=value["receiving_run_id"] or assignment.identity.agent_run_id)
