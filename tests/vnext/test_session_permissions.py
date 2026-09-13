"""P08 permission negatives over real PG, native boundaries and services.

Execution belongs to Dewey's existing PG/HTTP batch. The fixture supplies the
real native Session; these tests never synthesize Session roots or receipts.
"""

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

import psycopg
import pytest

from support.p08 import p08_candidate_case
from wuji_core.admission.registry import register_session_capability
from wuji_core.contracts.execution import SessionManifest
from wuji_core.contracts.sessions import BoundaryObjects
from wuji_core.http import strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text


async def _consume(runtime, assignment):
    try:
        return [event async for event in runtime.execute(assignment)]
    finally:
        await runtime.aclose()


def _owner(case):
    identity = case.assignment.identity
    return identity.tenant_id, identity.project_id, identity.task_id


def _publication_state(case):
    with case.environment.migration_connection() as connection:
        owner = _owner(case)
        manifests = connection.execute(
            "SELECT session_id,revision,manifest_ref,publication_id,manifest_digest "
            "FROM vnext.session_manifest WHERE tenant_id=%s AND project_id=%s "
            "AND task_id=%s ORDER BY session_id,revision", owner,
        ).fetchall()
        pins = connection.execute(
            "SELECT publication_id,artifact_id,artifact_revision,access_level "
            "FROM vnext.publication_ref WHERE tenant_id=%s AND project_id=%s "
            "AND task_id=%s ORDER BY publication_id,artifact_id,artifact_revision",
            owner,
        ).fetchall()
        publications = connection.execute(
            "SELECT publication_id FROM vnext.publication WHERE tenant_id=%s "
            "AND project_id=%s AND task_id=%s ORDER BY publication_id", owner,
        ).fetchall()
        pointer = connection.execute(
            "SELECT session_id,session_revision FROM vnext.work_item "
            "WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
            (*owner, case.assignment.identity.work_item_id),
        ).fetchone()
    return manifests, pins, publications, pointer


def _approval_snapshot(case, approval_ref):
    with case.environment.migration_connection() as connection:
        return connection.execute(
            "SELECT row_to_json(a)::text FROM vnext.approval_request a "
            "WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND approval_ref=%s",
            (*_owner(case), approval_ref),
        ).fetchone()


def _acl(connection, owner, subject):
    return connection.execute(
        "SELECT can_read,clearance,can_observe FROM vnext.task_access "
        "WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND subject=%s",
        (*owner, subject),
    ).fetchone()


