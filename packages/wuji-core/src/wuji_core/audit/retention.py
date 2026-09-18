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
from datetime import datetime, timedelta, timezone
from typing import Mapping

from wuji_core.completion import platform_errors
from wuji_core.persistence.uow import DomainError

RETENTION_ROLES = frozenset({"operator", "controller"})
MAX_KEY = 256
MAX_REASON = 2048
MAX_CHECKED_MATERIALS = 200
PURGE_AUTHORITY = "operator"
RETENTION_PROFILE_SCHEMA = "wuji.data-retention-profile.v1"
RETENTION_ACTIONS = frozenset({"gc", "purge"})
MAX_PROFILE_REASONS = 32
MAX_RETENTION_SECONDS = 2**31 - 1


@dataclass(frozen=True)
class DataRetentionProfile:
    """An explicit, reviewable retention policy rather than a hidden default.

    Durations are intentionally supplied by the caller.  The platform does
    not invent regulatory retention periods.  ``allow_policy_purge`` is an
    explicit override for a *specific* purge action; it never disables the
    hard live-lease boundary and never makes ordinary GC ignore references.
    """

    profile_id: str
    version: str = "1"
    approved: bool = False
    gc_after_seconds: int | None = None
    allow_policy_purge: bool = False
    purge_reasons: frozenset[str] = frozenset()

    def __post_init__(self):
        if (
            not isinstance(self.profile_id, str)
            or not 1 <= len(self.profile_id) <= MAX_KEY
            or "\x00" in self.profile_id
        ):
            raise ValueError("a bounded retention profile id is required")
        if (
            not isinstance(self.version, str)
            or not 1 <= len(self.version) <= 64
            or "\x00" in self.version
        ):
            raise ValueError("a bounded retention profile version is required")
        if not isinstance(self.approved, bool):
            raise ValueError("retention approval must be explicit")
        if self.gc_after_seconds is not None and (
            type(self.gc_after_seconds) is not int
            or not 1 <= self.gc_after_seconds <= MAX_RETENTION_SECONDS
        ):
            raise ValueError("gc_after_seconds must be a bounded positive integer")
        if not isinstance(self.allow_policy_purge, bool):
            raise ValueError("policy purge permission must be explicit")
        reasons = self.purge_reasons
        if not isinstance(reasons, (set, frozenset, tuple, list)):
            raise ValueError("purge_reasons must be a bounded collection")
        checked = frozenset(reasons)
        if len(checked) > MAX_PROFILE_REASONS or any(
            not isinstance(reason, str) or not 1 <= len(reason) <= MAX_REASON
            for reason in checked
        ):
            raise ValueError("purge reasons must be bounded strings")
        object.__setattr__(self, "purge_reasons", checked)

    @classmethod
    def from_document(cls, document: Mapping):
        if not isinstance(document, Mapping):
            raise ValueError("a retention profile document is required")
        expected = {
            "schema_version",
            "profile_id",
            "version",
            "approved",
            "gc_after_seconds",
            "allow_policy_purge",
            "purge_reasons",
        }
        if set(document) != expected or document["schema_version"] != RETENTION_PROFILE_SCHEMA:
            raise ValueError("unrecognized retention profile document")
        reasons = document["purge_reasons"]
        if not isinstance(reasons, list):
            raise ValueError("purge_reasons must be a list")
        return cls(
            profile_id=document["profile_id"],
            version=document["version"],
            approved=document["approved"],
            gc_after_seconds=document["gc_after_seconds"],
            allow_policy_purge=document["allow_policy_purge"],
            purge_reasons=frozenset(reasons),
        )

    def document(self) -> dict:
        return {
            "schema_version": RETENTION_PROFILE_SCHEMA,
            "profile_id": self.profile_id,
            "version": self.version,
            "approved": self.approved,
            "gc_after_seconds": self.gc_after_seconds,
            "allow_policy_purge": self.allow_policy_purge,
            "purge_reasons": sorted(self.purge_reasons),
        }


@dataclass(frozen=True)
class RetentionDecision:
    action: str
    allowed: bool
    reason: str
    authority: str | None = None
    code: str = "LIMIT_BLOCKED"
    status: int = 409

    def require(self):
        if not self.allowed:
            raise DomainError(self.code, self.status)
        return self


