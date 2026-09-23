"""Authorized fixed-snapshot knowledge listing, ranging and delivery receipts."""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from wuji_core.admission.model_material import (
    DEFAULT_SOURCE_BYTES,
    HTTP_EXCHANGE_MEDIA_TYPE,
    HTTP_RENDERER_VERSION,
    render_http_exchange_text_v1,
    render_text_artifact_v1,
)
from wuji_core.contracts import generated as wire
from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.snapshots import SnapshotQuery, SnapshotRepository
from wuji_core.persistence.uow import DomainError, json_text, row


RECORD_RENDERER = "wuji-record-renderer.v1"
TEXT_RENDERER = "wuji-text-renderer.v1"
REDACTION_POLICY = "wuji-redaction.v1"
WORKSPACE_BUNDLE_MEDIA_TYPE = "application/vnd.wuji.workspace-bundle+json"
COMMAND_LOG_MEDIA_TYPE = "application/vnd.wuji.command-log+json"
FIELD_WHITELISTS = {
    "claim": {"text", "limitations", "kind", "assertion_role", "basis_refs", "assessment"},
    "intent": {"question", "expected_output", "basis_refs", "acceptance_state", "planning"},
    "observation": {"capture_id", "completeness", "conditions", "observed_at", "environment_ref", "evidence_origin"},
    "artifact": {
        "media_type",
        "size_bytes",
        "completeness",
        "sha256",
        "state",
        "workspace_bundle_manifest",
    },
}


def _ref_key(ref):
    return ref.entity_type.value, ref.id, ref.revision.root


