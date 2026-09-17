"""Receive real Supervisor process evidence through the existing P05 producer.

No PID probe, result status, lease expiry, or absent HTTP record proves exit.
This module never creates a Run, spawns a process or writes knowledge/results.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Mapping

from wuji_core.contracts.envelopes import RunIdentity
from wuji_core.execution.control import ExecutionObservation
from wuji_core.http.json_boundary import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError, row
from wuji_core.scheduling.claims import DispatchRepository


@dataclass(frozen=True)
class RegisteredRun:
    identity: RunIdentity
    start_operation_id: str
    environment_ref: str
    pod_uid: str
    assignment_digest: str
    work_kind: str
    harness_profile_id: str
    harness_profile_digest: str


@dataclass(frozen=True)
class ObservedExecution:
    run: RegisteredRun
    state: str
    observation: ExecutionObservation | None
    reason: str
    # Private original transport receipt; never contains model/Worker raw bytes.
    source_receipt: bytes | None = None


class ObservationUnavailable(DomainError):
    def __init__(self, code="OPERATION_UNKNOWN"):
        super().__init__(code, 503)


def read_registered_run(tx, operation_id):
    """Same authorized observe transaction, canonical P09 Assignment and Run."""
    assignment, credential_ref = DispatchRepository().read(tx, operation_id=operation_id)
    record = row(tx.connection.execute(
        """SELECT * FROM vnext.agent_run
        WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s""",
        (*tx.owner, assignment.identity.agent_run_id),
    ))
    identity = assignment.identity.model_dump(mode="json")
    if (not record or any(str(record[key]) != value for key, value in identity.items())
            or record["start_operation_id"] != operation_id):
        raise DomainError("STALE_EXECUTION", 409)
    try:
        raw_definition = tx.task["definition_json"]
        if sha256(raw_definition.encode("utf-8")).hexdigest() != tx.task["definition_digest"]:
            raise ValueError("Task definition digest changed")
        definition = strict_json_loads(raw_definition)
        profile = definition["worker_profiles"][assignment.work_kind.value]
        body = profile["body"]
        expected_refs = (
            profile["ref"],
            definition["model_profile"]["ref"],
            definition["runtime_profile"]["ref"],
        )
        if (
            not isinstance(profile["ref"], str)
            or not isinstance(profile["digest"], str)
            or len(profile["digest"]) != 64
            or profile["digest"] != sha256(canonical_json_bytes(body)).hexdigest()
            or profile["ref"] != body["ref"]
            or str(profile["revision"]) != str(body["revision"])
            or body["work_kind"] != assignment.work_kind.value
            or tuple(ref.root for ref in assignment.profile_refs) != expected_refs
            or tuple(body["tool_definition_refs"])
            != tuple(ref.root for ref in assignment.tool_definition_refs)
        ):
            raise ValueError("assignment changed fixed profile selection")
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise DomainError("CAPABILITY_UNAVAILABLE", 503) from error
    # P10 does not invent a pod UID or modify another lane's receiver schema.
    if not record["environment_ref"] or not record["pod_uid"]:
        raise ObservationUnavailable("RECEIVER_ENVIRONMENT_UNBOUND")
    run = RegisteredRun(
        identity=assignment.identity, start_operation_id=operation_id,
        environment_ref=record["environment_ref"], pod_uid=record["pod_uid"],
        assignment_digest=sha256(canonical_json_bytes(assignment.model_dump(mode="json"))).hexdigest(),
        work_kind=assignment.work_kind.value, harness_profile_id=profile["ref"],
        harness_profile_digest=profile["digest"],
    )
    return run, assignment, credential_ref


def validate_receipt(run: RegisteredRun, receipt: Mapping) -> ObservedExecution:
    """Validate the receiver response, then the original P05 source document.

    Cryptographic peer authentication belongs to the configured transport;
    a content hash is integrity checking, not a replacement for that peer.
    """
    receiver = {
        "receiver_id": run.identity.receiver_id,
        "runtime_attempt": run.identity.runtime_attempt.root,
        "environment_ref": run.environment_ref, "pod_uid": run.pod_uid,
    }
    if (not isinstance(receipt, Mapping)
            or set(receipt) != {"operation_id", "identity", "receiver", "assignment_digest",
                                "profile_id", "state", "observation"}
            or receipt["operation_id"] != run.start_operation_id
            or receipt["identity"] != run.identity.model_dump(mode="json")
            or receipt["receiver"] != receiver
            or receipt["assignment_digest"] != run.assignment_digest
            or receipt["profile_id"] != run.harness_profile_id):
        raise DomainError("STALE_EXECUTION", 409)
    state = receipt["state"]
    if state not in {"prepared", "running", "exited", "not_started", "unknown"}:
        raise DomainError("INVALID_REFERENCE", 422)
    source = canonical_json_bytes(dict(receipt))
    if state == "prepared":
        if receipt["observation"] is not None:
            raise DomainError("INVALID_REFERENCE", 422)
        return ObservedExecution(run, state, None, "prepared_is_not_process_truth", source)
    observation = ExecutionObservation.model_validate(receipt["observation"])
    kind = "started" if state == "running" else state
    if (observation.identity != run.identity or observation.operation_id != run.start_operation_id
            or observation.kind != kind or observation.environment_ref != run.environment_ref
            or observation.pod_uid != run.pod_uid):
        raise DomainError("STALE_EXECUTION", 409)
    return ObservedExecution(run, state, observation, observation.reason, source)


class Reconciler:
    def __init__(self, uow, *, access, control, transport, persist_results):
        if not callable(persist_results):
            raise ValueError("actual existing-result persistence adapter required")
        self.uow, self.access = uow, access
        self.control, self.transport = control, transport
        self.persist_results = persist_results

    def registered(self, *, task_id, operation_id):
        with self.uow.transaction(self.access, task_id, capability="observe") as tx:
            run, _assignment, _credential_ref = read_registered_run(tx, operation_id)
            return run

    def inspect(self, run: RegisteredRun) -> ObservedExecution:
        if not isinstance(run, RegisteredRun):
            raise ValueError("RegisteredRun required")
        actual = self.registered(task_id=run.identity.task_id, operation_id=run.start_operation_id)
        if actual != run:
            raise DomainError("STALE_EXECUTION", 409)
        try:
            receipt = self.transport.query(
                run.start_operation_id, task_id=run.identity.task_id
            )
        except ObservationUnavailable:
            return ObservedExecution(run, "unknown", None, "receiver_response_unknown")
        if receipt is None:
            return ObservedExecution(run, "unknown", None, "receiver_record_absent")
        return validate_receipt(run, receipt)

    def settle_ended_environment(self, run: RegisteredRun, *, reason: str) -> ObservedExecution:
        """The attempt's environment is gone and this Run was never observed.

        The runtime only reports ``stopped`` once the Task Pod object is absent,
        so no query can ever produce a receipt for this Run. The platform records
        its own bounded observation rather than inventing a process exit or a
        result, and never claims the process failed to run.
        """

        if not isinstance(run, RegisteredRun) or not isinstance(reason, str) or not 0 < len(reason) <= 512:
            raise ValueError("bounded environment evidence required")
        observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        body = {
            "receipt_id": "environment-stopped:" + run.identity.agent_run_id,
            "identity": run.identity.model_dump(mode="json"),
            "operation_id": run.start_operation_id,
            "environment_ref": run.environment_ref,
            "pod_uid": run.pod_uid,
            "kind": "environment_stopped",
            "observed_at": observed_at,
            "process": None,
            "reason": reason,
        }
        source = canonical_json_bytes(body).decode()
        observation = ExecutionObservation.model_validate({
            **body, "source_receipt": source,
            "source_digest": sha256(source.encode()).hexdigest(),
        })
        self.control.record_observation(self.access, observation)
        self.control.reconcile(self.access, run.identity.task_id, run.identity.work_item_id)
        return ObservedExecution(run, "environment_stopped", None, reason)

    def reconcile(self, run: RegisteredRun) -> ObservedExecution:
        observed = self.inspect(run)
        # Reconcile actual previously produced bytes/receipts first. This port
        # must not re-execute MAF or fabricate a success when no output exists.
        self.persist_results(run)
        if observed.observation is not None:
            self.control.record_observation(self.access, observed.observation)
            self.control.reconcile(self.access, run.identity.task_id, run.identity.work_item_id)
        # With no trusted process observation P05 receives nothing and holds its
        # reservation. Unknown transport absence is not invented receiver proof.
        return observed
