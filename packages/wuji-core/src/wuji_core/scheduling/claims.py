"""Single-owner PostgreSQL Scheduler and atomic Work/Run/Outbox admission.

No network delivery, process spawn, Agent loop, credential fabrication or money
accounting is performed here. P10 consumes immutable assignment references.
"""

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

from wuji_core.admission.registry import AdmissionRegistry, RunCredentialBinding
from wuji_core.blackboard.relations import resolve
from wuji_core.contracts.envelopes import RunIdentity, WorkerAssignment
from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.execution.capacity import CapacityService
from wuji_core.execution.dependencies import dependencies_satisfied, intent_current
from wuji_core.execution.states import task_can_run
from wuji_core.http.json_boundary import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError, UnitOfWork, json_text, row
from wuji_core.persistence.snapshots import SnapshotQuery
from wuji_core.persistence.retained_result_schema import bind_receiver_result
from wuji_core.scheduling.policy import (
    Candidate,
    SchedulerPolicy,
    SchedulingSnapshot,
    WorkKey,
    problem_digest,
)
from wuji_core.scheduling.triggers import (
    TriggerRepository,
    block,
    require_admission,
    rows,
    state_row,
)
from wuji_core.scheduling.waiters import WaiterRepository
from wuji_core.scheduling.credentials import agent_subject, worker_subject


class SchedulerOwnership:
    """One dedicated session, without connection recovery or lease-expiry takeover."""

    LOCK = (1937006964, 9009)

    def __init__(self, connection):
        self.connection = connection
        self._pid = None
        self._closed = False

    def acquire(self):
        if self._closed or self.connection.closed:
            raise DomainError("scheduler_ownership_lost", 503)
        if self._pid is not None:
            with self.connection.transaction():
                self.assert_owned()
            return True
        with self.connection.transaction():
            privileged = self.connection.execute(
                """SELECT r.rolsuper OR r.rolbypassrls OR current_user=pg_get_userbyid(n.nspowner)
                FROM pg_roles r CROSS JOIN pg_namespace n WHERE r.rolname=current_user AND n.nspname='vnext'"""
            ).fetchone()
            if privileged != (False,):
                raise DomainError("scheduler_requires_application_role", 503)
            acquired, pid = self.connection.execute(
                "SELECT pg_try_advisory_lock(%s,%s),pg_backend_pid()",
                self.LOCK,
            ).fetchone()
        if acquired:
            self._pid = pid
        return acquired

    def assert_owned(self):
        if self._closed or self.connection.closed or self._pid is None:
            raise DomainError("scheduler_ownership_lost", 503)
        found = self.connection.execute(
            """SELECT pg_backend_pid()=%s AND EXISTS(SELECT 1 FROM pg_locks
            WHERE locktype='advisory' AND pid=pg_backend_pid() AND granted
            AND classid=%s AND objid=%s AND objsubid=2
            AND database=(SELECT oid FROM pg_database WHERE datname=current_database()))""",
            (self._pid, *self.LOCK),
        ).fetchone()
        if found != (True,):
            self._closed = True
            raise DomainError("scheduler_ownership_lost", 503)

    @contextmanager
    def borrow(self):
        if self.connection.closed or self._closed or self._pid is None:
            raise DomainError("scheduler_ownership_lost", 503)
        # Existing UnitOfWork owns transaction boundaries, not this borrowed
        # session. assert_owned runs inside that transaction at each entry.
        yield self.connection

    def close(self):
        if not self._closed and not self.connection.closed and self._pid is not None:
            with self.connection.transaction():
                self.connection.execute("SELECT pg_advisory_unlock(%s,%s)", self.LOCK)
        self._closed = True
        self._pid = None


