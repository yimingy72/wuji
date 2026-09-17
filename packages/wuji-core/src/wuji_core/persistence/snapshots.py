"""Persistent RR manifests. No long transaction survives a page/request boundary."""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
from uuid import uuid4

from psycopg import sql

from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.contracts.execution import GoalCriterionRef
from wuji_core.http.json_boundary import strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text, row


@dataclass(frozen=True)
class SnapshotQuery:
    entity_types: tuple[str, ...] = ("artifact", "observation", "claim", "intent")
    max_references: int = 1000

    def __post_init__(self):
        if (
            not self.entity_types
            or len(self.entity_types) > 4
            or len(set(self.entity_types)) != len(self.entity_types)
            or any(
                t not in {"artifact", "observation", "claim", "intent"}
                for t in self.entity_types
            )
            or isinstance(self.max_references, bool)
            or not 1 <= self.max_references <= 5000
        ):
            raise ValueError("invalid bounded snapshot query")

    def payload(self):
        return {
            "entity_types": sorted(self.entity_types),
            "max_references": self.max_references,
        }


@dataclass(frozen=True)
class SnapshotManifest:
    snapshot_id: str
    tenant_id: str
    project_id: str
    task_id: str
    query_digest: str
    access_digest: str
    created_at: datetime
    expires_at: datetime
    refs: tuple[KnowledgeRef, ...]
    states: dict
    dependencies: tuple[dict, ...]
    relations: tuple[dict, ...]


def _ref(kind, entity_id, revision):
    return KnowledgeRef.model_validate(
        {"entity_type": kind, "id": entity_id, "revision": str(revision)}
    )


def _access_digest(tx):
    return hashlib.sha256(
        json_text(
            {
                "owner": list(tx.owner),
                "subject": tx.access.principal.subject,
                "clearance": tx.permissions["clearance"],
                "can_read": tx.permissions["can_read"],
            }
        ).encode()
    ).hexdigest()


