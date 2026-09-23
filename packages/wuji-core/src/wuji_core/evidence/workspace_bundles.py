"""Immutable workspace bundle publication, CAS updates and exact materialization."""

import asyncio
import base64
import binascii
from hashlib import sha256
from pathlib import PurePosixPath
from typing import Protocol
from uuid import uuid4

from wuji_core.admission.common import digest
from wuji_core.admission.tools import ToolPermit
from wuji_core.blackboard.knowledge_reads import KnowledgeReadService
from wuji_core.blackboard.notifications import _current_output
from wuji_core.blackboard.relations import operation, save_operation
from wuji_core.contracts import generated as wire
from wuji_core.contracts.envelopes import WorkerAssignment
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text, row


WORKSPACE_BUNDLE_MEDIA_TYPE = "application/vnd.wuji.workspace-bundle+json"
WORKSPACE_FILE_MEDIA_TYPE = "application/octet-stream"
WORKSPACE_RENDERER = "wuji-workspace-manifest-renderer.v1"
WORKSPACE_REDACTION = "wuji-redaction.v1"
MAX_MANIFEST_BYTES = 16 * 1024


PUBLISH_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "purpose",
        "files",
        "entrypoint",
        "inputs_description",
        "outputs_description",
        "dependencies",
        "validation_statement",
        "limitations",
        "expected_base_publication_id",
    ],
    "properties": {
        "purpose": {"type": "string", "minLength": 1, "maxLength": 2048},
        "files": {
            "type": "array",
            "minItems": 1,
            "maxItems": 32,
            "uniqueItems": True,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["relative_path"],
                "properties": {
                    "relative_path": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 256,
                        "pattern": "^[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$",
                    }
                },
            },
        },
        "entrypoint": {
            "type": "object",
            "additionalProperties": False,
            "required": ["relative_path", "interpreter_argv"],
            "properties": {
                "relative_path": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 256,
                    "pattern": "^[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$",
                },
                "interpreter_argv": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 16,
                    "items": {"type": "string", "minLength": 1, "maxLength": 256},
                },
            },
        },
        "inputs_description": {
            "type": "string",
            "minLength": 1,
            "maxLength": 2048,
        },
        "outputs_description": {
            "type": "string",
            "minLength": 1,
            "maxLength": 2048,
        },
        "dependencies": {
            "type": "array",
            "maxItems": 32,
            "uniqueItems": True,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["description", "lockfile_path"],
                "properties": {
                    "description": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 1024,
                    },
                    "lockfile_path": {
                        "anyOf": [
                            {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 256,
                                "pattern": "^[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$",
                            },
                            {"type": "null"},
                        ]
                    },
                },
            },
        },
        "validation_statement": {
            "type": "string",
            "minLength": 1,
            "maxLength": 2048,
        },
        "limitations": {
            "type": "array",
            "maxItems": 32,
            "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": 1024},
        },
        "expected_base_publication_id": {
            "anyOf": [
                {"type": "string", "minLength": 1, "maxLength": 256},
                {"type": "null"},
            ]
        },
    },
}

MATERIALIZE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["publication_id", "manifest_ref"],
    "properties": {
        "publication_id": {"type": "string", "minLength": 1, "maxLength": 256},
        "manifest_ref": {
            "type": "object",
            "additionalProperties": False,
            "required": ["id", "version", "sha256"],
            "properties": {
                "id": {"type": "string", "minLength": 1, "maxLength": 256},
                "version": {"type": "string", "pattern": "^(0|[1-9][0-9]*)$"},
                "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            },
        },
    },
}


class WorkspaceTransferPort(Protocol):
    async def export(
        self, permit: ToolPermit, request: wire.WorkspaceExportRequestV1
    ) -> wire.WorkspaceExportReplyV1: ...

    async def import_publication(
        self, permit: ToolPermit, request: wire.WorkspaceImportRequestV1
    ) -> wire.WorkspaceImportReplyV1: ...


def _scalar(value):
    return getattr(value, "root", value)


def _path(value):
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or "\\" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise DomainError("INVALID_SCHEMA", 422)
    return value