class WorkRepository:
    def register(self, tx, *, key, kind, priority=0):
        require_admission(tx)
        if (
            not isinstance(key, WorkKey)
            or kind not in {"reason", "explore", "report"}
            or type(priority) is not int
            or not -10 <= priority <= 10
            or (kind == "explore" and key.intent_id is None)
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        content = json_text(asdict(key))
        existing = row(
            tx.connection.execute(
                """SELECT s.work_item_id,s.key_json,w.kind FROM vnext.scheduler_work s
            JOIN vnext.work_item w USING(tenant_id,project_id,task_id,work_item_id)
            WHERE s.tenant_id=%s AND s.project_id=%s AND s.task_id=%s AND
            (s.key_digest=%s OR (s.intent_id=%s AND s.intent_revision=%s))""",
                (*tx.owner, key.digest(), key.intent_id, key.intent_revision),
            )
        )
        if existing:
            if existing["key_json"] != content or existing["kind"] != kind:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            return existing["work_item_id"]
        config = AdmissionRegistry(None).config(tx)
        if tx.task["activated_at"] is None:
            raise DomainError("STALE_EXECUTION", 409)
        count = tx.connection.execute(
            "SELECT count(*) FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
            tx.owner,
        ).fetchone()[0]
        if count >= config.runtime.limits.max_work_items:
            raise DomainError("max_work_items", 429)
        for kind_ref, entity_id, revision in key.basis:
            resolve(
                tx,
                KnowledgeRef.model_validate(
                    {"entity_type": kind_ref, "id": entity_id, "revision": revision}
                ),
            )
        if key.intent_id is not None:
            intent = row(
                tx.connection.execute(
                    "SELECT * FROM vnext.intent_revision WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND entity_id=%s AND revision=%s",
                    (*tx.owner, key.intent_id, key.intent_revision),
                )
            )
            if not intent or intent["acceptance_state"] != "admitted":
                raise DomainError("INVALID_REFERENCE", 422)
            basis = tuple(
                (r["entity_type"], r["id"], r["revision"])
                for r in strict_json_loads(intent["basis_json"])
            )
            if basis != key.basis or intent["expected_output"] != key.output_contract:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            # Existing foreign producers are never silently replaced/duplicated.
            old = tx.connection.execute(
                "SELECT 1 FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND intent_id=%s AND intent_revision=%s LIMIT 1",
                (*tx.owner, key.intent_id, key.intent_revision),
            ).fetchone()
            if old:
                raise DomainError("work_identity_reconciliation_required", 409)
        work_id = str(uuid4())
        tx.connection.execute(
            "INSERT INTO vnext.work_item(tenant_id,project_id,task_id,work_item_id,kind,intent_id,intent_revision) VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (*tx.owner, work_id, kind, key.intent_id, key.intent_revision),
        )
        tx.connection.execute(
            "INSERT INTO vnext.scheduler_work(tenant_id,project_id,task_id,work_item_id,key_digest,key_json,intent_id,intent_revision,priority) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                *tx.owner,
                work_id,
                key.digest(),
                content,
                key.intent_id,
                key.intent_revision,
                priority,
            ),
        )
        return work_id

    def duplicate_problem(self, tx, *, digest):
        """The existing Work item that already asks this exact question, if any.

        The comparison is recomputed from what the platform stored — the frozen
        Intent question plus the recorded method, profile, basis, environment and
        output contract — so it can be verified from the rows alone.
        """

        for value in rows(
            tx.connection.execute(
                """SELECT s.work_item_id,s.key_json,i.question FROM vnext.scheduler_work s
            JOIN vnext.intent_revision i ON (i.tenant_id,i.project_id,i.task_id,i.entity_id,i.revision)=
            (s.tenant_id,s.project_id,s.task_id,s.intent_id,s.intent_revision)
            WHERE s.tenant_id=%s AND s.project_id=%s AND s.task_id=%s AND s.intent_id IS NOT NULL
            ORDER BY s.work_item_id""",
                tx.owner,
            )
        ):
            key = strict_json_loads(value["key_json"])
            if (
                problem_digest(
                    question=value["question"],
                    basis=tuple(tuple(item) for item in key["basis"]),
                    method_ref=key["method_ref"],
                    profile_digest=key["profile_digest"],
                    environment_ref=key["environment_ref"],
                    output_contract=key["output_contract"],
                )
                == digest
            ):
                return value["work_item_id"]
        return None


@dataclass(frozen=True)
class TickReceipt:
    assignments: tuple
    blocked: tuple[tuple[str, str, str], ...]
    selected: tuple


class DispatchRepository:
    def read(self, tx, *, operation_id):
        """P10 reads the original operation; lookup never creates another Run."""
        if (
            tx.purpose != "observe"
            or not tx.permissions.get("can_observe")
            or "agent" in tx.access.principal.roles
            or not tx.access.principal.roles.intersection({"controller", "reconciler"})
        ):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        record = row(
            tx.connection.execute(
                """SELECT d.* FROM vnext.scheduler_assignment d
            JOIN vnext.agent_run a USING(tenant_id,project_id,task_id,agent_run_id,work_item_id)
            JOIN vnext.scheduler_receiver r USING(tenant_id,project_id,task_id,runtime_attempt,receiver_id)
            WHERE d.tenant_id=%s AND d.project_id=%s AND d.task_id=%s AND d.operation_id=%s
            AND r.receiver_subject=%s""",
                (*tx.owner, operation_id, tx.access.principal.subject),
            )
        )
        if not record:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        body = strict_json_loads(record["assignment_json"])
        if (
            sha256(canonical_json_bytes(body)).hexdigest()
            != record["assignment_digest"]
        ):
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        return WorkerAssignment.model_validate(body), record["credential_ref"]


def _notification(tx, kind, payload):
    # Scheduling/transport notification is independent of knowledge revision.
    sequence = tx.connection.execute(
        "UPDATE vnext.task SET event_seq=event_seq+1 WHERE tenant_id=%s AND project_id=%s AND task_id=%s RETURNING event_seq",
        tx.owner,
    ).fetchone()[0]
    tx.connection.execute(
        "INSERT INTO vnext.outbox(tenant_id,project_id,task_id,event_seq,kind,payload_json,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s)",
        (*tx.owner, sequence, kind, json_text(payload), tx.permissions["clearance"]),
    )
    return sequence


