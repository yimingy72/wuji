"""M2c Runtime capture authority, replay and exact-byte checks."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import pytest

from support.p06 import OWNER, TASK
from support.core_ctf import catalog as core_ctf_catalog
from test_pod_runtime import POD_UID, _pod_case
from wuji_core.contracts import generated as wire
from wuji_core.evidence.artifacts import ArtifactStore
from wuji_core.evidence.runtime_capture import RuntimeCaptureService
from wuji_core.execution.control import require_runtime_terminal
from wuji_core.execution.pod_runtime import TaskPodLease
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.http.auth import Principal
from wuji_core.persistence.uow import AccessContext, DomainError, UnitOfWork


def _with_digest(model, payload, digest):
    value = model.model_validate({**payload, digest: "0" * 64})
    payload[digest] = sha256(
        canonical_json_bytes(value.model_dump(mode="json", exclude={digest}))
    ).hexdigest()
    return model.model_validate(payload)


def test_runtime_capture_gap_reuses_staged_part_and_terminal_without_session(
    db_environment, tmp_path, audit_directory
):
    with _pod_case(db_environment, tmp_path, audit_directory) as case:
        gap = b'{"schema_version":"wuji.capture-gap.v1","reason":"startup"}\n'
        policy = wire.CapturePolicyV1.model_validate(
            core_ctf_catalog()["admission"]["runtime"]["capture_policy"]
        ).model_dump(mode="json")
        with db_environment.migration_connection() as owner:
            definition, admission = owner.execute(
                """SELECT t.definition_json,a.document_json FROM vnext.task t
                JOIN vnext.admission_config a USING(tenant_id,project_id,task_id)
                WHERE t.tenant_id=%s AND t.project_id=%s AND t.task_id=%s""",
                OWNER,
            ).fetchone()
            definition = strict_json_loads(definition)
            admission = strict_json_loads(admission)
            definition["runtime_profile"]["capture_policy"] = policy
            admission["runtime"]["capture_policy"] = policy
            encoded = canonical_json_bytes(definition).decode()
            owner.execute(
                """UPDATE vnext.task SET definition_json=%s,definition_digest=%s
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s""",
                (encoded, sha256(encoded.encode()).hexdigest(), *OWNER),
            )
            owner.execute(
                """UPDATE vnext.admission_config SET document_json=%s
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s""",
                (canonical_json_bytes(admission).decode(), *OWNER),
            )
            owner.execute(
                """INSERT INTO vnext.scheduler_receiver(
                tenant_id,project_id,task_id,runtime_attempt,receiver_id,
                environment_ref,model_mode,receiver_subject,credential_template_ref,
                harness_profiles_json,pod_uid,enabled)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true)""",
                (
                    *OWNER,
                    case.config.runtime_attempt,
                    case.receiver.receiver_id,
                    case.receiver.environment_ref,
                    case.receiver.model_mode,
                    case.receiver.receiver_subject,
                    case.receiver.credential_template_ref,
                    canonical_json_bytes(case.profiles).decode(),
                    POD_UID,
                ),
            )
            owner.execute(
                """UPDATE vnext.task_access SET can_control=true
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                  AND subject=%s""",
                (*OWNER, case.access.principal.subject),
            )

        collector = AccessContext(
            Principal(
                "collector-fixture",
                OWNER[0],
                frozenset({"runtime", "collector"}),
                "fixture-token-id",
            ),
            "capture-fixture-request",
        )
        uow = UnitOfWork(db_environment.additional_app_connection)
        artifacts = ArtifactStore(
            uow, tmp_path / "runtime-capture-objects", max_bytes=67_108_864
        )
        capture = RuntimeCaptureService(uow, artifacts=artifacts)

        with db_environment.additional_app_connection() as connection:
            lease = TaskPodLease(connection, case.config)
            lease.acquire()
            try:
                controller_capture = RuntimeCaptureService(
                    UnitOfWork(lease.borrow), artifacts=artifacts
                )
                binding = {
                    "task_id": TASK,
                    "runtime_attempt": str(case.config.runtime_attempt),
                    "execution_epoch": str(case.config.execution_epoch),
                    "pod_uid": POD_UID,
                }
                status = _with_digest(
                    wire.RuntimeCaptureStatusV1,
                    {
                        "schema_version": "wuji.runtime-capture-status.v1",
                        "binding": binding,
                        "collector_ref": "collector-fixture",
                        "environment_ref": case.receiver.environment_ref,
                        "evidence_origin": "fixture_capture",
                        "capture_layer": "runtime_capture",
                        "state": "ready",
                        "started_at": "2026-09-23T00:00:00Z",
                    },
                    "status_digest",
                )
                session = controller_capture.register_session(case.access, status)

                descriptor = {
                    "part": "gap",
                    "media_type": "application/json",
                    "length": len(gap),
                    "sha256": sha256(gap).hexdigest(),
                }
                envelope = _with_digest(
                    wire.RuntimeCaptureEnvelopeV1,
                    {
                        "schema_version": "wuji.runtime-capture-envelope.v1",
                        "capture_session_id": session.capture_session_id,
                        "binding": binding,
                        "collector_ref": "collector-fixture",
                        "item_seq": 1,
                        "kind": "gap",
                        "completeness": "partial",
                        "observed_at": "2026-09-23T00:00:01Z",
                        "parts": [descriptor],
                        "metadata": {"exchange_id": "startup"},
                        "conditions": ["capture_startup_failed"],
                    },
                    "item_digest",
                )

                staged = artifacts.stage_runtime_capture(
                    collector,
                    TASK,
                    session.capture_session_id,
                    gap,
                    "application/json",
                    completeness="partial",
                    conditions=["capture_startup_failed"],
                    access_level=1,
                    lease_owner="runtime-capture:1:gap",
                )
                artifacts.seal(collector, TASK, staged)
                receipt = capture.ingest_item(collector, envelope, {"gap": gap})
                replay = capture.ingest_item(collector, envelope, {"gap": gap})
                assert receipt == replay
                assert receipt.artifact_refs == [staged]
                assert capture.read_part(
                    collector,
                    TASK,
                    session.capture_session_id,
                    1,
                    "gap",
                    max_bytes=67_108_864,
                )[0] == gap

                # Cancellation may revoke the receiver and advance the Task
                # epoch before the controller can persist the old Pod's exact
                # terminal state. The held TaskPod lease remains the authority.
                with db_environment.migration_connection() as owner:
                    owner.execute(
                        """DELETE FROM vnext.scheduler_receiver WHERE
                        tenant_id=%s AND project_id=%s AND task_id=%s
                        AND runtime_attempt=%s""",
                        (*OWNER, case.config.runtime_attempt),
                    )
                    owner.execute(
                        """UPDATE vnext.task SET execution_epoch=execution_epoch+1,
                        execution_allowed=false WHERE tenant_id=%s AND project_id=%s
                        AND task_id=%s""",
                        OWNER,
                    )

                terminal_payload = {
                    "schema_version": "wuji.runtime-terminal-observation.v1",
                    "capture_session_id": None,
                    "binding": binding,
                    "controller_ref": case.access.principal.subject,
                    "container_name": "agent",
                    "state": "not_started",
                    "container_id": None,
                    "exit_code": None,
                    "signal": None,
                    "reason": "capture_startup_failed",
                    "started_at": None,
                    "finished_at": None,
                    "observed_at": "2026-09-23T00:00:02Z",
                }
                terminal = wire.RuntimeTerminalObservationV1.model_validate(
                    {**terminal_payload, "source_digest": "0" * 64}
                )
                terminal = terminal.model_copy(
                    update={
                        "source_digest": wire.Sha256Digest.model_validate(
                            RuntimeCaptureService._terminal_source(terminal)
                        )
                    }
                )
                first = controller_capture.record_terminal_observation(
                    case.access, terminal
                )
                later = wire.RuntimeTerminalObservationV1.model_validate(
                    {
                        **terminal.model_dump(mode="json"),
                        "capture_session_id": session.capture_session_id,
                        "observed_at": datetime.now(timezone.utc) + timedelta(seconds=1),
                    }
                )
                second = controller_capture.record_terminal_observation(
                    case.access, later
                )
                assert second == first
                assert first.capture_session_id is None
                with controller_capture.uow.transaction(
                    case.access, TASK, capability="control"
                ) as tx:
                    with pytest.raises(DomainError) as incomplete:
                        require_runtime_terminal(tx)
                    assert incomplete.value.code == "OPERATION_UNKNOWN"
                for name, state in (
                    ("task-network-init", "terminated"),
                    ("kali", "not_started"),
                    ("capture", "not_started"),
                ):
                    next_payload = {
                        **terminal_payload,
                        "capture_session_id": (
                            session.capture_session_id
                            if name == "task-network-init" else None
                        ),
                        "container_name": name,
                        "state": state,
                        "exit_code": 0 if state == "terminated" else None,
                        "finished_at": "2026-09-23T00:00:02Z" if state == "terminated" else None,
                    }
                    next_terminal = wire.RuntimeTerminalObservationV1.model_validate(
                        {**next_payload, "source_digest": "0" * 64}
                    )
                    next_terminal = next_terminal.model_copy(
                        update={"source_digest": wire.Sha256Digest.model_validate(
                            RuntimeCaptureService._terminal_source(next_terminal)
                        )}
                    )
                    recorded = controller_capture.record_terminal_observation(
                        case.access, next_terminal
                    )
                    if name == "task-network-init":
                        assert next_terminal.capture_session_id.root == session.capture_session_id
                        assert recorded.capture_session_id.root == session.capture_session_id
                states = controller_capture.terminal_container_states(
                    case.access, TASK, runtime_attempt=binding["runtime_attempt"],
                    execution_epoch=binding["execution_epoch"], pod_uid=POD_UID,
                )
                assert states == {
                    "task-network-init": "terminated",
                    "agent": "not_started",
                    "kali": "not_started",
                    "capture": "not_started",
                }
                with controller_capture.uow.transaction(
                    case.access, TASK, capability="control"
                ) as tx:
                    require_runtime_terminal(tx)
            finally:
                lease.close()

        with db_environment.migration_connection() as owner:
            assert owner.execute(
                """SELECT (SELECT count(*) FROM vnext.artifact a WHERE
                  (a.tenant_id,a.project_id,a.task_id,a.capture_session_id)=
                  (s.tenant_id,s.project_id,s.task_id,s.capture_session_id)),
                (SELECT sum(size_bytes) FROM vnext.artifact a WHERE
                  (a.tenant_id,a.project_id,a.task_id,a.capture_session_id)=
                  (s.tenant_id,s.project_id,s.task_id,s.capture_session_id)),
                s.ingested_items,s.retained_bytes FROM vnext.capture_session s
                WHERE s.tenant_id=%s AND s.project_id=%s AND s.task_id=%s
                  AND s.capture_session_id=%s""",
                (*OWNER, session.capture_session_id),
            ).fetchone() == (1, len(gap), 1, len(gap))
