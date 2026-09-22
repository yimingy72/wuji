"""Same-transaction canonical records for an immutable display materialization."""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256

from pydantic import BaseModel

from wuji_core.contracts.envelopes import EvidenceReceipt
from wuji_core.contracts.execution import AgentRunRecord, TaskCreate, TaskView, WorkItemView
from wuji_core.contracts.knowledge import ArtifactRecord, KnowledgeRef, ObservationRecord
from wuji_core.contracts.views import RecordView
from wuji_core.http.json_boundary import strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text, row
from wuji_core.projection.access import AccessRequirements
from wuji_core.projection.builder import ProjectionRelation, node_id


def public_value(value):
    """Serialize typed display data without FastAPI's lossy Decimal conversion."""
    if isinstance(value, BaseModel):
        return public_value(value.model_dump(mode="python"))
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: public_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [public_value(item) for item in value]
    return value


def exact_ref(kind, identifier, revision):
    return KnowledgeRef.model_validate(dict(entity_type=kind, id=identifier, revision=str(revision)))


def _view(ref, payload):
    return RecordView.model_validate(dict(ref=ref, display_kind=ref.entity_type.value, record=payload))


def _rows(cursor):
    while (value := row(cursor)) is not None:
        yield value


@dataclass(frozen=True)
class FrozenRecords:
    records: tuple[RecordView, ...]
    relations: tuple[ProjectionRelation, ...]
    guards: list[dict]
    access_level: int


