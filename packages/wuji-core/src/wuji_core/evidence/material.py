"""Current-authority artifact previews, reusing the model's exact renderer."""

from wuji_core.admission.model_material import (
    DEFAULT_SOURCE_BYTES,
    omitted_model_material,
    render_http_exchange_v2,
)
from wuji_core.contracts.envelopes import BlobRef
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
