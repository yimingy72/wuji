"""E02: one published compatibility table decides what a role may receive.

The Task's frozen runtime profile and the deployment's published role profile
both have to allow a tool, the tool's published target kind decides which role
may hold it, and the Scheduler refuses everything else before a Run exists.
These tests use a real PostgreSQL fixture and the production Scheduler; the
target never leaves the fixture because no Run is dispatched here.
"""

from __future__ import annotations

from hashlib import sha256
import json

import pytest

from support.p06 import ENVIRONMENT, OWNER, RECEIVER, TASK, TENANT, production
from support.p09 import TOOL_REF, explore_assignment, scheduler_case
from wuji_core.http import canonical_json_bytes
from wuji_core.persistence.uow import DomainError


HTTP_TOOL_REF = "fixture-http-target-v1"
HTTP_EXECUTOR_REF = "http-target-fixture"
HTTP_TOOL_DOCUMENT = {
    "ref": HTTP_TOOL_REF,
    "revision": "1",
    "published_at": "2026-09-17T00:00:00Z",
    "name": "fetch_authorized_page",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["url", "method"],
        "properties": {
            "url": {"type": "string", "minLength": 1, "maxLength": 4096},
            "method": {"type": "string", "enum": ["GET", "HEAD", "OPTIONS"]},
        },
    },
    "allowed_target_kinds": ["http_target"],
    "executor_ref": HTTP_EXECUTOR_REF,
    "approval_required": False,
}
HTTP_EXECUTOR_DOCUMENT = {
    "ref": HTTP_EXECUTOR_REF,
    "receiver_id": RECEIVER,
    "environment_ref": ENVIRONMENT,
    "collector_subject": "collector-fixture",
    "evidence_origin": "fixture_capture",
    "capture_layer": "fixture_http_bytes",
    "allowed_tool_refs": [HTTP_TOOL_REF],
}


def retool_profile(profile, refs, *, revision="2"):
    body = dict(profile["body"])
    body["tool_definition_refs"] = list(refs)
    body["ref"] = body["ref"] + ".v" + revision
    body["revision"] = revision
    return {
        "body": body,
        "digest": sha256(canonical_json_bytes(body)).hexdigest(),
        "ref": body["ref"],
        "revision": revision,
    }


def publish_target_capability(case, *, reason_refs=(TOOL_REF,)):
    """Publish the second tool and bind the task's roles exactly as above."""

    registry = production("admission.registry")
    with case.control.env.migration_connection() as connection:
        registry.register_tool_definition(
            connection,
            tenant_id=TENANT,
            definition=registry.ToolDefinition.model_validate(HTTP_TOOL_DOCUMENT),
        )
        registry.register_executor(
            connection,
            owner=OWNER,
            executor=registry.ExecutorRegistration.model_validate(HTTP_EXECUTOR_DOCUMENT),
        )
        admission = json.loads(
            connection.execute(
                "SELECT document_json FROM vnext.admission_config"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                OWNER,
            ).fetchone()[0]
        )
        admission["allowed_tool_refs"] = [TOOL_REF, HTTP_TOOL_REF]
        admission["runtime"]["allowed_tool_refs"] = [TOOL_REF, HTTP_TOOL_REF]
        connection.execute(
            "UPDATE vnext.admission_config SET document_json=%s"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
            (json.dumps(admission, sort_keys=True), *OWNER),
        )
        definition = json.loads(
            connection.execute(
                "SELECT definition_json FROM vnext.task WHERE task_id=%s", (TASK,)
            ).fetchone()[0]
        )
        definition["runtime_profile"]["allowed_tool_refs"] = [TOOL_REF, HTTP_TOOL_REF]
        definition["worker_profiles"]["explore"] = retool_profile(
            definition["worker_profiles"]["explore"], [TOOL_REF, HTTP_TOOL_REF]
        )
        definition["worker_profiles"]["reason"] = retool_profile(
            definition["worker_profiles"]["reason"], list(reason_refs)
        )
        definition["worker_profiles"]["report"] = retool_profile(
            definition["worker_profiles"]["report"], [TOOL_REF]
        )
        body = canonical_json_bytes(definition).decode()
        connection.execute(
            "UPDATE vnext.task SET definition_json=%s,definition_digest=%s"
            " WHERE task_id=%s",
            (body, sha256(body.encode()).hexdigest(), TASK),
        )
        connection.execute(
            "UPDATE vnext.scheduler_receiver SET harness_profiles_json=%s"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
            (canonical_json_bytes(definition["worker_profiles"]).decode(), *OWNER),
        )
    return definition


def test_scheduler_hands_a_published_target_tool_to_explore_only(
    db_environment, tmp_path, audit_directory
):
    with scheduler_case(
        db_environment, tmp_path, audit_directory, evaluation_mode="real_model"
    ) as case:
        publish_target_capability(case)

        receipt = case.scheduler.tick(limit=2)
        assert receipt.blocked == (), receipt.blocked
        by_kind = {item.work_kind.value: item for item in receipt.assignments}
        assert set(by_kind) == {"explore", "reason"}
        explore_refs = [ref.root for ref in by_kind["explore"].tool_definition_refs]
        reason_refs = [ref.root for ref in by_kind["reason"].tool_definition_refs]
        assert explore_refs == [TOOL_REF, HTTP_TOOL_REF]
        # Reason never receives the target capability, even though the published
        # deployment profile in this fixture names it.
        assert reason_refs == [TOOL_REF]

        assert len(by_kind["explore"].tool_definition_refs) > len(
            by_kind["reason"].tool_definition_refs
        )


def test_scheduler_refuses_a_target_tool_on_reason_or_a_mechanism_task(
    db_environment, tmp_path, audit_directory
):
    """Negative control: a mis-published role profile blocks before any Run."""

    with scheduler_case(
        db_environment, tmp_path, audit_directory, evaluation_mode="real_model"
    ) as case:
        publish_target_capability(case, reason_refs=(HTTP_TOOL_REF,))
        with case.control.env.migration_connection() as connection:
            before = connection.execute(
                "SELECT count(*) FROM vnext.agent_run WHERE task_id=%s", (TASK,)
            ).fetchone()[0]

        receipt = case.scheduler.tick(limit=2)
        assert receipt.assignments == ()
        assert [code for _, _, code in receipt.blocked] == ["worker_profile_unavailable"]
        with case.control.env.migration_connection() as connection:
            state = connection.execute(
                "SELECT preparation_block_reason FROM vnext.scheduler_state"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                OWNER,
            ).fetchone()
            after = connection.execute(
                "SELECT count(*) FROM vnext.agent_run WHERE task_id=%s", (TASK,)
            ).fetchone()[0]
            leased = connection.execute(
                "SELECT count(*) FROM vnext.work_item"
                " WHERE task_id=%s AND state='leased'", (TASK,)
            ).fetchone()[0]
        assert state == ("worker_profile_unavailable",)
        # No new Run was admitted and nothing was left leased by the refusal.
        assert after == before
        assert leased == 0


def test_scheduler_refuses_a_target_tool_for_a_mechanism_task(
    db_environment, tmp_path, audit_directory
):
    """A mechanism Task keeps the loopback fixture: no target tool, ever."""

    with scheduler_case(
        db_environment, tmp_path, audit_directory, evaluation_mode="mechanism_synthetic"
    ) as case:
        publish_target_capability(case)

        receipt = case.scheduler.tick(limit=2)
        assert receipt.assignments == ()
        assert [code for _, _, code in receipt.blocked] == ["worker_profile_unavailable"]