@pytest.mark.parametrize("restriction", ["revoke_read", "lower_clearance"])
def test_publish_rechecks_source_access_after_real_stage(
    db_environment, tmp_path, audit_directory, restriction
):
    with p08_candidate_case(db_environment, tmp_path, audit_directory) as case:
        case.upstream.release_first_response.set()
        assert [event.kind for event in asyncio.run(
            _consume(case.runtime, case.assignment)
        )] == ["input_receipt"]
        receipt = case.runtime.session_receipt
        assert receipt is not None
        receiver = case.scheduler.receiver_access
        owner = _owner(case)
        worker = case.credential.access

        # Re-stage the exact native roots of the real publication, through the
        # real service. No SDK messages, process observations or hashes are made
        # up here, and no second model/tool request is issued.
        published = case.sessions.load_published(
            receiver, owner[2], receipt.session_id,
            revision=receipt.checkpoint_revision,
        )
        assert published.receipt == receipt
        staged = case.sessions.stage_objects(
            worker, case.assignment,
            BoundaryObjects(
                history=published.history,
                provider_state=published.provider_state,
                memory=published.memory,
            ),
        )
        previous = int(receipt.checkpoint_revision)
        manifest = SessionManifest.model_validate({
            **published.manifest.model_dump(mode="json"),
            "checkpoint_revision": str(previous + 1),
            "history_root": staged.history_root,
            "provider_state_ref": staged.provider_state_ref,
            "memory_manifest_ref": staged.memory_manifest_ref,
            "message_end": str(staged.history.message_end),
            "pending_operation_refs": [
                call.tool_call_id for call in staged.history.frontier.pending_approvals
            ],
            "saved_at": datetime.now(timezone.utc),
        })
        with case.environment.migration_connection() as connection:
            stage = connection.execute(
                """SELECT source_subject,source_token_id,graph_access_level
                FROM vnext.session_stage WHERE tenant_id=%s AND project_id=%s
                  AND task_id=%s AND stage_id=%s AND owner_run_id=%s
                  AND history_id=%s AND history_revision=%s
                  AND provider_id=%s AND provider_revision=%s
                  AND memory_id=%s AND memory_revision=%s""",
                (*owner, staged.lease_owner, case.assignment.identity.agent_run_id,
                 staged.history_root.id, staged.history_root.version.root,
                 staged.provider_state_ref.id, staged.provider_state_ref.version.root,
                 staged.memory_manifest_ref.id, staged.memory_manifest_ref.version.root),
            ).fetchone()
            assert stage is not None, "the real stage must have committed before ACL changes"
            assert stage[:2] == (worker.principal.subject, worker.principal.token_id)
            worker_acl = _acl(connection, owner, worker.principal.subject)
            receiver_acl = _acl(connection, owner, receiver.principal.subject)
            assert worker.principal.subject != receiver.principal.subject
            assert worker_acl[0] and worker_acl[1] >= stage[2] > 0
            assert receiver_acl[0] and receiver_acl[2] and receiver_acl[1] >= stage[2]

        before = _publication_state(case)
        with case.environment.migration_connection() as connection:
            changed_acl = (
                (False, worker_acl[1]) if restriction == "revoke_read"
                else (True, stage[2] - 1)
            )
            changed = connection.execute(
                "UPDATE vnext.task_access SET can_read=%s,clearance=%s "
                "WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND subject=%s",
                (*changed_acl, *owner, worker.principal.subject),
            )
            assert changed.rowcount == 1
            assert _acl(connection, owner, worker.principal.subject)[:2] == changed_acl
            assert _acl(connection, owner, receiver.principal.subject) == receiver_acl

        with pytest.raises((DomainError, psycopg.errors.InsufficientPrivilege)) as denied:
            case.sessions.publish(
                receiver, case.assignment, manifest, expected_revision=previous,
            )
        if isinstance(denied.value, DomainError):
            assert denied.value.code in {"STALE_EXECUTION", "NOT_FOUND_OR_FORBIDDEN"}
        else:
            assert denied.value.sqlstate == "42501"
        assert _publication_state(case) == before

        # The same staged request succeeds with its source ACL restored. This
        # rules out stale/malformed fixture data as the reason for the denial.
        with case.environment.migration_connection() as connection:
            connection.execute(
                "UPDATE vnext.task_access SET can_read=%s,clearance=%s "
                "WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND subject=%s",
                (*worker_acl[:2], *owner, worker.principal.subject),
            )
            assert _acl(connection, owner, receiver.principal.subject) == receiver_acl
        accepted = case.sessions.publish(
            receiver, case.assignment, manifest, expected_revision=previous,
        )
        assert accepted.status == "published"
        assert accepted.session_id == receipt.session_id
        assert accepted.checkpoint_revision == str(previous + 1)


def _insert_qualification_probe(case, approval_ref, qualifications):
    receiver = case.scheduler.receiver_access
    with case.control.uow.transaction(
        receiver, case.assignment.identity.task_id, capability="observe"
    ) as tx:
        role = tx.connection.execute(
            "SELECT current_user,pg_get_userbyid(c.relowner),r.rolsuper,r.rolbypassrls "
            "FROM pg_class c JOIN pg_roles r ON r.rolname=current_user "
            "WHERE c.oid='vnext.approval_request'::regclass"
        ).fetchone()
        assert role[0] == case.environment.application_role
        assert role[0] != role[1] and role[2:] == (False, False)
        assert tx.access.principal == receiver.principal
        # All source columns come from A's actual InputService insert. The
        # BEFORE trigger must reject B, not a later duplicate/FK constraint.
        # A's duplicate is deliberately a no-op, not claimed as a new approval.
        return tx.connection.execute(
            """INSERT INTO vnext.approval_request(
              tenant_id,project_id,task_id,approval_ref,input_request_id,work_item_id,
              session_id,session_revision,manifest_ref,tool_call_id,content_json,
              binding_json,parameters_digest,tool_digest,scope_json,scope_digest,
              profile_digest,qualifications_json,expires_at,access_level)
            SELECT tenant_id,project_id,task_id,%s,input_request_id,work_item_id,
              session_id,session_revision,manifest_ref,tool_call_id,content_json,
              binding_json,parameters_digest,tool_digest,scope_json,scope_digest,
              profile_digest,%s,expires_at,access_level
            FROM vnext.approval_request
            WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND approval_ref=%s
            ON CONFLICT(tenant_id,project_id,task_id,manifest_ref,tool_call_id)
              DO NOTHING RETURNING approval_ref""",
            (str(uuid4()), json_text(qualifications), *_owner(case), approval_ref),
        ).fetchone()


