"""Current authorization for saved projections, independent of Run delegation."""

from hashlib import sha256

from psycopg import sql

from wuji_core.blackboard.fact_view import require_complete_assessments
from wuji_core.blackboard.relations import resolve
from wuji_core.contracts.generated import RuntimeCaptureEnvelopeV1
from wuji_core.contracts.envelopes import EvidenceReceipt
from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.http.json_boundary import strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text, row


def access_digest(tx):
    """Only verified identity and actual ACL; no knowledge or event counters."""
    return sha256(json_text({
        "owner": list(tx.owner),
        "subject": tx.access.principal.subject,
        "roles": sorted(tx.access.principal.roles),
        "permissions": {
            key: value for key, value in tx.permissions.items()
            if key.startswith("can_") or key == "clearance"
        },
    }).encode()).hexdigest()


def require_binding(tx, saved):
    if (
        tuple(saved[key] for key in ("tenant_id", "project_id", "task_id")) != tx.owner
        or saved["subject"] != tx.access.principal.subject
        or saved["access_digest"] != access_digest(tx)
    ):
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")


# Saved guards are internal metadata, never RecordView fields or cursor payloads.
_ROWS = {
    "work": ("work_item", ("work_item_id",)),
    "run": ("agent_run", ("agent_run_id",)),
    "criterion": ("goal_criterion", ("criterion_id", "revision")),
    "submission": ("result_submission", ("submission_id",)),
    "result_receipt": ("result_receipt", ("submission_id",)),
    "publication": ("publication", ("publication_id",)),
    "session": ("session_manifest", ("session_id", "revision")),
    "evidence": ("evidence_receipt", ("capture_id",)),
    "capture_session": ("capture_session", ("capture_session_id",)),
    "capture_item": ("capture_item", ("capture_session_id", "item_seq")),
    "relation": ("entity_relation", (
        "source_type", "source_id", "source_revision", "relation",
        "target_type", "target_id", "target_revision",
    )),
    "dependency": ("work_dependency", ("work_item_id", "predecessor_id")),
    "observation_artifact": ("observation_artifact", (
        "observation_id", "observation_revision", "artifact_id", "artifact_revision",
    )),
}


