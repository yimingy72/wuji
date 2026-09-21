from hashlib import sha256

import pytest
from pydantic import ValidationError

from wuji_core.contracts.envelopes import AgentPayload, AgentPayloadV3
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence import schema
from wuji_maf_worker.factory import ProblemHarnessProfile, parse_profile
from support.p03 import access
from test_knowledge_admission import IDENTITY, TASK, case
from wuji_core.persistence.snapshots import SnapshotRepository


def test_v2_and_v3_are_explicit_and_mixed_payloads_are_rejected():
    old = AgentPayload.model_validate({
        "schema_version": "wuji.agent-payload.v2",
        "claims": [],
        "intent_proposals": [],
        "limitations": [],
        "reason_decision": None,
    })
    assert old.schema_version.root == "wuji.agent-payload.v2"

    value = {
        "schema_version": "wuji.agent-payload.v3",
        "claims": [],
        "intent_proposals": [],
        "reason_decision": {
            "decision": "blocked",
            "wait_refs": [],
            "public_rationale": "当前发布能力不足。",
            "basis_refs": [],
        },
        "work_result": None,
        "input_acknowledgements": [],
    }
    assert AgentPayloadV3.model_validate(value).for_work_kind("reason").reason_decision
    with pytest.raises(ValidationError):
        AgentPayloadV3.model_validate({**value, "schema_version": "wuji.agent-payload.v2"})
    with pytest.raises(ValueError, match="Explore requires"):
        AgentPayloadV3.model_validate(value).for_work_kind("explore")


def test_problem_profile_is_recognized_but_not_confused_with_session_v1():
    body = {
        "ref": "harness.explore.problem.v1",
        "revision": "1",
        "work_kind": "explore",
        "instructions": "解决固定问题并返回严格 JSON。",
        "tool_definition_refs": [],
        "material_representation": "wuji.model-material.v2",
        "lock_digest": "a" * 64,
        "max_context_records": 64,
        "max_context_bytes": 65536,
        "max_output_tokens": 4096,
        "capabilities": {
            "todo": True,
            "mode": False,
            "file_memory": True,
            "file_access": False,
            "skills": False,
            "shell": False,
            "web_search": False,
            "background_agents": False,
            "outer_loop": False,
            "auto_approval": False,
            "compaction": True,
            "restoration": True,
            "mcp": False,
            "native_approval": True,
            "versioned_memory": True,
        },
        "schema_version": "wuji.harness.problem.v1",
        "history_source_id": "history",
        "memory_mode": "work_memory",
        "memory_source_id": "memory",
        "session_limits": {
            "max_objects": 32,
            "max_reference_depth": 8,
            "max_object_bytes": 8192,
            "max_total_bytes": 65536,
            "max_messages": 256,
            "max_pending_approvals": 8,
        },
        "max_context_window_tokens": 65536,
        "compaction_enabled": True,
        "context_policy": {
            "policy_revision": "1",
            "initial_brief_bytes": 16384,
            "index_limit": 64,
            "default_read_bytes": 8192,
            "max_read_bytes": 16384,
            "max_delivered_bytes": 32768,
            "max_refreshes": 2,
            "renderer_version": "wuji-http-renderer.v2",
            "redaction_policy_ref": "redaction.v1",
        },
        "capability_manifest": [],
        "planning_policy": {
            "policy_revision": "1",
            "reason_proposal_limit": 3,
            "explore_proposal_limit": 2,
            "coalesce_milliseconds": 500,
            "max_delay_milliseconds": 5000,
            "no_progress_rounds": 3,
        },
        "work_memory_policy": {
            "store": "agent_file_store",
            "max_files": 8,
            "max_file_bytes": 8192,
            "max_total_bytes": 32768,
            "path_pattern": "^[a-z0-9][a-z0-9._/-]{0,127}$",
        },
        "function_limits": {
            "session_state_per_work": 16,
            "knowledge_read_per_work": 8,
            "environment_action_per_work": 0,
            "total_per_work": 24,
            "total_per_task": 24,
        },
        "tool_choice_policy": "auto",
        "completion_mode": "review_then_close",
    }
    snapshot = {
        "ref": body["ref"],
        "revision": body["revision"],
        "digest": sha256(canonical_json_bytes(body)).hexdigest(),
        "body": body,
    }
    profile = parse_profile(snapshot)
    assert isinstance(profile, ProblemHarnessProfile)
    assert profile.snapshot() == snapshot


