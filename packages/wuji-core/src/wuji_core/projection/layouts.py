"""Authorized personal topology layouts with optimistic compare-and-swap."""

from __future__ import annotations

from hashlib import sha256
import re
from typing import Iterable

from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.contracts.views import (
    LayoutAnchor,
    LayoutPatch,
    LayoutPreference,
    LayoutReceipt,
    LayoutViewport,
    ViewSelectionMode,
)
from wuji_core.http.json_boundary import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text, row
from wuji_core.projection.access import AccessRequirements


LAYOUT_SCHEMA = "wuji.layout.v1"
DEFAULT_VIEWPORT = LayoutViewport(x=0.0, y=0.0, zoom=0.82)
_VIEW_MODES = {
    "knowledge-live": ViewSelectionMode.follow_latest,
    "knowledge-history": ViewSelectionMode.explicit_revision,
}
_REVISION = re.compile(r"^(0|[1-9][0-9]*)$")
_MAX_LAYOUT_BYTES = 262_144


class LayoutRepository:
    """Persist only user layout state; domain records remain outside this port."""

    def __init__(self, uow, *, max_bytes: int = _MAX_LAYOUT_BYTES) -> None:
        if type(max_bytes) is not int or not 1 <= max_bytes <= 1_048_576:
            raise ValueError("invalid layout payload bound")
        self.uow = uow
        self.max_bytes = max_bytes

    @staticmethod
    def view_selection_mode(view_name: str) -> ViewSelectionMode:
        if view_name not in _VIEW_MODES:
            raise DomainError("INVALID_SCHEMA", 422)
        return _VIEW_MODES[view_name]

    @staticmethod
    def _revision(value: str) -> int:
        if not isinstance(value, str) or not _REVISION.fullmatch(value):
            raise DomainError("INVALID_SCHEMA", 422)
        # The wire contract is decimal text; the database value is bounded by
        # PostgreSQL numeric and we never expose its internal representation.
        try:
            return int(value)
        except ValueError as error:  # pragma: no cover - regex already bounds it
            raise DomainError("INVALID_SCHEMA", 422) from error

    @staticmethod
    def _stored_revision(value) -> int:
        try:
            revision = int(value)
        except (TypeError, ValueError, OverflowError) as error:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503) from error
        if revision < 1:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        return revision

    @staticmethod
    def _anchor_key(anchor: LayoutAnchor) -> tuple[str, str, str | None]:
        return (anchor.entity_type.value, anchor.id, anchor.revision.root if anchor.revision else None)

    def _validate_patch(self, view_name: str, patch: LayoutPatch) -> tuple[str, str, str]:
        if not isinstance(patch, LayoutPatch):
            try:
                patch = LayoutPatch.model_validate(patch)
            except Exception as error:  # pydantic error is mapped at the HTTP boundary
                raise DomainError("INVALID_SCHEMA", 422) from error
        expected_mode = self.view_selection_mode(view_name)
        if patch.selection_mode != expected_mode:
            raise DomainError("INVALID_SCHEMA", 422)
        keys = [self._anchor_key(entry.anchor) for entry in patch.entries]
        if len(keys) != len(set(keys)):
            raise DomainError("INVALID_SCHEMA", 422)
        try:
            encoded_entries = canonical_json_bytes(
                [entry.model_dump(mode="json") for entry in patch.entries]
            )
            encoded_viewport = canonical_json_bytes(patch.viewport.model_dump(mode="json"))
            encoded_patch = canonical_json_bytes(patch.model_dump(mode="json"))
        except (TypeError, ValueError) as error:
            raise DomainError("INVALID_SCHEMA", 422) from error
        if len(encoded_entries) + len(encoded_viewport) + len(encoded_patch) > self.max_bytes:
            raise DomainError("INVALID_SCHEMA", 422)
        return (
            json_text([entry.model_dump(mode="json") for entry in patch.entries]),
            json_text(patch.viewport.model_dump(mode="json")),
            patch.schema_version.root,
        )

    @staticmethod
    def _advisory_key(owner: tuple[str, str, str], subject: str, view_name: str) -> int:
        digest = sha256(json_text([*owner, subject, view_name, LAYOUT_SCHEMA]).encode()).digest()
        return int.from_bytes(digest[:8], byteorder="big", signed=True)

    @staticmethod
    def _require_current_acl(tx) -> None:
        current = row(
            tx.connection.execute(
                """SELECT can_read,clearance FROM vnext.task_access
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND subject=%s""",
                (*tx.owner, tx.access.principal.subject),
            )
        )
        if not current or not current["can_read"]:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        # UnitOfWork derived the RLS clearance before entering the port. A
        # concurrent ACL update cannot pass the share lock until this request
        # has finished, so the remaining checks use one coherent ACL.
        if int(current["clearance"]) != int(tx.permissions["clearance"]):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")

    @staticmethod
    def _visible_revisions(tx, entity_type: str, entity_id: str) -> list[str]:
        rows = tx.connection.execute(
            """SELECT revision FROM vnext.entity_revision_registry
            WHERE tenant_id=%s AND project_id=%s AND task_id=%s
              AND entity_type=%s AND entity_id=%s
            ORDER BY revision DESC""",
            (*tx.owner, entity_type, entity_id),
        ).fetchall()
        return [str(value[0]) for value in rows]

    def _validate_knowledge_anchor(self, tx, anchor: LayoutAnchor) -> None:
        kind = anchor.entity_type.value
        revisions = self._visible_revisions(tx, kind, anchor.id)
        if anchor.revision is not None:
            wanted = anchor.revision.root
            if wanted not in revisions:
                raise DomainError("INVALID_REFERENCE", 422)
            ref = KnowledgeRef.model_validate(
                {"entity_type": kind, "id": anchor.id, "revision": wanted}
            )
            # This rechecks the actual domain row (sealed artifacts, evidence
            # closure, and current RLS clearance) rather than trusting the
            # registry row alone.
            AccessRequirements(tx).knowledge(ref)
            return
        if not revisions:
            raise DomainError("INVALID_REFERENCE", 422)
        ref = KnowledgeRef.model_validate(
            {"entity_type": kind, "id": anchor.id, "revision": revisions[0]}
        )
        AccessRequirements(tx).knowledge(ref)

    def _validate_work_anchor(self, tx, anchor: LayoutAnchor) -> None:
        kind = anchor.entity_type.value
        if kind == "work_item":
            found = row(
                tx.connection.execute(
                    """SELECT revision FROM vnext.work_item
                    WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s""",
                    (*tx.owner, anchor.id),
                )
            )
            if not found:
                raise DomainError("INVALID_REFERENCE", 422)
            if anchor.revision is not None and anchor.revision.root != str(found["revision"]):
                raise DomainError("INVALID_REFERENCE", 422)
            AccessRequirements(tx).work(anchor.id)
            return
        if kind == "agent_run":
            if anchor.revision is not None and anchor.revision.root != "1":
                raise DomainError("INVALID_REFERENCE", 422)
            found = row(
                tx.connection.execute(
                    """SELECT agent_run_id FROM vnext.agent_run
                    WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s""",
                    (*tx.owner, anchor.id),
                )
            )
            if not found:
                raise DomainError("INVALID_REFERENCE", 422)
            AccessRequirements(tx).run(anchor.id)
            return
        raise DomainError("INVALID_REFERENCE", 422)

    def _validate_origin_anchor(self, tx, anchor: LayoutAnchor) -> None:
        if anchor.id != tx.owner[2]:
            raise DomainError("INVALID_REFERENCE", 422)
        current_revision = str(tx.task["control_version"])
        if anchor.revision is not None and anchor.revision.root != current_revision:
            raise DomainError("INVALID_REFERENCE", 422)

    def _validate_anchors(self, tx, entries: Iterable) -> None:
        for entry in entries:
            anchor = entry.anchor
            if anchor.entity_type.value in {"claim", "intent", "observation", "artifact"}:
                self._validate_knowledge_anchor(tx, anchor)
            elif anchor.entity_type.value in {"work_item", "agent_run"}:
                self._validate_work_anchor(tx, anchor)
            elif anchor.entity_type.value == "origin":
                self._validate_origin_anchor(tx, anchor)
            else:
                # Goal/verification/finding/report nodes have no stable P15
                # producer in the current schema. Do not create a layout row
                # that would become an unauthorized shadow node.
                raise DomainError("INVALID_REFERENCE", 422)

    def _default(self, view_name: str) -> LayoutPreference:
        return LayoutPreference.model_validate(
            {
                "schema_version": "wuji.api.v2",
                "view_name": view_name,
                "layout_revision": "0",
                "selection_mode": self.view_selection_mode(view_name).value,
                "entries": [],
                "viewport": DEFAULT_VIEWPORT.model_dump(mode="json"),
            }
        )

    @staticmethod
    def _row_value(view_name: str, saved) -> LayoutPreference:
        try:
            entries = strict_json_loads(saved["entries_json"])
            viewport = strict_json_loads(saved["viewport_json"])
            return LayoutPreference.model_validate(
                {
                    "schema_version": "wuji.api.v2",
                    "view_name": view_name,
                    "layout_revision": str(int(saved["layout_revision"])),
                    "selection_mode": saved["selection_mode"],
                    "entries": entries,
                    "viewport": viewport,
                }
            )
        except Exception as error:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503) from error

    def read(self, task_id: str, access, *, view_name: str) -> LayoutPreference:
        self.view_selection_mode(view_name)
        with self.uow.transaction(access, task_id, capability="layout") as tx:
            self._require_current_acl(tx)
            saved = row(
                tx.connection.execute(
                    """SELECT * FROM vnext.layout_preference
                    WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                      AND subject=%s AND view_name=%s AND layout_schema=%s""",
                    (*tx.owner, access.principal.subject, view_name, LAYOUT_SCHEMA),
                )
            )
            return self._default(view_name) if saved is None else self._row_value(view_name, saved)

    def write(
        self,
        task_id: str,
        access,
        *,
        view_name: str,
        patch: LayoutPatch,
        expected_revision: str,
        request_id: str,
    ) -> LayoutReceipt:
        self.view_selection_mode(view_name)
        expected = self._revision(expected_revision)
        entries_json, viewport_json, _schema_version = self._validate_patch(view_name, patch)
        with self.uow.transaction(access, task_id, capability="layout") as tx:
            self._require_current_acl(tx)
            self._validate_anchors(tx, patch.entries)
            tx.connection.execute(
                "SELECT pg_advisory_xact_lock(%s)",
                (self._advisory_key(tx.owner, access.principal.subject, view_name),),
            )
            saved = row(
                tx.connection.execute(
                    """SELECT * FROM vnext.layout_preference
                    WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                      AND subject=%s AND view_name=%s AND layout_schema=%s
                    FOR UPDATE""",
                    (*tx.owner, access.principal.subject, view_name, LAYOUT_SCHEMA),
                )
            )
            current = 0 if saved is None else self._stored_revision(saved["layout_revision"])
            if current != expected:
                raise DomainError("STALE_VERSION", 409)
            next_revision = current + 1
            if saved is None:
                tx.connection.execute(
                    """INSERT INTO vnext.layout_preference(
                    tenant_id,project_id,task_id,subject,view_name,layout_schema,
                    layout_revision,selection_mode,entries_json,viewport_json)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (*tx.owner, access.principal.subject, view_name, LAYOUT_SCHEMA,
                     next_revision, patch.selection_mode.value, entries_json, viewport_json),
                )
            else:
                tx.connection.execute(
                    """UPDATE vnext.layout_preference SET layout_revision=%s,
                    selection_mode=%s,entries_json=%s,viewport_json=%s,
                    updated_at=clock_timestamp()
                    WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                      AND subject=%s AND view_name=%s AND layout_schema=%s""",
                    (next_revision, patch.selection_mode.value, entries_json, viewport_json,
                     *tx.owner, access.principal.subject, view_name, LAYOUT_SCHEMA),
                )
            return LayoutReceipt.model_validate(
                {
                    "view_name": view_name,
                    "layout_revision": str(next_revision),
                    "request_id": request_id,
                }
            )

    # Friendly aliases for callers that model the repository as a key/value port.
    get = read
    put = write