class AccessRequirements:
    """Collect and recheck the complete actual basis without disclosing it."""

    def __init__(self, tx, *, limit=50000):
        self.tx, self.limit = tx, limit
        self.guards = {}
        self.level = 0
        self._knowledge = {}
        self._active = set()

    def _remember(self, guard, level=0):
        key = json_text(guard)
        self.guards[key] = guard
        self.level = max(self.level, int(level))
        if len(self.guards) > self.limit:
            raise DomainError("LIMIT_BLOCKED", 422)

    def require_row(self, kind, *values):
        if kind not in _ROWS:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        table, columns = _ROWS[kind]
        if len(values) != len(columns):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        found = row(self.tx.connection.execute(
            sql.SQL("SELECT * FROM {} WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND {}").format(
                sql.Identifier("vnext", table),
                sql.SQL(" AND ").join(sql.SQL("{}=%s").format(sql.Identifier(c)) for c in columns),
            ), (*self.tx.owner, *values),
        ))
        if found is None:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        self._remember({"kind": kind, "values": [str(v) for v in values]}, found.get("access_level", 0))
        return found

    def knowledge(self, ref, *, depth=0):
        ref = KnowledgeRef.model_validate(ref)
        key = (ref.entity_type.value, ref.id, ref.revision.root)
        if key in self._knowledge:
            return self._knowledge[key]
        if depth > 64 or key in self._active:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        self._active.add(key)
        try:
            try:
                value = resolve(self.tx, ref)
            except DomainError as error:
                if error.code == "INVALID_REFERENCE":
                    raise DomainError("NOT_FOUND_OR_FORBIDDEN") from error
                raise
            self._remember({"kind": "knowledge", "ref": ref.model_dump(mode="json")}, value["access_level"])
            kind = ref.entity_type.value
            if kind == "artifact" and value["body_removed"]:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            if kind in {"claim", "intent"}:
                for basis in strict_json_loads(value["basis_json"]):
                    self.knowledge(basis, depth=depth + 1)
            if kind == "claim":
                # Do not recalculate the saved assessment against latest revisions.
                # This canonical guard checks complete *current access* only.
                try:
                    require_complete_assessments(self.tx, value)
                except DomainError as error:
                    if error.code == "CAPABILITY_UNAVAILABLE":
                        raise DomainError("NOT_FOUND_OR_FORBIDDEN") from error
                    raise
                inputs = self.tx.connection.execute(
                    """SELECT i.entity_type,i.entity_id,i.revision FROM vnext.assessment_input i
                    JOIN vnext.assessment a ON (a.tenant_id,a.project_id,a.task_id,a.assessment_id,a.revision)=
                    (i.tenant_id,i.project_id,i.task_id,i.assessment_id,i.assessment_revision)
                    WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s
                    AND a.claim_id=%s AND a.claim_revision=%s""",
                    (*self.tx.owner, ref.id, ref.revision.root),
                ).fetchall()
                for t, i, v in inputs:
                    basis = KnowledgeRef.model_validate(dict(entity_type=t, id=i, revision=str(v)))
                    if (t, i, str(v)) != key:
                        self.knowledge(basis, depth=depth + 1)
            elif kind == "observation":
                session_id = value.get("capture_session_id")
                if session_id is None:
                    receipt_row = self.require_row("evidence", value["capture_id"])
                    receipt = EvidenceReceipt.model_validate(strict_json_loads(receipt_row["receipt_json"]))
                    if receipt.observation_ref != ref:
                        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                    expected = [(blob.id, blob.version.root, blob.sha256.root, None) for blob in receipt.artifact_refs]
                else:
                    session = self.require_row("capture_session", session_id)
                    item = self.require_row("capture_item", session_id, value["capture_item_seq"])
                    envelope = RuntimeCaptureEnvelopeV1.model_validate(strict_json_loads(item["envelope_json"]))
                    if (
                        item["observation_id"] != ref.id
                        or str(item["observation_revision"]) != ref.revision.root
                        or value["capture_id"] != session_id + ":" + str(item["item_seq"])
                        or envelope.capture_session_id != session_id
                        or envelope.item_seq != item["item_seq"]
                        or envelope.item_digest.root != item["item_digest"]
                        or envelope.collector_ref != value["collector_ref"]
                        or envelope.binding.task_id != self.tx.owner[2]
                        or envelope.binding.pod_uid != session["pod_uid"]
                        or envelope.binding.runtime_attempt.root != str(session["runtime_attempt"])
                        or envelope.binding.execution_epoch.root != str(session["execution_epoch"])
                    ):
                        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                    links = self.tx.connection.execute(
                        """SELECT ordinal,artifact_id,artifact_revision FROM vnext.observation_artifact
                        WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                        AND observation_id=%s AND observation_revision=%s ORDER BY ordinal""",
                        (*self.tx.owner, ref.id, ref.revision.root),
                    ).fetchall()
                    if len(links) != len(envelope.parts) or any(ordinal != index for index, (ordinal, *_rest) in enumerate(links)):
                        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                    expected = [
                        (artifact_id, str(revision), part.sha256.root, part.length)
                        for (_ordinal, artifact_id, revision), part in zip(links, envelope.parts)
                    ]
                for artifact_id, revision, digest, length in expected:
                    self.require_row("observation_artifact", ref.id, ref.revision.root, artifact_id, revision)
                    artifact = self.knowledge(dict(entity_type="artifact", id=artifact_id, revision=revision), depth=depth + 1)
                    if artifact["sha256"] != digest or (length is not None and artifact["size_bytes"] != length):
                        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            self._knowledge[key] = value
            return value
        finally:
            self._active.remove(key)

    def work(self, work_id, *, depth=0, active=None):
        if depth > 64:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        active = set() if active is None else active
        if work_id in active:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        active.add(work_id)
        try:
            value = self.require_row("work", work_id)
            if value["intent_id"] is not None:
                self.knowledge(dict(entity_type="intent", id=value["intent_id"], revision=str(value["intent_revision"])))
            dependencies = self.tx.connection.execute(
                "SELECT predecessor_id,criterion_id,criterion_revision FROM vnext.work_dependency WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
                (*self.tx.owner, work_id),
            ).fetchall()
            for predecessor, criterion, revision in dependencies:
                self.require_row("dependency", work_id, predecessor)
                if criterion is not None:
                    self.require_row("criterion", criterion, revision)
                self.work(predecessor, depth=depth + 1, active=active)
            if value["current_run_id"] is not None:
                run = self.require_row("run", value["current_run_id"])
                self._result(run)
            return value
        finally:
            active.remove(work_id)

    def _result(self, run):
        if run["result_submission_id"] is not None:
            self.require_row("submission", run["result_submission_id"])
            if run["result_state"] not in {"none", "received"}:
                self.require_row("result_receipt", run["result_submission_id"])

    def run(self, run_id):
        value = self.require_row("run", run_id)
        self.work(value["work_item_id"])
        self._result(value)
        return value

    def run_origin(self, run_id, *, required=True):
        origin = row(self.tx.connection.execute(
            "SELECT * FROM vnext.projection_run_origin(%s,%s,%s,%s)",
            (*self.tx.owner, run_id),
        ))
        if origin is None:
            if required:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            return None
        self._remember({"kind": "run_origin", "values": [run_id]})
        return origin

    def merge(self, other):
        for guard in other.guards.values():
            self._remember(guard, other.level)

    def saved(self):
        return [self.guards[key] for key in sorted(self.guards)]

    def reauthorize(self, guards):
        if not isinstance(guards, list) or len(guards) > self.limit:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        for guard in guards:
            kind = guard["kind"]
            if kind == "knowledge":
                self.knowledge(guard["ref"])
            elif kind == "work":
                self.work(*guard["values"])
            elif kind == "run":
                self.run(*guard["values"])
            elif kind == "run_origin":
                self.run_origin(*guard["values"])
            else:
                self.require_row(kind, *guard["values"])
