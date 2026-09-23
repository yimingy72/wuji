"""Trusted mid-Run Claim publication and bounded blackboard notices."""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from wuji_core.admission.common import current_run
from wuji_core.blackboard.claims import ClaimService
from wuji_core.blackboard.fact_view import claim_record
from wuji_core.blackboard.relations import (
    actor,
    operation,
    resolve,
    save_operation,
)
from wuji_core.contracts import generated as wire
from wuji_core.contracts.knowledge import KnowledgeRef, ProposalLocalRef
from wuji_core.execution.dependencies import dependencies_satisfied, intent_current
from wuji_core.execution.states import task_can_run
from wuji_core.evidence.artifacts import bound_run
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.snapshots import SnapshotQuery, SnapshotRepository
from wuji_core.persistence.uow import DomainError, row


NOTICE_FILTER_VERSION = "wuji.knowledge-notices.filter.v1"
NOTICE_SCAN_LIMIT = 256
NOTICE_KINDS = ("claim_shared", "workspace.published")
BOARD_RENDERER = "wuji-board-claim-renderer.v1"
BOARD_REDACTION = "wuji-redaction.v1"


def _ref_key(ref):
    return ref.entity_type.value, ref.id, ref.revision.root


def _current_output(tx, assignment, registry):
    binding = tx.run_binding
    if binding is None or binding.identity != assignment.identity:
        raise DomainError("STALE_EXECUTION", 409)
    run = bound_run(tx, assignment.identity.agent_run_id, assignment.identity)
    work = row(
        tx.connection.execute(
            "SELECT * FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s "
            "AND task_id=%s AND work_item_id=%s",
            (*tx.owner, assignment.identity.work_item_id),
        )
    )
    held = tx.connection.execute(
        "SELECT 1 FROM vnext.work_suspension WHERE tenant_id=%s AND project_id=%s "
        "AND task_id=%s AND work_item_id=%s LIMIT 1",
        (*tx.owner, assignment.identity.work_item_id),
    ).fetchone()
    assigned_snapshot = tx.connection.execute(
        "SELECT vnext.can_read_scheduler_snapshot(%s,%s,%s,%s)",
        (*tx.owner, assignment.snapshot_id),
    ).fetchone()
    identity = assignment.identity.model_dump(mode="json")
    if (
        run is None
        or work is None
        or any(str(run[key]) != str(value) for key, value in identity.items())
        or assignment.operation_id != run["start_operation_id"]
        or assignment.work_kind.value != work["kind"]
        or not assigned_snapshot
        or not assigned_snapshot[0]
        or not task_can_run(tx.task)
        or not run["execution_allowed"]
        or run["stop_kind"] is not None
        or run["process_state"] != "running"
        or work["kind"] != "explore"
        or work["state"] != "running"
        or work["desired_state"] != "run"
        or work["current_run_id"] != run["agent_run_id"]
        or work["run_epoch"] != run["run_epoch"]
        or held
        or not dependencies_satisfied(tx, work["work_item_id"])
        or not intent_current(tx, work)
    ):
        raise DomainError("STALE_EXECUTION", 409)
    definition = strict_json_loads(tx.task["definition_json"])
    expiry = datetime.fromisoformat(
        definition["task"]["authorization_expires_at"].replace("Z", "+00:00")
    )
    config = registry.config(tx)
    now = datetime.now(timezone.utc)
    if (
        expiry <= now
        or tx.task["activated_at"] is None
        or (now - tx.task["activated_at"]).total_seconds()
        >= config.runtime.limits.max_elapsed_seconds
    ):
        raise DomainError("LIMIT_BLOCKED", 429)
    return run, work