def _json_safe(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    return value


def _bounded_range(text, start, requested_end, maximum):
    if requested_end <= start:
        raise DomainError("INVALID_SCHEMA", 422)
    end = min(requested_end, len(text))
    low, high = start, end
    while low < high:
        candidate = (low + high + 1) // 2
        if len(text[start:candidate].encode("utf-8")) <= maximum:
            low = candidate
        else:
            high = candidate - 1
    return text[start:low], low


class KnowledgeReadService:
    def __init__(self, uow, *, ledger, artifacts, max_read_bytes=16 * 1024,
                 max_delivered_bytes=32 * 1024, max_reads=8, max_refreshes=2):
        if artifacts is None or not callable(getattr(artifacts, "checked_bytes", None)):
            raise ValueError("knowledge reads require the checked Artifact store")
        if any(type(value) is not int or value < 0 for value in (
            max_read_bytes, max_delivered_bytes, max_reads, max_refreshes
        )):
            raise ValueError("knowledge read limits must be fixed nonnegative integers")
        self.uow, self.ledger, self.artifacts = uow, ledger, artifacts
        self.snapshots = SnapshotRepository(uow)
        self.max_read_bytes = max_read_bytes
        self.max_delivered_bytes = max_delivered_bytes
        self.max_reads, self.max_refreshes = max_reads, max_refreshes

    def _limits(self, limits):
        if limits is None:
            return {
                "max_read_bytes": self.max_read_bytes,
                "max_delivered_bytes": self.max_delivered_bytes,
                "max_reads": self.max_reads,
                "max_refreshes": self.max_refreshes,
            }
        if not isinstance(limits, dict) or set(limits) != {
            "max_read_bytes", "max_delivered_bytes", "max_reads", "max_refreshes"
        }:
            raise DomainError("INVALID_SCHEMA", 422)
        if (
            any(type(value) is not int or value < 0 for value in limits.values())
            or not 1 <= limits["max_read_bytes"] <= 16_384
            or not 1 <= limits["max_delivered_bytes"] <= 1_048_576
            or limits["max_refreshes"] > 32
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        return limits

    @staticmethod
    def _cursor(snapshot_id, offset):
        digest = sha256(f"{snapshot_id}:{offset}".encode()).hexdigest()[:16]
        return f"knowledge:{offset}:{digest}"

    @classmethod
    def _offset(cls, snapshot_id, cursor):
        if cursor is None:
            return 0
        parts = cursor.split(":")
        if len(parts) != 3 or parts[0] != "knowledge" or not parts[1].isdecimal():
            raise DomainError("INVALID_REFERENCE", 422)
        offset = int(parts[1])
        if cls._cursor(snapshot_id, offset) != cursor:
            raise DomainError("INVALID_REFERENCE", 422)
        return offset

    def _record(self, tx, manifest, ref, raw):
        kind = ref.entity_type.value
        if kind in {"claim", "intent"}:
            record = self.ledger.read_in_transaction(tx, ref, manifest=manifest)
            payload = record.record.root.model_dump(mode="json")
            if kind == "claim":
                payload["assessment"] = (
                    None if record.assessment is None else record.assessment.model_dump(mode="json")
                )
            else:
                payload["planning"] = (
                    None if raw.get("planning_json") is None else strict_json_loads(raw["planning_json"])
                )
            return payload
        if kind == "observation":
            return {
                "capture_id": raw["capture_id"],
                "completeness": raw["completeness"],
                "conditions": strict_json_loads(raw["conditions_json"]),
                "observed_at": _json_safe(raw["observed_at"]),
                "environment_ref": raw["environment_ref"],
                "evidence_origin": raw["evidence_origin"],
            }
        result = {
            key: raw[key]
            for key in FIELD_WHITELISTS["artifact"]
            if key != "workspace_bundle_manifest"
        }
        if raw["media_type"] == WORKSPACE_BUNDLE_MEDIA_TYPE:
            if raw["state"] != "sealed":
                raise DomainError("INVALID_REFERENCE", 422)
            manifest = wire.WorkspaceBundleManifestV1.model_validate(
                strict_json_loads(self.artifacts.checked_bytes(raw))
            )
            result["workspace_bundle_manifest"] = manifest.model_dump(mode="json")
        else:
            result["workspace_bundle_manifest"] = None
        return result

    def _index(self, ref, raw):
        kind = ref.entity_type.value
        selectors = ["record_fields"]
        if (
            kind == "artifact"
            and raw["state"] == "sealed"
            and (
                raw["media_type"]
                in {HTTP_EXCHANGE_MEDIA_TYPE, COMMAND_LOG_MEDIA_TYPE}
                or raw["media_type"].startswith("text/")
            )
        ):
            selectors.append("text_range")
        return wire.KnowledgeIndexItemV1.model_validate({
            "ref": ref,
            "material_type": raw.get("media_type", kind),
            "disclosure": "metadata",
            "completeness": raw.get("completeness", "complete"),
            "available_selectors": selectors,
        })

    def list(self, access, assignment, *, snapshot_id, material_types=(), cursor=None, limit=10):
        if assignment.identity.task_id == "" or snapshot_id == "" or not 1 <= limit <= 20:
            raise DomainError("INVALID_SCHEMA", 422)
        allowed = {getattr(item, "value", item) for item in material_types}
        if not allowed <= {"artifact", "observation", "claim", "intent"}:
            raise DomainError("INVALID_SCHEMA", 422)
        with self.uow.transaction(access, assignment.identity.task_id) as tx:
            manifest = self.snapshots._get(tx, snapshot_id)
            refs = [ref for ref in manifest.refs if not allowed or ref.entity_type.value in allowed]
            offset = self._offset(snapshot_id, cursor)
            if offset > len(refs):
                raise DomainError("INVALID_REFERENCE", 422)
            page = refs[offset:offset + limit]
            items = [
                self._index(ref, self.snapshots.read_ref_in_transaction(tx, snapshot_id, ref))
                for ref in page
            ]
        next_offset = offset + len(page)
        return wire.KnowledgeListPageV1.model_validate({
            "schema_version": "wuji.knowledge-index.v1",
            "snapshot_id": snapshot_id,
            "items": items,
            "cursor": self._cursor(snapshot_id, next_offset) if next_offset < len(refs) else None,
        })

    def _identity(self, tx, assignment):
        binding = tx.run_binding
        if binding is None or binding.identity != assignment.identity:
            raise DomainError("STALE_EXECUTION", 409)
        work = row(tx.connection.execute(
            "SELECT session_id FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
            (*tx.owner, assignment.identity.work_item_id),
        ))
        if work is None:
            raise DomainError("STALE_EXECUTION", 409)
        return work

    def _persist(self, tx, assignment, *, native_occurrence, request, delivery, access_level,
                 idempotency_key=None, limits=None):
        self._identity(tx, assignment)
        request_digest = sha256(canonical_json_bytes(request)).hexdigest()
        suffix = native_occurrence if native_occurrence is not None else idempotency_key
        if not isinstance(suffix, str) or not suffix:
            raise DomainError("INVALID_SCHEMA", 422)
        key = assignment.identity.agent_run_id + ":" + suffix
        existing = row(tx.connection.execute(
            "SELECT * FROM vnext.knowledge_delivery WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND idempotency_key=%s",
            (*tx.owner, key),
        ))
        if existing:
            if existing["request_digest"] != request_digest:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            return wire.KnowledgeDeliveryV1.model_validate(strict_json_loads(existing["delivery_json"]))
        kind = delivery["kind"]
        limits = self._limits(limits)
        limit = limits["max_refreshes"] if kind == "refresh" else limits["max_reads"]
        count, delivered = tx.connection.execute(
            "SELECT count(*),COALESCE(sum((delivery_json::jsonb->>'byte_length')::integer),0) "
            "FROM vnext.knowledge_delivery WHERE tenant_id=%s AND project_id=%s AND task_id=%s "
            "AND work_item_id=%s AND kind=%s",
            (*tx.owner, assignment.identity.work_item_id, kind),
        ).fetchone()
        if (
            count >= limit
            or kind != "refresh"
            and delivered + delivery["byte_length"] > limits["max_delivered_bytes"]
        ):
            raise DomainError("LIMIT_BLOCKED", 429)
        checked = wire.KnowledgeDeliveryV1.model_validate(delivery)
        tx.connection.execute(
            """INSERT INTO vnext.knowledge_delivery(
            tenant_id,project_id,task_id,delivery_id,kind,work_item_id,agent_run_id,
            snapshot_id,session_id,native_occurrence,idempotency_key,request_digest,
            delivery_json,representation_digest,state,access_level)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'prepared',%s)""",
            (*tx.owner, checked.delivery_id, checked.kind.value,
             assignment.identity.work_item_id, assignment.identity.agent_run_id,
             checked.snapshot_id, checked.session_id, native_occurrence, key,
             request_digest, json_text(checked.model_dump(mode="json")),
             checked.representation_digest.root, access_level),
        )
        return checked

    def read(self, access, assignment, *, snapshot_id, ref, selector, native_occurrence,
             delivery_kind="knowledge_tool", idempotency_key=None, limits=None):
        limits = self._limits(limits)
        if delivery_kind not in {"knowledge_tool", "initial_context"}:
            raise DomainError("INVALID_SCHEMA", 422)
        if delivery_kind == "knowledge_tool" and not native_occurrence:
            raise DomainError("INVALID_SCHEMA", 422)
        if delivery_kind == "initial_context" and native_occurrence is not None:
            raise DomainError("INVALID_SCHEMA", 422)
        ref = KnowledgeRef.model_validate(ref)
        selector = wire.KnowledgeSelectorV1.model_validate(selector).root
        request = {
            "snapshot_id": snapshot_id,
            "ref": ref.model_dump(mode="json"),
            "selector": selector.model_dump(mode="json"),
        }
        with self.uow.transaction(
            access, assignment.identity.task_id, capability="model_output"
        ) as tx:
            manifest = self.snapshots._get(tx, snapshot_id)
            raw = self.snapshots.read_ref_in_transaction(tx, snapshot_id, ref)
            kind = ref.entity_type.value
            source_completeness = raw.get("completeness", "complete")
            renderer, redaction, truncated = RECORD_RENDERER, False, False
            if isinstance(selector, wire.RecordFieldsSelectorV1):
                requested = [item.root for item in selector.fields]
                if not requested or not set(requested) <= FIELD_WHITELISTS[kind]:
                    raise DomainError("INVALID_REFERENCE", 422)
                if (
                    "workspace_bundle_manifest" in requested
                    and raw.get("media_type") != WORKSPACE_BUNDLE_MEDIA_TYPE
                ):
                    raise DomainError("INVALID_REFERENCE", 422)
                complete = self._record(tx, manifest, ref, raw)
                source_digest = sha256(canonical_json_bytes(complete)).hexdigest()
                selected = {name: complete[name] for name in requested}
                text = canonical_json_bytes(selected).decode("utf-8")
                actual_selector = {"kind": "record_fields", "fields": requested}
                has_more = False
            else:
                if kind != "artifact" or raw["state"] != "sealed" or raw["size_bytes"] > DEFAULT_SOURCE_BYTES:
                    raise DomainError("UNSUPPORTED_MEDIA", 422)
                data = self.artifacts.checked_bytes(raw)
                if raw["media_type"] == HTTP_EXCHANGE_MEDIA_TYPE:
                    full = render_http_exchange_text_v1(
                        artifact_ref={"id": ref.id, "version": ref.revision.root, "sha256": raw["sha256"]},
                        artifact_record=raw,
                        raw=data,
                    )
                    if full.omission_reason is not None or full.text is None:
                        reason = full.omission_reason.value
                        code = (
                            "REPRESENTATION_LIMIT"
                            if reason in {"representation_limit", "capture_truncated"}
                            else "UNSUPPORTED_MEDIA"
                            if reason in {"unsupported_media", "unsupported_charset", "invalid_encoding"}
                            else "INVALID_REFERENCE"
                        )
                        raise DomainError(code, 422)
                    safe, redaction, renderer = full.text, full.redaction_applied, HTTP_RENDERER_VERSION
                elif raw["media_type"] == COMMAND_LOG_MEDIA_TYPE:
                    try:
                        command_log = strict_json_loads(data)
                    except (UnicodeDecodeError, ValueError, RecursionError):
                        raise DomainError("INVALID_REFERENCE", 422) from None
                    if (
                        not isinstance(command_log, dict)
                        or command_log.get("schema_version") != "wuji.command-log.v1"
                    ):
                        raise DomainError("INVALID_REFERENCE", 422)
                    safe, redaction = render_text_artifact_v1(
                        data, "text/plain; charset=utf-8"
                    )
                    renderer = TEXT_RENDERER
                else:
                    safe, redaction = render_text_artifact_v1(data, raw["media_type"])
                    renderer = TEXT_RENDERER
                source_digest = raw["sha256"]
                text, actual_end = _bounded_range(
                    safe, selector.start, selector.end, limits["max_read_bytes"]
                )
                actual_selector = {"kind": "text_range", "start": selector.start, "end": actual_end}
                has_more = actual_end < len(safe)
            encoded = text.encode("utf-8")
            representation_digest = sha256(encoded).hexdigest()
            work = self._identity(tx, assignment)
            delivery = {
                "schema_version": "wuji.knowledge-delivery.v1",
                "delivery_id": str(uuid4()),
                "kind": delivery_kind,
                "snapshot_id": snapshot_id,
                "ref": ref,
                "source_digest": source_digest,
                "selector": actual_selector,
                "renderer_version": renderer,
                "redaction_policy_ref": REDACTION_POLICY,
                "text": text,
                "representation_digest": representation_digest,
                "byte_length": len(encoded),
                "source_completeness": source_completeness,
                "representation_truncated": truncated,
                "has_more": has_more,
                "disclosure": "content",
                "state": "prepared",
                "work_item_id": assignment.identity.work_item_id,
                "agent_run_id": assignment.identity.agent_run_id,
                "session_id": work["session_id"],
                "native_occurrence": native_occurrence,
            }
            return self._persist(
                tx, assignment, native_occurrence=native_occurrence,
                request=request, delivery=delivery, access_level=raw["access_level"],
                idempotency_key=idempotency_key, limits=limits,
            )

    def refresh(self, access, assignment, *, snapshot_id, native_occurrence, limits=None):
        limits = self._limits(limits)
        old = self.snapshots.get(assignment.identity.task_id, access, snapshot_id)
        fresh = self.snapshots.create(
            assignment.identity.task_id,
            access,
            query=old.query,
        )
        old_refs = {_ref_key(ref): ref for ref in old.refs}
        fresh_refs = {_ref_key(ref): ref for ref in fresh.refs}
        added = [fresh_refs[key] for key in sorted(fresh_refs.keys() - old_refs.keys())]
        removed = [old_refs[key] for key in sorted(old_refs.keys() - fresh_refs.keys())]
        result = {
            "schema_version": "wuji.knowledge-refresh.v1",
            "previous_snapshot_id": snapshot_id,
            "snapshot_id": fresh.snapshot_id,
            "added_refs": [ref.model_dump(mode="json") for ref in added],
            "removed_refs": [ref.model_dump(mode="json") for ref in removed],
        }
        text = canonical_json_bytes(result).decode("utf-8")
        with self.uow.transaction(
            access, assignment.identity.task_id, capability="model_output"
        ) as tx:
            self._identity(tx, assignment)
            intent = row(tx.connection.execute(
                "SELECT intent_id,intent_revision FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
                (*tx.owner, assignment.identity.work_item_id),
            ))
            if intent is None or intent["intent_id"] is None:
                raise DomainError("INVALID_REFERENCE", 422)
            ref = KnowledgeRef.model_validate({
                "entity_type": "intent", "id": intent["intent_id"],
                "revision": str(intent["intent_revision"]),
            })
            digest = sha256(text.encode()).hexdigest()
            delivery = self._persist(tx, assignment, native_occurrence=native_occurrence,
                request=result, access_level=0, delivery={
                    "schema_version": "wuji.knowledge-delivery.v1",
                    "delivery_id": str(uuid4()), "kind": "refresh",
                    "snapshot_id": fresh.snapshot_id, "ref": ref,
                    "source_digest": digest,
                    "selector": {"kind": "record_fields", "fields": ["snapshot_delta"]},
                    "renderer_version": RECORD_RENDERER,
                    "redaction_policy_ref": REDACTION_POLICY,
                    "text": text, "representation_digest": digest,
                    "byte_length": len(text.encode()), "source_completeness": "complete",
                    "representation_truncated": False, "has_more": False,
                    "disclosure": "metadata", "state": "prepared",
                    "work_item_id": assignment.identity.work_item_id,
                    "agent_run_id": assignment.identity.agent_run_id,
                    "session_id": None, "native_occurrence": native_occurrence,
                }, limits=limits)
        return wire.KnowledgeRefreshResultV1.model_validate({
            **result, "delivery_id": delivery.delivery_id,
            "representation_digest": delivery.representation_digest,
        })

    def attach(
        self, access, assignment, *, deliveries, manifest_ref=None, channel=None
    ):
        expected = {
            item["delivery_id"]: item["representation_digest"]
            for item in deliveries
        }
        if len(expected) != len(deliveries):
            raise DomainError("INVALID_SCHEMA", 422)
        with self.uow.transaction(
            access, assignment.identity.task_id, capability="model_output"
        ) as tx:
            self._identity(tx, assignment)
            definition = strict_json_loads(tx.task["definition_json"])
            profile = definition["worker_profiles"][assignment.work_kind.value]
            native_v2 = (
                profile["body"].get("schema_version")
                == "wuji.harness.problem.v2"
                and profile["body"].get("session_codec")
                == "wuji.session.native.v2"
            )
            if native_v2:
                if manifest_ref is not None or channel not in {
                    "initial_input", "function_result"
                }:
                    raise DomainError("INVALID_SCHEMA", 422)
            elif channel is not None or manifest_ref is None:
                raise DomainError("INVALID_SCHEMA", 422)
            manifest = tx.connection.execute(
                "SELECT 1 FROM vnext.session_manifest WHERE tenant_id=%s AND project_id=%s AND task_id=%s "
                "AND work_item_id=%s AND owner_run_id=%s AND manifest_ref=%s",
                (*tx.owner, assignment.identity.work_item_id,
                 assignment.identity.agent_run_id, manifest_ref),
            ).fetchone() if not native_v2 else (1,)
            if manifest is None:
                raise DomainError("INVALID_REFERENCE", 422)
            rows = tx.connection.execute(
                "SELECT delivery_id,state,representation_digest,kind,native_occurrence FROM vnext.knowledge_delivery WHERE tenant_id=%s AND project_id=%s "
                "AND task_id=%s AND work_item_id=%s AND agent_run_id=%s AND delivery_id=ANY(%s) FOR UPDATE",
                (*tx.owner, assignment.identity.work_item_id,
                 assignment.identity.agent_run_id, list(expected)),
            ).fetchall()
            if (
                len(rows) != len(expected)
                or any(
                    state not in {"prepared", "attached", "returned_to_framework"}
                    or expected[delivery_id] != representation_digest
                    or (
                        native_v2
                        and (kind == "initial_context")
                        != (channel == "initial_input")
                    )
                    or (native_v2 and channel == "function_result" and not occurrence)
                    for delivery_id, state, representation_digest, kind, occurrence in rows
                )
            ):
                raise DomainError("INVALID_REFERENCE", 422)
            if native_v2:
                for delivery_id in sorted(expected):
                    handoff_id = "knowledge-handoff:" + sha256(
                        canonical_json_bytes({
                            "identity": assignment.identity.model_dump(mode="json"),
                            "delivery_id": delivery_id,
                            "representation_digest": expected[delivery_id],
                            "channel": channel,
                        })
                    ).hexdigest()
                    tx.connection.execute(
                        "UPDATE vnext.knowledge_delivery SET protocol_version='v2',"
                        "state='returned_to_framework',handoff_id=%s,handoff_channel=%s,"
                        "handoff_at=clock_timestamp() WHERE tenant_id=%s AND project_id=%s "
                        "AND task_id=%s AND work_item_id=%s AND agent_run_id=%s "
                        "AND delivery_id=%s AND state='prepared'",
                        (
                            handoff_id,
                            channel,
                            *tx.owner,
                            assignment.identity.work_item_id,
                            assignment.identity.agent_run_id,
                            delivery_id,
                        ),
                    )
                return {
                    "returned_to_framework": sorted(expected),
                    "channel": channel,
                }
            tx.connection.execute(
                "UPDATE vnext.knowledge_delivery SET state='attached',attached_manifest_ref=%s,attached_at=clock_timestamp() "
                "WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s AND agent_run_id=%s "
                "AND delivery_id=ANY(%s) AND state='prepared'",
                (manifest_ref, *tx.owner, assignment.identity.work_item_id,
                 assignment.identity.agent_run_id, list(expected)),
            )
        return {"attached": sorted(expected), "manifest_ref": manifest_ref}
