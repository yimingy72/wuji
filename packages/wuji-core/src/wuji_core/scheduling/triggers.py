"""Independent durable trigger generations and authoritative Reason consumption."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from wuji_core.admission.registry import AdmissionRegistry
from wuji_core.contracts.envelopes import (
    AgentPayload,
    AgentPayloadV3,
    ResultEnvelope,
    ResultEnvelopeV3,
    ResultReceipt,
)
from wuji_core.execution.capacity import operations_settled
from wuji_core.http.json_boundary import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text, row


def require_admission(tx):
    if (
        tx.purpose != "admit"
        or not tx.permissions.get("can_admit")
        or not tx.permissions.get("can_read")
        or "agent" in tx.access.principal.roles
        or not tx.access.principal.roles.intersection({"scheduler", "controller"})
        or not tx.capacity_pools
    ):
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")


def rows(cursor):
    result = []
    while (value := row(cursor)) is not None:
        result.append(value)
    return result


def state_row(tx):
    require_admission(tx)
    tx.connection.execute(
        "INSERT INTO vnext.scheduler_state(tenant_id,project_id,task_id) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
        tx.owner,
    )
    return row(
        tx.connection.execute(
            "SELECT * FROM vnext.scheduler_state WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
            tx.owner,
        )
    )


def block(
    tx,
    work_id,
    code,
    *,
    responsible="task_operator",
    remedy="Review the blocked work and supply an explicit resolution",
    machine=False,
):
    require_admission(tx)
    tx.connection.execute(
        """INSERT INTO vnext.scheduler_block(tenant_id,project_id,task_id,work_item_id,
        reason_code,responsible_role,release_condition,machine_recheck) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT(tenant_id,project_id,task_id,work_item_id) DO UPDATE SET
        reason_code=EXCLUDED.reason_code,responsible_role=EXCLUDED.responsible_role,
        release_condition=EXCLUDED.release_condition,machine_recheck=EXCLUDED.machine_recheck""",
        (*tx.owner, work_id, code, responsible, remedy, machine),
    )
    # Running/terminal Work remains under P05 process/control authority.
    tx.connection.execute(
        """UPDATE vnext.work_item SET state='blocked',blocked_reason=%s,revision=revision+1
        WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s
        AND state IN ('ready','blocked') AND (state<>'blocked' OR blocked_reason IS DISTINCT FROM %s)""",
        (code, *tx.owner, work_id, code),
    )


def _planning_policy(tx):
    definition = strict_json_loads(tx.task["definition_json"])
    body = definition.get("worker_profiles", {}).get("reason", {}).get("body", {})
    return (
        body.get("planning_policy")
        if body.get("schema_version") == "wuji.harness.problem.v1"
        else None
    )
def _bump(tx, *, event_key, reason, event_seq=None):
    current = state_row(tx)
    existing = row(
        tx.connection.execute(
            "SELECT generation FROM vnext.scheduler_trigger WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND event_key=%s",
            (*tx.owner, event_key),
        )
    )
    if existing is not None:
        return existing["generation"]
    generation = current["trigger_generation"] + 1 if reason is not None else None
    tx.connection.execute(
        "INSERT INTO vnext.scheduler_trigger(tenant_id,project_id,task_id,event_key,event_seq,generation,reason) VALUES(%s,%s,%s,%s,%s,%s,%s)",
        (*tx.owner, event_key, event_seq, generation, reason or "excluded_event"),
    )
    if generation is not None:
        policy = _planning_policy(tx)
        if policy is None:
            tx.connection.execute(
                "UPDATE vnext.scheduler_state SET trigger_generation=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                (generation, *tx.owner),
            )
        else:
            now = datetime.now(timezone.utc)
            tx.connection.execute(
                """UPDATE vnext.scheduler_state SET trigger_generation=%s,
                pending_since=COALESCE(pending_since,%s),
                max_pending_at=COALESCE(max_pending_at,%s)
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s""",
                (
                    generation,
                    now,
                    now + timedelta(milliseconds=policy["max_delay_milliseconds"]),
                    *tx.owner,
                ),
            )
    return generation


@dataclass(frozen=True)
class TriggerState:
    trigger_generation: int
    consumed_generation: int
    pending_generation: int | None
    inflight_reason_work_id: str | None
    failure_count: int
    retry_at: datetime | None
    blocked_reason: str | None
    pending_since: datetime | None = None
    max_pending_at: datetime | None = None


@dataclass(frozen=True)
class ReasonLease:
    work_item_id: str
    processing_generation: int
    snapshot_id: str


class TriggerRepository:
    def __init__(self, *, artifacts=None):
        self.artifacts = artifacts

    def read(self, tx):
        state = state_row(tx)
        pending = (
            state["trigger_generation"]
            if state["trigger_generation"] > state["consumed_generation"]
            else None
        )
        policy = _planning_policy(tx)
        if pending is not None and policy is not None and state["pending_since"] is not None:
            now = datetime.now(timezone.utc)
            due = state["pending_since"] + timedelta(
                milliseconds=policy["coalesce_milliseconds"]
            )
            if now < due and now < state["max_pending_at"]:
                pending = None
        return TriggerState(
            state["trigger_generation"],
            state["consumed_generation"],
            pending,
            state["inflight_reason_work_id"],
            state["failure_count"],
            state["retry_at"],
            state["blocked_reason"],
            state["pending_since"],
            state["max_pending_at"],
        )

    def start(self, tx):
        require_admission(tx)
        if tx.task["activated_at"] is None:
            raise DomainError("STALE_EXECUTION", 409)
        return _bump(tx, event_key="task.start", reason="task_started")

    def record(self, tx, *, event_seq):
        require_admission(tx)
        event = row(
            tx.connection.execute(
                "SELECT * FROM vnext.outbox WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND event_seq=%s",
                (*tx.owner, event_seq),
            )
        )
        if event is None:
            raise DomainError("INVALID_REFERENCE", 422)
        payload = strict_json_loads(event["payload_json"])
        kind = event["kind"]
        accepted = self._event_relevant(tx, kind, payload)
        generation = _bump(
            tx,
            event_key="outbox:" + str(event_seq),
            reason=kind if accepted else None,
            event_seq=event_seq,
        )
        if accepted:
            self._progress(tx, event, payload)
        # Predicates are re-read for every recorded event, not only for the ones
        # that start a new Reason generation: a Work usually becomes `done` while
        # its exit observation is being recorded, and a waiter whose condition
        # just became true has to wake on that event.
        from wuji_core.scheduling.waiters import WaiterRepository

        WaiterRepository().scan(tx)
        return generation

    def _event_relevant(self, tx, kind, payload):
        if kind == "result_committed":
            result = row(
                tx.connection.execute(
                    """SELECT w.kind,r.receipt_json FROM vnext.result_submission s
                JOIN vnext.result_receipt r USING(tenant_id,project_id,task_id,submission_id)
                JOIN vnext.agent_run a USING(tenant_id,project_id,task_id,agent_run_id)
                JOIN vnext.work_item w USING(tenant_id,project_id,task_id,work_item_id)
                WHERE s.tenant_id=%s AND s.project_id=%s AND s.task_id=%s AND s.submission_id=%s""",
                    (*tx.owner, payload.get("submission_id")),
                )
            )
            if not result or result["kind"] == "reason":
                return False
            receipt = strict_json_loads(result["receipt_json"])
            return receipt["status"] == "accepted" and any(
                c.get("canonical_ref") and not c.get("code")
                for c in receipt["components"]
            )
        if kind in {"claim_shared", "intent_shared"}:
            ref = payload.get("canonical_ref")
            if not ref or payload.get("code"):
                return False
            table = "intent_revision" if kind == "intent_shared" else "claim_revision"
            producer = row(
                tx.connection.execute(
                    f"""SELECT x.agent_run_id,w.kind FROM vnext.{table} x
                LEFT JOIN vnext.agent_run a USING(tenant_id,project_id,task_id,agent_run_id)
                LEFT JOIN vnext.work_item w USING(tenant_id,project_id,task_id,work_item_id)
                WHERE x.tenant_id=%s AND x.project_id=%s AND x.task_id=%s AND x.entity_id=%s AND x.revision=%s""",
                    (*tx.owner, ref["id"], ref["revision"]),
                )
            )
            return producer is not None and (
                producer["agent_run_id"] is None or producer["kind"] != "reason"
            )
        if kind == "completion.reviewed":
            # Only a review that still has a gap asks the Reason for another
            # look; a ready review waits for the operator's quiesce decision.
            return payload.get("decision") in {"wait", "blocked"}
        if kind in {"work.reconciled", "work.condition_changed"}:
            work = row(
                tx.connection.execute(
                    "SELECT kind,state FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
                    (*tx.owner, payload.get("work_item_id")),
                )
            )
            return bool(
                work
                and work["kind"] != "reason"
                and work["state"] in {"done", "failed", "cancelled", "ready"}
            )
        # These names are emitted by platform producers, not Agent role text.
        # Tokens, heartbeat, layout, control acknowledgements and proposed starts
        # are deliberately absent. Future producers need explicit registration.
        if kind == "evidence_ingested":
            return payload.get("status") == "accepted" and bool(
                payload.get("observation_ref")
            )
        return kind in {"assessment_recorded", "assessment_invalidated"}

    def _material(self, tx, *, key, event_seq):
        """Record one material row and release the no-progress window it ends."""

        inserted = tx.connection.execute(
            "INSERT INTO vnext.scheduler_progress(tenant_id,project_id,task_id,source_key,category,event_seq) VALUES(%s,%s,%s,%s,'material',%s) ON CONFLICT DO NOTHING",
            (*tx.owner, key, event_seq),
        ).rowcount
        if inserted:
            # New knowledge is the only thing that ends a no-progress window; a
            # retry or operator block stays until a human decides.
            tx.connection.execute(
                """UPDATE vnext.scheduler_state SET no_progress_count=0,
                blocked_reason=CASE WHEN blocked_reason='no_progress_window' THEN NULL ELSE blocked_reason END
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s""",
                tx.owner,
            )

    def _progress(self, tx, event, payload):
        """Record verified new material for the bounded no-progress check.

        Two producers count: a sealed Observation with content, provenance and
        environment (``evidence_ingested``), and an accepted non-Reason result
        whose components actually became canonical knowledge. The fingerprint is
        the accepted canonical references themselves, so replaying one result or
        renaming a ToolAttempt never looks like new knowledge.
        """

        if event["kind"] == "result_committed":
            self._result_material(tx, event, payload)
            return
        if event["kind"] != "evidence_ingested":
            return
        ref = payload.get("observation_ref")
        if not ref:
            return
        observation = row(
            tx.connection.execute(
                "SELECT * FROM vnext.observation WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND entity_id=%s AND revision=%s",
                (*tx.owner, ref["id"], ref["revision"]),
            )
        )
        if not observation:
            return
        source = {
            k: observation[k]
            for k in (
                "environment_ref",
                "conditions_json",
                "evidence_origin",
                "capture_layer",
                "completeness",
            )
        }
        artifacts = rows(
            tx.connection.execute(
                """SELECT a.sha256,a.size_bytes,a.provenance FROM vnext.observation_artifact o
            JOIN vnext.artifact a ON (a.tenant_id,a.project_id,a.task_id,a.entity_id,a.revision)=
            (o.tenant_id,o.project_id,o.task_id,o.artifact_id,o.artifact_revision)
            WHERE o.tenant_id=%s AND o.project_id=%s AND o.task_id=%s AND o.observation_id=%s
            AND o.observation_revision=%s AND a.state='sealed' ORDER BY o.ordinal""",
                (*tx.owner, ref["id"], ref["revision"]),
            )
        )
        if not artifacts:
            return
        source["artifacts"] = artifacts
        key = "material:" + sha256(canonical_json_bytes(source)).hexdigest()
        self._material(tx, key=key, event_seq=event["event_seq"])

    def _result_material(self, tx, event, payload):
        """One material row per accepted result, keyed by its canonical refs."""

        result = row(
            tx.connection.execute(
                """SELECT w.kind,r.receipt_json FROM vnext.result_submission s
            JOIN vnext.result_receipt r USING(tenant_id,project_id,task_id,submission_id)
            JOIN vnext.agent_run a USING(tenant_id,project_id,task_id,agent_run_id)
            JOIN vnext.work_item w USING(tenant_id,project_id,task_id,work_item_id)
            WHERE s.tenant_id=%s AND s.project_id=%s AND s.task_id=%s AND s.submission_id=%s""",
                (*tx.owner, payload.get("submission_id")),
            )
        )
        if not result or result["kind"] == "reason":
            return
        receipt = strict_json_loads(result["receipt_json"])
        if receipt.get("status") != "accepted":
            return
        canonical = sorted(
            (
                claim["kind"], claim["assertion_role"], claim["text"],
                claim["structured_json"], claim["basis_json"],
            )
            for component in receipt.get("components", [])
            if component.get("canonical_ref") and not component.get("code")
            and component["canonical_ref"]["entity_type"] == "claim"
            for claim in [row(tx.connection.execute(
                "SELECT kind,assertion_role,text,structured_json,basis_json FROM vnext.claim_revision "
                "WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND entity_id=%s AND revision=%s",
                (*tx.owner, component["canonical_ref"]["id"],
                 component["canonical_ref"]["revision"]),
            ))]
            if claim is not None
        )
        if not canonical:
            return
        key = "material:" + sha256(
            canonical_json_bytes({"accepted_claim_content": canonical})
        ).hexdigest()
        self._material(tx, key=key, event_seq=event["event_seq"])

    def begin_reason(self, tx, *, work_item_id, snapshot_id):
        state = state_row(tx)
        work = row(
            tx.connection.execute(
                "SELECT * FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s FOR UPDATE",
                (*tx.owner, work_item_id),
            )
        )
        snapshot = tx.connection.execute(
            "SELECT 1 FROM vnext.snapshot_manifest WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND snapshot_id=%s AND expires_at>clock_timestamp()",
            (*tx.owner, snapshot_id),
        ).fetchone()
        if (
            not work
            or work["kind"] != "reason"
            or work["state"] not in {"ready", "leased"}
            or not snapshot
            or state["blocked_reason"]
            or state["trigger_generation"] <= state["consumed_generation"]
            or state["inflight_reason_work_id"] is not None
            or state["retry_at"] is not None
            and state["retry_at"] > datetime.now(timezone.utc)
        ):
            raise DomainError("STALE_EXECUTION", 409)
        generation = state["trigger_generation"]
        tx.connection.execute(
            "INSERT INTO vnext.scheduler_reason_lease(tenant_id,project_id,task_id,work_item_id,processing_generation,snapshot_id,status) VALUES(%s,%s,%s,%s,%s,%s,'inflight')",
            (*tx.owner, work_item_id, generation, snapshot_id),
        )
        tx.connection.execute(
            "UPDATE vnext.scheduler_state SET inflight_reason_work_id=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
            (work_item_id, *tx.owner),
        )
        return ReasonLease(work_item_id, generation, snapshot_id)

    def consume(self, tx, *, submission_id):
        state = state_row(tx)
        old = row(
            tx.connection.execute(
                "SELECT status FROM vnext.scheduler_decision WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND submission_id=%s",
                (*tx.owner, submission_id),
            )
        )
        if old:
            return old["status"] == "accepted"
        value = row(
            tx.connection.execute(
                """SELECT s.*,r.receipt_json,a.work_item_id,a.execution_epoch,a.run_epoch,a.runtime_attempt,
            a.receiver_id,w.kind,w.current_run_id,w.desired_state,l.processing_generation,l.snapshot_id,l.status AS lease_status
            FROM vnext.result_submission s JOIN vnext.result_receipt r USING(tenant_id,project_id,task_id,submission_id)
            JOIN vnext.agent_run a USING(tenant_id,project_id,task_id,agent_run_id)
            JOIN vnext.work_item w USING(tenant_id,project_id,task_id,work_item_id)
            JOIN vnext.scheduler_reason_lease l USING(tenant_id,project_id,task_id,work_item_id)
            WHERE s.tenant_id=%s AND s.project_id=%s AND s.task_id=%s AND s.submission_id=%s""",
                (*tx.owner, submission_id),
            )
        )
        if (
            not value
            or value["kind"] != "reason"
            or value["lease_status"] != "inflight"
            or state["inflight_reason_work_id"] != value["work_item_id"]
            or value["current_run_id"] != value["agent_run_id"]
        ):
            raise DomainError("STALE_EXECUTION", 409)
        raw_envelope = strict_json_loads(value["envelope_json"])
        envelope = (
            ResultEnvelopeV3.model_validate(raw_envelope)
            if raw_envelope.get("schema_version") == "wuji.result-envelope.v3"
            else ResultEnvelope.model_validate(raw_envelope)
        )
        snapshot_id = (
            envelope.initial_snapshot_id
            if isinstance(envelope, ResultEnvelopeV3)
            else envelope.snapshot_id
        )
        receipt = ResultReceipt.model_validate(strict_json_loads(value["receipt_json"]))
        if (
            receipt.status.value != "accepted"
            or receipt.code is not None
            or snapshot_id != value["snapshot_id"]
            or any(
                str(value[k]) != str(v)
                for k, v in envelope.identity.model_dump(mode="json").items()
            )
            or value["execution_epoch"] != tx.task["execution_epoch"]
            or value["runtime_attempt"] != tx.task["runtime_attempt"]
            or value["desired_state"] != "run"
        ):
            raise DomainError("STALE_EXECUTION", 409)
        if self.artifacts is None:
            raise DomainError("reason_raw_reader_unavailable", 503)
        record = self.artifacts.record(tx, envelope.raw_output_ref)
        raw = self.artifacts.checked_bytes(record)
        if (
            sha256(raw).hexdigest() != envelope.raw_output_digest.root
            or record["agent_run_id"] != value["agent_run_id"]
            or record["writer_subject"] != value["writer_subject"]
        ):
            raise DomainError("INVALID_REFERENCE", 422)
        payload = (
            AgentPayloadV3.model_validate(
                strict_json_loads(raw.decode("utf-8"))
            ).for_work_kind("reason")
            if isinstance(envelope, ResultEnvelopeV3)
            else AgentPayload.model_validate(strict_json_loads(raw.decode("utf-8")))
        )
        decision = payload.reason_decision
        code = None
        try:
            if decision is None:
                raise DomainError("reason_decision_missing", 422)
            if any(
                c.code is not None and c.code.value == "STALE_INPUT"
                for c in receipt.components
            ):
                raise DomainError("STALE_INPUT", 409)
            with tx.connection.transaction():
                self._apply_decision(tx, value, decision, receipt)
        except DomainError as error:
            code = error.code
        tx.connection.execute(
            """INSERT INTO vnext.scheduler_decision(tenant_id,project_id,task_id,submission_id,
            work_item_id,processing_generation,status,reason_code,decision_json,raw_digest)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                *tx.owner,
                submission_id,
                value["work_item_id"],
                value["processing_generation"],
                "rejected" if code else "accepted",
                code,
                json_text(decision.model_dump(mode="json") if decision else None),
                envelope.raw_output_digest.root,
            ),
        )
        if code:
            block(
                tx,
                value["work_item_id"],
                code,
                remedy="Wait for terminal Run settlement, then bounded Reason retry or operator review",
            )
            return False
        new_material = tx.connection.execute(
            """SELECT 1 FROM vnext.scheduler_progress p JOIN vnext.scheduler_trigger t
            USING(tenant_id,project_id,task_id,event_seq)
            WHERE p.tenant_id=%s AND p.project_id=%s AND p.task_id=%s
            AND t.generation>%s AND t.generation<=%s LIMIT 1""",
            (*tx.owner, state["consumed_generation"], value["processing_generation"]),
        ).fetchone()
        # A round counts as no progress only when nothing else could still bring
        # material: no other live work, no unsatisfied waiter and no newer input
        # already waiting for the next Reason. Waiting is not the same as being
        # stuck, so a real wait never burns the window.
        counted = not bool(new_material) and self._no_progress_eligible(tx, state, value)
        tx.connection.execute(
            """UPDATE vnext.scheduler_state SET consumed_generation=%s,inflight_reason_work_id=NULL,
            failure_count=0,retry_at=NULL,
            no_progress_count=CASE WHEN %s THEN 0 WHEN %s THEN no_progress_count+1 ELSE no_progress_count END
            ,pending_since=CASE WHEN trigger_generation<=%s THEN NULL ELSE pending_since END
            ,max_pending_at=CASE WHEN trigger_generation<=%s THEN NULL ELSE max_pending_at END
            WHERE tenant_id=%s AND project_id=%s AND task_id=%s""",
            (
                value["processing_generation"],
                bool(new_material),
                counted,
                value["processing_generation"],
                value["processing_generation"],
                *tx.owner,
            ),
        )
        tx.connection.execute(
            "UPDATE vnext.scheduler_reason_lease SET status='consumed' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
            (*tx.owner, value["work_item_id"]),
        )
        if counted:
            self._stop_on_no_progress(tx, value=value)
        return True

    def _no_progress_eligible(self, tx, state, value):
        """Whether a settled round with no new material may count as no progress."""

        live = tx.connection.execute(
            """SELECT 1 FROM vnext.work_item w JOIN vnext.scheduler_work s
            USING(tenant_id,project_id,task_id,work_item_id)
            WHERE w.tenant_id=%s AND w.project_id=%s AND w.task_id=%s
            AND w.state IN ('ready','leased','running','reconciling') AND w.work_item_id<>%s LIMIT 1""",
            (*tx.owner, value["work_item_id"]),
        ).fetchone()
        if live:
            return False
        waiting = tx.connection.execute(
            """SELECT 1 FROM vnext.scheduler_waiter WHERE tenant_id=%s AND project_id=%s
            AND task_id=%s AND status='waiting' LIMIT 1""",
            tx.owner,
        ).fetchone()
        if waiting:
            return False
        return state["trigger_generation"] <= value["processing_generation"]

    def _stop_on_no_progress(self, tx, *, value):
        """One durable completion request when the published window is reached.

        The request goes to the existing completion consumer; the same state flag
        that records it also refuses to mint another Reason for this Task, so a
        stalled exploration asks a human exactly once instead of re-asking the
        model. New material releases the flag.
        """

        limits = AdmissionRegistry(None).config(tx).runtime.limits
        definition = strict_json_loads(tx.task["definition_json"])
        reason_profile = definition.get("worker_profiles", {}).get("reason", {}).get("body", {})
        window = (
            reason_profile.get("planning_policy", {}).get("no_progress_rounds")
            if reason_profile.get("schema_version") == "wuji.harness.problem.v1"
            else limits.max_no_progress_rounds
        )
        if not window:
            return
        count = tx.connection.execute(
            "SELECT no_progress_count FROM vnext.scheduler_state WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
            tx.owner,
        ).fetchone()[0]
        if count < window:
            return
        already = tx.connection.execute(
            """SELECT 1 FROM vnext.outbox WHERE tenant_id=%s AND project_id=%s AND task_id=%s
            AND kind='reason.completion_requested'
            AND payload_json::jsonb->>'reason'='no_progress_window' LIMIT 1""",
            tx.owner,
        ).fetchone()
        if already:
            return
        tx.semantic_event(
            "reason.completion_requested",
            {
                "work_item_id": value["work_item_id"],
                "processing_generation": str(value["processing_generation"]),
                "reason": "no_progress_window",
                "no_progress_count": str(count),
                "window": str(window),
            },
        )
        tx.connection.execute(
            "UPDATE vnext.scheduler_state SET blocked_reason='no_progress_window' WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
            tx.owner,
        )

    def _apply_decision(self, tx, lease, decision, receipt):
        from wuji_core.scheduling.waiters import WaiterRepository

        if decision.decision.value == "propose_intents":
            accepted = [
                component.canonical_ref
                for component in receipt.components
                if component.status.value == "accepted_shared"
                and component.code is None
                and component.canonical_ref is not None
                and component.canonical_ref.entity_type.value == "intent"
            ]
            if not accepted or not all(
                tx.connection.execute(
                    """SELECT 1 FROM vnext.intent_revision
                    WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                    AND entity_id=%s AND revision=%s AND agent_run_id=%s""",
                    (
                        *tx.owner,
                        reference.id,
                        reference.revision.root,
                        lease["agent_run_id"],
                    ),
                ).fetchone()
                for reference in accepted
            ):
                raise DomainError("reason_intent_not_accepted", 422)
        elif decision.decision.value == "wait":
            waiters = WaiterRepository()
            predicates = waiters.from_result(tx, decision.wait_refs, receipt.components)
            waiters.register(
                tx,
                work_item_id=lease["work_item_id"],
                processing_generation=lease["processing_generation"],
                predicates=predicates,
            )
        elif decision.wait_refs:
            raise DomainError("INVALID_REFERENCE", 422)
        elif decision.decision.value == "blocked":
            block(tx, lease["work_item_id"], "reason_operator_review")
            tx.connection.execute(
                "UPDATE vnext.scheduler_state SET blocked_reason='reason_operator_review' WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                tx.owner,
            )
        elif decision.decision.value == "propose_completion":
            # A request to P12, never an assertion that Goal met or Task closed.
            tx.semantic_event(
                "reason.completion_requested",
                {
                    "work_item_id": lease["work_item_id"],
                    "processing_generation": str(lease["processing_generation"]),
                },
            )

    def fail(self, tx, *, work_item_id, reason_code, now):
        state = state_row(tx)
        if now.tzinfo is None or reason_code not in {
            "invalid_result",
            "missing_result",
            "run_failed",
            "decision_rejected",
        }:
            raise DomainError("INVALID_SCHEMA", 422)
        if state["inflight_reason_work_id"] != work_item_id:
            raise DomainError("STALE_EXECUTION", 409)
        run = row(
            tx.connection.execute(
                """SELECT a.*,e.kind AS observation_kind FROM vnext.work_item w
            JOIN vnext.agent_run a ON (a.tenant_id,a.project_id,a.task_id,a.agent_run_id)=
            (w.tenant_id,w.project_id,w.task_id,w.current_run_id)
            JOIN vnext.execution_observation e ON (e.tenant_id,e.project_id,e.task_id,e.receipt_id,e.agent_run_id)=
            (a.tenant_id,a.project_id,a.task_id,a.last_observation_id,a.agent_run_id)
            WHERE w.tenant_id=%s AND w.project_id=%s AND w.task_id=%s AND w.work_item_id=%s AND w.kind='reason'""",
                (*tx.owner, work_item_id),
            )
        )
        if (
            not run
            or run["process_state"] != "exited"
            or run["observation_kind"]
            not in {"not_started", "exited", "environment_stopped"}
            or not operations_settled(tx, run["agent_run_id"])
        ):
            raise DomainError("OPERATION_UNKNOWN", 409)
        limits = AdmissionRegistry(None).config(tx).runtime.limits
        failures = state["failure_count"] + 1
        # The retry series has its own published budget. `repair_attempts` is the
        # model schema-repair budget (SPEC 10.2) and `max_attempts_per_work` bounds
        # one Work item, which a retry never reuses. The task-level Reason cap is
        # still included so a series cannot spin against an admission refusal.
        retries = limits.reason_retry_attempts or 0
        exhausted = failures >= min(limits.max_reason_runs, retries + 1)
        retry_at = (
            None
            if exhausted
            else now + timedelta(seconds=min(300, 2 ** min(failures, 8)))
        )
        tx.connection.execute(
            """UPDATE vnext.scheduler_state SET inflight_reason_work_id=NULL,failure_count=%s,
            retry_at=%s,blocked_reason=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s""",
            (
                failures,
                retry_at,
                "reason_retry_exhausted" if exhausted else None,
                *tx.owner,
            ),
        )
        tx.connection.execute(
            "UPDATE vnext.scheduler_reason_lease SET status='failed' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
            (*tx.owner, work_item_id),
        )
        if exhausted:
            block(
                tx,
                work_item_id,
                "reason_retry_exhausted",
                remedy="Operator reviews the failed Reason series; ticks cannot reset its attempt budget",
            )
        return self.read(tx)