class RetentionPolicyEngine:
    """Pure policy decision engine used before a GC or policy purge mutation.

    The engine receives database facts, but does not query or mutate them.  A
    caller must therefore obtain those facts through the scoped UoW first and
    still pass the resulting authority through the SECURITY DEFINER producer.
    This keeps policy choice separate from RLS and makes every rule directly
    testable without a fake database.
    """

    def __init__(self, profile: DataRetentionProfile | Mapping):
        self.profile = (
            profile
            if isinstance(profile, DataRetentionProfile)
            else DataRetentionProfile.from_document(profile)
        )

    @staticmethod
    def _now(value):
        value = datetime.now(timezone.utc) if value is None else value
        if value.tzinfo is None:
            raise ValueError("retention comparisons require timezone-aware datetimes")
        return value

    def evaluate(
        self,
        artifact: Mapping,
        *,
        action: str,
        now=None,
        explicit: bool = False,
        reason: str | None = None,
    ) -> RetentionDecision:
        if action not in RETENTION_ACTIONS:
            raise ValueError("unknown retention action")
        if not isinstance(artifact, Mapping):
            raise ValueError("artifact facts are required")
        if not self.profile.approved:
            return RetentionDecision(action, False, "policy_not_approved")
        if artifact.get("body_removed") or artifact.get("state") == "tombstoned":
            return RetentionDecision(action, False, "already_tombstoned")
        # This is a hard boundary, not a configurable retention preference.
        if artifact.get("live_lease"):
            return RetentionDecision(action, False, "live_lease")

        if action == "gc":
            if artifact.get("referenced"):
                return RetentionDecision(action, False, "published_reference")
            if artifact.get("state") not in {"staged", "sealed"}:
                return RetentionDecision(action, False, "state_not_collectable")
            if self.profile.gc_after_seconds is None:
                return RetentionDecision(action, False, "gc_window_not_configured")
            created_at = artifact.get("created_at")
            if not isinstance(created_at, datetime):
                raise ValueError("GC policy requires artifact created_at")
            if created_at + timedelta(seconds=self.profile.gc_after_seconds) > self._now(now):
                return RetentionDecision(action, False, "retention_window_open")
            return RetentionDecision(action, True, "gc_eligible", authority="retention_policy")

        if not explicit:
            return RetentionDecision(action, False, "explicit_purge_required")
        if not self.profile.allow_policy_purge:
            return RetentionDecision(action, False, "policy_purge_not_allowed")
        if self.profile.purge_reasons and reason not in self.profile.purge_reasons:
            return RetentionDecision(action, False, "purge_reason_not_approved")
        return RetentionDecision(
            action,
            True,
            "policy_purge_approved",
            authority="retention_policy",
        )

    def allow_gc(self, artifact: Mapping, *, now=None) -> RetentionDecision:
        return self.evaluate(artifact, action="gc", now=now)

    def authorize_purge(self, artifact: Mapping, *, reason: str, explicit=True):
        return self.evaluate(
            artifact, action="purge", reason=reason, explicit=explicit
        ).require()


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

    def __init__(self, uow, *, artifacts, policy=None):
        if not callable(getattr(artifacts, "remove_bytes", None)):
            raise ValueError("the real artifact store is required")
        self.uow = uow
        self.artifacts = artifacts
        self.policy = (
            None
            if policy is None or isinstance(policy, RetentionPolicyEngine)
            else RetentionPolicyEngine(policy)
        ) if policy is not None else None
        if isinstance(policy, RetentionPolicyEngine):
            self.policy = policy

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
                "SELECT entity_id,revision,state,body_removed,access_level,storage_key,sha256,created_at,"
                " EXISTS(SELECT 1 FROM vnext.artifact_lease l"
                "   WHERE l.tenant_id=a.tenant_id AND l.project_id=a.project_id AND l.task_id=a.task_id"
                "     AND l.artifact_id=a.entity_id AND l.artifact_revision=a.revision"
                "     AND l.expires_at>clock_timestamp()) AS live_lease,"
                " (EXISTS(SELECT 1 FROM vnext.publication_ref p"
                "    WHERE p.tenant_id=a.tenant_id AND p.project_id=a.project_id AND p.task_id=a.task_id"
                "      AND p.artifact_id=a.entity_id AND p.artifact_revision=a.revision)"
                "  OR EXISTS(SELECT 1 FROM vnext.observation_artifact o"
                "    WHERE o.tenant_id=a.tenant_id AND o.project_id=a.project_id AND o.task_id=a.task_id"
                "      AND o.artifact_id=a.entity_id AND o.artifact_revision=a.revision)"
                "  OR EXISTS(SELECT 1 FROM vnext.entity_relation r"
                "    WHERE r.tenant_id=a.tenant_id AND r.project_id=a.project_id AND r.task_id=a.task_id"
                "      AND r.target_type='artifact' AND r.target_id=a.entity_id AND r.target_revision=a.revision)"
                "  OR EXISTS(SELECT 1 FROM vnext.assessment_input i"
                "    WHERE i.tenant_id=a.tenant_id AND i.project_id=a.project_id AND i.task_id=a.task_id"
                "      AND i.entity_type='artifact' AND i.entity_id=a.entity_id AND i.revision=a.revision)"
                "  OR EXISTS(SELECT 1 FROM vnext.snapshot_ref s"
                "    WHERE s.tenant_id=a.tenant_id AND s.project_id=a.project_id AND s.task_id=a.task_id"
                "      AND s.entity_type='artifact' AND s.entity_id=a.entity_id AND s.revision=a.revision)) AS referenced"
                " FROM vnext.artifact"
                " a"
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
            authority = PURGE_AUTHORITY
            if replay is None and self.policy is not None:
                self.policy.authorize_purge(
                    {
                        "state": record[2],
                        "body_removed": bool(record[3]),
                        "created_at": record[7],
                        "live_lease": bool(record[8]),
                        "referenced": bool(record[9]),
                    },
                    reason=reason,
                )
                authority = "retention_policy"
            with platform_errors():
                stored = tx.connection.execute(
                    "SELECT vnext.purge_artifact(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        *tx.owner,
                        purge_key,
                        artifact_id,
                        revision,
                        reason,
                        authority,
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