def test_receiver_cannot_apply_other_capability_qualifications_to_published_session(
    db_environment, tmp_path, audit_directory
):
    with p08_candidate_case(db_environment, tmp_path, audit_directory) as case:
        case.upstream.release_first_response.set()
        events = asyncio.run(_consume(case.runtime, case.assignment))
        assert [event.kind for event in events] == ["input_receipt"]
        receipt = case.runtime.input_receipt
        assert receipt is not None and len(receipt.approval_refs) == 1
        approval_ref = receipt.approval_refs[0]

        # A is an actual published Session and committed Input/approval. B is a
        # second complete owner-registered candidate, never a fake verified row.
        with case.environment.migration_connection() as connection:
            stored = connection.execute(
                """SELECT c.document_json,c.digest,s.capability_ref,s.capability_digest
                FROM vnext.session_manifest s JOIN vnext.session_capability c
                  ON (c.tenant_id,c.ref,c.digest)=
                     (s.tenant_id,s.capability_ref,s.capability_digest)
                WHERE s.tenant_id=%s AND s.project_id=%s AND s.task_id=%s
                  AND s.manifest_ref=%s""",
                (*_owner(case), receipt.manifest_ref),
            ).fetchone()
            assert stored is not None
            capability_a = strict_json_loads(stored[0])
            assert sha256(stored[0].encode()).hexdigest() == stored[1] == stored[3]
            assert capability_a["ref"] == stored[2]
            assert capability_a["validation_status"] == "mechanism_candidate"
            capability_b = deepcopy(capability_a)
            capability_b["ref"] = "session-capability-permission-b-" + str(uuid4())
            capability_b["approver_subjects"] = ["p08-only-capability-b-approver"]
            assert capability_b["approver_subjects"] != capability_a["approver_subjects"]
            register_session_capability(
                connection, tenant_id=_owner(case)[0], capability=capability_b,
            )
            other = connection.execute(
                "SELECT document_json,digest,profile_digest,revoked "
                "FROM vnext.session_capability WHERE tenant_id=%s AND ref=%s",
                (_owner(case)[0], capability_b["ref"]),
            ).fetchone()
            assert strict_json_loads(other[0]) == capability_b
            assert sha256(other[0].encode()).hexdigest() == other[1] != stored[1]
            assert other[2] == capability_a["profile_digest"] and other[3] is False

        publication_before = _publication_state(case)
        approval_before = _approval_snapshot(case, approval_ref)
        assert approval_before is not None
        approval = strict_json_loads(approval_before[0])
        assert approval["manifest_ref"] == receipt.manifest_ref
        assert strict_json_loads(approval["qualifications_json"]) == capability_a["approver_subjects"]
        assert approval["decision_status"] == "pending"

        # The exact A qualification path still passes the DB intake guard even
        # while B exists. These probes do not call registry selection (A/B have
        # the same runtime snapshots); they test the manifest's pinned binding.
        assert _insert_qualification_probe(case, approval_ref, capability_a["approver_subjects"]) is None
        with pytest.raises(psycopg.errors.InsufficientPrivilege) as denied:
            _insert_qualification_probe(case, approval_ref, capability_b["approver_subjects"])
        assert denied.value.sqlstate == "42501"
        assert "guard_approval_intake_insert" in (denied.value.diag.context or "")
        assert _insert_qualification_probe(case, approval_ref, capability_a["approver_subjects"]) is None
        assert _approval_snapshot(case, approval_ref) == approval_before
        assert _publication_state(case) == publication_before
