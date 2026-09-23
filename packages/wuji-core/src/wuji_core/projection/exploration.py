"""Problem-centered projection from already-authorized fixed records."""

from hashlib import sha256

from wuji_core.contracts.generated import (
    ExplorationInsightV1,
    ExplorationProblemV1,
    ExplorationRelationV1,
)
from wuji_core.blackboard.work_results import read_work_result
from wuji_core.contracts.knowledge import ClaimRecord, IntentRecord
from wuji_core.http.json_boundary import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import row
from wuji_core.projection.builder import node_id


PROJECTION_VERSION = "wuji.exploration.v1"


def _metadata(tx, intent_records):
    """Read accepted public metadata without creating missing history."""

    result = {}
    for record in intent_records:
        ref = record.ref
        value = row(tx.connection.execute(
            """SELECT i.planning_json,
            COALESCE(b.canonical_work_item_id,s.work_item_id) AS work_item_id,
            w.state,w.terminal_reason,w.current_run_id,r.work_result_json
            FROM vnext.intent_revision i
            LEFT JOIN vnext.intent_work_binding b ON
              (b.tenant_id,b.project_id,b.task_id,b.intent_id,b.intent_revision)=
              (i.tenant_id,i.project_id,i.task_id,i.entity_id,i.revision)
            LEFT JOIN vnext.scheduler_work s ON
              (s.tenant_id,s.project_id,s.task_id,s.intent_id,s.intent_revision)=
              (i.tenant_id,i.project_id,i.task_id,i.entity_id,i.revision)
            LEFT JOIN vnext.work_item w ON
              (w.tenant_id,w.project_id,w.task_id,w.work_item_id)=
              (i.tenant_id,i.project_id,i.task_id,COALESCE(b.canonical_work_item_id,s.work_item_id))
            LEFT JOIN vnext.agent_run a ON
              (a.tenant_id,a.project_id,a.task_id,a.agent_run_id)=
              (w.tenant_id,w.project_id,w.task_id,w.current_run_id)
            LEFT JOIN vnext.result_submission r ON
              (r.tenant_id,r.project_id,r.task_id,r.submission_id)=
              (a.tenant_id,a.project_id,a.task_id,a.result_submission_id)
            WHERE i.tenant_id=%s AND i.project_id=%s AND i.task_id=%s
              AND i.entity_id=%s AND i.revision=%s""",
            (*tx.owner, ref.id, ref.revision.root),
        ))
        if value is None:
            continue
        attempts = []
        work_id = value["work_item_id"]
        if work_id is not None:
            for attempt in tx.connection.execute(
                """SELECT a.tool_attempt_id,a.status,c.tool_definition_version
                FROM vnext.tool_attempt a JOIN vnext.tool_call c
                  USING(tenant_id,project_id,task_id,tool_call_id)
                WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s
                  AND c.work_item_id=%s ORDER BY a.tool_attempt_id""",
                (*tx.owner, work_id),
            ).fetchall():
                attempts.append({
                    "kind": "environment_action",
                    "status": attempt[1] or "unknown",
                    "summary": "环境工具 " + attempt[2] + " · " + (attempt[1] or "unknown"),
                    "source_ref": "tool_attempt:" + attempt[0],
                })
            for delivery in tx.connection.execute(
                """SELECT delivery_id,kind,state FROM vnext.knowledge_delivery
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s
                ORDER BY prepared_at,delivery_id""",
                (*tx.owner, work_id),
            ).fetchall():
                attempts.append({
                    "kind": "knowledge_read",
                    "status": delivery[2],
                    "summary": "资料交付 " + delivery[1] + " · " + delivery[2],
                    "source_ref": "knowledge_delivery:" + delivery[0],
                })
        work_result = (
            read_work_result(value["work_result_json"]).effective_result()
            if value["work_result_json"] is not None
            else None
        )
        if work_result is not None:
            attempts.append({
                "kind": "work_result",
                "status": work_result.outcome.value,
                "summary": work_result.summary,
                "source_ref": "work_item:" + work_id,
            })
        result[node_id(ref)] = {
            "planning": strict_json_loads(value["planning_json"]) if value["planning_json"] else None,
            "work_item_id": work_id,
            "state": value["state"],
            "terminal_reason": value["terminal_reason"],
            "work_result": work_result,
            "attempts": attempts,
        }
    return result