class SnapshotRepository:
    def __init__(self, uow, *, ttl_seconds=3600):
        if not 0 < ttl_seconds <= 86400:
            raise ValueError("invalid snapshot lifetime")
        self.uow, self.ttl_seconds = uow, ttl_seconds

    def create(self, task_id, access, *, query=None):
        query = SnapshotQuery() if query is None else query
        if not isinstance(query, SnapshotQuery):
            raise ValueError("query must be a SnapshotQuery")
        with self.uow.transaction(
            access, task_id, capability="snapshot", repeatable_read=True
        ) as tx:
            return self.create_in_transaction(tx, query=query)

    def create_in_transaction(self, tx, *, query=None, reader_clearance=None):
        """Freeze in the caller's existing snapshot or pool→Task admit transaction.

        Snapshot callers retain Repeatable Read. Admission callers already hold
        Task against all domain writers, so generation and pins commit together.
        This port never opens a connection, commits, or sets a capability GUC.
        """
        query = SnapshotQuery() if query is None else query
        if not isinstance(query, SnapshotQuery):
            raise ValueError("query must be a SnapshotQuery")
        if tx.purpose == "admit":
            from wuji_core.scheduling.triggers import require_admission

            require_admission(tx)
        elif tx.purpose != "snapshot" or not tx.permissions.get("can_read"):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        if reader_clearance is not None:
            if (
                tx.purpose != "admit"
                or type(reader_clearance) is not int
                or not 0 <= reader_clearance <= tx.permissions["clearance"]
            ):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            # A savepoint rolls back the temporary GUC on errors; successful
            # completion restores it before leaving the caller's transaction.
            with tx.connection.transaction():
                tx.connection.execute(
                    "SELECT set_config('wuji.clearance',%s,true)",
                    (str(reader_clearance),),
                )
                narrowed = replace(
                    tx, permissions=dict(tx.permissions, clearance=reader_clearance)
                )
                result = self._create(narrowed, query)
                tx.connection.execute(
                    "SELECT set_config('wuji.clearance',%s,true)",
                    (str(tx.permissions["clearance"]),),
                )
                return result
        return self._create(tx, query)

    def _create(self, tx, query):
        task_id = tx.owner[2]
        refs = {}
        initial = tx.connection.execute(
            """SELECT DISTINCT ON(r.entity_type,r.entity_id) r.entity_type,r.entity_id,r.revision,r.access_level
            FROM vnext.entity_revision_registry r WHERE r.entity_type=ANY(%s)
            AND (r.entity_type<>'artifact' OR EXISTS(SELECT 1 FROM vnext.artifact a WHERE
            (a.tenant_id,a.project_id,a.task_id,a.entity_id,a.revision)=(r.tenant_id,r.project_id,r.task_id,r.entity_id,r.revision) AND a.state='sealed'))
            ORDER BY r.entity_type,r.entity_id,r.revision DESC LIMIT %s""",
            (list(query.entity_types), query.max_references + 1),
        ).fetchall()
        for kind, entity_id, revision, level in initial:
            refs[(kind, entity_id, str(revision))] = level
        # Close over fixed dependency references, not over newer revisions.
        todo = list(refs)
        relations = []
        while todo:
            if len(refs) > query.max_references:
                raise DomainError("LIMIT_BLOCKED", 422)
            kind, entity_id, revision = todo.pop()
            targets = []
            if kind == "observation":
                targets = [
                    ("artifact", a, str(v), level)
                    for a, v, level in tx.connection.execute(
                        "SELECT artifact_id,artifact_revision,access_level FROM vnext.observation_artifact WHERE observation_id=%s AND observation_revision=%s ORDER BY ordinal",
                        (entity_id, revision),
                    ).fetchall()
                ]
            elif kind == "claim":
                rows = tx.connection.execute(
                    "SELECT relation,target_type,target_id,target_revision,access_level FROM vnext.entity_relation WHERE source_type=%s AND source_id=%s AND source_revision=%s ORDER BY relation,target_type,target_id,target_revision",
                    (kind, entity_id, revision),
                ).fetchall()
                for relation, t, i, v, level in rows:
                    targets.append((t, i, str(v), level))
                    relations.append(
                        {
                            "source": _ref(kind, entity_id, revision).model_dump(
                                mode="json"
                            ),
                            "relation": relation,
                            "target": _ref(t, i, v).model_dump(mode="json"),
                        }
                    )
            if kind == "claim":
                # Assessment inputs need their own fixed closure even when the
                # original candidate had no basis or cited different evidence.
                for t, i, v, level in tx.connection.execute(
                    """SELECT ai.entity_type,ai.entity_id,ai.revision,ai.access_level
                    FROM vnext.assessment_input ai JOIN vnext.assessment a
                    USING(tenant_id,project_id,task_id,assessment_id)
                    WHERE a.claim_id=%s AND a.claim_revision=%s AND a.revision=ai.assessment_revision""",
                    (entity_id, revision),
                ).fetchall():
                    targets.append((t, i, str(v), level))
            elif kind == "intent":
                for t, i, v, level in tx.connection.execute(
                    "SELECT source_type,source_id,source_revision,access_level FROM vnext.entity_relation WHERE target_type='intent' AND target_id=%s AND target_revision=%s AND relation='input_to'",
                    (entity_id, revision),
                ).fetchall():
                    targets.append((t, i, str(v), level))
                    relations.append(
                        {
                            "source": _ref(t, i, v).model_dump(mode="json"),
                            "relation": "input_to",
                            "target": _ref(kind, entity_id, revision).model_dump(
                                mode="json"
                            ),
                        }
                    )
            for t, i, v, level in targets:
                if (t, i, v) not in refs:
                    refs[(t, i, v)] = level
                    todo.append((t, i, v))
        states = {
            "task": {
                "board_revision": str(tx.task["board_revision"]),
                "execution_epoch": str(tx.task["execution_epoch"]),
                "execution_allowed": tx.task["execution_allowed"],
            },
            "work_items": {},
            "agent_runs": {},
        }
        works = tx.connection.execute(
            "SELECT work_item_id,state,revision FROM vnext.work_item ORDER BY work_item_id LIMIT %s",
            (query.max_references + 1,),
        ).fetchall()
        runs = tx.connection.execute(
            "SELECT agent_run_id,process_state,model_mode,run_epoch FROM vnext.agent_run ORDER BY agent_run_id LIMIT %s",
            (query.max_references + 1,),
        ).fetchall()
        dependencies = [
            {
                "work_item_id": w,
                "predecessor_id": p,
                "condition": c,
                "criterion_ref": (
                    None
                    if i is None
                    else GoalCriterionRef(criterion_id=i, revision=str(v)).model_dump(
                        mode="json"
                    )
                ),
            }
            for w, p, c, t, i, v in tx.connection.execute(
                "SELECT work_item_id,predecessor_id,condition,criterion_type,criterion_id,criterion_revision FROM vnext.work_dependency ORDER BY work_item_id,predecessor_id LIMIT %s",
                (query.max_references + 1,),
            ).fetchall()
        ]
        if max(len(works), len(runs), len(dependencies)) > query.max_references:
            raise DomainError("LIMIT_BLOCKED", 422)
        states["work_items"] = {
            i: {"state": s, "revision": str(v)} for i, s, v in works
        }
        states["agent_runs"] = {
            i: {"process_state": s, "model_mode": m, "run_epoch": str(v)}
            for i, s, m, v in runs
        }
        # A completion review the Reason asked for is part of the material the
        # next Reason must be able to read: its gaps are the feedback that
        # decides whether the loop continues, waits or blocks.
        review = tx.connection.execute(
            "SELECT payload_json FROM vnext.outbox WHERE tenant_id=%s AND project_id=%s"
            " AND task_id=%s AND kind='completion.reviewed'"
            " ORDER BY event_seq DESC LIMIT 1",
            tx.owner,
        ).fetchone()
        if review is not None:
            states["completion_review"] = strict_json_loads(review[0])
        # Freeze P04 assessment policy/outcome in the same RR manifest transaction.
        from wuji_core.blackboard.fact_view import aggregate

        states["claim_assessments"] = {}
        for kind, entity_id, revision in refs:
            if kind == "claim":
                claim = row(
                    tx.connection.execute(
                        "SELECT * FROM vnext.claim_revision WHERE entity_id=%s AND revision=%s",
                        (entity_id, revision),
                    )
                )
                # P03 historical fixtures may not bind a policy yet. Such snapshots
                # cannot later claim a historical fact outcome they never froze.
                bound = tx.connection.execute(
                    "SELECT 1 FROM vnext.task_assessment_policy WHERE task_id=%s",
                    (task_id,),
                ).fetchone()
                if bound:
                    states["claim_assessments"][entity_id + "@" + revision] = aggregate(
                        tx, claim
                    ).model_dump(mode="python")
        snapshot_id = str(uuid4())
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=self.ttl_seconds)
        query_json = json_text(query.payload())
        query_digest = hashlib.sha256(query_json.encode()).hexdigest()
        access_digest = _access_digest(tx)
        level = max(refs.values(), default=0)
        ordered = sorted(refs, key=lambda key: (key[0], key[1], int(key[2])))
        tx.connection.execute(
            "INSERT INTO vnext.publication(tenant_id,project_id,task_id,publication_id,kind,access_level) VALUES (%s,%s,%s,%s,'snapshot',%s)",
            (*tx.owner, snapshot_id, level),
        )
        tx.connection.execute(
            """INSERT INTO vnext.snapshot_manifest(tenant_id,project_id,task_id,snapshot_id,publication_id,
            query_json,query_digest,access_digest,manifest_json,access_level,created_at,expires_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                *tx.owner,
                snapshot_id,
                snapshot_id,
                query_json,
                query_digest,
                access_digest,
                json_text(
                    {
                        "states": states,
                        "dependencies": dependencies,
                        "relations": relations,
                    }
                ),
                level,
                now,
                expires,
            ),
        )
        for ordinal, (kind, entity_id, revision) in enumerate(ordered):
            tx.connection.execute(
                "INSERT INTO vnext.snapshot_ref(tenant_id,project_id,task_id,snapshot_id,ordinal,entity_type,entity_id,revision,access_level) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (*tx.owner, snapshot_id, ordinal, kind, entity_id, revision, level),
            )
            if kind == "artifact":
                tx.connection.execute(
                    "INSERT INTO vnext.publication_ref(tenant_id,project_id,task_id,publication_id,artifact_id,artifact_revision,access_level) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (*tx.owner, snapshot_id, entity_id, revision, level),
                )
        return SnapshotManifest(
            snapshot_id,
            *tx.owner,
            query_digest,
            access_digest,
            now,
            expires,
            tuple(_ref(*key) for key in ordered),
            states,
            tuple(dependencies),
            tuple(relations),
        )

    def _get(self, tx, snapshot_id):
        saved = row(
            tx.connection.execute(
                "SELECT * FROM vnext.snapshot_manifest WHERE snapshot_id=%s",
                (snapshot_id,),
            )
        )
        if not saved:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        if saved["access_digest"] != _access_digest(tx):
            # Existing creator binding is unchanged. A different subject needs
            # the narrow, actual Assignment/Run-backed P09 reader registration.
            permitted = tx.connection.execute(
                "SELECT vnext.can_read_scheduler_snapshot(%s,%s,%s,%s)",
                (*tx.owner, snapshot_id),
            ).fetchone()
            if permitted != (True,):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        if saved["expires_at"] <= datetime.now(timezone.utc):
            raise DomainError("SNAPSHOT_EXPIRED", 410)
        refs = tx.connection.execute(
            "SELECT entity_type,entity_id,revision FROM vnext.snapshot_ref WHERE snapshot_id=%s ORDER BY ordinal",
            (snapshot_id,),
        ).fetchall()
        content = strict_json_loads(saved["manifest_json"])
        return SnapshotManifest(
            snapshot_id,
            *tx.owner,
            saved["query_digest"],
            saved["access_digest"],
            saved["created_at"],
            saved["expires_at"],
            tuple(_ref(*ref) for ref in refs),
            content["states"],
            tuple(content["dependencies"]),
            tuple(content["relations"]),
        )

    def get(self, task_id, access, snapshot_id):
        with self.uow.transaction(access, task_id) as tx:
            return self._get(tx, snapshot_id)

    def page(self, task_id, access, snapshot_id, *, offset=0, limit=100):
        if (
            isinstance(offset, bool)
            or isinstance(limit, bool)
            or offset < 0
            or not 1 <= limit <= 5000
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        manifest = self.get(task_id, access, snapshot_id)
        return manifest.refs[offset : offset + limit]

    def read_ref(self, task_id, access, snapshot_id, ref):
        with self.uow.transaction(access, task_id) as tx:
            manifest = self._get(tx, snapshot_id)
            if ref not in manifest.refs:
                raise DomainError("INVALID_REFERENCE", 422)
            tables = {
                "claim": "claim_revision",
                "intent": "intent_revision",
                "observation": "observation",
                "artifact": "artifact",
            }
            result = row(
                tx.connection.execute(
                    sql.SQL(
                        "SELECT * FROM {} WHERE entity_id=%s AND revision=%s"
                    ).format(sql.Identifier("vnext", tables[ref.entity_type.value])),
                    (ref.id, ref.revision.root),
                )
            )
            if result is None:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            # This is an internal immutable-domain row, not a public RecordView DTO.
            return result
