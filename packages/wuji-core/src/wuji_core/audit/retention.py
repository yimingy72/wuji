"""P16 retention: garbage collection keeps commitments, purge leaves a tombstone.

Two different acts share one honest rule -- bytes never disappear while the
platform still claims them:

- ``ArtifactStore.collect_garbage`` only touches staged objects that nothing
  retains (no publication, live lease, observation, relation, assessment or
  snapshot), and marks the row before removing the file;
- ``RetentionService.purge`` is the explicit, attributed act for content that
  *is* cited (for example by a frozen report) but must not stay readable. It
  records who purged what and why, tombstones the artifact, and then removes the
  bytes. Readers keep the digest and learn that the content is unavailable
  instead of being shown a repaired or invented copy.
"""

from __future__ import annotations

from dataclasses import dataclass

from wuji_core.completion import platform_errors
from wuji_core.persistence.uow import DomainError

RETENTION_ROLES = frozenset({"operator", "controller"})
MAX_KEY = 256
MAX_REASON = 2048
MAX_CHECKED_MATERIALS = 200
PURGE_AUTHORITY = "operator"
"""``retention_policy`` is reserved for a policy engine; only the operator path
records purges today, so no caller can claim a policy it did not run."""


@dataclass(frozen=True)
class PurgeReceipt:
    document: dict

    @property
    def purge_id(self) -> str:
        return self.document["purge_id"]


def _reference(value):
    """Split an indexed ``entity@revision`` reference; anything else is ignored."""

    if not isinstance(value, str) or "@" not in value:
        return None
    entity_id, _, revision = value.partition("@")
    if not entity_id or not revision.isdigit() or int(revision) < 1:
        return None
    return entity_id, int(revision)


def unavailable_materials(tx, materials):
    """Which of these indexed materials no longer have readable bytes.

    The digest stays exactly as it was indexed; only availability is reported,
    together with the recorded purge reason when this caller may see it.
    """

    refs = []
    for material in materials or ():
        if not isinstance(material, dict):
            continue
        parsed = _reference(material.get("source_ref"))
        if material.get("source") == "artifact" and parsed is not None:
            refs.append(parsed)
    refs = refs[:MAX_CHECKED_MATERIALS]
    if not refs:
        return ()
    placeholders = ",".join(["(%s,%s)"] * len(refs))
    rows = tx.connection.execute(
        "SELECT a.entity_id,a.revision,a.state,a.body_removed,a.sha256,"
        " (SELECT g.purge_id FROM vnext.artifact_purge g"
        "   WHERE g.tenant_id=a.tenant_id AND g.project_id=a.project_id"
        "     AND g.task_id=a.task_id AND g.artifact_id=a.entity_id"
        "     AND g.artifact_revision=a.revision"
        "   ORDER BY g.created_at DESC LIMIT 1),"
        " (SELECT g.reason FROM vnext.artifact_purge g"
        "   WHERE g.tenant_id=a.tenant_id AND g.project_id=a.project_id"
        "     AND g.task_id=a.task_id AND g.artifact_id=a.entity_id"
        "     AND g.artifact_revision=a.revision"
        "   ORDER BY g.created_at DESC LIMIT 1)"
        " FROM vnext.artifact a"
        " WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s"
        " AND (a.entity_id,a.revision) IN (" + placeholders + ")",
        (*tx.owner, *[value for ref in refs for value in ref]),
    ).fetchall()
    return tuple(
        {
            "source_ref": f"{row[0]}@{row[1]}",
            "sha256": row[4],
            "state": row[2],
            "reason": row[6] or "garbage_collected",
            "purge_id": row[5],
        }
        for row in rows
        if row[3] or row[2] == "tombstoned"
    )


