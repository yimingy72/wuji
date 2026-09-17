"""P16 delivery: publish a frozen report under the media its profile requires.

A delivery is not a second report and not a second authority. It records what
the frozen commit actually contains against the requirements of one explicitly
declared profile:

- the report itself is cited by the digest that was frozen, never re-composed;
- materials are sealed platform artifacts (or the frozen body) with their own
  digests and levels -- the platform never synthesizes a material record;
- ``ready`` means every *required* requirement is satisfied, ``incomplete``
  means at least one required one is not, and the database refuses either state
  when the manifest does not agree with it;
- a screenshot is enforced only when a profile declares it (AC-069), and an
  offline profile stores no HTTP exchange at all.

Nothing here applies a blanket "everything needs screenshots and HTTP" rule:
the profile must be declared per delivery and is frozen with its own digest.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re

from wuji_core.audit.retention import unavailable_materials
from wuji_core.completion import platform_errors
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError

DELIVERY_ROLES = frozenset({"operator", "controller", "reconciler"})
PROFILE_SCHEMA = "wuji.delivery-profile.v1"
DELIVERY_SCHEMA = "wuji.report-delivery.v1"
REPORT_MEDIA_TYPE = "application/vnd.wuji.report+json"
MODES = ("offline", "http")
STATES = ("delivery_pending", "ready", "incomplete", "failed")
MAX_REQUIREMENTS = 32
MAX_MATERIALS = 500
MIN_COUNT = 64
MAX_KEY = 256

# A failed delivery names *why* it failed from a fixed, bounded set. A free-form
# message would leak internals into a frozen record and cannot be reviewed.
ERROR_CODES = frozenset(
    {
        "report_body_unavailable",
        "material_read_failed",
        "manifest_too_large",
        "sink_rejected",
        "sink_unavailable",
        "sink_timeout",
    }
)

_ROLE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_MEDIA_TYPE = re.compile(
    r"^[a-z0-9][a-z0-9!#$&^_.+-]{0,63}/(\*|[a-z0-9][a-z0-9!#$&^_.+-]{0,63})$"
)
_PROFILE_KEYS = frozenset({"schema_version", "profile_id", "mode", "requirements"})
_REQUIREMENT_KEYS = frozenset({"role", "media_type", "min_count", "required"})


def _invalid(message):
    raise DomainError("INVALID_SCHEMA", 422) from ValueError(message)


def _bounded_key(value, what):
    if not isinstance(value, str) or not 1 <= len(value) <= MAX_KEY or "\x00" in value:
        _invalid(f"a bounded {what} is required")
    return value


def normalize_profile(profile) -> dict:
    """Validate one declared profile and return its canonical document.

    The platform has no default profile: requirements are always the ones the
    caller declared for this delivery, so the historical manuscript's blanket
    rule can never be presented as a new approval.
    """

    if not isinstance(profile, dict) or set(profile) != _PROFILE_KEYS:
        _invalid("a complete delivery profile is required")
    if profile.get("schema_version") != PROFILE_SCHEMA:
        _invalid("unrecognized delivery profile schema")
    profile_id = _bounded_key(profile.get("profile_id"), "profile id")
    mode = profile.get("mode")
    if mode not in MODES:
        _invalid("a delivery profile has one bounded mode")
    requirements = profile.get("requirements")
    if not isinstance(requirements, list) or not 1 <= len(requirements) <= MAX_REQUIREMENTS:
        _invalid("a delivery profile declares its requirements explicitly")
    checked = []
    seen = set()
    for item in requirements:
        if not isinstance(item, dict) or set(item) != _REQUIREMENT_KEYS:
            _invalid("each requirement is a complete document")
        role = item.get("role")
        media_type = item.get("media_type")
        min_count = item.get("min_count")
        required = item.get("required")
        if not isinstance(role, str) or _ROLE.fullmatch(role) is None:
            _invalid("a requirement role is a bounded identifier")
        if not isinstance(media_type, str) or _MEDIA_TYPE.fullmatch(media_type) is None:
            _invalid("a requirement names a bounded media type")
        if (
            not isinstance(min_count, int)
            or isinstance(min_count, bool)
            or not 1 <= min_count <= MIN_COUNT
        ):
            _invalid("a requirement count stays bounded")
        if not isinstance(required, bool):
            _invalid("a requirement says whether it is required")
        if role in seen:
            _invalid("a requirement role appears once")
        seen.add(role)
        checked.append(
            {
                "role": role,
                "media_type": media_type,
                "min_count": min_count,
                "required": required,
            }
        )
    return {
        "schema_version": PROFILE_SCHEMA,
        "profile_id": profile_id,
        "mode": mode,
        "requirements": checked,
    }


def _matches(media_type: str, wanted: str) -> bool:
    if wanted.endswith("/*"):
        return media_type.startswith(wanted[:-1])
    return media_type == wanted


@dataclass(frozen=True)
class DeliveryReceipt:
    """One frozen delivery decision, as the product route returns it."""

    document: dict

    @property
    def delivery_id(self) -> str:
        return self.document["delivery_id"]

    @property
    def state(self) -> str:
        return self.document["state"]


class ReportDeliveryService:
    """Deliver a frozen report against one explicitly declared profile."""

    def __init__(self, uow, *, max_materials=MAX_MATERIALS):
        if not 1 <= int(max_materials) <= MAX_MATERIALS:
            raise ValueError("the material bound stays within the platform bound")
        self.uow = uow
        self.max_materials = int(max_materials)

    # ---- authorization ---------------------------------------------------
    @staticmethod
    def _authorize(access):
        roles = access.principal.roles
        if not DELIVERY_ROLES.intersection(roles) or "agent" in roles:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")

    # ---- material index --------------------------------------------------
    def _report_material(self, commit):
        return {
            "source": "report_commit",
            "source_ref": commit["report_id"],
            "media_type": REPORT_MEDIA_TYPE,
            "sha256": commit["body_digest"],
            "size_bytes": len(commit["body"].encode()),
            "access_level": int(commit["access_level"]),
        }

    def _artifact_materials(self, tx, requirements):
        """Sealed artifacts of this Task that the profile asks for.

        Absent material is never replaced by a synthetic "not applicable" row:
        the requirement simply stays unsatisfied and the delivery says so.
        """

        wanted = sorted({item["media_type"] for item in requirements})
        clauses, wanted_values = [], []
        for media_type in wanted:
            if media_type.endswith("/*"):
                clauses.append("lower(media_type) LIKE %s")
                wanted_values.append(media_type[:-1] + "%")
            else:
                clauses.append("lower(media_type) = %s")
                wanted_values.append(media_type)
        rows = tx.connection.execute(
            "SELECT entity_id,revision,media_type,sha256,size_bytes,access_level"
            " FROM vnext.artifact"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND state='sealed'"
            " AND access_level <= %s AND (" + " OR ".join(clauses) + ")"
            " ORDER BY entity_id,revision LIMIT %s",
            (
                *tx.owner,
                tx.permissions["clearance"],
                *wanted_values,
                self.max_materials + 1,
            ),
        ).fetchall()
        if len(rows) > self.max_materials:
            # Refuse rather than deliver a silently truncated index.
            raise DomainError("delivery_too_large", 409)
        return [
            {
                "source": "artifact",
                "source_ref": f"{row[0]}@{row[1]}",
                "media_type": row[2],
                "sha256": row[3],
                "size_bytes": int(row[4]),
                "access_level": int(row[5]),
            }
            for row in rows
        ]

    def _evaluate(self, requirements, materials):
        manifest_requirements, missing = [], []
        for item in requirements:
            found = [
                material
                for material in materials
                if _matches(str(material["media_type"]).lower(), item["media_type"])
            ]
            shortfall = max(0, item["min_count"] - len(found))
            entry = {
                "role": item["role"],
                "media_type": item["media_type"],
                "min_count": item["min_count"],
                "required": item["required"],
                "present_count": len(found),
                "present": found,
                "missing_count": shortfall,
            }
            manifest_requirements.append(entry)
            if shortfall:
                missing.append(
                    {
                        "role": item["role"],
                        "media_type": item["media_type"],
                        "min_count": item["min_count"],
                        "present_count": len(found),
                        "missing_count": shortfall,
                        "required": item["required"],
                    }
                )
        return manifest_requirements, missing

    # ---- the delivery ----------------------------------------------------
    def deliver(
        self,
        access,
        task_id,
        *,
        report_key,
        delivery_key,
        profile,
        exchange=None,
    ) -> DeliveryReceipt:
        """Index the frozen report against one profile and record the outcome."""

        self._authorize(access)
        _bounded_key(report_key, "report key")
        _bounded_key(delivery_key, "delivery key")
        declared = normalize_profile(profile)
        if declared["mode"] == "http" and exchange is None:
            # No adapter can cite an exchange that has not happened yet.
            raise DomainError("delivery_exchange_required", 409)
        if declared["mode"] == "offline" and exchange is not None:
            _invalid("an offline delivery has no HTTP exchange")
        exchange_json = None
        if exchange is not None:
            if not isinstance(exchange, dict) or not exchange:
                _invalid("an exchange receipt is a non-empty document")
            exchange_json = canonical_json_bytes(exchange).decode()
            if len(exchange_json) > 65536:
                raise DomainError("delivery_too_large", 409)
        profile_json = canonical_json_bytes(declared).decode()
        with self.uow.transaction(access, task_id, capability="control") as tx:
            commit = self._commit(tx, report_key)
            materials = [self._report_material(commit)]
            materials.extend(self._artifact_materials(tx, declared["requirements"]))
            evaluated, missing = self._evaluate(declared["requirements"], materials)
            state = (
                "incomplete"
                if any(item["required"] for item in missing)
                else "ready"
            )
            manifest = canonical_json_bytes(
                {
                    "schema_version": DELIVERY_SCHEMA,
                    "report_id": commit["report_id"],
                    "report_digest": commit["body_digest"],
                    "epoch_id": commit["epoch_id"],
                    "profile": declared,
                    "mode": declared["mode"],
                    "state": state,
                    "requirements": evaluated,
                    "materials": materials,
                    "missing": missing,
                }
            ).decode()
            with platform_errors():
                stored = tx.connection.execute(
                    "SELECT vnext.record_report_delivery(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        *tx.owner,
                        delivery_key,
                        commit["report_id"],
                        commit["body_digest"],
                        declared["profile_id"],
                        profile_json,
                        state,
                        declared["mode"],
                        canonical_json_bytes(missing).decode(),
                        manifest,
                        exchange_json,
                        None,
                        tx.permissions["clearance"],
                    ),
                ).fetchone()[0]
            document = self._document(tx, stored)
        return DeliveryReceipt(document=document)

    def fail(
        self,
        access,
        task_id,
        *,
        report_key,
        delivery_key,
        profile,
        error_code,
    ) -> DeliveryReceipt:
        """Record a delivery that could not be produced, with a bounded reason."""

        self._authorize(access)
        _bounded_key(report_key, "report key")
        _bounded_key(delivery_key, "delivery key")
        if error_code not in ERROR_CODES:
            _invalid("a failed delivery names a bounded error code")
        declared = normalize_profile(profile)
        profile_json = canonical_json_bytes(declared).decode()
        with self.uow.transaction(access, task_id, capability="control") as tx:
            commit = self._commit(tx, report_key)
            with platform_errors():
                stored = tx.connection.execute(
                    "SELECT vnext.record_report_delivery(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        *tx.owner,
                        delivery_key,
                        commit["report_id"],
                        commit["body_digest"],
                        declared["profile_id"],
                        profile_json,
                        "failed",
                        declared["mode"],
                        None,
                        None,
                        None,
                        error_code,
                        tx.permissions["clearance"],
                    ),
                ).fetchone()[0]
            document = self._document(tx, stored)
        return DeliveryReceipt(document=document)

    # ---- reads -----------------------------------------------------------
    def read(self, access, task_id, report_key, delivery_key):
        _bounded_key(report_key, "report key")
        _bounded_key(delivery_key, "delivery key")
        with self.uow.transaction(access, task_id, capability="read") as tx:
            self._commit(tx, report_key)
            return self._document(tx, delivery_key)

    def list(self, access, task_id, report_key):
        """Every recorded delivery of one report, oldest first."""

        _bounded_key(report_key, "report key")
        with self.uow.transaction(access, task_id, capability="read") as tx:
            self._commit(tx, report_key)
            rows = tx.connection.execute(
                "SELECT delivery_id FROM vnext.report_delivery"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND report_id=%s"
                " ORDER BY created_at,delivery_id LIMIT %s",
                (*tx.owner, report_key, 100),
            ).fetchall()
            return tuple(self._document(tx, row[0]) for row in rows)

    # ---- internals -------------------------------------------------------
    @staticmethod
    def _commit(tx, report_key):
        record = tx.connection.execute(
            "SELECT body_json,body_digest,dispute_state,epoch_id,access_level"
            " FROM vnext.report_commit"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND report_id=%s",
            (*tx.owner, report_key),
        ).fetchone()
        if record is None:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        commit = {
            "report_id": report_key,
            "body": record[0],
            "body_digest": record[1],
            "dispute_state": record[2],
            "epoch_id": record[3],
            "access_level": int(record[4]),
        }
        # The delivery cites the bytes that were frozen; a mismatching row is a
        # corrupt commit, not something to deliver.
        if sha256(commit["body"].encode()).hexdigest() != commit["body_digest"]:
            raise DomainError("delivery_commit_corrupt", 409)
        if commit["access_level"] > tx.permissions["clearance"]:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        if (
            tx.task["observed_state"] != "closed"
            or tx.task["completion_epoch_id"] != commit["epoch_id"]
        ):
            raise DomainError("completion_not_closed", 409)
        return commit

    @staticmethod
    def _document(tx, delivery_key):
        record = tx.connection.execute(
            "SELECT delivery_id,report_id,report_digest,epoch_id,profile_json,profile_digest,"
            "state,mode,missing_json,manifest_json,manifest_digest,exchange_json,error_code,"
            "access_level,created_at"
            " FROM vnext.report_delivery"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND delivery_id=%s",
            (*tx.owner, delivery_key),
        ).fetchone()
        if record is None:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        manifest = strict_json_loads(record[9]) if record[9] is not None else None
        return {
            "delivery_id": record[0],
            "task_id": tx.owner[2],
            "report_id": record[1],
            "report_digest": record[2],
            "epoch_id": record[3],
            "profile": strict_json_loads(record[4]),
            "profile_digest": record[5],
            "state": record[6],
            "mode": record[7],
            "missing": strict_json_loads(record[8]) if record[8] is not None else [],
            "manifest": manifest,
            # The frozen manifest keeps every digest; availability is a read
            # fact, so a purge can never rewrite what was delivered.
            "unavailable_materials": list(
                unavailable_materials(tx, (manifest or {}).get("materials"))
            ),
            "manifest_digest": record[10],
            "exchange": strict_json_loads(record[11]) if record[11] is not None else None,
            "error_code": record[12],
            "access_level": int(record[13]),
            "created_at": record[14],
        }
