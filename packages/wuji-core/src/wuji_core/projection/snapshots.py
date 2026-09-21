"""Durable authorized topology pages and history over one saved RR read."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from uuid import uuid4

from wuji_core.blackboard.fact_view import FactLedger
from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.contracts.generated import ExplorationViewV1
from wuji_core.contracts.views import RecordView, SnapshotIndex, TopologySnapshot, ViewQuery
from wuji_core.http.json_boundary import strict_json_loads
from wuji_core.persistence.snapshots import SnapshotQuery, SnapshotRepository
from wuji_core.persistence.uow import DomainError, json_text, row
from wuji_core.projection.access import AccessRequirements, access_digest, require_binding
from wuji_core.projection.builder import build_projection, node_id
from wuji_core.projection.exploration import ExplorationReadModel, PROJECTION_VERSION as EXPLORATION_VERSION
from wuji_core.projection.records import ProjectionRecords, public_value


PROJECTION_VERSION = "wuji.topology.v1"


def _now():
    return datetime.now(timezone.utc)


def _query(query):
    return ViewQuery.model_validate(query if query is not None else dict(
        mode="live", snapshot_id=None, cursor=None, node_limit=300, edge_limit=600,
    ))


def _query_body(query):
    body = query.model_dump(mode="json")
    body["cursor"] = None
    return body


def _digest(value):
    return sha256(json_text(value).encode()).hexdigest()


def _scope(tx):
    return (*tx.owner, tx.access.principal.subject)


MAX_STREAM_PATCHES = 2000


def _patches(before, after, *, limit):
    """Node/edge upserts and removals between two materializations.

    ``None`` means the change is too large to describe as one bounded batch; the
    caller must send an explicit resnapshot instead of a partial patch list.
    """

    patches = []
    old_nodes = {node["id"]: node for node in before["nodes"]}
    new_nodes = {node["id"]: node for node in after["nodes"]}
    for identifier, node in new_nodes.items():
        if old_nodes.get(identifier) != node:
            patches.append({"op": "upsert_node", "value": node})
    for identifier in old_nodes:
        if identifier not in new_nodes:
            patches.append({"op": "remove_node", "value": {"id": identifier}})
    old_edges = {edge["id"]: edge for edge in before["edges"]}
    new_edges = {edge["id"]: edge for edge in after["edges"]}
    for identifier, edge in new_edges.items():
        if old_edges.get(identifier) != edge:
            patches.append({"op": "upsert_edge", "value": edge})
    for identifier in old_edges:
        if identifier not in new_edges:
            patches.append({"op": "remove_edge", "value": {"id": identifier}})
    if len(patches) > limit:
        return None
    return patches


class ProjectionRepository:
    def __init__(self, uow, *, snapshots=None, ledger=None, ttl_seconds=3600,
                 max_records=5000, history_page_size=100):
        if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 86400:
            raise ValueError("invalid projection lifetime")
        if type(max_records) is not int or not 1 <= max_records <= 5000:
            raise ValueError("invalid projection record bound")
        if type(history_page_size) is not int or not 1 <= history_page_size <= 1000:
            raise ValueError("invalid history page bound")
        self.uow, self.ttl_seconds = uow, ttl_seconds
        self.max_records, self.history_page_size = max_records, history_page_size
        self.snapshots = snapshots if snapshots is not None else SnapshotRepository(uow, ttl_seconds=ttl_seconds)
        self.ledger = ledger if ledger is not None else FactLedger(uow)
        if self.snapshots.uow is not uow or self.ledger.uow is not uow:
            raise ValueError("projection services must share the same UnitOfWork")
        self.records = ProjectionRecords(self.ledger, max_records=max_records)
        self.exploration = ExplorationReadModel()

    def topology(self, task_id, access, *, query=None):
        query = _query(query)
        if (query.mode.value == "history") != (query.snapshot_id is not None):
            raise DomainError("INVALID_SCHEMA", 422)
        with self.uow.transaction(access, task_id, capability="snapshot", repeatable_read=True) as tx:
            if query.cursor is not None:
                cursor = self._cursor(tx, query.cursor.root, "page")
                if cursor["query_digest"] != _digest(_query_body(query)):
                    raise DomainError("NOT_FOUND_OR_FORBIDDEN")
                view = self._view(tx, cursor["view_id"])
                if any(cursor[key] != view[key] for key in ("query_digest", "access_digest", "projection_version")):
                    raise DomainError("NOT_FOUND_OR_FORBIDDEN")
                saved = self._materialization(tx, view["snapshot_id"])
                return self._page(tx, saved, view, strict_json_loads(cursor["position_json"]))
            if query.snapshot_id is not None:
                saved = self._materialization(tx, query.snapshot_id.root, history=True)
                view = self._new_view(tx, saved, query)
                return self._page(tx, saved, view, {"node": 0, "edge": 0})
            return self.create_in_transaction(tx, query=query)

    def _compose(self, tx, query):
        """Build one materialization document for this subject without writing it."""

        create = getattr(self.snapshots, "create_in_transaction", None)
        if not callable(create):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        manifest = create(tx, query=SnapshotQuery(max_references=self.max_records))
        frozen = self.records.materialize(tx, manifest)
        # Execution records can inherit an older Intent's evidence that is not
        # part of the default latest-knowledge selection. Retain that actual
        # basis under the same existing publication, without changing its refs
        # or creating a second knowledge authority.
        for guard in frozen.guards:
            if guard["kind"] == "knowledge" and guard["ref"]["entity_type"] == "artifact":
                ref = guard["ref"]
                tx.connection.execute(
                    """INSERT INTO vnext.publication_ref(tenant_id,project_id,task_id,publication_id,
                    artifact_id,artifact_revision,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(tenant_id,project_id,task_id,publication_id,artifact_id,artifact_revision) DO NOTHING""",
                    (*tx.owner, manifest.snapshot_id, ref["id"], ref["revision"], frozen.access_level),
                )
        graph = build_projection(frozen.records, frozen.relations)
        problems, insights, problem_relations = self.exploration.materialize(tx, frozen)
        # Edges are scheduled only after both endpoints have been delivered.
        indexes = {node.id: index for index, node in enumerate(graph.nodes)}
        edges = sorted(graph.edges, key=lambda e: (max(indexes[e.source], indexes[e.target]), e.id))
        document = {
            "records": {node_id(record.ref): public_value(record) for record in frozen.records},
            "nodes": public_value(graph.nodes), "edges": public_value(edges),
            "exploration": {
                "problems": public_value(problems),
                "insights": public_value(insights),
                "relations": public_value(problem_relations),
                "missing_fields": sorted({
                    *("public_rationale" for problem in problems if problem.public_rationale is None),
                    *("work_result" for problem in problems if problem.work_result is None),
                    *("todo_summary" for problem in problems if not problem.todo_summary),
                }),
            },
            "guards": frozen.guards,
        }
        now = _now()
        expires = min(manifest.expires_at, now + timedelta(seconds=self.ttl_seconds))
        if expires <= now:
            raise DomainError("SNAPSHOT_EXPIRED", 410)
        query_body = _query_body(query)
        return dict(
            tenant_id=tx.owner[0], project_id=tx.owner[1], task_id=tx.owner[2],
            subject=tx.access.principal.subject, snapshot_id=manifest.snapshot_id,
            query_json=json_text(query_body), query_digest=_digest(query_body),
            access_digest=access_digest(tx), projection_version=PROJECTION_VERSION,
            materialization_json=json_text(document), created_at=now, expires_at=expires,
            access_level=frozen.access_level, document=document,
        )

    def _write_materialization(self, tx, saved, *, initial_view_id, event_origin):
        tx.connection.execute(
            """INSERT INTO vnext.projection_materialization(tenant_id,project_id,task_id,subject,snapshot_id,
            initial_view_id,query_json,query_digest,access_digest,projection_version,materialization_json,
            internal_event_origin,access_level,created_at,expires_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (*_scope(tx), saved["snapshot_id"], initial_view_id, saved["query_json"], saved["query_digest"],
             saved["access_digest"], PROJECTION_VERSION, saved["materialization_json"],
             event_origin, saved["access_level"], saved["created_at"], saved["expires_at"]),
        )

    def create_in_transaction(self, tx, *, query=None):
        """Write manifest, records, graph, view and first cursor in the caller's RR."""
        query = _query(query)
        if query.mode.value != "live" or query.snapshot_id is not None or query.cursor is not None:
            raise DomainError("INVALID_SCHEMA", 422)
        if tx.purpose != "snapshot" or not tx.permissions.get("can_read"):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        isolation = tx.connection.execute("SHOW transaction_isolation").fetchone()
        if isolation != ("repeatable read",):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        saved = self._compose(tx, query)
        view_id = str(uuid4())
        saved["initial_view_id"] = view_id
        self._write_materialization(tx, saved, initial_view_id=view_id,
                                    event_origin=tx.task["event_seq"])
        view = self._new_view(tx, saved, query, view_id=view_id)
        return self._page(tx, saved, view, {"node": 0, "edge": 0})

    def exploration_view(self, task_id, access, *, query=None):
        """Return problem semantics from the same fixed records as topology."""

        query = _query(query)
        if (query.mode.value == "history") != (query.snapshot_id is not None):
            raise DomainError("INVALID_SCHEMA", 422)
        with self.uow.transaction(access, task_id, capability="snapshot", repeatable_read=True) as tx:
            if query.cursor is not None:
                cursor = self._cursor(tx, query.cursor.root, "page")
                position = strict_json_loads(cursor["position_json"])
                if position.get("projection") != EXPLORATION_VERSION:
                    raise DomainError("NOT_FOUND_OR_FORBIDDEN")
                if cursor["query_digest"] != _digest(_query_body(query)):
                    raise DomainError("NOT_FOUND_OR_FORBIDDEN")
                view = self._view(tx, cursor["view_id"])
                saved = self._materialization(tx, view["snapshot_id"])
                return self._exploration_page(tx, saved, view, position)
            if query.snapshot_id is not None:
                saved = self._materialization(tx, query.snapshot_id.root, history=True)
                view = self._new_view(tx, saved, query)
                return self._exploration_page(tx, saved, view, {
                    "projection": EXPLORATION_VERSION, "problem": 0, "insight": 0, "relation": 0,
                })
            saved = self._compose(tx, query)
            view_id = str(uuid4())
            saved["initial_view_id"] = view_id
            self._write_materialization(
                tx, saved, initial_view_id=view_id, event_origin=tx.task["event_seq"]
            )
            view = self._new_view(tx, saved, query, view_id=view_id)
            return self._exploration_page(tx, saved, view, {
                "projection": EXPLORATION_VERSION, "problem": 0, "insight": 0, "relation": 0,
            })

    def _materialization(self, tx, snapshot_id, *, history=False):
        saved = row(tx.connection.execute(
            """SELECT p.*,m.expires_at AS manifest_expires_at FROM vnext.projection_materialization p
            JOIN vnext.snapshot_manifest m USING(tenant_id,project_id,task_id,snapshot_id)
            WHERE p.tenant_id=%s AND p.project_id=%s AND p.task_id=%s AND p.subject=%s AND p.snapshot_id=%s""",
            (*_scope(tx), snapshot_id),
        ))
        if saved is None:
            raise DomainError("HISTORY_UNAVAILABLE", 410) if history else DomainError("NOT_FOUND_OR_FORBIDDEN")
        require_binding(tx, saved)
        if min(saved["expires_at"], saved["manifest_expires_at"]) <= _now():
            raise DomainError("SNAPSHOT_EXPIRED", 410)
        if saved["projection_version"] != PROJECTION_VERSION:
            raise DomainError("VIEW_EXPIRED", 410)
        document = strict_json_loads(saved["materialization_json"])
        AccessRequirements(tx).reauthorize(document["guards"])
        return saved

    def _new_view(self, tx, saved, query, *, view_id=None):
        now = _now()
        expires = min(saved["expires_at"], now + timedelta(seconds=self.ttl_seconds))
        body = _query_body(query)
        view = dict(
            tenant_id=tx.owner[0], project_id=tx.owner[1], task_id=tx.owner[2], subject=tx.access.principal.subject,
            view_id=view_id or str(uuid4()), snapshot_id=saved["snapshot_id"],
            query_json=json_text(body), query_digest=_digest(body), access_digest=access_digest(tx),
            projection_version=PROJECTION_VERSION, view_revision="1", created_at=now, expires_at=expires,
        )
        tx.connection.execute(
            """INSERT INTO vnext.projection_view(tenant_id,project_id,task_id,subject,view_id,snapshot_id,
            query_json,query_digest,access_digest,projection_version,view_revision,created_at,expires_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (*_scope(tx), view["view_id"], view["snapshot_id"], view["query_json"], view["query_digest"],
             view["access_digest"], view["projection_version"], view["view_revision"], now, expires),
        )
        return view

    def _view(self, tx, view_id):
        view = row(tx.connection.execute(
            "SELECT * FROM vnext.projection_view WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND subject=%s AND view_id=%s",
            (*_scope(tx), view_id),
        ))
        if view is None:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        require_binding(tx, view)
        if view["expires_at"] <= _now() or view["projection_version"] != PROJECTION_VERSION:
            raise DomainError("VIEW_EXPIRED", 410)
        return view

    def _cursor(self, tx, handle, kind):
        cursor = row(tx.connection.execute(
            "SELECT * FROM vnext.projection_cursor WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND subject=%s AND handle=%s",
            (*_scope(tx), handle),
        ))
        if cursor is None or cursor["kind"] != kind:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        require_binding(tx, cursor)
        if cursor["expires_at"] <= _now() or cursor["projection_version"] != PROJECTION_VERSION:
            raise DomainError("VIEW_EXPIRED", 410)
        return cursor

    def _save_cursor(self, tx, *, kind, query_digest, expires_at, position, view_id=None):
        handle = token_urlsafe(32)
        tx.connection.execute(
            """INSERT INTO vnext.projection_cursor(tenant_id,project_id,task_id,subject,handle,kind,
            view_id,query_digest,access_digest,projection_version,position_json,expires_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (*_scope(tx), handle, kind, view_id, query_digest, access_digest(tx), PROJECTION_VERSION,
             json_text(position), expires_at),
        )
        return handle

    def _page(self, tx, saved, view, position):
        document = strict_json_loads(saved["materialization_json"])
        query = _query(strict_json_loads(view["query_json"]))
        nodes, edges = document["nodes"], document["edges"]
        start_node, start_edge = position["node"], position["edge"]
        if type(start_node) is not int or type(start_edge) is not int or not (
            0 <= start_node <= len(nodes) and 0 <= start_edge <= len(edges)
        ):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        end_node = min(len(nodes), start_node + query.node_limit)
        delivered = {node["id"] for node in nodes[:end_node]}
        end_edge = start_edge
        while end_edge < len(edges) and end_edge - start_edge < query.edge_limit:
            edge = edges[end_edge]
            if edge["source"] not in delivered or edge["target"] not in delivered:
                break
            end_edge += 1
        more = end_node < len(nodes) or end_edge < len(edges)
        handle = self._save_cursor(
            tx, kind="page", query_digest=view["query_digest"], expires_at=view["expires_at"],
            position={"node": end_node, "edge": end_edge}, view_id=view["view_id"],
        )
        return TopologySnapshot.model_validate(dict(
            view_id=view["view_id"], snapshot_id=saved["snapshot_id"], view_revision=str(view["view_revision"]),
            query_digest=view["query_digest"], access_scope_digest=view["access_digest"],
            projection_version=view["projection_version"], nodes=nodes[start_node:end_node],
            edges=edges[start_edge:end_edge], opaque_cursor=handle, truncated=more,
            continuation=handle if more else None, allowed_actions=[],
        ))

    def _exploration_page(self, tx, saved, view, position):
        document = strict_json_loads(saved["materialization_json"])
        content = document.get("exploration")
        if not isinstance(content, dict):
            raise DomainError("HISTORY_UNAVAILABLE", 410)
        query = _query(strict_json_loads(view["query_json"]))
        starts = tuple(position.get(key) for key in ("problem", "insight", "relation"))
        if any(type(value) is not int or value < 0 for value in starts):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        start_problem, start_insight, start_relation = starts
        problems, insights, relations = (
            content["problems"], content["insights"], content["relations"]
        )
        if start_problem > len(problems) or start_insight > len(insights) or start_relation > len(relations):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        end_problem = min(len(problems), start_problem + query.node_limit)
        end_insight = min(len(insights), start_insight + query.node_limit)
        delivered = {
            "intent:" + problem["intent_ref"]["id"] + "@" + problem["intent_ref"]["revision"]
            for problem in problems[:end_problem]
        } | {
            "claim:" + insight["claim_ref"]["id"] + "@" + insight["claim_ref"]["revision"]
            for insight in insights[:end_insight]
        }
        end_relation = start_relation
        while end_relation < len(relations) and end_relation - start_relation < query.edge_limit:
            relation = relations[end_relation]
            if relation["source_ref"] not in delivered or relation["target_ref"] not in delivered:
                break
            end_relation += 1
        more = (
            end_problem < len(problems)
            or end_insight < len(insights)
            or end_relation < len(relations)
        )
        handle = self._save_cursor(
            tx,
            kind="page",
            query_digest=view["query_digest"],
            expires_at=view["expires_at"],
            position={
                "projection": EXPLORATION_VERSION,
                "problem": end_problem,
                "insight": end_insight,
                "relation": end_relation,
            },
            view_id=view["view_id"],
        )
        states = [problem["execution_state"] for problem in problems if problem["execution_state"]]
        gaps = sum(bool(problem["gaps"]) for problem in problems)
        return ExplorationViewV1.model_validate({
            "schema_version": "wuji.exploration-view.v1",
            "task_id": tx.owner[2],
            "snapshot_id": saved["snapshot_id"],
            "view_revision": str(view["view_revision"]),
            "projection_version": EXPLORATION_VERSION,
            "mode": query.mode,
            "problems": problems[start_problem:end_problem],
            "insights": insights[start_insight:end_insight],
            "relations": relations[start_relation:end_relation],
            "execution_summary": {
                "settled_work": sum(state in {"done", "failed", "cancelled"} for state in states),
                "active_work": sum(state in {"leased", "running", "stopping"} for state in states),
                "waiting_work": sum(state in {"waiting_input", "blocked", "suspended"} for state in states),
                "reconciling_work": sum(state == "reconciling" for state in states),
                "needs_attention": gaps,
            },
            "opaque_cursor": handle,
            "continuation": handle if more else None,
            "missing_fields": content["missing_fields"],
        })

    def stream_task(self, access, view_id):
        """Resolve the Task of one saved view for the current tenant and subject.

        The frozen ``/views/{view_id}/events`` path carries no Task, so the
        application role resolves it with a bounded function that only sees rows
        of the acting tenant *and* subject. No view exists outside a Task.
        """

        if not isinstance(view_id, str) or not 1 <= len(view_id) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        with self.uow.connection_factory() as connection:
            with connection.transaction():
                for key, value in (
                    ("tenant", access.principal.tenant_id),
                    ("subject", access.principal.subject),
                ):
                    connection.execute(
                        "SELECT set_config(%s,%s,true)", ("wuji." + key, value)
                    ).fetchone()
                found = connection.execute(
                    "SELECT vnext.task_for_view(%s)", (view_id,)
                ).fetchone()
        if found is None or found[0] is None:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        return found[0]

    def stream_step(self, access, view_id, cursor=None):
        """One bounded step of an authorized view stream, or ``None`` when idle.

        The step advances the *same* view: a new materialization is written for
        the same query, the view revision moves by one, and the returned opaque
        cursor is the only resume handle. The view's own expiry is never
        extended, so a long stream cannot keep an expired view alive.
        """

        task_id = self.stream_task(access, view_id)
        with self.uow.transaction(access, task_id, capability="snapshot", repeatable_read=True) as tx:
            view = self._view(tx, view_id)
            saved = self._materialization(tx, view["snapshot_id"])
            if cursor is not None:
                saved_cursor = self._cursor(tx, cursor, "stream")
                if saved_cursor["view_id"] != view["view_id"] or saved_cursor["query_digest"] != view["query_digest"]:
                    raise DomainError("NOT_FOUND_OR_FORBIDDEN")
                # A cursor is a proof of the exact view state the client has
                # consumed. Once another consumer advances the same view, an
                # older cursor cannot safely resume by diffing from the new
                # server state; force a resnapshot instead of skipping a batch.
                position = strict_json_loads(saved_cursor["position_json"])
                if (
                    position.get("view_revision") != str(view["view_revision"])
                    or position.get("snapshot_id") != view["snapshot_id"]
                ):
                    raise DomainError("VIEW_RESET_REQUIRED", 409)
            origin = tx.connection.execute(
                "SELECT event_seq FROM vnext.task WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                tx.owner,
            ).fetchone()[0]
            if int(saved["internal_event_origin"]) >= int(origin):
                return None
            query = _query(strict_json_loads(view["query_json"]))
            advanced = self._compose(tx, query)
            before = strict_json_loads(saved["materialization_json"])
            patches = _patches(before, advanced["document"], limit=MAX_STREAM_PATCHES)
            if patches is None:
                raise DomainError("VIEW_RESET_REQUIRED", 409)
            self._write_materialization(
                tx, advanced, initial_view_id=view["view_id"], event_origin=origin
            )
            revision = int(view["view_revision"]) + 1
            tx.connection.execute(
                "UPDATE vnext.projection_view SET snapshot_id=%s,view_revision=%s"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND subject=%s AND view_id=%s",
                (advanced["snapshot_id"], revision, *_scope(tx), view["view_id"]),
            )
            if not patches:
                # Records moved without changing the delivered graph. The view
                # still advanced, but a batch must carry at least one patch, so
                # the caller sees no event for this step.
                return None
            handle = self._save_cursor(
                tx, kind="stream", query_digest=view["query_digest"],
                expires_at=view["expires_at"],
                position={
                    "event_seq": int(origin),
                    "snapshot_id": advanced["snapshot_id"],
                    "view_revision": str(revision),
                },
                view_id=view["view_id"],
            )
            return dict(
                schema_version="wuji.view-event.v3",
                view_id=view["view_id"],
                snapshot_id=advanced["snapshot_id"],
                base_view_revision=str(view["view_revision"]),
                view_revision=str(revision),
                cursor=handle,
                patches=patches,
            )

    def record(self, task_id, access, ref, *, snapshot_id=None):
        ref = KnowledgeRef.model_validate(ref)
        with self.uow.transaction(access, task_id, repeatable_read=True) as tx:
            if snapshot_id is not None:
                saved = self._materialization(tx, snapshot_id, history=True)
                value = strict_json_loads(saved["materialization_json"])["records"].get(node_id(ref))
                if value is None:
                    raise DomainError("NOT_FOUND_OR_FORBIDDEN")
                return RecordView.model_validate(value)
            if ref.entity_type.value not in {"claim", "intent", "observation", "artifact"}:
                raise DomainError("INVALID_REFERENCE", 422)
            return self.records.knowledge(tx, ref)

    def _summary(self, saved):
        return dict(
            snapshot_id=saved["snapshot_id"], view_id=saved["initial_view_id"], view_revision="1",
            created_at=saved["created_at"], query_digest=saved["query_digest"],
            projection_version=saved["projection_version"], query=strict_json_loads(saved["query_json"]),
        )

    def history(self, task_id, access, *, cursor=None):
        with self.uow.transaction(access, task_id, capability="snapshot", repeatable_read=True) as tx:
            digest = _digest({"kind": "snapshot_index", "page_size": self.history_page_size})
            if cursor is None:
                candidates = tx.connection.execute(
                    """SELECT snapshot_id FROM vnext.projection_materialization WHERE tenant_id=%s AND project_id=%s
                    AND task_id=%s AND subject=%s AND access_digest=%s AND projection_version=%s
                    AND expires_at>%s ORDER BY created_at DESC,snapshot_id""",
                    (*_scope(tx), access_digest(tx), PROJECTION_VERSION, _now()),
                )
                ids = []
                while batch := candidates.fetchmany(100):
                    for (snapshot_id,) in batch:
                        try:
                            self._materialization(tx, snapshot_id)
                        except DomainError as error:
                            if error.code in {"NOT_FOUND_OR_FORBIDDEN", "SNAPSHOT_EXPIRED", "VIEW_EXPIRED"}:
                                continue
                            raise
                        ids.append(snapshot_id)
                        if len(ids) > self.max_records:
                            # Only fully authorized retained views affect this
                            # bound, never invisible rows or internal counters.
                            raise DomainError("LIMIT_BLOCKED", 422)
                expires = _now() + timedelta(seconds=self.ttl_seconds)
            else:
                saved_cursor = self._cursor(tx, cursor, "index")
                if saved_cursor["query_digest"] != digest:
                    raise DomainError("NOT_FOUND_OR_FORBIDDEN")
                ids = strict_json_loads(saved_cursor["position_json"])["snapshot_ids"]
                expires = saved_cursor["expires_at"]
            # Reauthorize all frozen candidates before determining continuation;
            # revoked items cannot create empty pages or a hidden count signal.
            retained = []
            for snapshot_id in ids:
                try:
                    retained.append(self._materialization(tx, snapshot_id))
                except DomainError as error:
                    if error.code in {"NOT_FOUND_OR_FORBIDDEN", "SNAPSHOT_EXPIRED", "VIEW_EXPIRED"}:
                        continue
                    raise
            items = retained[:self.history_page_size]
            remaining = retained[self.history_page_size:]
            handle = None
            if remaining:
                handle = self._save_cursor(
                    tx, kind="index", query_digest=digest, expires_at=expires,
                    position={"snapshot_ids": [item["snapshot_id"] for item in remaining]},
                )
            return SnapshotIndex.model_validate(dict(items=[self._summary(item) for item in items], opaque_cursor=handle))