class RetentionService:
    """The explicit purge path: attributed, recorded, and byte-destroying."""

    def __init__(self, uow, *, artifacts):
        if not callable(getattr(artifacts, "remove_bytes", None)):
            raise ValueError("the real artifact store is required")
        self.uow = uow
        self.artifacts = artifacts

    @staticmethod
    def _authorize(access):
        roles = access.principal.roles
        if not RETENTION_ROLES.intersection(roles) or "agent" in roles:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")

    def purge(
        self, access, task_id, *, artifact_id, revision, reason, purge_key
    ) -> PurgeReceipt:
        """Purge one artifact version and leave the tombstone behind."""

        self._authorize(access)
        if not isinstance(artifact_id, str) or not 1 <= len(artifact_id) <= MAX_KEY:
            raise DomainError("INVALID_SCHEMA", 422)
        if (
            not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision < 1
        ):
            raise DomainError("INVALID_REFERENCE", 422)
        if not isinstance(reason, str) or not 1 <= len(reason) <= MAX_REASON:
            raise DomainError("INVALID_SCHEMA", 422)
        if not isinstance(purge_key, str) or not 1 <= len(purge_key) <= MAX_KEY:
            raise DomainError("INVALID_SCHEMA", 422)
        with self.uow.transaction(access, task_id, capability="purge") as tx:
            record = tx.connection.execute(
                "SELECT entity_id,revision,state,body_removed,access_level,storage_key,sha256"
                " FROM vnext.artifact"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s"
                " AND entity_id=%s AND revision=%s",
                (*tx.owner, artifact_id, revision),
            ).fetchone()
            if record is None or int(record[4]) > tx.permissions["clearance"]:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            # A retry of the same intent is answered by the producer's own
            # idempotency check, not by the "already tombstoned" refusal.
            replay = tx.connection.execute(
                "SELECT 1 FROM vnext.artifact_purge"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND purge_id=%s",
                (*tx.owner, purge_key),
            ).fetchone()
            if replay is None and record[2] == "tombstoned":
                raise DomainError("STALE_EXECUTION", 409)
            with platform_errors():
                stored = tx.connection.execute(
                    "SELECT vnext.purge_artifact(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        *tx.owner,
                        purge_key,
                        artifact_id,
                        revision,
                        reason,
                        PURGE_AUTHORITY,
                        tx.permissions["clearance"],
                    ),
                ).fetchone()[0]
            document = self._document(tx, stored)
            storage_key = record[5]
            already_removed = bool(record[3])
        if not already_removed:
            self.artifacts.remove_bytes({"storage_key": storage_key})
            with self.uow.transaction(access, task_id, capability="purge") as tx:
                tx.connection.execute(
                    "UPDATE vnext.artifact SET body_removed=true"
                    " WHERE tenant_id=%s AND project_id=%s AND task_id=%s"
                    " AND entity_id=%s AND revision=%s"
                    " AND state='tombstoned' AND NOT body_removed",
                    (*tx.owner, artifact_id, revision),
                )
                document = self._document(tx, stored)
        return PurgeReceipt(document=document)

    def read(self, access, task_id, purge_key):
        with self.uow.transaction(access, task_id, capability="read") as tx:
            return self._document(tx, purge_key)

    @staticmethod
    def _document(tx, purge_key):
        record = tx.connection.execute(
            "SELECT g.purge_id,g.artifact_id,g.artifact_revision,g.artifact_sha256,"
            "g.reason,g.authority,g.created_at,a.state,a.body_removed"
            " FROM vnext.artifact_purge g JOIN vnext.artifact a"
            " ON (a.tenant_id,a.project_id,a.task_id,a.entity_id,a.revision)"
            "  = (g.tenant_id,g.project_id,g.task_id,g.artifact_id,g.artifact_revision)"
            " WHERE g.tenant_id=%s AND g.project_id=%s AND g.task_id=%s AND g.purge_id=%s",
            (*tx.owner, purge_key),
        ).fetchone()
        if record is None:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        return {
            "purge_id": record[0],
            "task_id": tx.owner[2],
            "artifact_id": record[1],
            "artifact_revision": int(record[2]),
            "artifact_sha256": record[3],
            "reason": record[4],
            "authority": record[5],
            "state": record[7],
            "body_removed": bool(record[8]),
            "created_at": record[6],
        }
