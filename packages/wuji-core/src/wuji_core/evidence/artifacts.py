"""Server-owned immutable byte objects; no caller paths, URLs or fetch capability."""

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from threading import RLock
from typing import Protocol
from uuid import uuid4

from wuji_core.contracts.envelopes import BlobRef
from wuji_core.execution.retained_results import (
    RetainedResultKey,
    bound_retained_run,
)
from wuji_core.http.json_boundary import strict_json_loads
from wuji_core.persistence.uow import AccessContext, DomainError, json_text, row


def require_collector(access: AccessContext):
    if "collector" not in access.principal.roles or "agent" in access.principal.roles:
        raise DomainError("FORBIDDEN_COLLECTOR", 403)


def bound_attempt(tx, attempt_id: str):
    attempt = row(
        tx.connection.execute(
            """SELECT a.*,r.work_item_id,r.receiver_id,r.environment_ref,
        r.execution_epoch,r.run_epoch,r.runtime_attempt,r.execution_allowed,
        b.can_settle AS binding_can_settle FROM vnext.tool_attempt a
        JOIN vnext.agent_run r USING(tenant_id,project_id,task_id,agent_run_id)
        JOIN vnext.collector_binding b USING(tenant_id,project_id,task_id,tool_attempt_id)
        WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s AND a.tool_attempt_id=%s
        AND b.subject=%s AND NOT b.revoked""",
            (*tx.owner, attempt_id, tx.access.principal.subject),
        )
    )
    if attempt is None:
        raise DomainError("FORBIDDEN_COLLECTOR", 403)
    return attempt


def capture_disposition(tx, attempt):
    if attempt["started_at"] is None:
        raise DomainError("STALE_EXECUTION", 403)
    current = (
        tx.task["execution_allowed"]
        and attempt["execution_allowed"]
        and tx.task["execution_epoch"] == attempt["execution_epoch"]
        and tx.task["runtime_attempt"] == attempt["runtime_attempt"]
    )
    if current and tx.permissions["can_capture"]:
        return "accepted"
    if not current and tx.permissions["can_settle"] and attempt["binding_can_settle"]:
        return "historical_only"
    raise DomainError("STALE_EXECUTION", 403)


def bound_run(tx, run_id, identity=None):
    if (
        not tx.access.principal.roles.intersection({"worker", "supervisor"})
        or "agent" in tx.access.principal.roles
    ):
        raise DomainError("NOT_FOUND_OR_FORBIDDEN", 403)
    run = row(
        tx.connection.execute(
            """SELECT r.*,b.agent_subject,b.can_settle AS binding_can_settle
        FROM vnext.agent_run r JOIN vnext.run_writer b USING(tenant_id,project_id,task_id,agent_run_id)
        WHERE r.tenant_id=%s AND r.project_id=%s AND r.task_id=%s AND r.agent_run_id=%s
        AND b.subject=%s AND NOT b.revoked""",
            (*tx.owner, run_id, tx.access.principal.subject),
        )
    )
    if run is None:
        raise DomainError("NOT_FOUND_OR_FORBIDDEN", 403)
    if identity is not None:
        values = identity.model_dump(mode="json")
        if any(str(run[key]) != str(value) for key, value in values.items()):
            raise DomainError("STALE_EXECUTION", 403)
    return run


def run_disposition(tx, run):
    current = (
        tx.task["execution_allowed"]
        and run["execution_allowed"]
        and tx.task["execution_epoch"] == run["execution_epoch"]
        and tx.task["runtime_attempt"] == run["runtime_attempt"]
    )
    if current and tx.permissions["can_write"]:
        return "accepted"
    if not current and tx.permissions["can_settle"] and run["binding_can_settle"]:
        return "historical_only"
    raise DomainError("STALE_EXECUTION", 403)


class ArtifactStorageBackend(Protocol):
    """The byte-store boundary used by :class:`ArtifactStore`.

    Metadata and authority remain in PostgreSQL.  A backend only owns the
    immutable byte identified by ``storage_key`` and has an explicit, retryable
    delete result.  In particular, a successful metadata tombstone never
    depends on a backend pretending that an already absent object was a new
    deletion.
    """

    def put(self, storage_key, data: bytes) -> None: ...

    def read(self, storage_key, max_bytes: int) -> bytes: ...

    def delete(self, storage_key): ...