class ProjectionRecords:
    def __init__(self, ledger, *, max_records=5000):
        self.ledger, self.max_records = ledger, max_records

    def knowledge(self, tx, ref, *, manifest=None, requirements=None):
        requirements = requirements or AccessRequirements(tx)
        value = requirements.knowledge(ref)
        kind = ref.entity_type.value
        if kind == "claim" and value.get("agent_run_id") is not None:
            # ClaimRecord includes producer provenance. Its readable statement
            # must not expose an otherwise private producing execution context.
            requirements.run(value["agent_run_id"])
        if kind in {"claim", "intent"}:
            read = getattr(self.ledger, "read_in_transaction", None)
            if not callable(read):
                # Main assigns the P04 extraction; never open a nested latest read.
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            return read(tx, ref, manifest=manifest)
        if kind == "artifact":
            payload = ArtifactRecord.model_validate(dict(
                artifact_ref=dict(id=ref.id, version=ref.revision.root, sha256=value["sha256"]),
                state=value["state"], media_type=value["media_type"],
                size_bytes=str(value["size_bytes"]), created_at=value["created_at"],
            ))
        elif kind == "observation":
            receipt_row = requirements.require_row("evidence", value["capture_id"])
            receipt = EvidenceReceipt.model_validate(strict_json_loads(receipt_row["receipt_json"]))
            payload = ObservationRecord.model_validate(dict(
                observation_id=ref.id, revision=ref.revision.root, task_id=tx.owner[2],
                capture_id=value["capture_id"], tool_attempt_id=value["tool_attempt_id"],
                collector_ref=value["collector_ref"], artifact_refs=receipt.artifact_refs,
                capture_layer=value["capture_layer"], observed_at=value["observed_at"],
                received_at=value["received_at"], environment_ref=value["environment_ref"],
                conditions=strict_json_loads(value["conditions_json"]),
                completeness=value["completeness"], evidence_origin=value["evidence_origin"],
            ))
        else:
            raise DomainError("INVALID_REFERENCE", 422)
        return _view(ref, payload)

    def _origin(self, tx):
        raw = tx.task["definition_json"]
        if not raw:
            return None
        if sha256(raw.encode()).hexdigest() != tx.task["definition_digest"]:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        definition = strict_json_loads(raw)
        task = TaskCreate.model_validate(definition["task"])
        if task.project_id != tx.owner[1]:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        # Current TaskDefinition stores the initial immutable TaskCreate Goal.
        # This does not synthesize a GoalRecord or a later P12 goal assessment.
        if "goal_revision" in definition and definition["goal_revision"] != "1":
            # A later Goal producer needs its own explicit canonical adapter.
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        goal_revision = "1"
        payload = TaskView.model_validate(dict(
            task_id=tx.owner[2], tenant_id=tx.owner[0], project_id=tx.owner[1],
            version=str(tx.task["control_version"]), name=task.name, scenario=task.scenario,
            desired_state=tx.task["desired_state"], observed_state=tx.task["observed_state"],
            goal_revision=goal_revision, execution_epoch=str(tx.task["execution_epoch"]),
            activated_at=tx.task["activated_at"], close_trigger=tx.task["close_trigger"],
            result_outcome=tx.task["result_outcome"], allowed_actions=[],
        ))
        return _view(exact_ref("origin", tx.owner[2], payload.version.root), payload)

    def _work(self, tx, value, manifest, requirements):
        dependencies = []
        for dependency in manifest.dependencies:
            if dependency["work_item_id"] != value["work_item_id"]:
                continue
            requirements.require_row("dependency", value["work_item_id"], dependency["predecessor_id"])
            dependencies.append(dict(
                predecessor_work_id=dependency["predecessor_id"], condition=dependency["condition"],
                criterion_ref=dependency["criterion_ref"],
            ))
        causes = [item[0] for item in tx.connection.execute(
            "SELECT DISTINCT cause_kind FROM vnext.work_suspension WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s ORDER BY cause_kind",
            (*tx.owner, value["work_item_id"]),
        ).fetchall()]
        result_state = "none"
        if value["current_run_id"] is not None:
            result_state = requirements.require_row("run", value["current_run_id"])["result_state"]
        payload = WorkItemView.model_validate(dict(
            work_item_id=value["work_item_id"], task_id=tx.owner[2], revision=str(value["revision"]),
            kind=value["kind"], desired_state=value["desired_state"], state=value["state"],
            dependencies=dependencies, suspension_causes=causes, result_state=result_state,
            terminal_reason=value["terminal_reason"],
        ))
        return _view(exact_ref("work_item", value["work_item_id"], value["revision"]), payload)

    def _run(self, tx, value, requirements):
        # P09 emits this actual registration/dispatch notification in the same
        # admission transaction. Never substitute snapshot time or started_at.
        # The narrow read function joins the actual restricted Assignment and
        # checks full registered identity/start operation plus current ACL. It
        # returns no Assignment, credential reference or caller-supplied time.
        origin = requirements.run_origin(value["agent_run_id"], required=False)
        if origin is None:
            return None
        identity = {key: value[key] for key in (
            "tenant_id", "project_id", "task_id", "work_item_id", "agent_run_id", "receiver_id",
        )}
        identity.update({key: str(value[key]) for key in ("execution_epoch", "run_epoch", "runtime_attempt")})
        raw = tx.connection.execute(
            "SELECT p.publication_id,a.entity_id,a.revision FROM vnext.publication p "
            "JOIN vnext.publication_ref r USING(tenant_id,project_id,task_id,publication_id) "
            "JOIN vnext.artifact a ON (a.tenant_id,a.project_id,a.task_id,a.entity_id,a.revision)="
            "(r.tenant_id,r.project_id,r.task_id,r.artifact_id,r.artifact_revision) "
            "WHERE p.tenant_id=%s AND p.project_id=%s AND p.task_id=%s AND p.kind='raw_result' "
            "AND a.agent_run_id=%s AND a.state='sealed' AND NOT a.body_removed "
            "ORDER BY p.publication_id LIMIT 1",
            (*tx.owner, value["agent_run_id"]),
        ).fetchone()
        if raw:
            requirements.require_row("publication", raw[0])
            requirements.knowledge(exact_ref("artifact", raw[1], raw[2]))
        checkpoint = tx.connection.execute(
            "SELECT session_id,revision,manifest_ref FROM vnext.session_manifest "
            "WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND owner_run_id=%s "
            "AND manifest_ref IS NOT NULL ORDER BY revision DESC LIMIT 1",
            (*tx.owner, value["agent_run_id"]),
        ).fetchone()
        if checkpoint:
            requirements.require_row("session", checkpoint[0], checkpoint[1])
        payload = AgentRunRecord.model_validate(dict(
            identity=identity, process_state=value["process_state"], result_state=value["result_state"],
            model_mode=value["model_mode"], created_at=origin["created_at"], exited_at=value["exited_at"],
            raw_result_state="saved" if raw else "not_recorded",
            checkpoint_state="published" if checkpoint else "not_recorded",
            checkpoint_ref=checkpoint[2] if checkpoint else None,
        ))
        return _view(exact_ref("agent_run", value["agent_run_id"], "1"), payload)

    def materialize(self, tx, manifest):
        if (manifest.tenant_id, manifest.project_id, manifest.task_id) != tx.owner:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        requirements = AccessRequirements(tx)
        records, relation_list = {}, []
        domain_rows, works, runs = {}, {}, {}

        def add(record):
            key = node_id(record.ref)
            if key in records and record != records[key]:
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            records[key] = record
            if len(records) > self.max_records:
                raise DomainError("LIMIT_BLOCKED", 422)

        def relation(kind, source, target, identity):
            if node_id(source) in records and node_id(target) in records:
                stable_id = sha256(json_text([kind, identity]).encode()).hexdigest()
                relation_list.append(ProjectionRelation(stable_id, source, target, kind))

        for ref in manifest.refs:
            domain_rows[node_id(ref)] = requirements.knowledge(ref)
            add(self.knowledge(tx, ref, manifest=manifest, requirements=requirements))
        origin = self._origin(tx)
        if origin is not None:
            add(origin)

        for work_id in sorted(manifest.states["work_items"]):
            candidate = AccessRequirements(tx)
            try:
                value = candidate.work(work_id)
                frozen = manifest.states["work_items"][work_id]
                if str(value["revision"]) != frozen["revision"] or value["state"] != frozen["state"]:
                    raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                record = self._work(tx, value, manifest, candidate)
            except DomainError as error:
                if error.code == "NOT_FOUND_OR_FORBIDDEN":
                    continue
                raise
            requirements.merge(candidate)
            add(record)
            works[work_id] = (record, value)

        for run_id in sorted(manifest.states["agent_runs"]):
            candidate = AccessRequirements(tx)
            try:
                value = candidate.run(run_id)
                if value["work_item_id"] not in works:
                    continue
                record = self._run(tx, value, candidate)
            except DomainError as error:
                if error.code == "NOT_FOUND_OR_FORBIDDEN":
                    continue
                raise
            if record is not None:
                requirements.merge(candidate)
                add(record)
                runs[run_id] = (record, value)

        # Read only actual canonical relationships; never retarget a revision.
        for item in _rows(tx.connection.execute(
            "SELECT * FROM vnext.entity_relation WHERE tenant_id=%s AND project_id=%s AND task_id=%s ORDER BY source_type,source_id,source_revision,relation,target_type,target_id,target_revision",
            tx.owner,
        )):
            source = exact_ref(item["source_type"], item["source_id"], item["source_revision"])
            target = exact_ref(item["target_type"], item["target_id"], item["target_revision"])
            if node_id(source) not in records or node_id(target) not in records:
                continue
            keys = [item[key] for key in (
                "source_type", "source_id", "source_revision", "relation", "target_type", "target_id", "target_revision",
            )]
            requirements.require_row("relation", *keys)
            relation(item["relation"], source, target, [str(key) for key in keys])

        for key, value in domain_rows.items():
            record = records[key]
            if record.ref.entity_type.value == "observation":
                for blob in record.record.root.artifact_refs:
                    relation("captured_artifact", record.ref, exact_ref("artifact", blob.id, blob.version.root), [key, blob.id, blob.version.root])
            run_id = value.get("agent_run_id")
            if run_id in runs:
                relation("produced", runs[run_id][0].ref, record.ref, [run_id, key])

        for work_id, (record, value) in works.items():
            if origin is not None:
                relation("contains_work", origin.ref, record.ref, work_id)
            if value["intent_id"] is not None:
                relation("scheduled_as", exact_ref("intent", value["intent_id"], value["intent_revision"]), record.ref, [value["intent_id"], work_id])
            for dependency in record.record.root.dependencies:
                predecessor = dependency.predecessor_work_id
                if predecessor in works:
                    relation("depends_on", record.ref, works[predecessor][0].ref, [work_id, predecessor])
        for run_id, (record, value) in runs.items():
            relation("has_run", works[value["work_item_id"]][0].ref, record.ref, run_id)

        return FrozenRecords(tuple(records.values()), tuple(relation_list), requirements.saved(), requirements.level)