class BoardPublishService:
    def __init__(self, uow, *, registry, knowledge_reads):
        self.uow, self.registry = uow, registry
        self.claims = ClaimService(uow)
        self.knowledge_reads = knowledge_reads

    @staticmethod
    def _operation_id(assignment, occurrence):
        return "board-publish:" + sha256(
            canonical_json_bytes(
                {
                    "identity": assignment.identity.model_dump(mode="json"),
                    "native_occurrence": occurrence,
                }
            )
        ).hexdigest()

    @staticmethod
    def _delivered(tx, work_id, ref):
        return tx.connection.execute(
            """SELECT 1 FROM vnext.knowledge_delivery
            WHERE tenant_id=%s AND project_id=%s AND task_id=%s
              AND work_item_id=%s
              AND state IN ('attached','returned_to_framework')
              AND delivery_json::jsonb->>'disclosure'='content'
              AND delivery_json::jsonb#>>'{ref,entity_type}'=%s
              AND delivery_json::jsonb#>>'{ref,id}'=%s
              AND delivery_json::jsonb#>>'{ref,revision}'=%s LIMIT 1""",
            (*tx.owner, work_id, *_ref_key(ref)),
        ).fetchone() is not None

    def publish(self, access, assignment, *, native_occurrence, claim):
        assignment = wire.WorkerAssignment.model_validate(assignment)
        proposal = wire.ClaimProposal.model_validate(claim)
        request = {
            "identity": assignment.identity.model_dump(mode="json"),
            "native_occurrence": native_occurrence,
            "claim": proposal.model_dump(mode="json"),
        }
        key = self._operation_id(assignment, native_occurrence)
        with self.uow.transaction(
            access, assignment.identity.task_id, capability="model_output"
        ) as tx:
            run, work = _current_output(tx, assignment, self.registry)
            digest, saved = operation(tx, "board_publish", key, request)
            if saved is not None:
                return wire.BoardPublishResultV1.model_validate(saved)
            declared = [item.root for item in proposal.basis_refs]
            if any(isinstance(ref, ProposalLocalRef) for ref in declared):
                raise DomainError("INVALID_REFERENCE", 422)
            required = [*declared]
            if proposal.revises is not None:
                required.append(proposal.revises)
            if any(
                not self._delivered(tx, work["work_item_id"], ref)
                for ref in required
            ):
                raise DomainError("INVALID_REFERENCE", 422)
            receipt, level = self.claims.append(
                tx,
                proposal,
                kind="claim",
                who=actor(tx, run["agent_subject"]),
                run_id=run["agent_run_id"],
            )
            claim_ref = receipt.canonical_ref
            if claim_ref is None:
                raise DomainError("INVALID_REFERENCE", 422)
            record = claim_record(tx, resolve(tx, claim_ref))
            source = canonical_json_bytes(record.model_dump(mode="json"))
            rendered = canonical_json_bytes(
                {
                    "schema_version": "wuji.board-claim-content.v1",
                    "ref": claim_ref.model_dump(mode="json"),
                    "claim": record.model_dump(mode="json"),
                }
            )
            if len(rendered) > min(16 * 1024, self.knowledge_reads.max_read_bytes):
                raise DomainError("REPRESENTATION_LIMIT", 422)
            text = rendered.decode("utf-8")
            representation_digest = sha256(rendered).hexdigest()
            delivery = self.knowledge_reads._persist(
                tx,
                assignment,
                native_occurrence=native_occurrence,
                request=request,
                access_level=level,
                delivery={
                    "schema_version": "wuji.knowledge-delivery.v1",
                    "delivery_id": str(uuid4()),
                    "kind": "environment_material",
                    "snapshot_id": assignment.snapshot_id,
                    "ref": claim_ref,
                    "source_digest": sha256(source).hexdigest(),
                    "selector": {
                        "kind": "record_fields",
                        "fields": [
                            "text",
                            "limitations",
                            "kind",
                            "assertion_role",
                            "basis_refs",
                        ],
                    },
                    "renderer_version": BOARD_RENDERER,
                    "redaction_policy_ref": BOARD_REDACTION,
                    "text": text,
                    "representation_digest": representation_digest,
                    "byte_length": len(rendered),
                    "source_completeness": "complete",
                    "representation_truncated": False,
                    "has_more": False,
                    "disclosure": "content",
                    "state": "prepared",
                    "work_item_id": work["work_item_id"],
                    "agent_run_id": run["agent_run_id"],
                    "session_id": work["session_id"],
                    "native_occurrence": native_occurrence,
                },
            )
            result = wire.BoardPublishResultV1.model_validate(
                {
                    "schema_version": "wuji.board-publish-result.v1",
                    "receipt": receipt,
                    "claim": record,
                    "delivery": delivery,
                }
            )
            save_operation(
                tx,
                "board_publish",
                key,
                digest,
                result.model_dump(mode="json"),
                level,
            )
            tx.semantic_event(
                "claim_shared", receipt.model_dump(mode="python"), access_level=level
            )
            return result