def _transfer_bytes(item):
    try:
        raw = base64.b64decode(item.data_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise DomainError("INVALID_REFERENCE", 422) from error
    if (
        base64.b64encode(raw).decode("ascii") != item.data_base64
        or len(raw) != item.byte_length
        or sha256(raw).hexdigest() != item.sha256.root
    ):
        raise DomainError("INVALID_REFERENCE", 422)
    return raw


class WorkspaceBundleService:
    def __init__(
        self,
        uow,
        *,
        registry,
        artifacts,
        knowledge_reads: KnowledgeReadService,
        transfer: WorkspaceTransferPort,
        max_total_bytes=32 * 1024 * 1024,
    ):
        if not all(
            callable(getattr(transfer, name, None))
            for name in ("export", "import_publication")
        ):
            raise TypeError("workspace transfer port is required")
        if type(max_total_bytes) is not int or not 1 <= max_total_bytes <= 64 * 1024 * 1024:
            raise ValueError("workspace transfer limit must be bounded")
        self.uow, self.registry, self.artifacts = uow, registry, artifacts
        self.knowledge_reads, self.transfer = knowledge_reads, transfer
        self.max_total_bytes = max_total_bytes

    @staticmethod
    def _operation(kind, permit):
        return f"workspace-{kind}:{permit.tool_attempt_id}"

    def replay(self, permit, name):
        if name not in {"workspace_publish", "workspace_materialize"}:
            raise DomainError("INVALID_REFERENCE", 422)
        model = (
            wire.WorkspacePublishResultV1
            if name == "workspace_publish"
            else wire.WorkspaceMaterializeResultV1
        )
        request_model = (
            wire.WorkspacePublishArgumentsV1
            if name == "workspace_publish"
            else wire.WorkspaceMaterializeArgumentsV1
        )
        arguments = request_model.model_validate(permit.arguments).model_dump(mode="json")
        with self.uow.transaction(permit.access, permit.identity.task_id) as tx:
            attempt = row(
                tx.connection.execute(
                    """SELECT a.permit_json,d.document_json AS definition_json
                    FROM vnext.tool_attempt a
                    JOIN vnext.tool_call c
                      USING(tenant_id,project_id,task_id,tool_call_id)
                    JOIN vnext.tool_definition d
                      ON d.tenant_id=a.tenant_id AND d.ref=c.tool_definition_version
                    WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s
                      AND a.tool_attempt_id=%s AND a.agent_run_id=%s""",
                    (
                        *tx.owner,
                        permit.tool_attempt_id,
                        permit.identity.agent_run_id,
                    ),
                )
            )
            definition = (
                None
                if attempt is None
                else strict_json_loads(attempt["definition_json"])
            )
            if (
                attempt is None
                or strict_json_loads(attempt["permit_json"]).get(
                    "arguments_digest"
                )
                != permit.arguments_digest
                or digest(strict_json_loads(attempt["permit_json"]))
                != digest(permit.stored())
                or definition.get("name") != name
                or definition.get("allowed_target_kinds") != ["workspace_bundle"]
            ):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            _input_digest, saved = operation(
                tx,
                name,
                self._operation(name.removeprefix("workspace_"), permit),
                arguments,
            )
            return None if saved is None else model.model_validate(saved)

    def _current(self, tx, permit, assignment, *, tool_name):
        assignment = WorkerAssignment.model_validate(assignment)
        if (
            not isinstance(permit, ToolPermit)
            or permit.tool_attempt_id is None
            or tx.run_binding is None
            or tx.run_binding.identity != permit.identity
            or assignment.identity != permit.identity
        ):
            raise DomainError("STALE_EXECUTION", 409)
        run, work = _current_output(tx, assignment, self.registry)
        attempt = row(
            tx.connection.execute(
                """SELECT a.*,c.tool_definition_version,
                d.document_json AS definition_json
                FROM vnext.tool_attempt a JOIN vnext.tool_call c
                  USING(tenant_id,project_id,task_id,tool_call_id)
                JOIN vnext.tool_definition d
                  ON d.tenant_id=a.tenant_id AND d.ref=c.tool_definition_version
                WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s
                  AND a.tool_attempt_id=%s AND a.agent_run_id=%s""",
                (
                    *tx.owner,
                    permit.tool_attempt_id,
                    permit.identity.agent_run_id,
                ),
            )
        )
        definition = (
            None
            if attempt is None
            else strict_json_loads(attempt["definition_json"])
        )
        if (
            attempt is None
            or attempt["tool_call_id"] != permit.tool_call_id
            or attempt["tool_definition_version"] != permit.tool_definition_ref
            or strict_json_loads(attempt["permit_json"]).get(
                "arguments_digest"
            )
            != permit.arguments_digest
            or digest(strict_json_loads(attempt["permit_json"]))
            != digest(permit.stored())
            or attempt["status"]
            not in {"admitted", "dispatched", "running", "evidence_pending"}
            or definition.get("name") != tool_name
            or definition.get("allowed_target_kinds") != ["workspace_bundle"]
            or work["kind"] != "explore"
        ):
            raise DomainError("STALE_EXECUTION", 409)
        return assignment, attempt, work, run

    @staticmethod
    def _head(tx, asset_id):
        value = tx.connection.execute(
            "SELECT publication_id,accessible FROM vnext.workspace_bundle_head(%s)",
            (asset_id,),
        ).fetchone()
        if value is None:
            return None, True
        return value[0], value[1]

    @staticmethod
    def _base(tx, publication_id):
        return row(
            tx.connection.execute(
                "SELECT * FROM vnext.publication WHERE tenant_id=%s AND project_id=%s "
                "AND task_id=%s AND publication_id=%s AND kind='workspace_bundle.v1'",
                (*tx.owner, publication_id),
            )
        )

    @staticmethod
    def _conflict(status, current=None):
        return wire.WorkspacePublishResultV1.model_validate(
            {
                "schema_version": "wuji.workspace-publish-result.v1",
                "status": status,
                "publication_id": None,
                "manifest_ref": None,
                "asset_id": None,
                "asset_revision": None,
                "parent_publication_id": None,
                "current_publication_id": current,
                "delivery": None,
            }
        )

    async def publish(self, permit, arguments, assignment):
        arguments = wire.WorkspacePublishArgumentsV1.model_validate(arguments)
        file_paths = [item.relative_path for item in arguments.files]
        for value in file_paths:
            _path(value)
        if len(set(file_paths)) != len(file_paths):
            raise DomainError("INVALID_SCHEMA", 422)
        _path(arguments.entrypoint.relative_path)
        if arguments.entrypoint.relative_path not in file_paths:
            raise DomainError("INVALID_REFERENCE", 422)
        for item in arguments.dependencies:
            if item.lockfile_path is not None:
                _path(item.lockfile_path)
                if item.lockfile_path not in file_paths:
                    raise DomainError("INVALID_REFERENCE", 422)

        request = arguments.model_dump(mode="json")
        key = self._operation("publish", permit)
        with self.uow.transaction(
            permit.access, permit.identity.task_id, capability="model_output"
        ) as tx:
            assignment, _attempt, _work, _run = self._current(
                tx, permit, assignment, tool_name="workspace_publish"
            )
            operation_digest, saved = operation(
                tx, "workspace_publish", key, request
            )
            if saved is not None:
                return wire.WorkspacePublishResultV1.model_validate(saved)
            access_level = tx.permissions["clearance"]

        exported = wire.WorkspaceExportReplyV1.model_validate(
            await self.transfer.export(
                permit,
                wire.WorkspaceExportRequestV1(files=arguments.files),
            )
        )
        exported_paths = [item.relative_path for item in exported.files]
        if exported_paths != file_paths or len(set(exported_paths)) != len(exported_paths):
            raise DomainError("INVALID_REFERENCE", 422)
        source_files = []
        total = 0
        for item in exported.files:
            raw = _transfer_bytes(item)
            total += len(raw)
            if total > self.max_total_bytes:
                raise DomainError("LIMIT_BLOCKED", 429)
            source_files.append((item.relative_path, raw, item.sha256.root))

        refs = []
        for relative_path, raw, file_digest in source_files:
            ref = await asyncio.to_thread(
                self.artifacts.stage_model_output,
                permit.access,
                permit.identity.task_id,
                permit.identity.agent_run_id,
                raw,
                WORKSPACE_FILE_MEDIA_TYPE,
                access_level=access_level,
            )
            if ref.sha256.root != file_digest:
                raise DomainError("INVALID_REFERENCE", 422)
            await asyncio.to_thread(
                self.artifacts.seal,
                permit.access,
                permit.identity.task_id,
                ref,
            )
            refs.append((relative_path, ref, len(raw)))

        expected = (
            None if arguments.expected_base_publication_id is None
            else arguments.expected_base_publication_id.root
        )
        with self.uow.transaction(
            permit.access, permit.identity.task_id, capability="model_output"
        ) as tx:
            assignment, _attempt, _work, run = self._current(
                tx, permit, assignment, tool_name="workspace_publish"
            )
            base = None if expected is None else self._base(tx, expected)
            if expected is not None and base is None:
                result = self._conflict("head_unavailable")
                save_operation(
                    tx,
                    "workspace_publish",
                    key,
                    operation_digest,
                    result.model_dump(mode="json"),
                    access_level,
                )
                return result
            if base is None:
                asset_id, asset_revision, parent, parent_level = (
                    str(uuid4()),
                    1,
                    None,
                    0,
                )
            else:
                head, accessible = self._head(tx, base["asset_id"])
                if not accessible:
                    result = self._conflict("head_unavailable")
                    save_operation(
                        tx,
                        "workspace_publish",
                        key,
                        operation_digest,
                        result.model_dump(mode="json"),
                        access_level,
                    )
                    return result
                if head != expected:
                    result = self._conflict("publication_conflict", head)
                    save_operation(
                        tx,
                        "workspace_publish",
                        key,
                        operation_digest,
                        result.model_dump(mode="json"),
                        max(access_level, base["access_level"]),
                    )
                    return result
                asset_id = base["asset_id"]
                asset_revision = int(base["asset_revision"]) + 1
                parent = expected
                parent_level = base["access_level"]
            if exported.environment_ref != run["environment_ref"]:
                raise DomainError("INVALID_REFERENCE", 422)

        level = max(access_level, parent_level)
        manifest = wire.WorkspaceBundleManifestV1.model_validate(
            {
                "schema_version": "wuji.workspace-bundle.v1",
                "asset_id": asset_id,
                "asset_revision": str(asset_revision),
                "parent_publication_id": parent,
                "purpose": arguments.purpose,
                "producer_work_ref": permit.identity.work_item_id,
                "environment_ref": exported.environment_ref,
                "image_digest": exported.image_digest,
                "files": [
                    {
                        "relative_path": relative_path,
                        "ref": ref,
                        "sha256": ref.sha256,
                        "bytes": byte_length,
                    }
                    for relative_path, ref, byte_length in refs
                ],
                "entrypoint": arguments.entrypoint,
                "inputs_description": arguments.inputs_description,
                "outputs_description": arguments.outputs_description,
                "dependencies": arguments.dependencies,
                "validation_statement": {
                    "author_report": arguments.validation_statement,
                    "platform_checks": [
                        "source_fd_stable",
                        "sealed_sha256_verified",
                        "publication_membership_committed",
                    ],
                },
                "limitations": arguments.limitations,
            }
        )
        manifest_bytes = canonical_json_bytes(manifest.model_dump(mode="json"))
        if len(manifest_bytes) > MAX_MANIFEST_BYTES:
            raise DomainError("REPRESENTATION_LIMIT", 422)
        manifest_ref = await asyncio.to_thread(
            self.artifacts.stage_model_output,
            permit.access,
            permit.identity.task_id,
            permit.identity.agent_run_id,
            manifest_bytes,
            WORKSPACE_BUNDLE_MEDIA_TYPE,
            access_level=level,
        )
        await asyncio.to_thread(
            self.artifacts.seal,
            permit.access,
            permit.identity.task_id,
            manifest_ref,
        )

        publication_id = str(uuid4())
        with self.uow.transaction(
            permit.access, permit.identity.task_id, capability="model_output"
        ) as tx:
            assignment, _attempt, work, _run = self._current(
                tx, permit, assignment, tool_name="workspace_publish"
            )
            _digest, saved = operation(tx, "workspace_publish", key, request)
            if saved is not None:
                return wire.WorkspacePublishResultV1.model_validate(saved)
            if expected is not None:
                current, accessible = self._head(tx, asset_id)
                if not accessible:
                    result = self._conflict("head_unavailable")
                    save_operation(
                        tx,
                        "workspace_publish",
                        key,
                        operation_digest,
                        result.model_dump(mode="json"),
                        level,
                    )
                    return result
                if current != expected:
                    result = self._conflict("publication_conflict", current)
                    save_operation(
                        tx,
                        "workspace_publish",
                        key,
                        operation_digest,
                        result.model_dump(mode="json"),
                        level,
                    )
                    return result
            tx.connection.execute(
                """INSERT INTO vnext.publication(
                tenant_id,project_id,task_id,publication_id,kind,access_level,
                source_tool_attempt_id,manifest_artifact_id,
                manifest_artifact_revision,asset_id,asset_revision,
                parent_publication_id)
                VALUES(%s,%s,%s,%s,'workspace_bundle.v1',%s,%s,%s,%s,%s,%s,%s)""",
                (
                    *tx.owner,
                    publication_id,
                    level,
                    permit.tool_attempt_id,
                    manifest_ref.id,
                    manifest_ref.version.root,
                    asset_id,
                    asset_revision,
                    parent,
                ),
            )
            members = [manifest_ref, *(ref for _path_value, ref, _size in refs)]
            for ref in members:
                tx.connection.execute(
                    """INSERT INTO vnext.publication_ref(
                    tenant_id,project_id,task_id,publication_id,artifact_id,
                    artifact_revision,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        *tx.owner,
                        publication_id,
                        ref.id,
                        ref.version.root,
                        level,
                    ),
                )
            occurrence = "workspace-publish:" + permit.tool_call_id
            knowledge_ref = {
                "entity_type": "artifact",
                "id": manifest_ref.id,
                "revision": manifest_ref.version.root,
            }
            delivery = self.knowledge_reads._persist(
                tx,
                assignment,
                native_occurrence=occurrence,
                request={
                    "publication_id": publication_id,
                    "manifest_ref": manifest_ref.model_dump(mode="json"),
                },
                access_level=level,
                delivery={
                    "schema_version": "wuji.knowledge-delivery.v1",
                    "delivery_id": str(uuid4()),
                    "kind": "environment_material",
                    "snapshot_id": assignment.snapshot_id,
                    "ref": knowledge_ref,
                    "source_digest": manifest_ref.sha256.root,
                    "selector": {
                        "kind": "record_fields",
                        "fields": ["workspace_bundle_manifest"],
                    },
                    "renderer_version": WORKSPACE_RENDERER,
                    "redaction_policy_ref": WORKSPACE_REDACTION,
                    "text": manifest_bytes.decode("utf-8"),
                    "representation_digest": manifest_ref.sha256.root,
                    "byte_length": len(manifest_bytes),
                    "source_completeness": "complete",
                    "representation_truncated": False,
                    "has_more": False,
                    "disclosure": "content",
                    "state": "prepared",
                    "work_item_id": work["work_item_id"],
                    "agent_run_id": permit.identity.agent_run_id,
                    "session_id": work["session_id"],
                    "native_occurrence": occurrence,
                },
            )
            result = wire.WorkspacePublishResultV1.model_validate(
                {
                    "schema_version": "wuji.workspace-publish-result.v1",
                    "status": "published",
                    "publication_id": publication_id,
                    "manifest_ref": manifest_ref,
                    "asset_id": asset_id,
                    "asset_revision": str(asset_revision),
                    "parent_publication_id": parent,
                    "current_publication_id": publication_id,
                    "delivery": delivery,
                }
            )
            save_operation(
                tx,
                "workspace_publish",
                key,
                operation_digest,
                result.model_dump(mode="json"),
                level,
            )
            tx.semantic_event(
                "workspace.published",
                {
                    "publication_id": publication_id,
                    "asset_id": asset_id,
                    "asset_revision": str(asset_revision),
                    "parent_publication_id": parent,
                    "manifest_ref": manifest_ref.model_dump(mode="json"),
                    "producer_work_ref": work["work_item_id"],
                    "producer_run_ref": permit.identity.agent_run_id,
                },
                access_level=level,
            )
            return result

    async def materialize(self, permit, arguments, assignment):
        arguments = wire.WorkspaceMaterializeArgumentsV1.model_validate(arguments)
        request = arguments.model_dump(mode="json")
        key = self._operation("materialize", permit)
        with self.uow.transaction(
            permit.access, permit.identity.task_id, capability="model_output"
        ) as tx:
            assignment, _attempt, _work, _run = self._current(
                tx, permit, assignment, tool_name="workspace_materialize"
            )
            operation_digest, saved = operation(
                tx, "workspace_materialize", key, request
            )
            if saved is not None:
                return wire.WorkspaceMaterializeResultV1.model_validate(saved)
            publication = row(
                tx.connection.execute(
                    """SELECT * FROM vnext.publication WHERE tenant_id=%s
                    AND project_id=%s AND task_id=%s AND publication_id=%s
                    AND kind='workspace_bundle.v1'""",
                    (*tx.owner, arguments.publication_id),
                )
            )
            manifest_ref = arguments.manifest_ref
            if (
                publication is None
                or publication["manifest_artifact_id"] != manifest_ref.id
                or str(publication["manifest_artifact_revision"])
                != manifest_ref.version.root
                or tx.connection.execute(
                    "SELECT 1 FROM vnext.snapshot_ref WHERE tenant_id=%s "
                    "AND project_id=%s AND task_id=%s AND snapshot_id=%s "
                    "AND entity_type='artifact' AND entity_id=%s AND revision=%s",
                    (
                        *tx.owner,
                        assignment.snapshot_id,
                        manifest_ref.id,
                        manifest_ref.version.root,
                    ),
                ).fetchone()
                is None
            ):
                raise DomainError("INVALID_REFERENCE", 422)
            manifest_record = self.artifacts.record(tx, manifest_ref)
            member_cursor = tx.connection.execute(
                """SELECT a.* FROM vnext.publication_ref p JOIN vnext.artifact a
                ON (a.tenant_id,a.project_id,a.task_id,a.entity_id,a.revision)=
                   (p.tenant_id,p.project_id,p.task_id,p.artifact_id,
                    p.artifact_revision)
                WHERE p.tenant_id=%s AND p.project_id=%s AND p.task_id=%s
                  AND p.publication_id=%s""",
                (*tx.owner, arguments.publication_id),
            )
            names = [column.name for column in member_cursor.description]
            members = {
                (record["entity_id"], str(record["revision"])): record
                for record in (
                    dict(zip(names, value)) for value in member_cursor.fetchall()
                )
            }

        manifest_bytes = self.artifacts.checked_bytes(manifest_record)
        if sha256(manifest_bytes).hexdigest() != manifest_ref.sha256.root:
            raise DomainError("INVALID_REFERENCE", 422)
        manifest = wire.WorkspaceBundleManifestV1.model_validate(
            strict_json_loads(manifest_bytes)
        )
        if (
            manifest.asset_id != publication["asset_id"]
            or manifest.asset_revision.root != str(publication["asset_revision"])
            or manifest.parent_publication_id != publication["parent_publication_id"]
        ):
            raise DomainError("INVALID_REFERENCE", 422)
        transfer_files = []
        total = 0
        for item in manifest.files:
            record = members.get((item.ref.id, item.ref.version.root))
            if record is None or record["state"] != "sealed":
                raise DomainError("INVALID_REFERENCE", 422)
            raw = self.artifacts.checked_bytes(record)
            total += len(raw)
            if (
                total > self.max_total_bytes
                or len(raw) != item.bytes
                or sha256(raw).hexdigest() != item.sha256.root
                or item.ref.sha256 != item.sha256
            ):
                raise DomainError("INVALID_REFERENCE", 422)
            transfer_files.append(
                {
                    "relative_path": item.relative_path,
                    "data_base64": base64.b64encode(raw).decode("ascii"),
                    "byte_length": len(raw),
                    "sha256": item.sha256,
                }
            )
        imported = wire.WorkspaceImportReplyV1.model_validate(
            await self.transfer.import_publication(
                permit,
                wire.WorkspaceImportRequestV1(
                    publication_id=arguments.publication_id,
                    manifest_digest=manifest_ref.sha256,
                    files=transfer_files,
                ),
            )
        )
        actual = {
            item.relative_path: (item.sha256.root, item.byte_length)
            for item in imported.files
        }
        expected_files = {
            item.relative_path: (item.sha256.root, item.bytes)
            for item in manifest.files
        }
        if actual != expected_files:
            raise DomainError("INVALID_REFERENCE", 422)
        result = wire.WorkspaceMaterializeResultV1.model_validate(
            {
                "schema_version": "wuji.workspace-materialize-result.v1",
                "publication_id": arguments.publication_id,
                "manifest_ref": manifest_ref,
                "source_assurance": "platform_sealed",
                "destination_assurance": "executor_reported",
                "imports_root": imported.imports_root,
                "files": imported.files,
            }
        )
        with self.uow.transaction(
            permit.access, permit.identity.task_id, capability="model_output"
        ) as tx:
            _assignment, _attempt, _work, _run = self._current(
                tx, permit, assignment, tool_name="workspace_materialize"
            )
            _digest, saved = operation(tx, "workspace_materialize", key, request)
            if saved is not None:
                return wire.WorkspaceMaterializeResultV1.model_validate(saved)
            save_operation(
                tx,
                "workspace_materialize",
                key,
                operation_digest,
                result.model_dump(mode="json"),
                publication["access_level"],
            )
        return result