def test_problem_core_migration_chain_reaches_the_current_head(db_environment):
    with db_environment.migration_connection() as connection:
        schema.migrate(connection, application_role=db_environment.application_role)
        assert connection.execute(
            "SELECT head FROM vnext.schema_migration WHERE head=%s", (schema.HEAD,)
        ).fetchone() == (schema.HEAD,)
        columns = {
            row[0]
            for row in connection.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='vnext' AND table_name IN "
                "('intent_work_binding','knowledge_delivery')"
            ).fetchall()
        }
        assert {"canonical_work_item_id", "problem_digest", "delivery_json", "state"} <= columns
        assert connection.execute(
            "SELECT planning_json IS NULL FROM vnext.intent_revision LIMIT 1"
        ).fetchone() is None
        assert connection.execute(
            "SELECT work_result_json IS NULL FROM vnext.result_submission LIMIT 1"
        ).fetchone() is None


def test_v3_result_persists_content_outcome_without_changing_work_state(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        worker = access("worker-fixture", role="worker")
        payload = {
            "schema_version": "wuji.agent-payload.v3",
            "claims": [], "intent_proposals": [], "reason_decision": None,
            "work_result": {
                "outcome": "answered", "summary": "The fixed problem is answered.",
                "answer_basis_refs": [], "unresolved_items": [], "capability_gaps": [],
            },
            "input_acknowledgements": [],
        }
        raw = canonical_json_bytes(payload)
        raw_ref = c.store.stage_model_output(
            worker, TASK, IDENTITY["agent_run_id"], raw, "text/plain; charset=utf-8"
        )
        c.store.seal(worker, TASK, raw_ref)
        delivery_bytes = canonical_json_bytes({
            "schema_version": "wuji.delivery-manifest.v1",
            "initial_snapshot_id": "pending", "context_digest": "a" * 64,
            "deliveries": [],
        })
        delivery_ref = c.store.stage_model_output(
            worker, TASK, IDENTITY["agent_run_id"], delivery_bytes,
            "application/vnd.wuji.delivery-manifest+json",
        )
        c.store.seal(worker, TASK, delivery_ref)
        snapshot = SnapshotRepository(c.uow).create(TASK, worker)
        envelope = {
            "schema_version": "wuji.result-envelope.v3",
            "submission_id": "problem-result-v3",
            "identity": IDENTITY,
            "initial_snapshot_id": snapshot.snapshot_id,
            "delivery_manifest_ref": delivery_ref.model_dump(mode="json"),
            "read_set": [], "native_tool_receipt_refs": [],
            "raw_output_ref": raw_ref.model_dump(mode="json"),
            "raw_output_digest": raw_ref.sha256.root,
            "payload": None, "producer_version": "problem-test",
        }
        receipt = c.committer.submit(worker, envelope)
        assert receipt.status.value == "accepted"
        with c.uow.transaction(worker, TASK) as tx:
            result, work_state = tx.connection.execute(
                "SELECT s.work_result_json,w.state FROM vnext.result_submission s "
                "JOIN vnext.agent_run a USING(tenant_id,project_id,task_id,agent_run_id) "
                "JOIN vnext.work_item w USING(tenant_id,project_id,task_id,work_item_id) "
                "WHERE s.submission_id='problem-result-v3'"
            ).fetchone()
        assert strict_json_loads(result)["outcome"] == "answered"
        assert work_state != "done", "content outcome must not forge execution settlement"