def _storage_key(value) -> str:
    """Return a database-generated key without allowing a caller path."""

    key = str(value)
    if (
        not key
        or len(key) > 256
        or "\x00" in key
        or "/" in key
        or "\\" in key
        or key in {".", ".."}
    ):
        raise ValueError("storage keys are bounded opaque identifiers")
    return key


@dataclass(frozen=True)
class StorageDeleteResult:
    """The observable semantics of a byte deletion.

    ``removed`` means this call removed bytes.  ``already_absent`` means the
    desired end state was already true, which is safe for a retry but is not a
    fresh deletion.  Both backends deliberately expose the same result.
    """

    storage_key: str
    removed: bool
    already_absent: bool

    @property
    def deleted(self) -> bool:
        return self.removed or self.already_absent


class FileSystemArtifactBackend:
    """Durable local/PVC semantics: exclusive put, bounded read, fsynced unlink."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def path(self, storage_key):
        return self.root / (_storage_key(storage_key) + ".blob")

    def _sync_directory(self):
        fd = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def put(self, storage_key, data: bytes) -> None:
        if not isinstance(data, bytes):
            raise TypeError("artifact bytes are required")
        path = self.path(storage_key)
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        path.chmod(0o400)
        self._sync_directory()

    def read(self, storage_key, max_bytes: int) -> bytes:
        with self.path(storage_key).open("rb") as stream:
            return stream.read(max_bytes + 1)

    def delete(self, storage_key) -> StorageDeleteResult:
        key = _storage_key(storage_key)
        try:
            self.path(key).unlink()
        except FileNotFoundError:
            return StorageDeleteResult(key, removed=False, already_absent=True)
        self._sync_directory()
        return StorageDeleteResult(key, removed=True, already_absent=False)


class InMemoryArtifactBackend:
    """Deterministic test backend with the same immutable/idempotent contract."""

    def __init__(self):
        self._objects = {}
        self._lock = RLock()

    def put(self, storage_key, data: bytes) -> None:
        if not isinstance(data, bytes):
            raise TypeError("artifact bytes are required")
        key = _storage_key(storage_key)
        with self._lock:
            if key in self._objects:
                raise FileExistsError(key)
            self._objects[key] = bytes(data)

    def read(self, storage_key, max_bytes: int) -> bytes:
        key = _storage_key(storage_key)
        with self._lock:
            if key not in self._objects:
                raise FileNotFoundError(key)
            return self._objects[key][: max_bytes + 1]

    def delete(self, storage_key) -> StorageDeleteResult:
        key = _storage_key(storage_key)
        with self._lock:
            if self._objects.pop(key, None) is None:
                return StorageDeleteResult(key, removed=False, already_absent=True)
        return StorageDeleteResult(key, removed=True, already_absent=False)

    def contains(self, storage_key) -> bool:
        with self._lock:
            return _storage_key(storage_key) in self._objects


# Short aliases make the storage boundary easy to discover without changing
# the more descriptive names used in the implementation and tests.
FileArtifactBackend = FileSystemArtifactBackend
MemoryArtifactBackend = InMemoryArtifactBackend


class ArtifactStore:
    def __init__(
        self,
        uow,
        root: Path | None = None,
        *,
        backend: ArtifactStorageBackend | None = None,
        max_bytes=8 * 1024 * 1024,
    ):
        if backend is not None and root is not None:
            raise ValueError("choose a root or an artifact backend, not both")
        if backend is None:
            if root is None:
                raise ValueError("a root or an artifact backend is required")
            backend = FileSystemArtifactBackend(root)
        self.uow, self.backend, self.max_bytes = uow, backend, max_bytes
        # Existing callers use ``root`` to inspect the durable fixture.  It is
        # intentionally None for non-filesystem stores.
        self.root = getattr(backend, "root", None)

    def _path(self, record):
        # storage_key is a database UUID generated by stage, never an external path.
        path = getattr(self.backend, "path", None)
        if not callable(path):
            raise TypeError("the configured artifact backend has no filesystem path")
        return path(record["storage_key"])

    def stage(
        self,
        access,
        task_id,
        tool_attempt_id,
        data: bytes,
        media_type: str,
        *,
        completeness="complete",
        conditions=(),
        provenance="capture",
        access_level=0,
    ):
        require_collector(access)
        if not isinstance(data, bytes) or len(data) > self.max_bytes:
            raise DomainError("LIMIT_BLOCKED", 422)
        if (
            not isinstance(media_type, str)
            or not 1 <= len(media_type) <= 256
            or "\r" in media_type
            or "\n" in media_type
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        if completeness not in {"complete", "partial", "unknown"} or provenance not in {
            "capture",
            "model_output",
            "import",
        }:
            raise DomainError("INVALID_SCHEMA", 422)
        if len(conditions) > 128 or any(
            not isinstance(item, str) or not 1 <= len(item) <= 8192
            for item in conditions
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        if (
            not isinstance(access_level, int)
            or isinstance(access_level, bool)
            or access_level < 0
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        entity_id = str(uuid4())
        storage_key = uuid4()
        digest = hashlib.sha256(data).hexdigest()
        ref = BlobRef.model_validate(
            {"id": entity_id, "version": "1", "sha256": digest}
        )
        # Reserve metadata/lease before writing bytes: a crash leaves a known staged object.
        with self.uow.transaction(access, task_id, capability="evidence") as tx:
            attempt = bound_attempt(tx, tool_attempt_id)
            capture_disposition(tx, attempt)
            origin = (
                "imported_unverified"
                if provenance == "import"
                else attempt["evidence_origin"]
            )
            tx.connection.execute(
                """INSERT INTO vnext.artifact(tenant_id,project_id,task_id,entity_id,revision,
                state,storage_key,sha256,size_bytes,media_type,tool_attempt_id,provenance,evidence_origin,
                capture_layer,environment_ref,completeness,conditions_json,access_level)
                VALUES (%s,%s,%s,%s,1,'staged',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    *tx.owner,
                    entity_id,
                    storage_key,
                    digest,
                    len(data),
                    media_type,
                    tool_attempt_id,
                    provenance,
                    origin,
                    attempt["capture_layer"],
                    attempt["environment_ref"],
                    completeness,
                    json_text(list(conditions)),
                    access_level,
                ),
            )
            tx.connection.execute(
                "INSERT INTO vnext.artifact_lease(tenant_id,project_id,task_id,artifact_id,artifact_revision,lease_owner,expires_at,access_level) VALUES (%s,%s,%s,%s,1,'staging',clock_timestamp()+interval '5 minutes',%s)",
                (*tx.owner, entity_id, access_level),
            )
        with self.uow.transaction(access, task_id, capability="evidence") as tx:
            record = self.record(tx, ref, lock=True)
            if record["state"] != "staged":
                raise DomainError("INVALID_REFERENCE", 422)
            self.backend.put(record["storage_key"], data)
        return ref

    def stage_model_output(
        self,
        access,
        task_id,
        agent_run_id,
        data: bytes,
        media_type: str,
        *,
        access_level=0,
    ):
        """A real Run writer can stage final output without inventing a ToolAttempt."""
        return self._stage_model_output(
            access,
            task_id,
            agent_run_id,
            data,
            media_type,
            access_level=access_level,
            retained=None,
        )

    def stage_runtime_capture(
        self,
        access,
        task_id,
        capture_session_id,
        data: bytes,
        media_type: str,
        *,
        completeness,
        conditions=(),
        access_level=0,
        lease_owner,
    ):
        """Stage one exact part pulled by the trusted Task Runtime."""

        from wuji_core.evidence.runtime_capture import (
            bound_capture_session,
            capture_session_disposition,
            require_runtime_collector,
        )

        require_runtime_collector(access)
        if not isinstance(data, bytes) or len(data) > self.max_bytes:
            raise DomainError("LIMIT_BLOCKED", 422)
        if (
            not isinstance(media_type, str)
            or not 1 <= len(media_type) <= 256
            or "\r" in media_type
            or "\n" in media_type
            or completeness not in {"complete", "partial", "unknown"}
            or len(conditions) > 128
            or any(
                not isinstance(item, str) or not 1 <= len(item) <= 8192
                for item in conditions
            )
            or type(access_level) is not int
            or access_level < 0
            or not isinstance(lease_owner, str)
            or not 1 <= len(lease_owner) <= 256
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        digest = hashlib.sha256(data).hexdigest()
        existing = None
        with self.uow.transaction(access, task_id, capability="evidence") as tx:
            session = bound_capture_session(tx, capture_session_id, lock=True)
            capture_session_disposition(tx, session)
            if access_level != session["access_level"]:
                raise DomainError("INVALID_REFERENCE", 422)
            cursor = tx.connection.execute(
                """SELECT a.* FROM vnext.artifact_lease l JOIN vnext.artifact a ON
                  (a.tenant_id,a.project_id,a.task_id,a.entity_id,a.revision)=
                  (l.tenant_id,l.project_id,l.task_id,l.artifact_id,
                   l.artifact_revision)
                WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s
                  AND a.capture_session_id=%s AND l.lease_owner=%s
                  AND a.state<>'tombstoned' FOR UPDATE OF a""",
                (*tx.owner, capture_session_id, lease_owner),
            )
            matches = [dict(zip((column.name for column in cursor.description), value))
                       for value in cursor.fetchall()]
            if len(matches) > 1:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            existing = matches[0] if matches else None
            if existing is not None:
                if (
                    existing["sha256"] != digest
                    or existing["size_bytes"] != len(data)
                    or existing["media_type"] != media_type
                    or existing["completeness"] != completeness
                    or strict_json_loads(existing["conditions_json"])
                    != list(conditions)
                    or existing["access_level"] != access_level
                ):
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                ref = BlobRef.model_validate(
                    {
                        "id": existing["entity_id"],
                        "version": str(existing["revision"]),
                        "sha256": existing["sha256"],
                    }
                )
                tx.connection.execute(
                    """UPDATE vnext.artifact_lease SET
                    expires_at=clock_timestamp()+interval '5 minutes'
                    WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                      AND artifact_id=%s AND artifact_revision=%s
                      AND lease_owner=%s""",
                    (*tx.owner, ref.id, ref.version.root, lease_owner),
                )
            else:
                ref = BlobRef.model_validate(
                    {"id": str(uuid4()), "version": "1", "sha256": digest}
                )
                storage_key = uuid4()
                tx.connection.execute(
                    """INSERT INTO vnext.artifact(tenant_id,project_id,task_id,
                    entity_id,revision,state,storage_key,sha256,size_bytes,media_type,
                    capture_session_id,provenance,evidence_origin,capture_layer,
                    environment_ref,completeness,conditions_json,access_level)
                    VALUES(%s,%s,%s,%s,1,'staged',%s,%s,%s,%s,%s,'capture',
                    %s,%s,%s,%s,%s,%s)""",
                    (
                        *tx.owner,
                        ref.id,
                        storage_key,
                        ref.sha256.root,
                        len(data),
                        media_type,
                        capture_session_id,
                        session["evidence_origin"],
                        session["capture_layer"],
                        session["environment_ref"],
                        completeness,
                        json_text(list(conditions)),
                        access_level,
                    ),
                )
                tx.connection.execute(
                    """INSERT INTO vnext.artifact_lease(tenant_id,project_id,task_id,
                    artifact_id,artifact_revision,lease_owner,expires_at,access_level)
                    VALUES(%s,%s,%s,%s,1,%s,
                    clock_timestamp()+interval '5 minutes',%s)""",
                    (*tx.owner, ref.id, lease_owner, access_level),
                )
        with self.uow.transaction(access, task_id, capability="evidence") as tx:
            session = bound_capture_session(tx, capture_session_id)
            capture_session_disposition(tx, session)
            record = self.record(tx, ref, lock=True)
            try:
                self.checked_bytes(record)
            except DomainError:
                if record["state"] != "staged":
                    raise
                self.backend.put(record["storage_key"], data)
        return ref

    def stage_retained_output(
        self,
        access,
        task_id,
        agent_run_id,
        data: bytes,
        media_type: str,
        *,
        retained: RetainedResultKey,
        access_level=0,
    ):
        """Stage exact Worker bytes under an SQL-opened receiver binding."""
        if not isinstance(retained, RetainedResultKey):
            raise DomainError("INVALID_REFERENCE", 422)
        return self._stage_model_output(
            access,
            task_id,
            agent_run_id,
            data,
            media_type,
            access_level=access_level,
            retained=retained,
        )

    def _output_transaction(self, access, task_id, retained):
        if retained is None:
            return self.uow.transaction(access, task_id, capability="model_output")
        return self.uow.transaction(
            access,
            task_id,
            capability="retained_result",
            retained_result=retained.document(),
        )

    @staticmethod
    def _bound_output(tx, agent_run_id, retained):
        if retained is None:
            run = bound_run(tx, agent_run_id)
            run_disposition(tx, run)
            return run
        run = bound_retained_run(tx, retained)
        if run["agent_run_id"] != agent_run_id:
            raise DomainError("STALE_EXECUTION", 403)
        return run

    def _stage_model_output(
        self,
        access,
        task_id,
        agent_run_id,
        data,
        media_type,
        *,
        access_level,
        retained,
    ):
        if not isinstance(data, bytes) or len(data) > self.max_bytes:
            raise DomainError("LIMIT_BLOCKED", 422)
        if (
            not isinstance(media_type, str)
            or not 1 <= len(media_type) <= 256
            or "\r" in media_type
            or "\n" in media_type
            or type(access_level) is not int
            or access_level < 0
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        ref = BlobRef.model_validate(
            dict(id=str(uuid4()), version="1", sha256=hashlib.sha256(data).hexdigest())
        )
        with self._output_transaction(access, task_id, retained) as tx:
            run = self._bound_output(tx, agent_run_id, retained)
            tx.connection.execute(
                """INSERT INTO vnext.artifact(tenant_id,project_id,task_id,entity_id,revision,
                state,storage_key,sha256,size_bytes,media_type,agent_run_id,writer_subject,provenance,evidence_origin,
                capture_layer,environment_ref,completeness,conditions_json,access_level)
                VALUES(%s,%s,%s,%s,1,'staged',%s,%s,%s,%s,%s,%s,'model_output','imported_unverified',
                'model_output',%s,'complete','[]',%s)""",
                (
                    *tx.owner,
                    ref.id,
                    uuid4(),
                    ref.sha256.root,
                    len(data),
                    media_type,
                    agent_run_id,
                    access.principal.subject,
                    run["environment_ref"],
                    access_level,
                ),
            )
            tx.connection.execute(
                """INSERT INTO vnext.artifact_lease(tenant_id,project_id,task_id,artifact_id,
                artifact_revision,lease_owner,expires_at,access_level) VALUES(%s,%s,%s,%s,1,'staging',
                clock_timestamp()+interval '5 minutes',%s)""",
                (*tx.owner, ref.id, access_level),
            )
        with self._output_transaction(access, task_id, retained) as tx:
            self._bound_output(tx, agent_run_id, retained)
            record = self.record(tx, ref, lock=True)
            self.backend.put(record["storage_key"], data)
        return ref

    def _mutation_capability(self, access, task_id, ref):
        with self.uow.transaction(access, task_id) as tx:
            record = self.record(tx, ref)
            if record["agent_run_id"] is not None:
                bound_run(tx, record["agent_run_id"])
                return "model_output"
            if record.get("capture_session_id") is not None:
                from wuji_core.evidence.runtime_capture import require_runtime_collector

                require_runtime_collector(access)
                return "evidence"
        require_collector(access)
        return "evidence"

    def _authorize_mutation(self, tx, record, *, disposition=True):
        if record["agent_run_id"] is not None:
            run = bound_run(tx, record["agent_run_id"])
            if disposition:
                run_disposition(tx, run)
        elif record.get("capture_session_id") is not None:
            from wuji_core.evidence.runtime_capture import (
                bound_capture_session,
                capture_session_disposition,
            )

            session = bound_capture_session(tx, record["capture_session_id"])
            if disposition:
                capture_session_disposition(tx, session)
        else:
            attempt = bound_attempt(tx, record["tool_attempt_id"])
            if disposition:
                capture_disposition(tx, attempt)

    def record(self, tx, ref, *, lock=False):
        result = row(
            tx.connection.execute(
                "SELECT * FROM vnext.artifact WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND entity_id=%s AND revision=%s"
                + (" FOR UPDATE" if lock else ""),
                (*tx.owner, ref.id, ref.version.root),
            )
        )
        if (
            not result
            or result["sha256"] != ref.sha256.root
            or result["state"] == "tombstoned"
        ):
            raise DomainError("INVALID_REFERENCE", 422)
        return result

    def checked_bytes(self, record):
        try:
            data = self.backend.read(record["storage_key"], self.max_bytes)
        except (OSError, KeyError) as error:
            raise DomainError("INVALID_REFERENCE", 422) from error
        if (
            len(data) > self.max_bytes
            or len(data) != record["size_bytes"]
            or hashlib.sha256(data).hexdigest() != record["sha256"]
        ):
            raise DomainError("INVALID_REFERENCE", 422)
        return data

    def seal(self, access, task_id, ref):
        capability = self._mutation_capability(access, task_id, ref)
        with self.uow.transaction(access, task_id, capability=capability) as tx:
            record = self.record(tx, ref, lock=True)
            self._authorize_mutation(tx, record)
            self.checked_bytes(record)
            if record["state"] == "staged":
                tx.connection.execute(
                    "UPDATE vnext.artifact SET state='sealed' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND entity_id=%s AND revision=%s",
                    (*tx.owner, ref.id, ref.version.root),
                )
        return ref

    def seal_retained(self, access, task_id, ref, *, retained: RetainedResultKey):
        """Seal only an Artifact staged for the same retained Run binding."""
        if not isinstance(retained, RetainedResultKey):
            raise DomainError("INVALID_REFERENCE", 422)
        with self._output_transaction(access, task_id, retained) as tx:
            record = self.record(tx, ref, lock=True)
            if (
                record["agent_run_id"] != retained.agent_run_id
                or record["writer_subject"] != access.principal.subject
            ):
                raise DomainError("INVALID_REFERENCE", 422)
            self._bound_output(tx, record["agent_run_id"], retained)
            self.checked_bytes(record)
            if record["state"] == "staged":
                tx.connection.execute(
                    "UPDATE vnext.artifact SET state='sealed' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND entity_id=%s AND revision=%s",
                    (*tx.owner, ref.id, ref.version.root),
                )
        return ref

    def read(self, access, artifact_id, version, *, max_bytes=None):
        if max_bytes is not None and (type(max_bytes) is not int or max_bytes < 1):
            raise ValueError("max_bytes must be a positive integer")
        located = self.uow.locate_artifact(access, artifact_id, version)
        if located is None:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        with self.uow.transaction(access, located["task_id"]) as tx:
            ref = BlobRef.model_validate(
                {"id": artifact_id, "version": version, "sha256": located["sha256"]}
            )
            try:
                record = self.record(tx, ref)
                if record["state"] != "sealed":
                    raise DomainError("INVALID_REFERENCE", 422)
                if max_bytes is not None and record["size_bytes"] > max_bytes:
                    raise DomainError("NOT_FOUND_OR_FORBIDDEN")
                data = self.checked_bytes(record)
            except DomainError as error:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN") from error
        return data, "sha-256=" + base64.b64encode(
            hashlib.sha256(data).digest()
        ).decode("ascii")

    def acquire_lease(self, access, task_id, ref, *, lease_owner, seconds=300):
        capability = self._mutation_capability(access, task_id, ref)
        if (
            not isinstance(lease_owner, str)
            or not 1 <= len(lease_owner) <= 256
            or not 0 < seconds <= 3600
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        with self.uow.transaction(access, task_id, capability=capability) as tx:
            record = self.record(tx, ref, lock=True)
            self._authorize_mutation(tx, record)
            tx.connection.execute(
                """INSERT INTO vnext.artifact_lease(tenant_id,project_id,task_id,artifact_id,artifact_revision,lease_owner,expires_at,access_level)
                VALUES (%s,%s,%s,%s,%s,%s,clock_timestamp()+%s*interval '1 second',%s)
                ON CONFLICT(tenant_id,project_id,task_id,artifact_id,artifact_revision,lease_owner) DO UPDATE SET expires_at=EXCLUDED.expires_at""",
                (
                    *tx.owner,
                    ref.id,
                    ref.version.root,
                    lease_owner,
                    seconds,
                    record["access_level"],
                ),
            )

    def release_lease(self, access, task_id, ref, *, lease_owner):
        capability = self._mutation_capability(access, task_id, ref)
        with self.uow.transaction(access, task_id, capability=capability) as tx:
            record = self.record(tx, ref, lock=True)
            self._authorize_mutation(tx, record, disposition=False)
            tx.connection.execute(
                "DELETE FROM vnext.artifact_lease WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND artifact_id=%s AND artifact_revision=%s AND lease_owner=%s",
                (*tx.owner, ref.id, ref.version.root, lease_owner),
            )

    def remove_bytes(self, record):
        """Unlink the exact bytes of a tombstoned artifact; metadata is untouched.

        Called after the row was already marked ``tombstoned``, so an
        interrupted removal leaves inaccessible bytes for a retry instead of a
        published reference whose content disappeared behind a live metadata
        row.
        """

        return self.backend.delete(record["storage_key"])

    def collect_garbage(
        self,
        access,
        task_id,
        *,
        older_than,
        limit=100,
        retention_policy=None,
        policy=None,
    ):
        if retention_policy is not None and policy is not None:
            raise ValueError("choose retention_policy or policy, not both")
        retention_policy = retention_policy if retention_policy is not None else policy
        if (
            older_than.tzinfo is None
            or older_than > datetime.now(timezone.utc)
            or not 1 <= limit <= 1000
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        if retention_policy is not None and not callable(
            getattr(retention_policy, "allow_gc", None)
        ):
            from wuji_core.audit.retention import RetentionPolicyEngine

            retention_policy = RetentionPolicyEngine(retention_policy)
        now = datetime.now(timezone.utc)
        candidates = []
        with self.uow.transaction(access, task_id, capability="gc") as tx:
            cursor = tx.connection.execute(
                """SELECT * FROM vnext.artifact a WHERE NOT body_removed AND created_at<%s
                AND NOT vnext.artifact_retained(a.tenant_id,a.project_id,a.task_id,a.entity_id,a.revision)
                ORDER BY entity_id,revision LIMIT %s FOR UPDATE""",
                (older_than, limit),
            )
            columns = [c.name for c in cursor.description]
            candidates = [dict(zip(columns, values)) for values in cursor.fetchall()]
            if retention_policy is not None:
                candidates = [
                    candidate
                    for candidate in candidates
                    if retention_policy.allow_gc(
                        {
                            **candidate,
                            "live_lease": False,
                            "referenced": False,
                        },
                        now=now,
                    ).allowed
                ]
            for candidate in candidates:
                if candidate["state"] != "tombstoned":
                    tx.connection.execute(
                        "UPDATE vnext.artifact SET state='tombstoned' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND entity_id=%s AND revision=%s",
                        (*tx.owner, candidate["entity_id"], candidate["revision"]),
                    )
        # Mark first, then remove: interruption leaves an inaccessible object for retry,
        # never a published reference whose bytes were removed before a failed commit.
        for candidate in candidates:
            self.remove_bytes(candidate)
        if candidates:
            with self.uow.transaction(access, task_id, capability="gc") as tx:
                for candidate in candidates:
                    tx.connection.execute(
                        "UPDATE vnext.artifact SET body_removed=true WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND entity_id=%s AND revision=%s AND state='tombstoned' AND NOT body_removed",
                        (*tx.owner, candidate["entity_id"], candidate["revision"]),
                    )
        return [c["entity_id"] for c in candidates]
