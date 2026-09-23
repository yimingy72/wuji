"""Trusted Runtime ingestion of Task-level capture items and terminal state."""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from wuji_core.admission.registry import AdmissionRegistry
from wuji_core.contracts import generated as wire
from wuji_core.contracts.envelopes import BlobRef
from wuji_core.contracts.knowledge import ObservationRecord
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text, row


MAX_ITEM_DOCUMENT_BYTES = 128 * 1024
MAX_METADATA_BYTES = 64 * 1024


def require_runtime_collector(access):
    if (
        "runtime" not in access.principal.roles
        or "collector" not in access.principal.roles
        or "agent" in access.principal.roles
    ):
        raise DomainError("FORBIDDEN_COLLECTOR", 403)


def _lock_capture_session(tx, capture_session_id):
    tx.connection.execute(
        """SELECT pg_advisory_xact_lock(hashtextextended(json_build_array(
        %s::text,%s::text,%s::text,%s::text,%s::text)::text,0))""",
        (
            "wuji.vnext.capture-session",
            tx.owner[0],
            tx.owner[1],
            tx.owner[2],
            capture_session_id,
        ),
    )


def bound_capture_session(tx, capture_session_id, *, lock=False):
    if lock:
        _lock_capture_session(tx, capture_session_id)
    result = row(
        tx.connection.execute(
            "SELECT * FROM vnext.capture_session WHERE tenant_id=%s AND "
            "project_id=%s AND task_id=%s AND capture_session_id=%s",
            (*tx.owner, capture_session_id),
        )
    )
    if (
        result is None
        or result["collector_subject"] != tx.access.principal.subject
    ):
        raise DomainError("FORBIDDEN_COLLECTOR", 403)
    return result


def capture_session_disposition(tx, session):
    current = (
        int(tx.task["runtime_attempt"]) == int(session["runtime_attempt"])
        and int(tx.task["execution_epoch"]) == int(session["execution_epoch"])
    )
    if current and tx.permissions["can_capture"]:
        return "accepted"
    if tx.permissions["can_settle"]:
        return "historical_only"
    raise DomainError("STALE_EXECUTION", 403)


def _binding(value):
    return wire.RuntimeCaptureBindingV1.model_validate(value).model_dump(mode="json")


def _rows(cursor):
    values = []
    while (value := row(cursor)) is not None:
        values.append(value)
    return values


def _part_lease_owner(item_seq, part):
    return f"runtime-capture:{item_seq}:{part}"


def _session_model(record):
    return wire.RuntimeCaptureSessionV1.model_validate(
        {
            "schema_version": "wuji.runtime-capture-session.v1",
            "capture_session_id": record["capture_session_id"],
            "binding": {
                "task_id": record["task_id"],
                "runtime_attempt": str(record["runtime_attempt"]),
                "execution_epoch": str(record["execution_epoch"]),
                "pod_uid": record["pod_uid"],
            },
            "collector_ref": record["collector_subject"],
            "environment_ref": record["environment_ref"],
            "evidence_origin": record["evidence_origin"],
            "capture_layer": record["capture_layer"],
            "state": record["state"],
            "status_digest": record["status_digest"],
            "policy": strict_json_loads(record["policy_json"]),
            "policy_digest": record["policy_digest"],
            "started_at": record["started_at"],
        }
    )


def terminal_container_states(tx, *, runtime_attempt, execution_epoch, pod_uid):
    """Return a complete, persisted external terminal observation for one Pod UID."""
    expected = {"task-network-init", "agent", "kali", "capture"}
    values = tx.connection.execute(
        """SELECT container_name,document_json FROM vnext.runtime_terminal_observation
        WHERE tenant_id=%s AND project_id=%s AND task_id=%s
          AND runtime_attempt=%s AND execution_epoch=%s AND pod_uid=%s""",
        (*tx.owner, runtime_attempt, execution_epoch, pod_uid),
    ).fetchall()
    if len(values) != len(expected):
        return None
    states = {}
    for name, document in values:
        if name in states or name not in expected:
            return None
        state = strict_json_loads(document).get("state")
        if state not in ({"terminated"} if name == "task-network-init" else {"terminated", "not_started"}):
            return None
        states[name] = state
    return states if states.keys() == expected else None