class KnowledgeNoticeService:
    def __init__(self, uow, *, registry):
        self.uow, self.registry = uow, registry
        self.snapshots = SnapshotRepository(uow)

    @staticmethod
    def _cursor(binding, assignment, limit, event_seq):
        digest = sha256(
            canonical_json_bytes(
                {
                    "task_id": assignment.identity.task_id,
                    "work_item_id": assignment.identity.work_item_id,
                    "session_lineage": binding.session_lineage,
                    "filter": NOTICE_FILTER_VERSION,
                    "limit": limit,
                    "event_seq": str(event_seq),
                }
            )
        ).hexdigest()[:24]
        return f"notice:{event_seq}:{digest}"

    def _offset(self, tx, binding, assignment, cursor, limit):
        manifest = self.snapshots._get(tx, assignment.snapshot_id)
        initial = manifest.states.get("task", {}).get("notification_event_seq", "0")
        if not isinstance(initial, str) or not initial.isdecimal():
            initial = "0"
        if cursor in {None, "initial"}:
            return int(initial), manifest
        parts = cursor.split(":")
        if len(parts) != 3 or parts[0] != "notice" or not parts[1].isdecimal():
            raise DomainError("INVALID_REFERENCE", 422)
        event_seq = int(parts[1])
        if self._cursor(binding, assignment, limit, event_seq) != cursor:
            raise DomainError("INVALID_REFERENCE", 422)
        return event_seq, manifest

    @staticmethod
    def _already_read(tx, work_id, ref):
        return tx.connection.execute(
            """SELECT 1 FROM vnext.knowledge_delivery
            WHERE tenant_id=%s AND project_id=%s AND task_id=%s
              AND work_item_id=%s
              AND state IN ('attached','returned_to_framework')
              AND delivery_json::jsonb->>'disclosure'='content'
              AND delivery_json::jsonb#>>'{ref,entity_type}'=%s
              AND delivery_json::jsonb#>>'{ref,id}'=%s
              AND delivery_json::jsonb#>>'{ref,revision}'=%s LIMIT 1""",
            (*tx.owner, work_id, *_ref_key(ref)),
        ).fetchone() is not None

    @staticmethod
    def _relevant(tx, work, source_work, claim):
        claim_basis = {
            _ref_key(KnowledgeRef.model_validate(item))
            for item in strict_json_loads(claim["basis_json"])
        }
        intent_basis = set()
        if work["intent_id"] is not None:
            intent = row(
                tx.connection.execute(
                    "SELECT basis_json FROM vnext.intent_revision WHERE tenant_id=%s "
                    "AND project_id=%s AND task_id=%s AND entity_id=%s AND revision=%s",
                    (*tx.owner, work["intent_id"], work["intent_revision"]),
                )
            )
            if intent is not None:
                intent_basis = {
                    _ref_key(KnowledgeRef.model_validate(item))
                    for item in strict_json_loads(intent["basis_json"])
                }
        predecessor = source_work is not None and tx.connection.execute(
            "SELECT 1 FROM vnext.work_dependency WHERE tenant_id=%s AND project_id=%s "
            "AND task_id=%s AND work_item_id=%s AND predecessor_id=%s LIMIT 1",
            (*tx.owner, work["work_item_id"], source_work),
        ).fetchone()
        supersedes_basis = tx.connection.execute(
            """SELECT 1 FROM vnext.entity_relation
            WHERE tenant_id=%s AND project_id=%s AND task_id=%s
              AND source_type='claim' AND source_id=%s AND source_revision=%s
              AND relation IN ('cites','supersedes','contradicts')
              AND (target_type,target_id,target_revision) IN (
                SELECT source_type,source_id,source_revision
                FROM vnext.entity_relation WHERE tenant_id=%s AND project_id=%s
                  AND task_id=%s AND target_type='intent' AND target_id=%s
                  AND target_revision=%s AND relation='input_to') LIMIT 1""",
            (
                *tx.owner,
                claim["entity_id"],
                claim["revision"],
                *tx.owner,
                work["intent_id"],
                work["intent_revision"],
            ),
        ).fetchone() if work["intent_id"] is not None else None
        return bool(
            claim_basis & intent_basis
            or predecessor
            or supersedes_basis
            # The first release has no semantic search index. A same-Task Claim
            # with canonical evidence is the bounded fallback, so this branch is
            # deliberately broader than question-level matching.
            or claim_basis
        )

    def list(self, access, assignment, *, cursor=None, limit=16):
        assignment = wire.WorkerAssignment.model_validate(assignment)
        if cursor is not None and (not isinstance(cursor, str) or not cursor):
            raise DomainError("INVALID_SCHEMA", 422)
        if type(limit) is not int or not 1 <= limit <= 16:
            raise DomainError("INVALID_SCHEMA", 422)
        pending = []
        with self.uow.transaction(
            access, assignment.identity.task_id, capability="model_request"
        ) as tx:
            binding = tx.run_binding
            run, work = current_run(tx, self.registry.config(tx))
            if binding is None or binding.identity != assignment.identity:
                raise DomainError("STALE_EXECUTION", 409)
            after, initial_manifest = self._offset(
                tx, binding, assignment, cursor, limit
            )
            initial_refs = {_ref_key(ref) for ref in initial_manifest.refs}
            high_water = int(
                tx.connection.execute(
                    "SELECT COALESCE(max(event_seq),%s) FROM vnext.outbox "
                    "WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                    (after, *tx.owner),
                ).fetchone()[0]
            )
            events = tx.connection.execute(
                "SELECT event_seq,kind,payload_json FROM vnext.outbox "
                "WHERE tenant_id=%s AND project_id=%s AND task_id=%s "
                "AND event_seq>%s AND event_seq<=%s AND kind=ANY(%s) "
                "ORDER BY event_seq LIMIT %s",
                (*tx.owner, after, high_water, list(NOTICE_KINDS), NOTICE_SCAN_LIMIT),
            ).fetchall()
            scanned = after
            page_full = False
            for event_seq, kind, payload_json in events:
                scanned = int(event_seq)
                if kind == "workspace.published":
                    payload = strict_json_loads(payload_json)
                    try:
                        manifest = wire.BlobRef.model_validate(payload["manifest_ref"])
                        ref = KnowledgeRef.model_validate(
                            {
                                "entity_type": "artifact",
                                "id": manifest.id,
                                "revision": manifest.version.root,
                            }
                        )
                        source_work = payload["producer_work_ref"]
                        source_run = payload["producer_run_ref"]
                        metadata = {
                            "claim_kind": None,
                            "assertion_role": None,
                            "effective_outcome": None,
                            "publication_id": payload["publication_id"],
                            "asset_id": payload["asset_id"],
                            "asset_revision": payload["asset_revision"],
                        }
                    except (KeyError, TypeError, ValueError):
                        continue
                    if (
                        source_run == run["agent_run_id"]
                        or _ref_key(ref) in initial_refs
                        or self._already_read(tx, work["work_item_id"], ref)
                    ):
                        continue
                    category = "workspace_published"
                else:
                    receipt = wire.ComponentReceipt.model_validate(
                        strict_json_loads(payload_json)
                    )
                    ref = receipt.canonical_ref
                    if ref is None or _ref_key(ref) in initial_refs:
                        continue
                    claim = row(
                        tx.connection.execute(
                            "SELECT * FROM vnext.claim_revision WHERE tenant_id=%s "
                            "AND project_id=%s AND task_id=%s AND entity_id=%s "
                            "AND revision=%s",
                            (*tx.owner, ref.id, ref.revision.root),
                        )
                    )
                    if claim is None or claim["agent_run_id"] == run["agent_run_id"]:
                        continue
                    source_work = None
                    if claim["agent_run_id"] is not None:
                        source = tx.connection.execute(
                            "SELECT work_item_id FROM vnext.agent_run WHERE tenant_id=%s "
                            "AND project_id=%s AND task_id=%s AND agent_run_id=%s",
                            (*tx.owner, claim["agent_run_id"]),
                        ).fetchone()
                        source_work = None if source is None else source[0]
                    if self._already_read(
                        tx, work["work_item_id"], ref
                    ) or not self._relevant(tx, work, source_work, claim):
                        continue
                    category = (
                        "claim_revised"
                        if int(ref.revision.root) > 1
                        else "claim_published"
                    )
                    metadata = {
                        "claim_kind": claim["kind"],
                        "assertion_role": claim["assertion_role"],
                        "effective_outcome": None,
                        "publication_id": None,
                        "asset_id": None,
                        "asset_revision": None,
                    }
                pending.append(
                    {
                        "category": category,
                        "ref": ref,
                        "snapshot_id": "pending",
                        "source_work_ref": source_work,
                        "metadata": metadata,
                    }
                )
                if len(pending) == limit:
                    page_full = True
                    break
            if not page_full and len(events) < NOTICE_SCAN_LIMIT:
                scanned = high_water
            next_cursor = self._cursor(binding, assignment, limit, scanned)

        if pending:
            refs = tuple(dict.fromkeys(_ref_key(item["ref"]) for item in pending))
            snapshot = self.snapshots.create(
                assignment.identity.task_id,
                access,
                query=SnapshotQuery(entity_types=(), required_refs=refs),
            )
            for item in pending:
                item["snapshot_id"] = snapshot.snapshot_id

        with self.uow.transaction(
            access, assignment.identity.task_id, capability="model_request"
        ) as tx:
            binding = tx.run_binding
            current_run(tx, self.registry.config(tx))
            if (
                binding is None
                or binding.identity != assignment.identity
                or next_cursor
                != self._cursor(binding, assignment, limit, scanned)
            ):
                raise DomainError("STALE_EXECUTION", 409)
        return wire.KnowledgeNoticesPageV1.model_validate(
            {
                "schema_version": "wuji.knowledge-notices.v1",
                "next_cursor": next_cursor,
                "notices": pending,
            }
        )