class Scheduler:
    def __init__(
        self,
        uow,
        *,
        ownership,
        accesses,
        snapshots,
        registry,
        control,
        credential_issuer=None,
        policy=None,
        completion=None,
    ):
        if not isinstance(uow, UnitOfWork) or not isinstance(
            ownership, SchedulerOwnership
        ):
            raise ValueError(
                "existing UnitOfWork and a real SchedulerOwnership are required"
            )
        # Reuse the entire P05 UoW auth/lock implementation on a borrowed session.
        # The passed UoW's pool is never used for a Scheduler admission.
        self.uow = UnitOfWork(ownership.borrow)
        self.ownership, self.accesses = ownership, tuple(accesses)
        self.snapshots, self.registry, self.control = snapshots, registry, control
        self.credential_issuer = credential_issuer
        self.policy = policy or SchedulerPolicy()
        # P12's review is read inside the scheduler transaction that already holds
        # the Task lock, so "what was verified" is exactly what gets recorded.
        if completion is not None and not callable(
            getattr(completion, "review_in_transaction", None)
        ):
            raise ValueError("a real completion review port is required")
        self.completion = completion
        self.triggers = TriggerRepository(artifacts=control.artifacts)
        self.waiters, self.works = WaiterRepository(), WorkRepository()
        if len(
            {(a.principal.tenant_id, a.principal.subject) for a in self.accesses}
        ) != len(self.accesses):
            raise ValueError("duplicate scheduler service access")

    @contextmanager
    def _transaction(self, access, task_id):
        with self.uow.transaction(access, task_id, capability="admit") as tx:
            if tx.connection is not self.ownership.connection:
                raise DomainError("scheduler_ownership_lost", 503)
            self.ownership.assert_owned()
            require_admission(tx)
            yield tx
            self.ownership.assert_owned()

    def _tasks(self):
        located = {}
        for access in self.accesses:
            if (
                "agent" in access.principal.roles
                or not access.principal.roles.intersection({"scheduler", "controller"})
            ):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            with self.ownership.connection.transaction():
                self.ownership.assert_owned()
                for key, value in {
                    "tenant": access.principal.tenant_id,
                    "subject": access.principal.subject,
                    "token_id": access.principal.token_id,
                    "project": "",
                    "task": "",
                    "clearance": "-1",
                    "write": "false",
                    "admit": "false",
                    "request_purpose": "",
                }.items():
                    self.ownership.connection.execute(
                        "SELECT set_config(%s,%s,true)", ("wuji." + key, value)
                    )
                tasks = rows(
                    self.ownership.connection.execute(
                        "SELECT task_id FROM vnext.task_access WHERE tenant_id=%s AND subject=%s AND can_read AND can_admit ORDER BY task_id",
                        (access.principal.tenant_id, access.principal.subject),
                    )
                )
            for task in tasks:
                located.setdefault(
                    (access.principal.tenant_id, task["task_id"]), access
                )
        return located

    def _receiver(self, tx):
        value = row(
            tx.connection.execute(
                """SELECT r.*,t.clearance AS worker_clearance FROM vnext.scheduler_receiver r
            JOIN vnext.scheduler_identity_template t ON (t.tenant_id,t.project_id,t.task_id,t.template_ref)=
            (r.tenant_id,r.project_id,r.task_id,r.credential_template_ref)
            WHERE r.tenant_id=%s AND r.project_id=%s AND r.task_id=%s AND r.runtime_attempt=%s
            AND r.enabled AND t.enabled
            AND vnext.scheduler_receiver_authorized(
                r.tenant_id,r.project_id,r.task_id,r.runtime_attempt)""",
                (*tx.owner, tx.task["runtime_attempt"]),
            )
        )
        if not value:
            raise DomainError("receiver_unavailable", 503)
        return value

    def _profile(self, tx, kind, config, receiver):
        try:
            definition = strict_json_loads(tx.task["definition_json"])
            profile = definition["worker_profiles"][kind]
            published = strict_json_loads(receiver["harness_profiles_json"])[kind]
            body = profile["body"]
            session_profile = body.get("schema_version") == "wuji.harness.session.v1"
            if session_profile:
                self.registry.session_capability(tx, profile)
            disabled = {
                name: False
                for name in (
                    "todo",
                    "mode",
                    "file_memory",
                    "file_access",
                    "skills",
                    "shell",
                    "web_search",
                    "background_agents",
                    "outer_loop",
                    "auto_approval",
                    "compaction",
                    "restoration",
                    "mcp",
                )
            }
            if (
                canonical_json_bytes(profile) != canonical_json_bytes(published)
                or profile["digest"] != sha256(canonical_json_bytes(body)).hexdigest()
                or profile["ref"] != body["ref"]
                or profile["revision"] != body["revision"]
                or body["work_kind"] != kind
                or body["lock_digest"] != config.runtime.lock_digest
                or (not session_profile and body["capabilities"] != disabled)
                or not body["instructions"]
                or not body["tool_definition_refs"]
                or any(
                    type(body[n]) is not int or body[n] <= 0
                    for n in (
                        "max_context_records",
                        "max_context_bytes",
                        "max_output_tokens",
                    )
                )
            ):
                raise ValueError("published M1 profile differs")
            refs = tuple(body["tool_definition_refs"])
            if len(set(refs)) != len(refs) or not set(refs) <= (
                set(config.allowed_tool_refs) & set(config.runtime.allowed_tool_refs)
            ):
                raise ValueError("profile tool refs exceed frozen configuration")
            # A published target tool is handed to Explore only, and only for a
            # Task that was frozen as a real-model Task: the loopback mechanism
            # fixture must never gain a path to a real asset, and Reason/Report
            # keep material reads instead of target access. The tool's own
            # admission still re-checks the Task's frozen authorization scope
            # before any external action.
            mode = definition.get("evaluation_mode")
            names = set()
            for ref in refs:
                tool = self.registry.tool(tx, ref)
                executor = self.registry.executor(tx, tool.executor_ref)
                kinds = list(tool.allowed_target_kinds)
                if (
                    (tool.approval_required and not session_profile)
                    or kinds not in (["workspace_read"], ["http_target"])
                    or (kinds == ["http_target"] and (kind != "explore" or mode != "real_model"))
                    or tool.name in names
                    or ref not in executor.allowed_tool_refs
                    or executor.receiver_id != receiver["receiver_id"]
                    or executor.environment_ref != receiver["environment_ref"]
                ):
                    raise ValueError(
                        "published tool/executor does not match current receiver"
                    )
                names.add(tool.name)
            return profile
        except (KeyError, TypeError, ValueError) as error:
            if isinstance(error, DomainError):
                raise
            raise DomainError("worker_profile_unavailable", 503) from error

    def _consume_events(self, tx):
        if not task_can_run(tx.task):
            return
        self.triggers.start(tx)
        events = rows(
            tx.connection.execute(
                """SELECT o.event_seq,o.kind,o.payload_json FROM vnext.outbox o WHERE o.tenant_id=%s AND o.project_id=%s AND o.task_id=%s
            AND NOT EXISTS(SELECT 1 FROM vnext.scheduler_trigger t WHERE
            (t.tenant_id,t.project_id,t.task_id,t.event_seq)=(o.tenant_id,o.project_id,o.task_id,o.event_seq))
            ORDER BY o.event_seq LIMIT 256""",
                tx.owner,
            )
        )
        for event in events:
            if event["kind"] == "reason.completion_requested":
                self._completion_review(tx, event)
            if event["kind"] == "input.resolved":
                payload = strict_json_loads(event["payload_json"])
                waiting_work = row(tx.connection.execute("SELECT * FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s FOR UPDATE", (*tx.owner, payload["work_item_id"])))
                if waiting_work and waiting_work["input_request_id"] == payload["input_request_id"]:
                    self.control._restore(tx, waiting_work)
            self.triggers.record(tx, event_seq=event["event_seq"])
        self.waiters.scan(tx)

    def _completion_review(self, tx, event):
        """Answer one ``reason.completion_requested`` with one durable review.

        The Reason asked the platform to look; the platform never lets that
        request close the Task. The review is recomputed here, inside the same
        transaction that already holds the Task lock and consumed the request,
        so its basis is exactly the state it read, and it is emitted once per
        request event: a repeated delivery finds the trigger already recorded.
        """

        if self.completion is None:
            raise DomainError("completion_review_unavailable", 503)
        review = self.completion.review_in_transaction(tx)
        existing = tx.connection.execute(
            "SELECT 1 FROM vnext.outbox WHERE tenant_id=%s AND project_id=%s"
            " AND task_id=%s AND kind='completion.reviewed'"
            " AND payload_json::jsonb->>'request_event_seq'=%s",
            (*tx.owner, str(event["event_seq"])),
        ).fetchone()
        if existing:
            return
        review_id = str(uuid4())
        basis = {
            "request_event_seq": event["event_seq"],
            "work_item_id": strict_json_loads(event["payload_json"]).get("work_item_id"),
            "processing_generation": strict_json_loads(event["payload_json"]).get(
                "processing_generation"
            ),
            "control_version": str(tx.task["control_version"]),
            "board_revision": str(tx.task["board_revision"]),
        }
        document = {
            "schema_version": "wuji.completion-review.v1",
            "review_id": review_id,
            "decision": review.decision,
            "reasons": list(review.reasons),
            "coverage": asdict(review.coverage),
            "open_work": list(review.open_work),
            "unsettled_runs": list(review.unsettled_runs),
            "basis": basis,
        }
        document["review_digest"] = sha256(
            canonical_json_bytes(document)
        ).hexdigest()
        tx.semantic_event("completion.reviewed", document)

    def _deduplicated(self, tx, *, intent, work_item_id, digest):
        """Record that this Intent asks the same question as an existing Work."""

        existing = tx.connection.execute(
            """SELECT 1 FROM vnext.outbox WHERE tenant_id=%s AND project_id=%s AND task_id=%s
            AND kind='intent.deduplicated'
            AND payload_json::jsonb->>'problem_digest'=%s
            AND payload_json::jsonb#>>'{intent_ref,id}'=%s
            AND payload_json::jsonb#>>'{intent_ref,revision}'=%s LIMIT 1""",
            (*tx.owner, digest, intent["entity_id"], str(intent["revision"])),
        ).fetchone()
        if existing:
            return
        tx.semantic_event(
            "intent.deduplicated",
            {
                "intent_ref": {
                    "entity_type": "intent",
                    "id": intent["entity_id"],
                    "revision": str(intent["revision"]),
                },
                "duplicate_of": work_item_id,
                "problem_digest": digest,
                "rule": "exact-question-basis-method-environment-output-v1",
            },
        )

    def _prepare(self, tx, now):
        if not task_can_run(tx.task):
            return
        config = self.registry.config(tx)
        receiver = self._receiver(tx)
        # Materialize accepted Intent refs before consuming a Reason wait whose
        # local ref points to one of them. No model-supplied Work IDs are used.
        intents = rows(
            tx.connection.execute(
                """SELECT i.* FROM vnext.intent_revision i WHERE i.tenant_id=%s AND i.project_id=%s AND i.task_id=%s
            AND i.acceptance_state='admitted' AND NOT EXISTS(SELECT 1 FROM vnext.scheduler_work s
            WHERE (s.tenant_id,s.project_id,s.task_id,s.intent_id,s.intent_revision)=
            (i.tenant_id,i.project_id,i.task_id,i.entity_id,i.revision)) ORDER BY i.created_at,i.entity_id LIMIT 256""",
                tx.owner,
            )
        )
        if intents:
            profile = self._profile(tx, "explore", config, receiver)
            for intent in intents:
                key = WorkKey(
                    "intent:" + intent["entity_id"],
                    intent["entity_id"],
                    str(intent["revision"]),
                    profile["ref"] + ":" + profile["revision"],
                    profile["digest"],
                    tuple(
                        (r["entity_type"], r["id"], r["revision"])
                        for r in strict_json_loads(intent["basis_json"])
                    ),
                    receiver["environment_ref"],
                    intent["expected_output"],
                )
                digest = problem_digest(
                    question=intent["question"],
                    basis=key.basis,
                    method_ref=key.method_ref,
                    profile_digest=key.profile_digest,
                    environment_ref=key.environment_ref,
                    output_contract=key.output_contract,
                )
                duplicate = self.works.duplicate_problem(tx, digest=digest)
                if duplicate is not None:
                    # One durable association per repeated question. The
                    # identical question is not new work, so it neither creates
                    # a second Explore nor wakes the Reason again.
                    self._deduplicated(tx, intent=intent, work_item_id=duplicate, digest=digest)
                    continue
                self.works.register(tx, key=key, kind="explore")
        state = self.triggers.read(tx)
        if state.inflight_reason_work_id:
            work = row(
                tx.connection.execute(
                    """SELECT w.current_run_id,a.result_submission_id,a.process_state FROM vnext.work_item w
                LEFT JOIN vnext.agent_run a ON (a.tenant_id,a.project_id,a.task_id,a.agent_run_id)=
                (w.tenant_id,w.project_id,w.task_id,w.current_run_id)
                WHERE w.tenant_id=%s AND w.project_id=%s AND w.task_id=%s AND w.work_item_id=%s""",
                    (*tx.owner, state.inflight_reason_work_id),
                )
            )
            consumed = False
            if work and work["result_submission_id"]:
                with tx.connection.transaction():
                    try:
                        consumed = self.triggers.consume(
                            tx, submission_id=work["result_submission_id"]
                        )
                    except DomainError as error:
                        if error.code not in {
                            "STALE_EXECUTION",
                            "reason_raw_reader_unavailable",
                        }:
                            raise
            if work and not consumed and work["process_state"] == "exited":
                self.triggers.fail(
                    tx,
                    work_item_id=state.inflight_reason_work_id,
                    reason_code=(
                        "invalid_result"
                        if work["result_submission_id"]
                        else "missing_result"
                    ),
                    now=now,
                )
        state = self.triggers.read(tx)
        if (
            state.pending_generation is None
            or state.inflight_reason_work_id
            or state.blocked_reason
            or state.retry_at is not None
            and state.retry_at > now
        ):
            return
        existing_reason = tx.connection.execute(
            """SELECT 1 FROM vnext.work_item w JOIN vnext.scheduler_work s USING(tenant_id,project_id,task_id,work_item_id)
            WHERE w.tenant_id=%s AND w.project_id=%s AND w.task_id=%s AND w.kind='reason'
            AND w.state NOT IN ('done','failed','cancelled') LIMIT 1""",
            tx.owner,
        ).fetchone()
        if not existing_reason:
            profile = self._profile(tx, "reason", config, receiver)
            key = WorkKey(
                f"reason:{state.pending_generation}:retry:{state.failure_count}",
                None,
                None,
                profile["ref"] + ":" + profile["revision"],
                profile["digest"],
                (),
                receiver["environment_ref"],
                "wuji.agent-payload.v2:reason_decision",
            )
            self.works.register(tx, key=key, kind="reason")

    def _limits(self, tx, work, config, now):
        limits = config.runtime.limits
        if (
            tx.task["activated_at"] is None
            or (now - tx.task["activated_at"]).total_seconds()
            >= limits.max_elapsed_seconds
        ):
            raise DomainError("max_elapsed_seconds", 429)
        counts = row(
            tx.connection.execute(
                "SELECT * FROM vnext.admission_counter WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                tx.owner,
            )
        )
        if counts and (
            counts["model_attempts"] >= limits.max_model_requests
            or counts["output_bytes"] >= limits.max_total_output_bytes
            or counts["tool_attempts"] >= limits.max_tool_calls
        ):
            raise DomainError("task_call_limit", 429)
        if limits.max_model_requests < 1 or limits.max_tool_calls < 1:
            raise DomainError("task_call_limit", 429)
        count = tx.connection.execute(
            "SELECT count(*) FROM vnext.agent_run WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
            (*tx.owner, work["work_item_id"]),
        ).fetchone()[0]
        if count >= limits.max_attempts_per_work:
            raise DomainError("max_attempts_per_work", 429)
        if work["kind"] == "reason":
            reasons = tx.connection.execute(
                """SELECT count(*) FROM vnext.agent_run a JOIN vnext.work_item w
                USING(tenant_id,project_id,task_id,work_item_id)
                WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s AND w.kind='reason'""",
                tx.owner,
            ).fetchone()[0]
            if reasons >= limits.max_reason_runs:
                raise DomainError("max_reason_runs", 429)
        return count

    def _admit(self, tx, proposal, now):
        work = row(
            tx.connection.execute(
                "SELECT * FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s FOR UPDATE",
                (*tx.owner, proposal.work_item_id),
            )
        )
        if not work or work["state"] not in {"ready", "blocked"}:
            raise DomainError("STALE_EXECUTION", 409)
        config = self.registry.config(tx)
        receiver = self._receiver(tx)
        profile = self._profile(tx, work["kind"], config, receiver)
        registration = row(
            tx.connection.execute(
                "SELECT key_json FROM vnext.scheduler_work WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
                (*tx.owner, work["work_item_id"]),
            )
        )
        if not registration:
            raise DomainError("work_identity_reconciliation_required", 409)
        key = strict_json_loads(registration["key_json"])
        if (
            key["profile_digest"] != profile["digest"]
            or key["environment_ref"] != receiver["environment_ref"]
        ):
            raise DomainError("work_profile_changed", 409)
        old_block = row(
            tx.connection.execute(
                "SELECT * FROM vnext.scheduler_block WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
                (*tx.owner, work["work_item_id"]),
            )
        )
        if old_block and not old_block["machine_recheck"]:
            raise DomainError(old_block["reason_code"], 409)
        if work["state"] == "blocked":
            if not old_block:
                raise DomainError("work_blocked_by_control", 409)
            # Provisional within admission savepoint. Any failed guard rolls
            # this back; only an actual successful recheck clears the block.
            work = dict(work, state="ready")
            tx.connection.execute(
                "UPDATE vnext.work_item SET state='ready',blocked_reason=NULL,revision=revision+1 WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
                (*tx.owner, work["work_item_id"]),
            )
        if not self.control.can_dispatch(tx, work):
            raise DomainError("dispatch_guard_unsatisfied", 409)
        attempts = self._limits(tx, work, config, now)
        recovery = None
        published = None
        previous_run_id = work["current_run_id"]
        if work["session_id"] is not None:
            if self.control.sessions is None or profile["body"].get("schema_version") != "wuji.harness.session.v1":
                raise DomainError("worker_recovery_unavailable", 503)
            recovery = self.control.sessions.validate_recovery_in_transaction(tx, work)
            if not recovery.resumable:
                raise DomainError(recovery.reason_code or "worker_recovery_unavailable", 409)
            published = self.control.sessions._load_in_transaction(tx, work)
        elif attempts:
            # No native state can be invented from an unknown earlier Run.
            raise DomainError("worker_recovery_unavailable", 503)
        if not any(pool["tier"] == "model" for pool in tx.capacity_pools):
            raise DomainError("model_pool_unavailable", 503)
        if any(pool["used"] >= pool["capacity"] for pool in tx.capacity_pools):
            raise DomainError("capacity_unavailable", 409)
        creator = getattr(self.snapshots, "create_in_transaction", None)
        if not callable(creator):
            raise DomainError("snapshot_transaction_unavailable", 503)
        issuer = self.credential_issuer
        if not callable(getattr(issuer, "prepare", None)) or not callable(
            getattr(issuer, "bind_admitted_run", None)
        ):
            raise DomainError("credential_issuer_unavailable", 503)
        manifest = (
            self.snapshots._get(tx, published.history.snapshot_id)
            if published is not None
            # A Run reads the Task's knowledge — claims, questions, observations
            # and the evidence those observations own. Sealed platform output
            # (raw model responses, session roots, result bindings) is a Run's
            # private working state, never board material: re-delivering it grew
            # every later context until a real session boundary refused the Run.
            else creator(
                tx,
                query=SnapshotQuery(
                    entity_types=("claim", "intent", "observation"),
                    required_refs=tuple(
                        (
                            item["ref"]["entity_type"],
                            item["ref"]["id"],
                            str(item["ref"]["revision"]),
                        )
                        for item in profile["body"].get("memory_inputs", ())
                    ),
                ),
                reader_clearance=receiver["worker_clearance"],
            )
        )
        if (manifest.tenant_id, manifest.project_id, manifest.task_id) != tx.owner:
            raise DomainError("INVALID_REFERENCE", 422)
        exact_key = WorkKey(
            **{
                **key,
                "basis": tuple(tuple(reference) for reference in key["basis"]),
            }
        )
        required_refs = set(exact_key.basis)
        if exact_key.intent_id is not None:
            required_refs.add(
                ("intent", exact_key.intent_id, exact_key.intent_revision)
            )
        available_refs = {
            (reference.entity_type.value, reference.id, reference.revision.root)
            for reference in manifest.refs
        }
        if not required_refs.issubset(available_refs):
            # The Worker must receive the exact fixed problem inputs. Lowering
            # template clearance may block the Work; it must never silently
            # produce a smaller context and continue admission.
            raise DomainError("required_snapshot_input_unavailable", 503)
        if work["kind"] == "reason" and recovery is None:
            self.triggers.begin_reason(
                tx, work_item_id=work["work_item_id"], snapshot_id=manifest.snapshot_id
            )
        run_id, operation_id = str(uuid4()), str(uuid4())
        epoch = int(work["run_epoch"]) + 1
        identity = RunIdentity.model_validate(
            {
                "tenant_id": tx.owner[0],
                "project_id": tx.owner[1],
                "task_id": tx.owner[2],
                "work_item_id": work["work_item_id"],
                "agent_run_id": run_id,
                "execution_epoch": str(tx.task["execution_epoch"]),
                "run_epoch": str(epoch),
                "runtime_attempt": str(tx.task["runtime_attempt"]),
                "receiver_id": receiver["receiver_id"],
            }
        )
        assignment = WorkerAssignment.model_validate(
            {
                "schema_version": "wuji.assignment.v2",
                "operation_id": operation_id,
                "identity": identity,
                "work_kind": work["kind"],
                "snapshot_id": manifest.snapshot_id,
                "profile_refs": [profile["ref"], config.model.ref, config.runtime.ref],
                "session_manifest_ref": recovery.manifest_ref if recovery is not None else None,
                "tool_definition_refs": profile["body"]["tool_definition_refs"],
                "limits": config.runtime.limits,
                "resume_reason": "persisted_input_or_settled_boundary" if recovery is not None else None,
            }
        )
        tx.connection.execute(
            """INSERT INTO vnext.agent_run(tenant_id,project_id,task_id,agent_run_id,work_item_id,
            receiver_id,execution_epoch,run_epoch,runtime_attempt,environment_ref,model_mode,pod_uid,start_operation_id,output_expectation)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'final_output')""",
            (
                *tx.owner,
                run_id,
                work["work_item_id"],
                receiver["receiver_id"],
                tx.task["execution_epoch"],
                epoch,
                tx.task["runtime_attempt"],
                receiver["environment_ref"],
                receiver["model_mode"],
                receiver["pod_uid"],
                operation_id,
            ),
        )
        tx.connection.execute(
            "UPDATE vnext.work_item SET state='leased',run_epoch=%s,current_run_id=%s,blocked_reason=NULL,revision=revision+1 WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
            (epoch, run_id, *tx.owner, work["work_item_id"]),
        )
        CapacityService.reserve(tx, run_id)
        if recovery is not None:
            tx.connection.execute("INSERT INTO vnext.session_holder(tenant_id,project_id,task_id,agent_run_id,work_item_id,manifest_ref,session_lineage,previous_run_id,frontier_digest) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (*tx.owner, run_id, work["work_item_id"], recovery.manifest_ref, recovery.session_lineage, previous_run_id, recovery.frontier_digest))
        definition = strict_json_loads(tx.task["definition_json"])
        authorization_expiry = datetime.fromisoformat(
            definition["task"]["authorization_expires_at"].replace("Z", "+00:00")
        )
        expires_at = min(
            authorization_expiry,
            tx.task["activated_at"]
            + timedelta(seconds=config.runtime.limits.max_elapsed_seconds),
        )
        recovery_options = {} if recovery is None else {"session_lineage": recovery.session_lineage}
        binding, credential_ref = issuer.prepare(
            tx,
            identity=identity,
            tool_definition_refs=tuple(profile["body"]["tool_definition_refs"]),
            expires_at=expires_at,
            **recovery_options,
        )
        binding = RunCredentialBinding.model_validate(binding)
        if (
            binding.identity != identity
            or binding.subject != worker_subject(run_id)
            or binding.expires_at > expires_at
            or binding.expires_at <= now
            or set(binding.purposes) != {"model_request", "tool_request"}
            or binding.session_lineage != (recovery.session_lineage if recovery is not None else "run:" + run_id)
            or tuple(binding.allowed_tool_refs)
            != tuple(profile["body"]["tool_definition_refs"])
            or not isinstance(credential_ref, str)
            or not credential_ref
            or len(credential_ref) > 256
        ):
            raise DomainError("credential_binding_mismatch", 409)
        issuer.bind_admitted_run(tx, binding=binding, credential_ref=credential_ref)
        writer = tx.connection.execute(
            "SELECT 1 FROM vnext.run_writer WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND subject=%s AND agent_subject=%s AND NOT revoked",
            (*tx.owner, run_id, binding.subject, agent_subject(run_id)),
        ).fetchone()
        if not writer:
            raise DomainError("run_writer_unavailable", 503)
        body = assignment.model_dump(mode="json")
        digest = sha256(canonical_json_bytes(body)).hexdigest()
        # Public Outbox contains only a reference to restricted assignment data.
        event_seq = _notification(
            tx,
            "run.dispatch_requested",
            {
                "agent_run_id": run_id,
                "operation_id": operation_id,
                "assignment_digest": digest,
            },
        )
        tx.connection.execute(
            """INSERT INTO vnext.scheduler_assignment(tenant_id,project_id,task_id,agent_run_id,
            work_item_id,operation_id,snapshot_id,assignment_json,assignment_digest,credential_ref,event_seq)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                *tx.owner,
                run_id,
                work["work_item_id"],
                operation_id,
                manifest.snapshot_id,
                json_text(body),
                digest,
                credential_ref,
                event_seq,
            ),
        )
        bind_receiver_result(tx, agent_run_id=run_id)
        tx.connection.execute(
            "SELECT vnext.bind_scheduler_snapshot(%s,%s,%s,%s,%s)",
            (*tx.owner, run_id, manifest.snapshot_id),
        ).fetchone()
        tx.connection.execute(
            "DELETE FROM vnext.scheduler_block WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
            (*tx.owner, work["work_item_id"]),
        )
        return assignment

    def tick(self, *, now=None, limit=16):
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None or type(limit) is not int or not 1 <= limit <= 256:
            raise ValueError("invalid bounded tick")
        located = self._tasks()
        candidates, blocks, positions = [], [], []
        for (tenant, task_id), access in located.items():
            try:
                with self._transaction(access, task_id) as tx:
                    state = state_row(tx)
                    positions.append((state["last_selected"], tenant, task_id))
                    self._consume_events(tx)
                    try:
                        with tx.connection.transaction():
                            self._prepare(tx, now)
                    except DomainError as error:
                        blocks.append((task_id, "", error.code))
                        tx.connection.execute(
                            """UPDATE vnext.scheduler_state SET preparation_block_reason=%s,
                            preparation_release_condition='Platform operator supplies the actual missing prerequisite; next preparation must recheck it'
                            WHERE tenant_id=%s AND project_id=%s AND task_id=%s""",
                            (error.code, *tx.owner),
                        )
                    else:
                        tx.connection.execute(
                            "UPDATE vnext.scheduler_state SET preparation_block_reason=NULL,preparation_release_condition=NULL WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                            tx.owner,
                        )
                    items = rows(
                        tx.connection.execute(
                            """SELECT w.*,s.priority,s.ready_since,s.consideration_round FROM vnext.work_item w
                        JOIN vnext.scheduler_work s USING(tenant_id,project_id,task_id,work_item_id)
                        LEFT JOIN vnext.scheduler_block b USING(tenant_id,project_id,task_id,work_item_id)
                        WHERE w.tenant_id=%s AND w.project_id=%s AND w.task_id=%s
                        AND w.state IN ('ready','blocked') AND w.desired_state='run'
                        AND (b.work_item_id IS NULL OR b.machine_recheck)
                        ORDER BY s.ready_since,w.work_item_id""",
                            tx.owner,
                        )
                    )
                    if task_can_run(tx.task):
                        for w in items:
                            # Informational dependency eligibility prevents a
                            # blocked priority head from starving unrelated work.
                            # Actual admission still repeats the complete guard.
                            eligible = dependencies_satisfied(
                                tx, w["work_item_id"]
                            ) and intent_current(tx, w)
                            candidates.append(
                                Candidate(
                                    tenant,
                                    task_id,
                                    w["work_item_id"],
                                    w["kind"],
                                    w["priority"],
                                    w["ready_since"],
                                    eligible,
                                    w["consideration_round"],
                                )
                            )
            except DomainError as error:
                if error.code == "scheduler_ownership_lost":
                    raise
                blocks.append((task_id, "", error.code))
        latest = max(positions, default=(0, None, None))
        task_cursors = {}
        for position, tenant, task_id in sorted(positions):
            if position:
                task_cursors[tenant] = task_id
        proposal = self.policy.select(
            SchedulingSnapshot(
                tuple(candidates),
                now,
                latest[1] if latest[0] else None,
                tuple(task_cursors.items()),
                limit,
            )
        )
        assignments = []
        for selected in proposal:
            access = located[(selected.tenant_id, selected.task_id)]
            assignment = None
            try:
                with self._transaction(access, selected.task_id) as tx:
                    state_row(tx)
                    # Persist every consideration before its admission savepoint.
                    # Rejection advances the Work's round just like admission,
                    # so restart cannot return a blocker to the front forever.
                    tx.connection.execute(
                        "UPDATE vnext.scheduler_state SET last_selected=nextval('vnext.scheduler_selection_order') WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                        tx.owner,
                    )
                    advanced = tx.connection.execute(
                        """UPDATE vnext.scheduler_work
                        SET consideration_round=consideration_round+1
                        WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                        AND work_item_id=%s RETURNING consideration_round""",
                        (*tx.owner, selected.work_item_id),
                    ).fetchone()
                    if advanced is None:
                        raise DomainError("STALE_EXECUTION", 409)
                    try:
                        with tx.connection.transaction():
                            assignment = self._admit(tx, selected, now)
                    except DomainError as error:
                        machine = error.code in {
                            "capacity_unavailable",
                            "dispatch_guard_unsatisfied",
                            "receiver_unavailable",
                            "worker_profile_unavailable",
                            "snapshot_transaction_unavailable",
                            "credential_issuer_unavailable",
                            "model_pool_unavailable",
                            "CAPABILITY_UNAVAILABLE",
                            "credential_template_unavailable",
                            "credential_encryption_unavailable",
                            "credential_key_unavailable",
                            "credential_signing_unavailable",
                            "required_snapshot_input_unavailable",
                        }
                        block(
                            tx,
                            selected.work_item_id,
                            error.code,
                            machine=machine,
                            responsible=(
                                "platform_operator"
                                if error.status == 503
                                else "task_operator"
                            ),
                            remedy=(
                                "Recheck the actual registered prerequisite and current P05 dispatch guard"
                                if machine
                                else "Operator review required; cumulative limits are retained"
                            ),
                        )
                        blocks.append(
                            (selected.task_id, selected.work_item_id, error.code)
                        )
                if assignment is not None:
                    assignments.append(assignment)
            except DomainError as error:
                if error.code == "scheduler_ownership_lost":
                    raise
                blocks.append((selected.task_id, selected.work_item_id, error.code))
        return TickReceipt(tuple(assignments), tuple(blocks), proposal)
