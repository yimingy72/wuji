"""Controller-owned transport facade for the existing hosted MAF runtime.

Only this side holds platform services. Stored intake contains exact bytes and
the already authenticated writer; it grants no permission to execute again.
"""

import base64
from dataclasses import dataclass
import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os
from pathlib import Path
import stat
import tempfile
from threading import RLock

from wuji_core.admission.common import current_run
from wuji_core.admission.model_material import (
    HTTP_EXCHANGE_MEDIA_TYPE,
    render_http_exchange_v2,
)
from wuji_core.contracts import generated as wire
from wuji_core.contracts.envelopes import WorkerAssignment
from wuji_core.execution.control import ExecutionObservation
from wuji_core.execution.dispatch_outbox import ReceiverAuthorizer
from wuji_core.execution.reconcile import read_registered_run
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.http.auth import TokenVerifier
from wuji_core.persistence.snapshots import SnapshotRepository
from wuji_core.persistence.uow import AccessContext, DomainError, row


def document(value):
    """Keep opaque Decimals exact; only typed datetime values become RFC3339."""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="python")
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {k: document(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [document(v) for v in value]
    return value


def assignment_digest(assignment):
    return sha256(canonical_json_bytes(document(assignment))).hexdigest()


def _receiver(run):
    return {"receiver_id": run.identity.receiver_id,
            "runtime_attempt": run.identity.runtime_attempt.root,
            "environment_ref": run.environment_ref, "pod_uid": run.pod_uid}


def _principal(principal):
    return {"subject": principal.subject, "tenant_id": principal.tenant_id,
            "roles": sorted(principal.roles), "token_id": principal.token_id}


@dataclass(frozen=True)
class HostContext:
    """Structural host input, not a framework type or parallel HTTP schema."""
    snapshot_id: str
    read_set: tuple
    record_refs: tuple
    text: str
    input_digest: str

    @classmethod
    def from_wire(cls, value):
        value = wire.WorkerContext.model_validate(value)
        if sha256(value.text.encode()).hexdigest() != value.input_digest.root:
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        return cls(value.snapshot_id, tuple(value.read_set), tuple(value.record_refs),
                   value.text, value.input_digest.root)


class PrivateIntake:
    """Fixed per-operation files, atomically immutable, bounded before reading.

    Deployment must keep this directory inaccessible to Workers/other tenants.
    It stores no bearer, Task key or arbitrary request-selected filesystem path.
    """
    def __init__(self, directory, maximum):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.directory.is_symlink():
            raise ValueError("private controller intake must not be a symlink")
        os.chmod(self.directory, 0o700)
        self.maximum = maximum

    def _path(self, assignment, name):
        key = sha256(canonical_json_bytes({
            "identity": document(assignment.identity), "operation_id": assignment.operation_id,
        })).hexdigest()
        return self.directory / (key + "." + name + ".json")

    def read(self, assignment, name):
        path = self._path(assignment, name)
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return None
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > self.maximum:
                raise DomainError("LIMIT_BLOCKED", 422)
            data = stream.read(self.maximum + 1)
        if len(data) > self.maximum:
            raise DomainError("LIMIT_BLOCKED", 422)
        return strict_json_loads(data)

    def save(self, assignment, name, value):
        data = canonical_json_bytes(document(value))
        if len(data) > self.maximum:
            raise DomainError("LIMIT_BLOCKED", 422)
        path = self._path(assignment, name)
        fd, temporary = tempfile.mkstemp(prefix=".intake-", dir=self.directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if canonical_json_bytes(self.read(assignment, name)) != data:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409) from None
            fd = os.open(self.directory, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        finally:
            os.unlink(temporary)


def inline_material(*, artifacts, artifact_rows, references, context_bytes,
                    max_single_output_bytes):
    """Authorized, bounded text bodies for a read set, plus every omission.

    Only a sealed text artifact inside its own inline bound is fetched, and the
    whole set stays inside half of the published context bytes so the
    surrounding records always fit. Nothing is truncated: a body either arrives
    whole or the record names why it did not.
    """

    if artifacts is None or not artifact_rows or not callable(
        getattr(artifacts, "checked_bytes", None)
    ):
        return None
    from wuji_maf_worker.context import InlineMaterial

    per_artifact = min(
        int(max_single_output_bytes), max(1, int(context_bytes) // 4), 32 * 1024
    )
    total_budget = min(64 * 1024, max(1, int(context_bytes) // 2))
    bodies, reasons, total = {}, {}, 0
    for key, value in artifact_rows.items():
        if key not in references:
            continue
        if value.get("state") != "sealed":
            reasons[key] = "not_sealed"
            continue
        media_type = value.get("media_type")
        if media_type == HTTP_EXCHANGE_MEDIA_TYPE:
            try:
                from wuji_core.contracts.envelopes import BlobRef

                tool_call_id = value.get("tool_call_id")
                if not isinstance(tool_call_id, str) or not tool_call_id:
                    reasons[key] = "delivery_error"
                    continue
                if (
                    type(value.get("size_bytes")) is not int
                    or value["size_bytes"] > min(1 * 1024 * 1024, int(max_single_output_bytes))
                ):
                    reasons[key] = "representation_limit"
                    continue
                ref = BlobRef.model_validate(
                    {
                        "id": key[1],
                        "version": key[2],
                        "sha256": value["sha256"],
                    }
                )
                raw = artifacts.checked_bytes(value)
                packet = render_http_exchange_v2(
                    tool_call_id,
                    artifact_ref=ref,
                    artifact_record=value,
                    raw=raw,
                    max_source_bytes=min(1 * 1024 * 1024, int(max_single_output_bytes)),
                    max_representation_bytes=per_artifact,
                )
            except (DomainError, KeyError, TypeError, ValueError):
                reasons[key] = "source_unavailable"
                continue
            if packet.status.value != "delivered" or packet.representation is None:
                reasons[key] = packet.omission_reason.value if packet.omission_reason else "delivery_error"
                continue
            entry = packet.model_dump(mode="json")
            entry_size = len(canonical_json_bytes(entry))
            if total + entry_size > total_budget:
                reasons[key] = "context_byte_limit"
                continue
            bodies[key] = entry
            total += entry_size
            continue
        if not isinstance(media_type, str) or not media_type.startswith("text/"):
            reasons[key] = "not_text_media"
            continue
        try:
            size = int(value.get("size_bytes"))
        except (TypeError, ValueError):
            reasons[key] = "unreadable"
            continue
        if size < 0 or size > per_artifact:
            reasons[key] = "over_inline_limit"
            continue
        if total + size > total_budget:
            reasons[key] = "context_byte_limit"
            continue
        try:
            raw = artifacts.checked_bytes(value)
        except DomainError:
            # The published row and the stored bytes disagree: the artifact is
            # named as unreadable instead of being replaced by anything.
            reasons[key] = "unreadable"
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            reasons[key] = "not_utf8"
            continue
        bodies[key] = {"encoding": "utf-8", "byte_length": len(raw), "text": text}
        total += len(raw)
    return InlineMaterial(bodies=bodies, reasons=reasons)


class WorkerHostBridge:
    def __init__(self, uow, *, registry, credentials, receiver_access, host_factory,
                 context_builder, ledger, retained_results, child_config, spool_directory,
                 session_resolve_encoder=None, artifacts=None):
        if not all(callable(fn) for fn in (receiver_access, host_factory, context_builder)):
            raise ValueError("registered controller and context ports are required")
        if not all(callable(getattr(retained_results, name, None)) for name in (
            "submit_result", "archive_sdk",
        )):
            raise ValueError("registered retained-result service is required")
        if session_resolve_encoder is not None and not callable(session_resolve_encoder):
            raise ValueError("Session resolve encoder must be callable")
        if artifacts is not None and not callable(getattr(artifacts, "checked_bytes", None)):
            raise ValueError("an artifacts port must verify sealed bytes")
        self.uow, self.registry, self.credentials = uow, registry, credentials
        self.receiver_access, self.host_factory = receiver_access, host_factory
        self.context_builder, self.ledger = context_builder, ledger
        self.retained_results = retained_results
        self.session_resolve_encoder = session_resolve_encoder
        self.artifacts = artifacts
        allowed = {"public_key_pem", "issuer", "audience", "host_origin", "model_gate_url",
                   "tool_gate_url", "wait_timeout_seconds", "transport_timeout_seconds",
                   "max_transport_bytes"}
        if set(child_config) != allowed or "PRIVATE KEY" in child_config["public_key_pem"]:
            raise ValueError("only public verification material and fixed endpoints may reach child")
        self.child_config = strict_json_loads(canonical_json_bytes(child_config))
        maximum = child_config["max_transport_bytes"]
        if type(maximum) is not int or not 1 <= maximum <= 67108864:
            raise ValueError("bounded bridge transport is required")
        self.verifier = TokenVerifier(public_key_pem=child_config["public_key_pem"].encode(),
                                      issuer=child_config["issuer"], audience=child_config["audience"])
        self.intake = PrivateIntake(spool_directory, maximum)
        self.authorizer = ReceiverAuthorizer(uow)
        self._lock = RLock()

    def _registered(self, assignment, access=None):
        assignment = WorkerAssignment.model_validate(assignment)
        registered_access = self.receiver_access(assignment)
        if not isinstance(registered_access, AccessContext):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        if access is not None:
            if (access.principal.subject != registered_access.principal.subject
                    or access.principal.tenant_id != registered_access.principal.tenant_id
                    or "agent" in access.principal.roles
                    or not access.principal.roles.intersection({"controller", "reconciler"})):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            registered_access = access
        with self.uow.transaction(registered_access, assignment.identity.task_id, capability="observe") as tx:
            run, stored, credential_ref = read_registered_run(tx, assignment.operation_id)
            if assignment != stored:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        return run, credential_ref, registered_access

    def _worker(self, access, assignment):
        if "worker" not in access.principal.roles or "agent" in access.principal.roles:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        binding = self.registry.binding(access)
        if binding.identity != assignment.identity:
            raise DomainError("STALE_EXECUTION", 409)
        stored = self.intake.read(assignment, "writer")
        if stored is None or stored != {"assignment_digest": assignment_digest(assignment),
                                       "principal": _principal(access.principal)}:
            raise DomainError("STALE_EXECUTION", 409)
        return binding

    def receiver_authorize(self, access, payload):
        payload = wire.ReceiverBridgeRequest.model_validate(payload)
        run, _ref, receiver_access = self._registered(payload.assignment, access)
        return self.authorizer.authorize(
            access=receiver_access, assignment=payload.assignment,
            assignment_digest=payload.assignment_digest.root,
            receiver=document(payload.receiver), action=payload.action.value,
            control_operation_id=(payload.control_operation_id.root
                                  if payload.control_operation_id is not None else None),
        )

    def receiver_bootstrap(self, access, assignment):
        assignment = WorkerAssignment.model_validate(assignment)
        run, credential_ref, receiver_access = self._registered(assignment, access)
        self.authorizer.authorize(
            access=receiver_access, action="start", assignment=assignment,
            assignment_digest=run.assignment_digest, receiver=_receiver(run),
        )
        with self.uow.transaction(receiver_access, assignment.identity.task_id, capability="observe") as tx:
            fresh, stored, ref = read_registered_run(tx, assignment.operation_id)
            if fresh != run or stored != assignment or ref != credential_ref:
                raise DomainError("STALE_EXECUTION", 409)
            bearer = self.credentials.retrieve(tx, credential_ref=ref, identity=run.identity)
        principal = self.verifier.verify(bearer)
        worker = AccessContext(principal, access.request_id)
        if ("worker" not in principal.roles or "agent" in principal.roles
                or self.registry.binding(worker).identity != run.identity):
            raise DomainError("STALE_EXECUTION", 409)
        # Save the verified original writer, never the token, for trusted late
        # reconciliation. A later HTTP caller cannot select this identity.
        self.intake.save(assignment, "writer", {
            "assignment_digest": run.assignment_digest, "principal": _principal(principal),
        })
        return wire.WorkerBootstrap.model_validate({
            **self.child_config, "assignment": document(assignment),
            "assignment_digest": run.assignment_digest, "receiver": _receiver(run),
            "run_credential": bearer,
        })

    def await_start(self, access, assignment):
        return self._await_start(
            access, assignment, allow_running_transition_recheck=True
        )

    def _await_start(
        self, access, assignment, *, allow_running_transition_recheck
    ):
        assignment = WorkerAssignment.model_validate(assignment)
        run, _ref, receiver_access = self._registered(assignment)
        self._worker(access, assignment)
        response = {"status": "wait", "identity": document(run.identity),
                    "start_operation_id": run.start_operation_id,
                    "assignment_digest": run.assignment_digest, "receiver": _receiver(run),
                    "birth_id": None, "observation_id": None, "source_digest": None,
                    "valid_until": document(datetime.now(timezone.utc) + timedelta(seconds=2))}
        # Bounded operator context for a refused start: which step refused and
        # what the two durable states were. No identity, assignment, bearer or
        # peer detail is ever attached.
        refusal = {"step": "receiver_registration", "waiting": None, "process_state": None,
                   "work_state": None}
        try:
            with self.uow.transaction(
                receiver_access,
                assignment.identity.task_id,
                capability="observe",
            ) as receiver_tx:
                receiver = row(receiver_tx.connection.execute(
                    """SELECT * FROM vnext.scheduler_receiver
                    WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                    AND runtime_attempt=%s AND receiver_id=%s
                    AND receiver_subject=%s""",
                    (
                        *receiver_tx.owner,
                        run.identity.runtime_attempt.root,
                        run.identity.receiver_id,
                        receiver_access.principal.subject,
                    ),
                ))
                if (
                    not receiver
                    or not receiver["enabled"]
                    or receiver["environment_ref"] != run.environment_ref
                    or receiver["pod_uid"] != run.pod_uid
                ):
                    raise DomainError("STALE_EXECUTION", 409)
            # This is the existing real credential purpose, with no counter or
            # send. It rejects revoked/expired credentials even while inert.
            refusal["step"] = "run_record"
            with self.uow.transaction(access, assignment.identity.task_id, capability="model_request") as tx:
                config = self.registry.config(tx)
                record = row(tx.connection.execute(
                    "SELECT * FROM vnext.agent_run WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s",
                    (*tx.owner, assignment.identity.agent_run_id)))
                if not record:
                    raise DomainError("STALE_EXECUTION", 409)
                refusal["process_state"] = str(record["process_state"])
                if record["process_state"] in {"registered", "starting"}:
                    waiting = True
                elif record["process_state"] == "running":
                    waiting = False
                    # The child races the platform's own bookkeeping: the start
                    # observation is recorded first and the work item's
                    # ``leased -> running`` transition commits in the next
                    # transaction. A run that is already running with a matching
                    # started observation is authoritative for this gate, so the
                    # lease state is accepted here and nowhere else.
                    refusal["step"] = "current_run"
                    record, work = current_run(tx, config, allow_leased_work=True)
                    refusal["work_state"] = str(work["state"])
                    refusal["step"] = "observation"
                    observed = row(tx.connection.execute(
                        "SELECT * FROM vnext.execution_observation WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND receipt_id=%s AND agent_run_id=%s",
                        (*tx.owner, record["last_observation_id"], record["agent_run_id"])))
                    if not observed or observed["kind"] != "started" or observed["subject"] != receiver_access.principal.subject:
                        raise DomainError("STALE_EXECUTION", 409)
                    source = strict_json_loads(observed["source_receipt"])
                    observation = ExecutionObservation.model_validate({
                        **source, "source_receipt": observed["source_receipt"],
                        "source_digest": observed["source_digest"],
                    })
                    if (observation.identity != run.identity
                            or observation.operation_id != run.start_operation_id
                            or observation.environment_ref != run.environment_ref
                            or observation.pod_uid != run.pod_uid
                            or observation.receipt_id != record["last_observation_id"]
                            or observation.kind != "started"
                            or document(observation.process) != strict_json_loads(record["process_identity_json"])):
                        raise DomainError("STALE_EXECUTION", 409)
                    response.update(status="ready", birth_id=observation.process.birth_id,
                                    observation_id=observation.receipt_id,
                                    source_digest=observation.source_digest)
                else:
                    raise DomainError("STALE_EXECUTION", 409)
            refusal["waiting"] = waiting
            if waiting:
                refusal["step"] = "start_authorize"
                # The actual P09/P05 start predicate includes Task/Work epochs,
                # holds, dependency/input, authorization expiry and capacity.
                try:
                    self.authorizer.authorize(
                        access=receiver_access, action="start", assignment=assignment,
                        assignment_digest=run.assignment_digest, receiver=_receiver(run),
                        refusal=refusal,
                    )
                except DomainError as error:
                    if (
                        allow_running_transition_recheck
                        and error.code == "STALE_EXECUTION"
                    ):
                        # P05 may have committed the exact started observation
                        # after the waiting read. Re-run the complete same-
                        # Assignment checks once; every mismatch still fails.
                        return self._await_start(
                            access,
                            assignment,
                            allow_running_transition_recheck=False,
                        )
                    raise
        except DomainError as error:
            if error.code not in {"STALE_EXECUTION", "LIMIT_BLOCKED"}:
                raise
            # A refused child start is otherwise indistinguishable from a
            # revoked credential. Only the stable code is emitted; no identity,
            # assignment, bearer, path or peer detail is logged.
            print(json.dumps({"event": "worker_start_refused", "code": error.code,
                              **refusal}, sort_keys=True), flush=True)
            response.update(status="revoked", birth_id=None, observation_id=None, source_digest=None)
        return wire.WorkerStartPermission.model_validate(response)

    def _ready(self, access, assignment):
        permission = self.await_start(access, assignment)
        if permission.status.value != "ready":
            raise DomainError("STALE_EXECUTION", 409)

    def current_worker_host(self, access, assignment):
        """Return only the Host bound to this ready, current Worker Principal."""
        assignment = WorkerAssignment.model_validate(assignment)
        self._ready(access, assignment)
        host = self.host_factory(access)
        if host.access.principal != access.principal:
            raise DomainError("STALE_EXECUTION", 409)
        return host

    def _records(self, access, assignment, manifest):
        """The exact read-set records plus the raw rows of its artifacts.

        The artifact rows keep the published media type, state and byte count of
        each candidate body without reading any bytes yet; the caller decides
        which bodies may be inlined into the delivered context.
        """

        snapshots = SnapshotRepository(self.uow)
        records = []
        artifact_rows = {}
        for ref in manifest.refs:
            value = snapshots.read_ref(assignment.identity.task_id, access, manifest.snapshot_id, ref)
            kind = ref.entity_type.value
            if kind == "artifact":
                # HTTP exchange artifacts retain their exact ToolCall binding
                # through the captured ToolAttempt.  A Reason context must not
                # invent a call id from content or a hash.
                value = dict(value)
                attempt_id = value.get("tool_attempt_id")
                if attempt_id:
                    with self.uow.transaction(
                        access, assignment.identity.task_id, capability="model_request"
                    ) as tx:
                        linked = tx.connection.execute(
                            "SELECT tool_call_id FROM vnext.tool_attempt "
                            "WHERE tenant_id=%s AND project_id=%s AND task_id=%s "
                            "AND tool_attempt_id=%s",
                            (*tx.owner, attempt_id),
                        ).fetchone()
                    if linked is not None:
                        value["tool_call_id"] = linked[0]
                artifact_rows[(kind, ref.id, ref.revision.root)] = value
            if kind in {"claim", "intent"}:
                records.append(self.ledger.read(access, assignment.identity.task_id, ref,
                                                snapshot_id=manifest.snapshot_id))
                continue
            if kind == "artifact":
                payload = wire.ArtifactRecord.model_validate({
                    "artifact_ref": {"id": ref.id, "version": ref.revision.root, "sha256": value["sha256"]},
                    "state": value["state"], "media_type": value["media_type"],
                    "size_bytes": str(value["size_bytes"]), "created_at": value["created_at"],
                })
            elif kind == "observation":
                with self.uow.transaction(access, assignment.identity.task_id) as tx:
                    attached = tx.connection.execute(
                        """SELECT p.artifact_id,p.artifact_revision,a.sha256 FROM vnext.observation_artifact p
                        JOIN vnext.artifact a ON (a.tenant_id,a.project_id,a.task_id,a.entity_id,a.revision)=
                        (p.tenant_id,p.project_id,p.task_id,p.artifact_id,p.artifact_revision)
                        WHERE p.tenant_id=%s AND p.project_id=%s AND p.task_id=%s
                        AND p.observation_id=%s AND p.observation_revision=%s ORDER BY p.ordinal""",
                        (*tx.owner, ref.id, ref.revision.root)).fetchall()
                payload = wire.ObservationRecord.model_validate({
                    "observation_id": ref.id, "revision": ref.revision.root,
                    "task_id": assignment.identity.task_id,
                    **{key: value[key] for key in ("capture_id", "tool_attempt_id", "collector_ref",
                        "capture_layer", "observed_at", "received_at", "environment_ref", "completeness", "evidence_origin")},
                    "conditions": strict_json_loads(value["conditions_json"]),
                    "artifact_refs": [{"id": aid, "version": str(rev), "sha256": digest}
                                      for aid, rev, digest in attached],
                })
            else:
                raise DomainError("INVALID_REFERENCE", 422)
            records.append(wire.RecordView.model_validate({"ref": ref, "display_kind": kind, "record": payload}))
        return records, artifact_rows

    def _inline_material(self, assignment, manifest, artifact_rows, *, body, limits):
        references = {
            (ref.entity_type.value, ref.id, ref.revision.root) for ref in manifest.refs
        }
        return inline_material(
            artifacts=self.artifacts,
            artifact_rows=artifact_rows,
            references=references,
            context_bytes=int(body["max_context_bytes"]),
            max_single_output_bytes=int(limits["max_single_output_bytes"]),
        )

    def _resolve_refused(self, step, error):
        """Emit the bounded predicate that refused one Host context build.

        A refused resolve is otherwise an opaque 5xx/4xx for the child. Only the
        step label and the stable refusal code/status are emitted; the
        assignment, manifest, snapshot records, bearers and peer detail stay on
        the private channel. This is the resolve counterpart of the bounded
        ``worker_start_refused`` signal.
        """

        if isinstance(error, DomainError):
            code, status = error.code, error.status
        else:
            code, status = "internal_error", 500
        print(json.dumps({"event": "worker_resolve_refused", "step": step,
                          "code": code, "status": status}, sort_keys=True), flush=True)

    def resolve(self, access, assignment):
        step = "validate_assignment"
        try:
            assignment = WorkerAssignment.model_validate(assignment)
            step = "current_host"
            host = self.current_worker_host(access, assignment)
            with self._lock:
                step = "snapshot_manifest"
                snapshots = SnapshotRepository(self.uow)
                manifest = snapshots.get(assignment.identity.task_id, access, assignment.snapshot_id)
                # Resolve the profile from the frozen Task before building context;
                # PlatformWorkerHost validates its complete binding again below.
                step = "profile_binding"
                with self.uow.transaction(access, assignment.identity.task_id, capability="model_request") as tx:
                    config = self.registry.config(tx)
                    current_run(tx, config)
                    definition = strict_json_loads(tx.task["definition_json"])
                    profile = definition["worker_profiles"][assignment.work_kind.value]
                    if host.profiles.get(profile["ref"]) != profile:
                        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                body = profile["body"]
                step = "record_limit"
                if len(manifest.refs) > min(body["max_context_records"], 5000):
                    raise DomainError("LIMIT_BLOCKED", 422)
                step = "read_records"
                records, artifact_rows = self._records(access, assignment, manifest)
                step = "context_build"
                published_limits = config.runtime.limits.model_dump(mode="json")
                material = self._inline_material(
                    assignment, manifest, artifact_rows, body=body,
                    limits=published_limits,
                )
                context_options = {"states": manifest.states}
                if material is not None:
                    # Only the deployment's own builder accepts inline material;
                    # a host without an artifact reader keeps the metadata-only
                    # context instead of pretending the bodies were delivered.
                    context_options["material"] = material
                context = self.context_builder(
                    records=records, read_set=manifest.refs,
                    snapshot_id=manifest.snapshot_id, max_records=body["max_context_records"],
                    max_bytes=min(body["max_context_bytes"], 16777216), relations=manifest.relations,
                    **context_options,
                )
                context_wire = wire.WorkerContext.model_validate({
                    "snapshot_id": context.snapshot_id, "read_set": list(context.read_set),
                    "record_refs": list(context.record_refs), "text": context.text,
                    "input_digest": context.input_digest,
                })
                step = "context_binding"
                if (tuple(context.read_set) != manifest.refs or tuple(context.record_refs) != manifest.refs
                        or context.snapshot_id != assignment.snapshot_id):
                    raise DomainError("INVALID_REFERENCE", 422)
                step = "host_resolve"
                resolved = host.resolve(assignment, context, verified_principal=access.principal)
                profile_body = resolved.get("profile", {}).get("body", {})
                if profile_body.get("schema_version") == "wuji.harness.session.v1":
                    step = "session_encode"
                    if self.session_resolve_encoder is None:
                        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                    resolved = self.session_resolve_encoder(resolved)
                step = "reply_validate"
                reply = wire.WorkerResolvedContext.model_validate({
                    "context": document(context_wire), "resolved": resolved,
                    "assignment_digest": assignment_digest(assignment),
                })
                step = "context_spool"
                self.intake.save(assignment, "context", context_wire)
                return reply
        except Exception as error:
            self._resolve_refused(step, error)
            raise

    def _stored_context(self, assignment, context):
        expected = self.intake.read(assignment, "context")
        if expected is None or canonical_json_bytes(document(context)) != canonical_json_bytes(expected):
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        return HostContext.from_wire(expected)

    @staticmethod
    def _bytes(encoded, digest, maximum):
        if len(encoded) > 4 * ((maximum + 2) // 3):
            raise DomainError("LIMIT_BLOCKED", 422)
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError):
            raise DomainError("INVALID_SCHEMA", 422) from None
        if len(data) > maximum or sha256(data).hexdigest() != digest:
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        return data

    def _archive(self, access, payload):
        context = self.intake.read(payload.assignment, "context")
        if context is None or context["snapshot_id"] != payload.assignment.snapshot_id:
            raise DomainError("INVALID_REFERENCE", 422)
        body = self._bytes(payload.sdk_output_base64, payload.sdk_digest.root,
                           min(payload.assignment.limits.max_total_output_bytes, 16777216))
        self.intake.save(payload.assignment, "archive", payload)
        host = self.host_factory(access)
        if host.access.principal != access.principal:
            raise DomainError("STALE_EXECUTION", 409)
        return host.archive_sdk(payload.assignment, body)

    def _submit(self, access, payload):
        context = self._stored_context(payload.assignment, payload.context)
        raw = self._bytes(payload.raw_output_base64, payload.raw_digest.root,
                          min(payload.assignment.limits.max_single_output_bytes, 16777216))
        sdk = self._bytes(payload.sdk_output_base64, payload.sdk_digest.root,
                          min(payload.assignment.limits.max_total_output_bytes, 16777216))
        self.intake.save(payload.assignment, "result", payload)
        host = self.host_factory(access)
        if host.access.principal != access.principal:
            raise DomainError("STALE_EXECUTION", 409)
        return host.submit_result(payload.assignment, raw_output=raw, context=context,
                                  tool_receipts=tuple(payload.tool_receipts), sdk_output=sdk)

    def archive_sdk(self, access, payload):
        payload = wire.WorkerArchiveRequest.model_validate(payload)
        self._ready(access, payload.assignment)
        with self._lock:
            return self._archive(access, payload)

    def submit_result(self, access, payload):
        payload = wire.WorkerSubmitRequest.model_validate(payload)
        self._ready(access, payload.assignment)
        with self._lock:
            return self._submit(access, payload)

    def replay(self, access, payload):
        # Same exact raw binding and P04 durable idempotency, no cached ack.
        return self.submit_result(access, payload)

    def receiver_replay(self, access, payload):
        payload = wire.WorkerSubmitRequest.model_validate(payload)
        self._registered(payload.assignment, access)
        context = self._stored_context(payload.assignment, payload.context)
        raw = self._bytes(
            payload.raw_output_base64,
            payload.raw_digest.root,
            min(payload.assignment.limits.max_single_output_bytes, 16777216),
        )
        sdk = self._bytes(
            payload.sdk_output_base64,
            payload.sdk_digest.root,
            min(payload.assignment.limits.max_total_output_bytes, 16777216),
        )
        with self._lock:
            self.intake.save(payload.assignment, "result", payload)
            return self.retained_results.submit_result(
                access,
                payload.assignment,
                raw_output=raw,
                context=context,
                tool_receipts=tuple(payload.tool_receipts),
                sdk_output=sdk,
            )

    def receiver_archive(self, access, payload):
        payload = wire.WorkerArchiveRequest.model_validate(payload)
        self._registered(payload.assignment, access)
        context = self.intake.read(payload.assignment, "context")
        if context is None or context["snapshot_id"] != payload.assignment.snapshot_id:
            raise DomainError("INVALID_REFERENCE", 422)
        body = self._bytes(
            payload.sdk_output_base64,
            payload.sdk_digest.root,
            min(payload.assignment.limits.max_total_output_bytes, 16777216),
        )
        with self._lock:
            self.intake.save(payload.assignment, "archive", payload)
            return self.retained_results.archive_sdk(
                access, payload.assignment, body
            )

    def reconcile_results(self, run):
        """P10 Reconciler.persist_results callback; no output is no receipt."""
        access = self.receiver_access(run)
        with self.uow.transaction(access, run.identity.task_id, capability="observe") as tx:
            actual, assignment, _ref = read_registered_run(tx, run.start_operation_id)
            if actual != run:
                raise DomainError("STALE_EXECUTION", 409)
        result = self.intake.read(assignment, "result")
        if result is not None:
            return self.receiver_replay(access, result)
        archive = self.intake.read(assignment, "archive")
        if archive is not None:
            return self.receiver_archive(access, archive)
        return None
