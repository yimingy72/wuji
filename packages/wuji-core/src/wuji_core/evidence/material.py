"""Current-authority artifact previews, reusing the model's exact renderer."""

from wuji_core.admission.model_material import (
    DEFAULT_SOURCE_BYTES,
    omitted_model_material,
    render_http_exchange_v2,
    render_runtime_http_part_v1,
)
from wuji_core.contracts import generated as wire
from wuji_core.contracts.envelopes import BlobRef
from wuji_core.http import strict_json_loads
from wuji_core.persistence.uow import DomainError, row


class ArtifactMaterialService:
    def __init__(self, artifacts):
        self.artifacts = artifacts

    def read(self, access, task_id, artifact_id, version):
        # Artifact and producing attempt are selected under current Task/RLS
        # clearance. This public reader never acquires a Run credential.
        with self.artifacts.uow.transaction(access, task_id) as tx:
            record = row(tx.connection.execute(
                "SELECT * FROM vnext.artifact WHERE tenant_id=%s AND project_id=%s "
                "AND task_id=%s AND entity_id=%s AND revision=%s",
                (*tx.owner, artifact_id, version),
            ))
            if record is None or record["state"] == "tombstoned":
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            if record.get("capture_session_id") is not None:
                return self._runtime_capture(tx, record, artifact_id, version)
            attempt = row(tx.connection.execute(
                "SELECT tool_call_id FROM vnext.tool_attempt WHERE tenant_id=%s "
                "AND project_id=%s AND task_id=%s AND tool_attempt_id=%s",
                (*tx.owner, record["tool_attempt_id"]),
            ))
            if attempt is None or not attempt["tool_call_id"]:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            call_id = attempt["tool_call_id"]
            if record["state"] != "sealed":
                return omitted_model_material(call_id, "source_not_sealed")
            if record["size_bytes"] > DEFAULT_SOURCE_BYTES:
                return omitted_model_material(call_id, "representation_limit")
            try:
                raw = self.artifacts.checked_bytes(record)
            except DomainError:
                return omitted_model_material(call_id, "source_unavailable")
            ref = BlobRef.model_validate({
                "id": artifact_id, "version": str(version), "sha256": record["sha256"],
            })
            return render_http_exchange_v2(
                call_id, artifact_ref=ref, artifact_record=record, raw=raw,
            )

    def _runtime_capture(self, tx, record, artifact_id, version):
        item = row(
            tx.connection.execute(
                """SELECT i.*,o.ordinal FROM vnext.observation_artifact o
                JOIN vnext.capture_item i ON
                  (i.tenant_id,i.project_id,i.task_id,i.observation_id,
                   i.observation_revision)=
                  (o.tenant_id,o.project_id,o.task_id,o.observation_id,
                   o.observation_revision)
                WHERE o.tenant_id=%s AND o.project_id=%s AND o.task_id=%s
                  AND o.artifact_id=%s AND o.artifact_revision=%s""",
                (*tx.owner, artifact_id, version),
            )
        )
        if item is None:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        envelope = wire.RuntimeCaptureEnvelopeV1.model_validate(
            strict_json_loads(item["envelope_json"])
        )
        if item["ordinal"] >= len(envelope.parts):
            raise DomainError("INVALID_REFERENCE", 422)
        descriptor = envelope.parts[item["ordinal"]]
        source_id = (
            "capture:"
            + item["capture_session_id"]
            + ":"
            + str(item["item_seq"])
            + ":"
            + descriptor.part
        )
        ref = BlobRef.model_validate(
            {"id": artifact_id, "version": str(version), "sha256": record["sha256"]}
        )
        source = {
            "artifact_ref": ref,
            "artifact_sha256": record["sha256"],
            "media_type": record["media_type"],
            "completeness": record["completeness"],
        }
        if item["kind"] != "http_exchange":
            return omitted_model_material(source_id, "unsupported_media", source=source)
        if record["state"] != "sealed":
            return omitted_model_material(source_id, "source_not_sealed", source=source)
        try:
            raw = self.artifacts.checked_bytes(record)
        except DomainError:
            return omitted_model_material(source_id, "source_unavailable")

        metadata_raw = None
        if descriptor.part in {"request_body", "response_body"}:
            metadata_part = descriptor.part.removesuffix("_body") + "_metadata"
            names = [part.part for part in envelope.parts]
            if metadata_part not in names:
                return omitted_model_material(source_id, "unsupported_schema", source=source)
            metadata_record = row(
                tx.connection.execute(
                    """SELECT a.* FROM vnext.observation_artifact o
                    JOIN vnext.artifact a ON
                      (a.tenant_id,a.project_id,a.task_id,a.entity_id,a.revision)=
                      (o.tenant_id,o.project_id,o.task_id,o.artifact_id,
                       o.artifact_revision)
                    WHERE o.tenant_id=%s AND o.project_id=%s AND o.task_id=%s
                      AND o.observation_id=%s AND o.observation_revision=%s
                      AND o.ordinal=%s""",
                    (
                        *tx.owner,
                        item["observation_id"],
                        item["observation_revision"],
                        names.index(metadata_part),
                    ),
                )
            )
            if metadata_record is None or metadata_record["state"] != "sealed":
                return omitted_model_material(source_id, "source_unavailable")
            try:
                metadata_raw = self.artifacts.checked_bytes(metadata_record)
            except DomainError:
                return omitted_model_material(source_id, "source_unavailable")
        return render_runtime_http_part_v1(
            source_id,
            part=descriptor.part,
            artifact_ref=ref,
            artifact_record=record,
            raw=raw,
            metadata_raw=metadata_raw,
        )