class RuntimeCaptureService:
    def __init__(self, uow, *, artifacts):
        if not all(
            callable(getattr(artifacts, name, None))
            for name in ("stage_runtime_capture", "seal", "record", "checked_bytes")
        ):
            raise TypeError("Runtime capture requires the authoritative Artifact store")
        self.uow, self.artifacts = uow, artifacts

    @staticmethod
    def _status_digest(status):
        value = status.model_dump(mode="json", exclude={"status_digest"})
        return sha256(canonical_json_bytes(value)).hexdigest()

    @staticmethod
    def _item_digest(envelope):
        value = envelope.model_dump(mode="json", exclude={"item_digest"})
        return sha256(canonical_json_bytes(value)).hexdigest()

    def register_session(self, access, status):
        if (
            "controller" not in access.principal.roles
            or access.principal.roles & {"agent", "worker", "supervisor"}
        ):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        status = wire.RuntimeCaptureStatusV1.model_validate(status)
        if (
            status.binding.task_id == ""
            or self._status_digest(status) != status.status_digest.root
        ):
            raise DomainError("INVALID_REFERENCE", 422)
        binding = status.binding.model_dump(mode="json")
        if binding["task_id"] != status.binding.task_id:
            raise DomainError("INVALID_REFERENCE", 422)
        binding_digest = sha256(canonical_json_bytes(binding)).hexdigest()
        with self.uow.transaction(
            access, status.binding.task_id, capability="admit"
        ) as tx:
            config = AdmissionRegistry(None).config(tx)
            policy = getattr(config.runtime, "capture_policy", None)
            if policy is None:
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            policy_value = policy.model_dump(mode="json")
            policy_digest = sha256(canonical_json_bytes(policy_value)).hexdigest()
            existing = row(
                tx.connection.execute(
                    """SELECT * FROM vnext.capture_session WHERE tenant_id=%s
                    AND project_id=%s AND task_id=%s AND runtime_attempt=%s
                    """,
                    (*tx.owner, status.binding.runtime_attempt.root),
                )
            )
            if existing is not None:
                _lock_capture_session(tx, existing["capture_session_id"])
                existing = row(
                    tx.connection.execute(
                        """SELECT * FROM vnext.capture_session WHERE tenant_id=%s
                        AND project_id=%s AND task_id=%s AND capture_session_id=%s""",
                        (*tx.owner, existing["capture_session_id"]),
                    )
                )
            fixed = {
                "execution_epoch": int(status.binding.execution_epoch.root),
                "pod_uid": status.binding.pod_uid,
                "environment_ref": status.environment_ref,
                "controller_subject": access.principal.subject,
                "collector_subject": status.collector_ref,
                "evidence_origin": status.evidence_origin.value,
                "capture_layer": status.capture_layer,
                "binding_digest": binding_digest,
                "policy_digest": policy_digest,
            }
            if existing is not None:
                if any(existing[key] != value for key, value in fixed.items()) or (
                    strict_json_loads(existing["policy_json"]) != policy_value
                    or existing["started_at"] != status.started_at
                ):
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                if (
                    existing["state"] != status.state.value
                    or existing["status_digest"] != status.status_digest.root
                ):
                    tx.connection.execute(
                        """UPDATE vnext.capture_session SET state=%s,
                        status_digest=%s WHERE tenant_id=%s AND project_id=%s
                        AND task_id=%s AND capture_session_id=%s""",
                        (
                            status.state.value,
                            status.status_digest.root,
                            *tx.owner,
                            existing["capture_session_id"],
                        ),
                    )
                    existing.update(
                        state=status.state.value,
                        status_digest=status.status_digest.root,
                    )
                return _session_model(existing)
            capture_session_id = str(uuid4())
            tx.connection.execute(
                """INSERT INTO vnext.capture_session(tenant_id,project_id,task_id,
                capture_session_id,runtime_attempt,execution_epoch,pod_uid,
                environment_ref,controller_subject,collector_subject,evidence_origin,capture_layer,
                state,binding_digest,status_digest,policy_json,policy_digest,
                started_at,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    *tx.owner,
                    capture_session_id,
                    status.binding.runtime_attempt.root,
                    status.binding.execution_epoch.root,
                    status.binding.pod_uid,
                    status.environment_ref,
                    access.principal.subject,
                    status.collector_ref,
                    status.evidence_origin.value,
                    status.capture_layer,
                    status.state.value,
                    binding_digest,
                    status.status_digest.root,
                    json_text(policy_value),
                    policy_digest,
                    status.started_at,
                    tx.permissions["clearance"],
                ),
            )
            saved = row(
                tx.connection.execute(
                    "SELECT * FROM vnext.capture_session WHERE tenant_id=%s AND "
                    "project_id=%s AND task_id=%s AND capture_session_id=%s",
                    (*tx.owner, capture_session_id),
                )
            )
            return _session_model(saved)

    def _receipt(self, tx, item):
        artifacts = [
            BlobRef.model_validate(
                {"id": entity_id, "version": str(revision), "sha256": digest}
            )
            for entity_id, revision, digest in tx.connection.execute(
                """SELECT a.entity_id,a.revision,a.sha256
                FROM vnext.observation_artifact o JOIN vnext.artifact a ON
                  (a.tenant_id,a.project_id,a.task_id,a.entity_id,a.revision)=
                  (o.tenant_id,o.project_id,o.task_id,o.artifact_id,o.artifact_revision)
                WHERE o.tenant_id=%s AND o.project_id=%s AND o.task_id=%s
                  AND o.observation_id=%s AND o.observation_revision=%s
                ORDER BY o.ordinal""",
                (*tx.owner, item["observation_id"], item["observation_revision"]),
            ).fetchall()
        ]
        return wire.RuntimeCaptureReceiptV1.model_validate(
            {
                "schema_version": "wuji.runtime-capture-receipt.v1",
                "capture_session_id": item["capture_session_id"],
                "item_seq": item["item_seq"],
                "item_digest": item["item_digest"],
                "status": item["disposition"],
                "observation_ref": {
                    "entity_type": "observation",
                    "id": item["observation_id"],
                    "revision": str(item["observation_revision"]),
                },
                "artifact_refs": artifacts,
                "request_id": tx.access.request_id,
            }
        )

    def ingest_item(self, access, envelope, parts):
        require_runtime_collector(access)
        envelope = wire.RuntimeCaptureEnvelopeV1.model_validate(envelope)
        if (
            envelope.collector_ref != access.principal.subject
            or self._item_digest(envelope) != envelope.item_digest.root
            or len(canonical_json_bytes(envelope.metadata)) > MAX_METADATA_BYTES
            or len(canonical_json_bytes(envelope.model_dump(mode="json")))
            > MAX_ITEM_DOCUMENT_BYTES
            or not isinstance(parts, dict)
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        descriptors = {item.part: item for item in envelope.parts}
        if len(descriptors) != len(envelope.parts) or set(parts) != set(descriptors):
            raise DomainError("INVALID_SCHEMA", 422)
        if not parts:
            raise DomainError("INVALID_SCHEMA", 422)
        for name, value in parts.items():
            descriptor = descriptors[name]
            if not isinstance(value, bytes):
                raise DomainError("INVALID_SCHEMA", 422)
            if (
                len(value) != descriptor.length
                or sha256(value).hexdigest() != descriptor.sha256.root
            ):
                raise DomainError("INVALID_REFERENCE", 422)

        task_id = envelope.binding.task_id
        with self.uow.transaction(access, task_id, capability="evidence") as tx:
            session = bound_capture_session(tx, envelope.capture_session_id, lock=True)
            disposition = capture_session_disposition(tx, session)
            if (
                _binding(envelope.binding)
                != _session_model(session).binding.model_dump(mode="json")
                or envelope.collector_ref != session["collector_subject"]
            ):
                raise DomainError("INVALID_REFERENCE", 422)
            existing = row(
                tx.connection.execute(
                    """SELECT * FROM vnext.capture_item WHERE tenant_id=%s
                    AND project_id=%s AND task_id=%s AND capture_session_id=%s
                    AND item_seq=%s""",
                    (*tx.owner, envelope.capture_session_id, envelope.item_seq),
                )
            )
            if existing is not None:
                if existing["item_digest"] != envelope.item_digest.root:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                return self._receipt(tx, existing)
            policy = wire.CapturePolicyV1.model_validate(
                strict_json_loads(session["policy_json"])
            )
            if envelope.item_seq != int(session["ingested_items"]) + 1:
                raise DomainError("INVALID_REFERENCE", 422)
            if (
                envelope.item_seq > policy.max_items
                or int(session["ingested_items"]) >= policy.max_items
                or any(
                    len(value)
                    > (
                        policy.max_request_body_bytes
                        if name == "request_body"
                        else policy.max_response_body_bytes
                        if name == "response_body"
                        else min(self.artifacts.max_bytes, 67_108_864)
                        if envelope.kind.value == "pcap_segment"
                        else policy.pcap_segment_bytes
                    )
                    for name, value in parts.items()
                )
            ):
                raise DomainError("LIMIT_BLOCKED", 429)
            level = session["access_level"]

        refs = []
        for descriptor in envelope.parts:
            ref = self.artifacts.stage_runtime_capture(
                access,
                task_id,
                envelope.capture_session_id,
                parts[descriptor.part],
                descriptor.media_type,
                completeness=envelope.completeness.value,
                conditions=[item.root for item in envelope.conditions],
                access_level=level,
                lease_owner=_part_lease_owner(
                    envelope.item_seq, descriptor.part
                ),
            )
            self.artifacts.seal(access, task_id, ref)
            refs.append(ref)

        with self.uow.transaction(access, task_id, capability="evidence") as tx:
            session = bound_capture_session(tx, envelope.capture_session_id, lock=True)
            disposition = capture_session_disposition(tx, session)
            existing = row(
                tx.connection.execute(
                    """SELECT * FROM vnext.capture_item WHERE tenant_id=%s
                    AND project_id=%s AND task_id=%s AND capture_session_id=%s
                    AND item_seq=%s""",
                    (*tx.owner, envelope.capture_session_id, envelope.item_seq),
                )
            )
            if existing is not None:
                if existing["item_digest"] != envelope.item_digest.root:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                return self._receipt(tx, existing)
            policy = wire.CapturePolicyV1.model_validate(
                strict_json_loads(session["policy_json"])
            )
            if int(session["ingested_items"]) >= policy.max_items:
                raise DomainError("LIMIT_BLOCKED", 429)
            observation_id = str(uuid4())
            received_at = datetime.now(timezone.utc)
            observation = ObservationRecord.model_validate(
                {
                    "observation_id": observation_id,
                    "revision": "1",
                    "task_id": task_id,
                    "capture_id": (
                        envelope.capture_session_id + ":" + str(envelope.item_seq)
                    ),
                    "tool_attempt_id": None,
                    "capture_session_id": envelope.capture_session_id,
                    "capture_item_seq": envelope.item_seq,
                    "collector_ref": access.principal.subject,
                    "artifact_refs": refs,
                    "capture_layer": session["capture_layer"],
                    "observed_at": envelope.observed_at,
                    "received_at": received_at,
                    "environment_ref": session["environment_ref"],
                    "conditions": [item.root for item in envelope.conditions],
                    "completeness": envelope.completeness.value,
                    "evidence_origin": session["evidence_origin"],
                }
            )
            tx.connection.execute(
                """INSERT INTO vnext.observation(tenant_id,project_id,task_id,
                entity_id,revision,capture_id,tool_attempt_id,capture_session_id,
                capture_item_seq,collector_ref,capture_layer,observed_at,received_at,
                environment_ref,conditions_json,completeness,evidence_origin,
                access_level) VALUES(%s,%s,%s,%s,1,%s,NULL,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s)""",
                (
                    *tx.owner,
                    observation_id,
                    observation.capture_id,
                    envelope.capture_session_id,
                    envelope.item_seq,
                    access.principal.subject,
                    observation.capture_layer,
                    observation.observed_at,
                    received_at,
                    observation.environment_ref,
                    json_text([item.root for item in envelope.conditions]),
                    observation.completeness.value,
                    observation.evidence_origin.value,
                    level,
                ),
            )
            tx.connection.execute(
                """INSERT INTO vnext.capture_item(tenant_id,project_id,task_id,
                capture_session_id,item_seq,kind,completeness,disposition,item_digest,
                envelope_json,observation_id,observation_revision,observed_at,
                access_level) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s,%s)""",
                (
                    *tx.owner,
                    envelope.capture_session_id,
                    envelope.item_seq,
                    envelope.kind.value,
                    envelope.completeness.value,
                    disposition,
                    envelope.item_digest.root,
                    json_text(envelope.model_dump(mode="json")),
                    observation_id,
                    envelope.observed_at,
                    level,
                ),
            )
            tx.connection.execute(
                """INSERT INTO vnext.publication(tenant_id,project_id,task_id,
                publication_id,kind,access_level) VALUES(%s,%s,%s,%s,
                'observation',%s)""",
                (*tx.owner, observation_id, level),
            )
            for ordinal, ref in enumerate(refs):
                tx.connection.execute(
                    """INSERT INTO vnext.observation_artifact(tenant_id,project_id,
                    task_id,observation_id,observation_revision,ordinal,artifact_id,
                    artifact_revision,access_level) VALUES(%s,%s,%s,%s,1,%s,%s,%s,%s)""",
                    (*tx.owner, observation_id, ordinal, ref.id, ref.version.root, level),
                )
                tx.connection.execute(
                    """INSERT INTO vnext.publication_ref(tenant_id,project_id,
                    task_id,publication_id,artifact_id,artifact_revision,
                    access_level) VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                    (*tx.owner, observation_id, ref.id, ref.version.root, level),
                )
                tx.connection.execute(
                    """DELETE FROM vnext.artifact_lease WHERE tenant_id=%s
                    AND project_id=%s AND task_id=%s AND artifact_id=%s
                    AND artifact_revision=%s AND lease_owner=%s""",
                    (
                        *tx.owner,
                        ref.id,
                        ref.version.root,
                        _part_lease_owner(
                            envelope.item_seq, envelope.parts[ordinal].part
                        ),
                    ),
                )
            tx.semantic_event(
                "capture.item_ingested",
                {
                    "capture_session_id": envelope.capture_session_id,
                    "item_seq": str(envelope.item_seq),
                    "kind": envelope.kind.value,
                    "observation_ref": {
                        "entity_type": "observation",
                        "id": observation_id,
                        "revision": "1",
                    },
                },
                observations=1,
                access_level=level,
            )
            saved = row(
                tx.connection.execute(
                    """SELECT * FROM vnext.capture_item WHERE tenant_id=%s
                    AND project_id=%s AND task_id=%s AND capture_session_id=%s
                    AND item_seq=%s""",
                    (*tx.owner, envelope.capture_session_id, envelope.item_seq),
                )
            )
            return self._receipt(tx, saved)

    @staticmethod
    def _terminal_source(observation):
        value = observation.model_dump(
            mode="json",
            exclude={
                "source_digest",
                "observed_at",
                "controller_ref",
                "capture_session_id",
            },
        )
        return sha256(canonical_json_bytes(value)).hexdigest()

    def record_terminal_observation(self, access, observation):
        if "controller" not in access.principal.roles or "agent" in access.principal.roles:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        observation = wire.RuntimeTerminalObservationV1.model_validate(observation)
        if (
            observation.controller_ref != access.principal.subject
            or self._terminal_source(observation) != observation.source_digest.root
            or (
                observation.state.value == "not_started"
                and any(
                    value is not None
                    for value in (
                        observation.container_id,
                        observation.exit_code,
                        observation.signal,
                        observation.started_at,
                        observation.finished_at,
                    )
                )
            )
            or (
                observation.state.value == "terminated"
                and (
                    observation.exit_code is None
                    or observation.finished_at is None
                )
            )
        ):
            raise DomainError("INVALID_REFERENCE", 422)
        with self.uow.transaction(
            access, observation.binding.task_id, capability="control"
        ) as tx:
            if observation.capture_session_id is not None:
                session = row(
                    tx.connection.execute(
                        """SELECT * FROM vnext.capture_session WHERE tenant_id=%s
                        AND project_id=%s AND task_id=%s AND capture_session_id=%s""",
                        (*tx.owner, observation.capture_session_id),
                    )
                )
                if session is None or _binding(
                    observation.binding
                ) != _session_model(session).binding.model_dump(mode="json"):
                    raise DomainError("INVALID_REFERENCE", 422)
            existing = row(
                tx.connection.execute(
                    """SELECT * FROM vnext.runtime_terminal_observation WHERE
                    tenant_id=%s AND project_id=%s AND task_id=%s
                    AND runtime_attempt=%s AND pod_uid=%s AND container_name=%s""",
                    (
                        *tx.owner,
                        observation.binding.runtime_attempt.root,
                        observation.binding.pod_uid,
                        observation.container_name,
                    ),
                )
            )
            if existing is not None:
                if existing["source_digest"] != observation.source_digest.root:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                return wire.RuntimeTerminalObservationReceiptV1.model_validate(
                    {
                        "schema_version": "wuji.runtime-terminal-observation-receipt.v1",
                        "terminal_observation_id": existing["terminal_observation_id"],
                        "capture_session_id": existing["capture_session_id"],
                        "container_name": existing["container_name"],
                        "source_digest": existing["source_digest"],
                        "observed_at": existing["observed_at"],
                    }
                )
            terminal_id = str(uuid4())
            tx.connection.execute(
                """INSERT INTO vnext.runtime_terminal_observation(tenant_id,
                project_id,task_id,terminal_observation_id,capture_session_id,
                runtime_attempt,execution_epoch,pod_uid,container_name,source_digest,
                document_json,controller_subject,observed_at,access_level)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    *tx.owner,
                    terminal_id,
                    observation.capture_session_id,
                    observation.binding.runtime_attempt.root,
                    observation.binding.execution_epoch.root,
                    observation.binding.pod_uid,
                    observation.container_name,
                    observation.source_digest.root,
                    json_text(observation.model_dump(mode="json")),
                    access.principal.subject,
                    observation.observed_at,
                    tx.permissions["clearance"],
                ),
            )
            return wire.RuntimeTerminalObservationReceiptV1.model_validate(
                {
                    "schema_version": "wuji.runtime-terminal-observation-receipt.v1",
                    "terminal_observation_id": terminal_id,
                    "capture_session_id": observation.capture_session_id,
                    "container_name": observation.container_name,
                    "source_digest": observation.source_digest,
                    "observed_at": observation.observed_at,
                }
            )

    def list_sessions(self, access, task_id):
        with self.uow.transaction(access, task_id) as tx:
            values = [
                _session_model(row_value) for row_value in _rows(
                    tx.connection.execute(
                        """SELECT * FROM vnext.capture_session WHERE
                        tenant_id=%s AND project_id=%s AND task_id=%s
                        ORDER BY runtime_attempt DESC LIMIT 100""",
                        tx.owner,
                    )
                )
            ]
        return wire.RuntimeCaptureSessionPageV1.model_validate(
            {"schema_version": "wuji.runtime-capture-sessions.v1", "sessions": values}
        )

    def latest_contiguous_item_seq(self, access, task_id, capture_session_id):
        require_runtime_collector(access)
        with self.uow.transaction(access, task_id, capability="evidence") as tx:
            session = bound_capture_session(tx, capture_session_id)
            return int(session["ingested_items"])

    def terminal_container_states(
        self, access, task_id, *, runtime_attempt, execution_epoch, pod_uid
    ):
        with self.uow.transaction(access, task_id, capability="control") as tx:
            return terminal_container_states(
                tx, runtime_attempt=runtime_attempt,
                execution_epoch=execution_epoch, pod_uid=pod_uid,
            )

    def list_items(self, access, task_id, capture_session_id, *, after=0, limit=50):
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise DomainError("INVALID_SCHEMA", 422)
        with self.uow.transaction(access, task_id) as tx:
            session = row(
                tx.connection.execute(
                    """SELECT 1 FROM vnext.capture_session WHERE tenant_id=%s
                    AND project_id=%s AND task_id=%s AND capture_session_id=%s""",
                    (*tx.owner, capture_session_id),
                )
            )
            if session is None:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            items = []
            for item in _rows(
                tx.connection.execute(
                    """SELECT * FROM vnext.capture_item WHERE tenant_id=%s
                    AND project_id=%s AND task_id=%s AND capture_session_id=%s
                    AND item_seq>%s ORDER BY item_seq LIMIT %s""",
                    (*tx.owner, capture_session_id, after, limit + 1),
                )
            ):
                receipt = self._receipt(tx, item)
                items.append(
                    wire.RuntimeCaptureItemViewV1.model_validate(
                        {
                            "envelope": strict_json_loads(item["envelope_json"]),
                            "observation_ref": receipt.observation_ref,
                            "artifact_refs": receipt.artifact_refs,
                            "received_at": item["received_at"],
                        }
                    )
                )
        more = len(items) > limit
        page = items[:limit]
        return wire.RuntimeCaptureItemPageV1.model_validate(
            {
                "schema_version": "wuji.runtime-capture-items.v1",
                "capture_session_id": capture_session_id,
                "items": page,
                "next_item_seq": page[-1].envelope.item_seq if more else None,
            }
        )

    def read_part(
        self, access, task_id, capture_session_id, item_seq, part, *, max_bytes
    ):
        if (
            type(item_seq) is not int
            or not 1 <= item_seq <= 1_000_000
            or not isinstance(part, str)
            or not 1 <= len(part) <= 128
            or type(max_bytes) is not int
            or not 1 <= max_bytes <= 67_108_864
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        with self.uow.transaction(access, task_id) as tx:
            item = row(
                tx.connection.execute(
                    """SELECT * FROM vnext.capture_item WHERE tenant_id=%s
                    AND project_id=%s AND task_id=%s AND capture_session_id=%s
                    AND item_seq=%s""",
                    (*tx.owner, capture_session_id, item_seq),
                )
            )
            if item is None:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            envelope = wire.RuntimeCaptureEnvelopeV1.model_validate(
                strict_json_loads(item["envelope_json"])
            )
            names = [descriptor.part for descriptor in envelope.parts]
            if part not in names:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            ordinal = names.index(part)
            descriptor = envelope.parts[ordinal]
            value = tx.connection.execute(
                """SELECT a.* FROM vnext.observation_artifact o JOIN vnext.artifact a
                ON (a.tenant_id,a.project_id,a.task_id,a.entity_id,a.revision)=
                   (o.tenant_id,o.project_id,o.task_id,o.artifact_id,o.artifact_revision)
                WHERE o.tenant_id=%s AND o.project_id=%s AND o.task_id=%s
                  AND o.observation_id=%s AND o.observation_revision=%s
                  AND o.ordinal=%s""",
                (
                    *tx.owner,
                    item["observation_id"],
                    item["observation_revision"],
                    ordinal,
                ),
            )
            record = row(value)
            if record is None or record["size_bytes"] > max_bytes:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        data = self.artifacts.checked_bytes(record)
        return data, descriptor.media_type, "sha-256=" + descriptor_digest(data)


def descriptor_digest(data):
    import base64

    return base64.b64encode(sha256(data).digest()).decode("ascii")
