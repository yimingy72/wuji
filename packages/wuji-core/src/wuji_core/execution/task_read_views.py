"""Bounded human-facing Task overview and activity projections."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import quote

from wuji_core.blackboard.fact_view import aggregate
from wuji_core.blackboard.work_results import read_work_result
from wuji_core.evidence.runtime_capture import terminal_container_states
from wuji_core.contracts.generated import (
    KnowledgeRef,
    TaskActivityPageV1,
    TaskCommandInventoryV1,
    TaskOverviewV1,
    TaskPublicationPageV1,
)
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import AccessContext, DomainError


_EVENTS = {
    "task.started": ("task", "key", "succeeded", "任务已启动"),
    "control.applied": ("task", "key", "pending", "任务控制请求已记录"),
    "work.stop_requested": ("work", "key", "pending", "停止工作请求已受理"),
    "work.reconciled": ("work", "key", "info", "工作状态已核对"),
    "work.condition_changed": ("work", "detail", "info", "工作条件已更新"),
    "work.settled": ("work", "key", "succeeded", "工作已结算"),
    "execution.observed": ("work", "key", "info", "执行状态已更新"),
    "result_committed": ("work", "key", "succeeded", "工作结果已保存"),
    "claim_shared": ("finding", "key", "info", "发现已共享"),
    "intent_shared": ("work", "key", "pending", "新问题已加入任务"),
    "assessment_recorded": ("finding", "key", "info", "发现的验证状态已更新"),
    "assessment_invalidated": ("finding", "key", "blocked", "发现的旧验证已失效"),
    "evidence_ingested": ("evidence", "key", "succeeded", "证据已保存"),
    "input.registered": ("input", "key", "blocked", "任务正在等待补充信息"),
    "input.resolved": ("input", "key", "succeeded", "补充信息已提交"),
    "approval.decided": ("input", "key", "succeeded", "审批结果已记录"),
    "completion.reviewed": ("completion", "key", "info", "完成条件已复核"),
    "completion.control_applied": ("completion", "key", "pending", "任务收尾请求已记录"),
    "tool.dispatch_requested": ("tool", "detail", "running", "开始执行一个工具步骤"),
    "session.published": ("work", "detail", "info", "工作会话状态已保存"),
}

_WORK_ITEM_SQL = """COALESCE(
    NULLIF(o.payload_json::jsonb->>'work_item_id',''),
    (SELECT run.work_item_id FROM vnext.agent_run run
      WHERE (run.tenant_id,run.project_id,run.task_id)=(o.tenant_id,o.project_id,o.task_id)
        AND run.agent_run_id=o.payload_json::jsonb->>'agent_run_id' LIMIT 1),
    (SELECT call.work_item_id FROM vnext.tool_call call
      WHERE (call.tenant_id,call.project_id,call.task_id)=(o.tenant_id,o.project_id,o.task_id)
        AND call.tool_call_id=o.payload_json::jsonb->>'tool_call_id' LIMIT 1),
    (SELECT run.work_item_id FROM vnext.tool_attempt attempt
      JOIN vnext.agent_run run USING(tenant_id,project_id,task_id,agent_run_id)
      WHERE (attempt.tenant_id,attempt.project_id,attempt.task_id)=(o.tenant_id,o.project_id,o.task_id)
        AND attempt.tool_attempt_id=o.payload_json::jsonb->>'tool_attempt_id' LIMIT 1),
    (SELECT run.work_item_id FROM vnext.result_submission submission
      JOIN vnext.agent_run run USING(tenant_id,project_id,task_id,agent_run_id)
      WHERE (submission.tenant_id,submission.project_id,submission.task_id)=(o.tenant_id,o.project_id,o.task_id)
        AND submission.submission_id=o.payload_json::jsonb->>'submission_id' LIMIT 1),
    (SELECT run.work_item_id FROM vnext.claim_revision claim
      JOIN vnext.agent_run run USING(tenant_id,project_id,task_id,agent_run_id)
      WHERE (claim.tenant_id,claim.project_id,claim.task_id)=(o.tenant_id,o.project_id,o.task_id)
        AND COALESCE(o.payload_json::jsonb->'canonical_ref'->>'entity_type',o.payload_json::jsonb->'claim_ref'->>'entity_type')='claim'
        AND claim.entity_id=COALESCE(o.payload_json::jsonb->'canonical_ref'->>'id',o.payload_json::jsonb->'claim_ref'->>'id')
        AND claim.revision::text=COALESCE(o.payload_json::jsonb->'canonical_ref'->>'revision',o.payload_json::jsonb->'claim_ref'->>'revision') LIMIT 1),
    (SELECT run.work_item_id FROM vnext.intent_revision intent
      JOIN vnext.agent_run run USING(tenant_id,project_id,task_id,agent_run_id)
      WHERE (intent.tenant_id,intent.project_id,intent.task_id)=(o.tenant_id,o.project_id,o.task_id)
        AND o.payload_json::jsonb->'canonical_ref'->>'entity_type'='intent'
        AND intent.entity_id=o.payload_json::jsonb->'canonical_ref'->>'id'
        AND intent.revision::text=o.payload_json::jsonb->'canonical_ref'->>'revision' LIMIT 1),
    (SELECT run.work_item_id FROM vnext.assessment assessment
      JOIN vnext.claim_revision claim ON
        (claim.tenant_id,claim.project_id,claim.task_id,claim.entity_id,claim.revision)=
        (assessment.tenant_id,assessment.project_id,assessment.task_id,assessment.claim_id,assessment.claim_revision)
      JOIN vnext.agent_run run ON
        (run.tenant_id,run.project_id,run.task_id,run.agent_run_id)=
        (claim.tenant_id,claim.project_id,claim.task_id,claim.agent_run_id)
      WHERE (assessment.tenant_id,assessment.project_id,assessment.task_id)=(o.tenant_id,o.project_id,o.task_id)
        AND assessment.assessment_id=o.payload_json::jsonb->>'assessment_id' LIMIT 1),
    (SELECT run.work_item_id FROM vnext.observation observation
      JOIN vnext.tool_attempt attempt USING(tenant_id,project_id,task_id,tool_attempt_id)
      JOIN vnext.agent_run run USING(tenant_id,project_id,task_id,agent_run_id)
      WHERE (observation.tenant_id,observation.project_id,observation.task_id)=(o.tenant_id,o.project_id,o.task_id)
        AND observation.entity_id=o.payload_json::jsonb->'observation_ref'->>'id'
        AND observation.revision::text=o.payload_json::jsonb->'observation_ref'->>'revision' LIMIT 1),
    (SELECT input.work_item_id FROM vnext.input_request input
      WHERE (input.tenant_id,input.project_id,input.task_id)=(o.tenant_id,o.project_id,o.task_id)
        AND input.input_request_id=o.payload_json::jsonb->>'input_request_id' LIMIT 1)
)"""


def _encoded_cursor(task_id, filters, direction, event_seq):
    body = canonical_json_bytes({
        "task_id": task_id,
        "filters": filters,
        "direction": direction,
        "event_seq": int(event_seq),
    })
    return base64.urlsafe_b64encode(body).rstrip(b"=").decode("ascii")


def _decoded_cursor(raw, *, task_id, filters, direction):
    if not isinstance(raw, str) or not 1 <= len(raw) <= 4096:
        raise DomainError("INVALID_SCHEMA", 422)
    try:
        document = strict_json_loads(
            base64.b64decode(
                raw + "=" * (-len(raw) % 4), altchars=b"-_", validate=True
            )
        )
    except (TypeError, ValueError):
        raise DomainError("INVALID_SCHEMA", 422) from None
    if (
        not isinstance(document, dict)
        or set(document) != {"task_id", "filters", "direction", "event_seq"}
        or document["task_id"] != task_id
        or document["filters"] != filters
        or document["direction"] != direction
        or type(document["event_seq"]) is not int
        or document["event_seq"] < 0
    ):
        raise DomainError("INVALID_SCHEMA", 422)
    return document["event_seq"]


def _status_message(task):
    if task["desired_state"] == "cancel" and task["observed_state"] != "closed":
        return "停止请求已受理，正在等待运行环境停止。"
    return {
        "ready": "任务尚未启动。",
        "running": "任务正在运行。",
        "quiescing": "任务正在结束剩余工作。",
        "paused": "任务已暂停，已有结果仍可查看。",
        "reconciling": "平台正在核对执行状态。",
        "closed": "任务已经停止。",
    }[task["observed_state"]]


def _summary_text(value, maximum):
    return value[:maximum] if isinstance(value, str) and value else None


class TaskReadViews:
    def __init__(self, uow) -> None:
        self.uow = uow

    @staticmethod
    def _definition(tx):
        raw = tx.task.get("definition_json")
        digest = tx.task.get("definition_digest")
        if not isinstance(raw, str) or sha256(raw.encode()).hexdigest() != digest:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        definition = strict_json_loads(raw)
        if not isinstance(definition, dict) or not isinstance(definition.get("task"), dict):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        return definition

    @staticmethod
    def _criteria(tx, definition):
        judgments = {
            value[0]: value[1:]
            for value in tx.connection.execute(
                """SELECT criterion.criterion_id,judgment.status,judgment.applicability
                FROM vnext.goal_criterion criterion
                LEFT JOIN vnext.criterion_judgment judgment ON
                  (judgment.tenant_id,judgment.project_id,judgment.task_id,judgment.judgment_id)=
                  (criterion.tenant_id,criterion.project_id,criterion.task_id,criterion.current_judgment_id)
                WHERE criterion.tenant_id=%s AND criterion.project_id=%s AND criterion.task_id=%s
                  AND criterion.revision=1""",
                tx.owner,
            ).fetchall()
        }
        result = []
        for criterion in definition["task"]["goal"]["criteria"]:
            status, applicability = judgments.get(
                criterion["criterion_id"], (None, None)
            )
            result.append({
                "criterion_id": criterion["criterion_id"],
                "object": criterion["object"],
                "condition": criterion["condition"],
                "required": criterion["required"],
                "judgment_status": status or "missing",
                "judgment_applicability": applicability or "missing",
            })
        return result

    @staticmethod
    def _current_work(tx):
        rows = tx.connection.execute(
            """SELECT work.work_item_id,work.kind,work.state,intent.question,
            work.blocked_reason,work.terminal_reason,run.process_state,run.result_state,
            result.work_result_json,COALESCE(run.exited_at,run.started_at,scheduler.ready_since)
            FROM vnext.work_item work
            LEFT JOIN vnext.intent_revision intent ON
              (intent.tenant_id,intent.project_id,intent.task_id,intent.entity_id,intent.revision)=
              (work.tenant_id,work.project_id,work.task_id,work.intent_id,work.intent_revision)
            LEFT JOIN vnext.agent_run run ON
              (run.tenant_id,run.project_id,run.task_id,run.agent_run_id)=
              (work.tenant_id,work.project_id,work.task_id,work.current_run_id)
            LEFT JOIN vnext.result_submission result ON
              (result.tenant_id,result.project_id,result.task_id,result.submission_id)=
              (run.tenant_id,run.project_id,run.task_id,run.result_submission_id)
            LEFT JOIN vnext.scheduler_work scheduler ON
              (scheduler.tenant_id,scheduler.project_id,scheduler.task_id,scheduler.work_item_id)=
              (work.tenant_id,work.project_id,work.task_id,work.work_item_id)
            WHERE work.tenant_id=%s AND work.project_id=%s AND work.task_id=%s
              AND work.state NOT IN ('done','failed','cancelled')
            ORDER BY COALESCE(run.exited_at,run.started_at,scheduler.ready_since) DESC NULLS LAST,
              work.work_item_id LIMIT 5""",
            tx.owner,
        ).fetchall()
        result = []
        for value in rows:
            work_result = None
            if value[7] == "accepted" and value[8] is not None:
                work_result = read_work_result(value[8]).effective_result()
            result.append({
                "work_item_id": value[0],
                "kind": value[1],
                "state": value[2],
                "question": value[3],
                "result_summary": None if work_result is None else work_result.summary,
                "blocked_reason": _summary_text(value[4], 1024),
                "terminal_reason": _summary_text(value[5], 1024),
                "run_process_state": value[6],
                "updated_at": value[9],
            })
        return result

    @staticmethod
    def _findings(tx):
        cursor = tx.connection.execute(
            """SELECT latest.* FROM (
              SELECT DISTINCT ON(entity_id) * FROM vnext.claim_revision
              WHERE tenant_id=%s AND project_id=%s AND task_id=%s
              ORDER BY entity_id,revision DESC
            ) latest ORDER BY latest.created_at DESC,latest.entity_id LIMIT 5""",
            tx.owner,
        )
        claims = [
            dict(zip((column.name for column in cursor.description), value))
            for value in cursor.fetchall()
        ]
        result = []
        for claim in claims:
            try:
                assessment = aggregate(tx, claim)
            except DomainError as error:
                if error.code == "CAPABILITY_UNAVAILABLE":
                    continue
                raise
            assessment_ids = [item.root for item in assessment.assessment_ids]

            def assessed_refs(evidence_state):
                if not assessment_ids:
                    return []
                rows = tx.connection.execute(
                    """SELECT DISTINCT input.entity_type,input.entity_id,input.revision
                    FROM vnext.assessment_input input
                    JOIN vnext.assessment assessment ON
                      (assessment.tenant_id,assessment.project_id,assessment.task_id,
                       assessment.assessment_id,assessment.revision)=
                      (input.tenant_id,input.project_id,input.task_id,
                       input.assessment_id,input.assessment_revision)
                    WHERE input.tenant_id=%s AND input.project_id=%s AND input.task_id=%s
                      AND assessment.assessment_id=ANY(%s::text[])
                      AND assessment.method_kind<>'model_review'
                      AND assessment.grounding_state='content_checked'
                      AND assessment.evidence_state=%s
                      AND (%s='contradicted' OR assessment.applicability_state='current')
                    ORDER BY input.entity_type,input.entity_id,input.revision LIMIT 32""",
                    (*tx.owner, assessment_ids, evidence_state, evidence_state),
                ).fetchall()
                return [
                    KnowledgeRef.model_validate({
                        "entity_type": value[0], "id": value[1], "revision": str(value[2])
                    })
                    for value in rows
                ]

            updated = tx.connection.execute(
                """SELECT max(created_at) FROM vnext.assessment
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                  AND claim_id=%s AND claim_revision=%s""",
                (*tx.owner, claim["entity_id"], claim["revision"]),
            ).fetchone()[0] or claim["created_at"]
            result.append({
                "claim_ref": {
                    "entity_type": "claim",
                    "id": claim["entity_id"],
                    "revision": str(claim["revision"]),
                },
                "text": claim["text"],
                "kind": claim["kind"],
                "grounding_state": assessment.grounding_state,
                "evidence_state": assessment.evidence_state,
                "applicability_state": assessment.applicability_state,
                "supporting_refs": assessed_refs("supported"),
                "opposing_refs": assessed_refs("contradicted"),
                "updated_at": updated,
            })
        return result

    @staticmethod
    def _artifacts(tx):
        rows = tx.connection.execute(
            """SELECT artifact.entity_id,artifact.revision,artifact.sha256,artifact.state,
            artifact.media_type,artifact.size_bytes,artifact.completeness,artifact.provenance,
            artifact.created_at,artifact.body_removed,COALESCE(direct.work_item_id,captured.work_item_id)
            FROM vnext.artifact artifact
            LEFT JOIN vnext.agent_run direct ON
              (direct.tenant_id,direct.project_id,direct.task_id,direct.agent_run_id)=
              (artifact.tenant_id,artifact.project_id,artifact.task_id,artifact.agent_run_id)
            LEFT JOIN vnext.tool_attempt attempt ON
              (attempt.tenant_id,attempt.project_id,attempt.task_id,attempt.tool_attempt_id)=
              (artifact.tenant_id,artifact.project_id,artifact.task_id,artifact.tool_attempt_id)
            LEFT JOIN vnext.agent_run captured ON
              (captured.tenant_id,captured.project_id,captured.task_id,captured.agent_run_id)=
              (attempt.tenant_id,attempt.project_id,attempt.task_id,attempt.agent_run_id)
            WHERE artifact.tenant_id=%s AND artifact.project_id=%s AND artifact.task_id=%s
              AND artifact.provenance IN ('capture','import')
            ORDER BY artifact.created_at DESC,artifact.entity_id,artifact.revision DESC LIMIT 100""",
            tx.owner,
        ).fetchall()
        return [{
            "artifact_ref": {"id": value[0], "version": str(value[1]), "sha256": value[2]},
            "state": value[3],
            "media_type": value[4],
            "size_bytes": str(value[5]),
            "completeness": value[6],
            "provenance": value[7],
            "created_at": value[8],
            "source_work_item_id": value[10],
            "download_available": value[3] == "sealed" and not value[9],
        } for value in rows]

    @staticmethod
    def _runtime(tx, definition):
        attempt = str(tx.task["runtime_attempt"])
        receiver = tx.connection.execute(
            """SELECT pod_uid FROM vnext.scheduler_receiver WHERE tenant_id=%s
            AND project_id=%s AND task_id=%s AND runtime_attempt=%s""",
            (*tx.owner, attempt),
        ).fetchone()
        receiver_uid = None if receiver is None else receiver[0]
        records = tx.connection.execute(
            """SELECT terminal_observation_id,execution_epoch,pod_uid,
              container_name,document_json FROM vnext.runtime_terminal_observation
            WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND runtime_attempt=%s
            ORDER BY container_name LIMIT 5""",
            (*tx.owner, attempt),
        ).fetchall()
        bindings = {(str(value[1]), value[2]) for value in records}
        valid_binding = len(bindings) == 1 and (
            receiver_uid is None or next(iter(bindings))[1] == receiver_uid
        )
        pod_uid = receiver_uid or (next(iter(bindings))[1] if valid_binding else None)
        documents = []
        ids = []
        containers = {}
        if valid_binding and len(records) <= 4:
            for observation_id, _, _, name, document in records:
                value = strict_json_loads(document)
                ids.append(observation_id)
                documents.append(value)
                containers[name] = value["state"]
        core = (definition.get("runtime_profile") or {}).get("capture_policy") is not None
        complete = (
            valid_binding
            and pod_uid is not None
            and terminal_container_states(
                tx, runtime_attempt=attempt,
                execution_epoch=next(iter(bindings))[0], pod_uid=pod_uid,
            ) is not None
        )
        if tx.task["activated_at"] is None:
            state = "not_started"
        elif complete:
            state = "stopped"
        elif (
            tx.task["desired_state"] in {"cancel", "pause"}
            or not tx.task["execution_allowed"]
            or tx.task["observed_state"] in {"quiescing", "reconciling"}
        ):
            state = "stopping"
        elif core and pod_uid is not None and tx.task["observed_state"] == "running":
            state = "running"
        else:
            state = "unknown"
        return {
            "state": state,
            "runtime_attempt": attempt,
            "pod_uid": pod_uid,
            "containers": containers,
            "terminal_observation_ids": ids,
            "terminal_observations": documents,
        }

    def overview(self, access, task_id):
        if not isinstance(access, AccessContext):
            raise TypeError("the authenticated AccessContext is required")
        with self.uow.transaction(access, task_id, repeatable_read=True) as tx:
            definition = self._definition(tx)
            task = definition["task"]
            launch = strict_json_loads(
                tx.connection.execute(
                    "SELECT vnext.read_task_launch(%s)", (task_id,)
                ).fetchone()[0]
            )
            capabilities = set((definition.get("runtime_profile") or {}).get("capabilities") or [])
            return TaskOverviewV1.model_validate({
                "schema_version": "wuji.task-overview.v1",
                "task_id": task_id,
                "observed_at": datetime.now(timezone.utc),
                "status_message": _status_message(tx.task),
                "goal": {"text": task["goal"]["text"], "criteria": self._criteria(tx, definition)},
                "budget": task["budget"],
                "current_work": self._current_work(tx),
                "latest_findings": self._findings(tx),
                "artifacts": self._artifacts(tx),
                "workspace_capabilities": {
                    "work_files": "work_files" in capabilities,
                    "shared_versions": "shared_versions" in capabilities,
                    "command_output": "command_output" in capabilities,
                },
                "runtime": self._runtime(tx, definition),
                "technical": {
                    "definition_digest": tx.task["definition_digest"],
                    "control_version": str(tx.task["control_version"]),
                    "execution_epoch": str(tx.task["execution_epoch"]),
                    "runtime_attempt": str(tx.task["runtime_attempt"]),
                    "schema_version": task["schema_version"],
                    "latest_launch_operation_id": launch["operation_id"],
                    "latest_launch_phase": launch["phase"],
                    "latest_launch_reason_code": launch["reason_code"],
                },
            })

    def command_inventory(self, access, task_id, *, limit=50, after=None):
        if type(limit) is not int or not 1 <= limit <= 100 or (
            after is not None and (not isinstance(after, str) or not 1 <= len(after) <= 256)
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        with self.uow.transaction(access, task_id, repeatable_read=True) as tx:
            values = tx.connection.execute(
                """SELECT process.tool_attempt_id,run.work_item_id,
                  process.state,process.exit_code,process.output_completeness,
                  attempt.permit_json
                FROM vnext.process_execution process
                JOIN vnext.tool_attempt attempt USING(tenant_id,project_id,task_id,tool_attempt_id)
                JOIN vnext.agent_run run ON
                  (run.tenant_id,run.project_id,run.task_id,run.agent_run_id)=
                  (process.tenant_id,process.project_id,process.task_id,process.agent_run_id)
                WHERE process.tenant_id=%s AND process.project_id=%s AND process.task_id=%s
                  AND process.tool_attempt_id>%s
                  AND attempt.process_action='exec'
                ORDER BY process.tool_attempt_id LIMIT %s""",
                (*tx.owner, after or "", limit + 1),
            ).fetchall()
            page = values[:limit]
            ids = [value[0] for value in page]
            refs = {identity: [] for identity in ids}
            if ids:
                for identity, artifact_id, revision, digest in tx.connection.execute(
                    """SELECT tool_attempt_id,entity_id,revision,sha256 FROM vnext.artifact
                    WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                      AND tool_attempt_id=ANY(%s) AND state='sealed' AND NOT body_removed
                      AND media_type='application/vnd.wuji.command-log+json'
                    ORDER BY tool_attempt_id,entity_id,revision""",
                    (*tx.owner, ids),
                ).fetchall():
                    refs[identity].append({
                        "id": artifact_id, "version": str(revision), "sha256": digest,
                    })
            items = []
            for identity, work_id, state, exit_code, completeness, permit_json in page:
                permit = strict_json_loads(permit_json)
                command = permit["arguments"]["command"]
                items.append({
                    "work_item_id": work_id,
                    "exec_id": identity,
                    "command": command[:1024],
                    "state": state,
                    "exit_code": exit_code,
                    "output_completeness": completeness,
                    "output_refs": refs[identity][:16],
                    "assurance": "executor_reported",
                })
        return TaskCommandInventoryV1.model_validate({
            "schema_version": "wuji.command-inventory.v1",
            "items": items,
            "next_after": page[-1][0] if len(values) > limit else None,
        })

    def publications(self, access, task_id, *, limit=50, after=None):
        if type(limit) is not int or not 1 <= limit <= 100 or (
            after is not None and (not isinstance(after, str) or not 1 <= len(after) <= 256)
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        with self.uow.transaction(access, task_id, repeatable_read=True) as tx:
            values = tx.connection.execute(
                """SELECT publication.publication_id,publication.asset_id,
                  publication.asset_revision,run.work_item_id,run.agent_run_id,
                  artifact.entity_id,artifact.revision,artifact.sha256,
                  publication.created_at
                FROM vnext.publication publication
                JOIN vnext.tool_attempt attempt ON
                  (attempt.tenant_id,attempt.project_id,attempt.task_id,attempt.tool_attempt_id)=
                  (publication.tenant_id,publication.project_id,publication.task_id,
                   publication.source_tool_attempt_id)
                JOIN vnext.agent_run run ON
                  (run.tenant_id,run.project_id,run.task_id,run.agent_run_id)=
                  (attempt.tenant_id,attempt.project_id,attempt.task_id,attempt.agent_run_id)
                JOIN vnext.artifact artifact ON
                  (artifact.tenant_id,artifact.project_id,artifact.task_id,
                   artifact.entity_id,artifact.revision)=
                  (publication.tenant_id,publication.project_id,publication.task_id,
                   publication.manifest_artifact_id,publication.manifest_artifact_revision)
                WHERE publication.tenant_id=%s AND publication.project_id=%s
                  AND publication.task_id=%s AND publication.publication_id>%s
                  AND publication.kind='workspace_bundle.v1'
                  AND artifact.state='sealed' AND NOT artifact.body_removed
                ORDER BY publication.publication_id LIMIT %s""",
                (*tx.owner, after or "", limit + 1),
            ).fetchall()
            page = values[:limit]
            items = [{
                "publication_id": value[0],
                "asset_id": value[1],
                "asset_revision": str(value[2]),
                "producer_work_item_id": value[3],
                "producer_run_id": value[4],
                "manifest_ref": {
                    "id": value[5], "version": str(value[6]), "sha256": value[7],
                },
                "created_at": value[8],
                "download_url": (
                    f"/api/v2/artifacts/{quote(value[5], safe='')}/content"
                    f"?version={value[6]}"
                ),
            } for value in page]
        return TaskPublicationPageV1.model_validate({
            "schema_version": "wuji.task-publications.v1",
            "items": items,
            "next_after": page[-1][0] if len(values) > limit else None,
        })

    @staticmethod
    def _event_item(tx, event, filters):
        seq, kind, raw, created_at, work_id = event
        category, importance, status, summary = _EVENTS[kind]
        payload = strict_json_loads(raw)
        payload = payload if isinstance(payload, dict) else {}
        if not isinstance(work_id, str):
            work_id = None
        state = payload.get("state")
        observed_kind = payload.get("kind")
        if kind in {"work.settled", "work.reconciled"} and isinstance(state, str):
            status = {
                "done": "succeeded", "failed": "failed", "cancelled": "stopped",
                "blocked": "blocked", "running": "running",
            }.get(state, status)
            summary = {
                "done": "工作已完成", "failed": "工作失败", "cancelled": "工作已取消",
                "blocked": "工作被阻断",
            }.get(state, summary)
        elif kind == "execution.observed" and isinstance(observed_kind, str):
            status, summary = {
                "started": ("running", "工作开始执行"),
                "exited": ("info", "执行进程已退出，结果仍需核对"),
                "environment_stopped": ("stopped", "运行环境已停止"),
                "not_started": ("stopped", "工作没有启动"),
                "unknown": ("blocked", "执行状态需要核对"),
            }.get(observed_kind, (status, summary))
        reason = _summary_text(payload.get("reason") or payload.get("terminal_reason"), 2048)
        refs = []
        candidates = [payload.get(key) for key in ("observation_ref", "claim_ref", "canonical_ref")]
        components = payload.get("components")
        if isinstance(components, list):
            candidates.extend(
                component.get("canonical_ref")
                for component in components
                if isinstance(component, dict)
            )
        for candidate in candidates:
            if candidate is not None:
                try:
                    ref = KnowledgeRef.model_validate(candidate)
                    if ref not in refs:
                        refs.append(ref)
                except ValueError:
                    pass
        step_count = 0
        if work_id is not None and kind in {"work.settled", "result_committed"}:
            step_count = tx.connection.execute(
                """SELECT count(*) FROM vnext.tool_attempt attempt
                JOIN vnext.tool_call call USING(tenant_id,project_id,task_id,tool_call_id)
                WHERE attempt.tenant_id=%s AND attempt.project_id=%s AND attempt.task_id=%s
                  AND call.work_item_id=%s""",
                (*tx.owner, work_id),
            ).fetchone()[0]
        return {
            "activity_id": "event-" + str(seq),
            "event_cursor": _encoded_cursor(tx.owner[2], filters, "after", seq),
            "occurred_at": created_at,
            "category": category,
            "importance": importance,
            "status": status,
            "summary": summary,
            "work_item_id": work_id,
            "source_ref": "event:" + str(seq),
            "reason": reason,
            "evidence_refs": refs[:32],
            "step_count": int(step_count),
        }

    def activity(
        self,
        access,
        task_id,
        *,
        limit=20,
        cursor=None,
        after_cursor=None,
        importance="key",
        category=None,
        work_item_id=None,
    ):
        if not isinstance(access, AccessContext):
            raise TypeError("the authenticated AccessContext is required")
        if type(limit) is not int or not 1 <= limit <= 100 or importance not in {"key", "all"}:
            raise DomainError("INVALID_SCHEMA", 422)
        if cursor is not None and after_cursor is not None:
            raise DomainError("INVALID_SCHEMA", 422)
        categories = {value[0] for value in _EVENTS.values()}
        if category is not None and category not in categories:
            raise DomainError("INVALID_SCHEMA", 422)
        if work_item_id is not None and (
            not isinstance(work_item_id, str) or not 1 <= len(work_item_id) <= 256
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        filters = {
            "importance": importance,
            "category": category,
            "work_item_id": work_item_id,
        }
        direction = "after" if after_cursor is not None else "history"
        bound = None
        if cursor is not None:
            bound = _decoded_cursor(cursor, task_id=task_id, filters=filters, direction="history")
        elif after_cursor is not None:
            bound = _decoded_cursor(after_cursor, task_id=task_id, filters=filters, direction="after")
        allowed_kinds = [
            kind for kind, value in _EVENTS.items()
            if (importance == "all" or value[1] == "key")
            and (category is None or value[0] == category)
        ]
        with self.uow.transaction(access, task_id, repeatable_read=True) as tx:
            clauses = [
                "o.tenant_id=%s", "o.project_id=%s", "o.task_id=%s", "o.kind=ANY(%s)"
            ]
            params = [*tx.owner, allowed_kinds]
            if bound is not None:
                clauses.append("o.event_seq>%s" if direction == "after" else "o.event_seq<%s")
                params.append(bound)
            if work_item_id is not None:
                clauses.append("resolved.work_item_id=%s")
                params.append(work_item_id)
            params.append(limit + 1)
            rows = tx.connection.execute(
                "SELECT o.event_seq,o.kind,o.payload_json,o.created_at,resolved.work_item_id "
                "FROM vnext.outbox o CROSS JOIN LATERAL (SELECT "
                + _WORK_ITEM_SQL
                + " AS work_item_id) resolved WHERE "
                + " AND ".join(clauses)
                + (" ORDER BY o.event_seq ASC" if direction == "after" else " ORDER BY o.event_seq DESC")
                + " LIMIT %s",
                tuple(params),
            ).fetchall()
            has_more = len(rows) > limit
            page_rows = rows[:limit]
            items = [self._event_item(tx, event, filters) for event in page_rows]
            next_cursor = None
            if direction == "history" and has_more and page_rows:
                next_cursor = _encoded_cursor(task_id, filters, "history", page_rows[-1][0])
            latest_seq = (
                page_rows[-1][0]
                if direction == "after" and has_more and page_rows
                else tx.task["event_seq"]
            )
            return TaskActivityPageV1.model_validate({
                "schema_version": "wuji.task-activity.v1",
                "task_id": task_id,
                "observed_at": datetime.now(timezone.utc),
                "latest_cursor": _encoded_cursor(task_id, filters, "after", latest_seq),
                "items": items,
                "next_cursor": next_cursor,
            })