def _relation_id(kind, source, target, witnesses):
    return "exploration:" + sha256(
        canonical_json_bytes([kind, source, target, sorted(witnesses)])
    ).hexdigest()


def build_exploration(records, relations, *, metadata, can_control=False):
    """Purely map fixed records; nulls stay null and no model fills history."""

    intents = [record for record in records if isinstance(record.record.root, IntentRecord)]
    claims = [record for record in records if isinstance(record.record.root, ClaimRecord)]
    problem_ids = {node_id(record.ref) for record in intents}
    insight_ids = {node_id(record.ref) for record in claims}
    problems = []
    for record in intents:
        ref, intent = record.ref, record.record.root
        info = metadata.get(node_id(ref), {})
        planning = info.get("planning")
        work_result = info.get("work_result")
        gaps = []
        if work_result is not None:
            gaps.extend(item.root for item in work_result.unresolved_items)
            gaps.extend(item.root for item in work_result.capability_gaps)
        if info.get("work_item_id") is None:
            gaps.append("规范工作尚未登记")
        elif info.get("terminal_reason"):
            gaps.append(info["terminal_reason"])
        actions = []
        if can_control and info.get("work_item_id") is not None:
            state = info.get("state")
            if state in {"leased", "running", "waiting_input", "blocked", "suspended"}:
                actions.append("cancel")
            if state in {"leased", "running"}:
                actions.append("hold")
            if state in {"waiting_input", "blocked", "suspended"}:
                actions.append("resume")
        problems.append(ExplorationProblemV1.model_validate({
            "intent_ref": ref,
            "canonical_work_ref": info.get("work_item_id"),
            "question": intent.question,
            "public_rationale": planning.get("public_rationale") if planning else None,
            "goal_criterion_refs": planning.get("goal_criterion_refs", []) if planning else [],
            "execution_state": info.get("state"),
            "work_result": work_result,
            "basis_refs": intent.basis_refs,
            "attempts": info.get("attempts", []),
            "gaps": gaps,
            "todo_summary": [],
            "allowed_actions": actions,
        }))

    insights = []
    for record in claims:
        claim, assessment = record.record.root, record.assessment
        grounding = "unchecked" if assessment is None else assessment.grounding_state.value
        evidence = "unassessed" if assessment is None else assessment.evidence_state.value
        applicability = "current" if assessment is None else assessment.applicability_state.value
        basis = list(claim.basis_refs)
        insights.append(ExplorationInsightV1.model_validate({
            "claim_ref": record.ref,
            "text": claim.text,
            "kind": claim.kind,
            "grounding_state": grounding,
            "evidence_state": evidence,
            "applicability_state": applicability,
            "source_refs": basis,
            "limitations": [item.root for item in claim.limitations]
                + ([] if assessment is None else [item.root for item in assessment.limitations]),
            "supporting_refs": basis if evidence == "supported" else [],
            "opposing_refs": basis if evidence == "contradicted" else [],
        }))

    projected_relations = []
    direct = {
        "basis": "basis",
        "input_to": "input_to",
        "supersedes": "supersedes",
        "contradicts": "contradicts",
        "depends_on": "depends_on",
    }
    for relation in relations:
        source, target = node_id(relation.source), node_id(relation.target)
        kind = direct.get(relation.edge_type)
        if kind is None or source not in problem_ids | insight_ids or target not in problem_ids | insight_ids:
            continue
        witnesses = ["relation:" + relation.relation_id]
        projected_relations.append(ExplorationRelationV1.model_validate({
            "relation_id": _relation_id(kind, source, target, witnesses),
            "kind": kind,
            "source_ref": source,
            "target_ref": target,
            "witness_refs": witnesses,
        }))
    return tuple(problems), tuple(insights), tuple(projected_relations)


class ExplorationReadModel:
    def materialize(self, tx, frozen):
        intents = [record for record in frozen.records if isinstance(record.record.root, IntentRecord)]
        return build_exploration(
            frozen.records,
            frozen.relations,
            metadata=_metadata(tx, intents),
            can_control=bool(tx.permissions.get("can_control")),
        )
