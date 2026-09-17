"""P16 delivery: a frozen report delivered under one declared media profile.

Real PostgreSQL, the real completion services and the signed HTTP boundary.
Nothing here lets a caller decide that a delivery is complete: the platform
indexes the frozen bytes and the sealed artifacts, and both the service and the
database refuse a ``ready`` delivery that still misses required material.
"""

from __future__ import annotations

from hashlib import sha256
import json
from uuid import uuid4

import psycopg
import pytest

from support.http_capture import RecordedTestClient
from support.p03 import access
from test_completion_portal import portal, ready_goal
from test_completion_protocol import ASSESSOR, WORKER
from test_work_state_guards import OPERATOR, OWNER, TASK, control_case
from wuji_core.audit.delivery import (
    PROFILE_SCHEMA,
    REPORT_MEDIA_TYPE,
    ReportDeliveryService,
)
from wuji_core.audit.retention import RetentionService
from wuji_core.completion.reports import ReportService
from wuji_core.http import create_app
from wuji_core.http.delivery import create_delivery_router
from wuji_core.http.retention import create_retention_router
from wuji_core.persistence.uow import DomainError

PNG = b"\x89PNG\r\n\x1a\nfixture-screenshot-bytes"


def profile(*requirements, profile_id="offline-document-v1", mode="offline"):
    return {
        "schema_version": PROFILE_SCHEMA,
        "profile_id": profile_id,
        "mode": mode,
        "requirements": list(requirements),
    }


def body_requirement():
    return {
        "role": "report_body",
        "media_type": REPORT_MEDIA_TYPE,
        "min_count": 1,
        "required": True,
    }


def screenshot_requirement(*, required=True, min_count=1):
    return {
        "role": "screenshot",
        "media_type": "image/*",
        "min_count": min_count,
        "required": required,
    }


def canonical_sha256(document) -> str:
    return sha256(
        json.dumps(document, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()


def service(case) -> ReportDeliveryService:
    return ReportDeliveryService(case.uow)


def closed_report(case, *, key="p16"):
    """Close the Task through the real product entry and return its report."""

    entry = portal(case)
    entry.submit(
        OPERATOR, TASK, action="quiesce", close_trigger="goal_satisfied",
        result_outcome="complete", idempotency_key=f"{key}-quiesce",
    )
    closed = entry.submit(
        OPERATOR, TASK, action="close", close_trigger="goal_satisfied",
        result_outcome="complete", idempotency_key=f"{key}-close",
    )
    return closed.report


def staged_image(case, body=PNG):
    return case.store.stage_model_output(
        WORKER, TASK, "run-fixture", body, "image/png", access_level=1
    )


def rows(case):
    with case.env.migration_connection() as connection:
        return connection.execute(
            "SELECT delivery_id,state,mode,profile_id,profile_digest,manifest_digest,"
            "exchange_json,error_code,report_digest FROM vnext.report_delivery"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s ORDER BY created_at,delivery_id",
            OWNER,
        ).fetchall()


def test_an_offline_document_delivery_records_what_the_frozen_report_contains(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        report = closed_report(case)
        receipt = service(case).deliver(
            OPERATOR, TASK, report_key=report["report_id"],
            delivery_key="delivery-offline", profile=profile(body_requirement()),
        )
        document = receipt.document
        assert document["state"] == "ready"
        assert document["mode"] == "offline"
        assert document["missing"] == []
        assert document["exchange"] is None
        assert document["report_digest"] == report["body_digest"]
        assert document["profile_digest"] == canonical_sha256(document["profile"])
        manifest = document["manifest"]
        assert manifest["report_digest"] == report["body_digest"]
        assert manifest["state"] == "ready"
        assert [item["source"] for item in manifest["materials"]] == ["report_commit"]
        assert [item["role"] for item in manifest["requirements"]] == ["report_body"]
        assert manifest["requirements"][0]["present_count"] == 1
        assert manifest["materials"][0]["sha256"] == report["body_digest"]
        assert document["manifest_digest"] == canonical_sha256(manifest)
        stored = rows(case)
        assert len(stored) == 1
        assert stored[0][:4] == ("delivery-offline", "ready", "offline", "offline-document-v1")
        assert stored[0][6] is None, "an offline delivery stores no HTTP exchange"
        assert stored[0][8] == report["body_digest"]


def test_a_required_screenshot_is_incomplete_until_the_real_material_is_sealed(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        staged = staged_image(case)
        report = closed_report(case)
        declared = profile(body_requirement(), screenshot_requirement())
        deliveries = service(case)

        first = deliveries.deliver(
            OPERATOR, TASK, report_key=report["report_id"],
            delivery_key="delivery-before-seal", profile=declared,
        )
        assert first.state == "incomplete"
        assert first.document["missing"] == [
            {
                "role": "screenshot",
                "media_type": "image/*",
                "min_count": 1,
                "present_count": 0,
                "missing_count": 1,
                "required": True,
            }
        ]

        # A staged object is not evidence yet: only sealed bytes are indexed.
        case.store.seal(WORKER, TASK, staged)
        second = deliveries.deliver(
            OPERATOR, TASK, report_key=report["report_id"],
            delivery_key="delivery-after-seal", profile=declared,
        )
        assert second.state == "ready"
        assert second.document["missing"] == []
        indexed = [
            item
            for item in second.document["manifest"]["materials"]
            if item["source"] == "artifact"
        ]
        assert [item["source_ref"] for item in indexed] == [f"{staged.id}@{staged.version.root}"]
        assert indexed[0]["sha256"] == sha256(PNG).hexdigest()
        assert indexed[0]["media_type"] == "image/png"
        # The earlier decision is untouched: a later seal never rewrites it.
        stored = dict((row[0], row) for row in rows(case))
        assert stored["delivery-before-seal"][1] == "incomplete"
        assert stored["delivery-after-seal"][1] == "ready"


def test_an_optional_requirement_never_blocks_an_offline_document(
    db_environment, tmp_path, audit_directory
):
    """AC-069: a screenshot is enforced only when the profile requires it."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        report = closed_report(case)
        receipt = service(case).deliver(
            OPERATOR, TASK, report_key=report["report_id"],
            delivery_key="delivery-optional", profile=profile(
                body_requirement(), screenshot_requirement(required=False)
            ),
        )
        assert receipt.state == "ready"
        assert [item["role"] for item in receipt.document["missing"]] == ["screenshot"]
        assert receipt.document["missing"][0]["required"] is False


def test_the_database_refuses_a_ready_delivery_that_misses_required_material(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        report = closed_report(case)
        declared = profile(body_requirement(), screenshot_requirement())
        missing = (
            '[{"role":"screenshot","media_type":"image/*","min_count":1,'
            '"present_count":0,"missing_count":1,"required":true}]'
        )
        manifest = (
            '{"schema_version":"wuji.report-delivery.v1","materials":[],"missing":'
            + missing
            + '}'
        )
        with case.uow.transaction(OPERATOR, TASK, capability="control") as tx:
            with pytest.raises(psycopg.errors.InvalidParameterValue):
                tx.connection.execute(
                    "SELECT vnext.record_report_delivery(%s,%s,%s,'delivery-forged',%s,%s,"
                    "'offline-document-v1',%s,'ready','offline',%s,%s,NULL,NULL,1)",
                    (
                        *OWNER, report["report_id"], report["body_digest"],
                        json.dumps(declared, separators=(",", ":"), sort_keys=True),
                        missing, manifest,
                    ),
                )
        # The same function still refuses to say a delivery is complete when the
        # caller tries to smuggle the missing list out of the record.
        with case.uow.transaction(OPERATOR, TASK, capability="control") as tx:
            with pytest.raises(psycopg.errors.InvalidParameterValue):
                tx.connection.execute(
                    "SELECT vnext.record_report_delivery(%s,%s,%s,'delivery-forged',%s,%s,"
                    "'offline-document-v1',%s,'ready','offline',NULL,%s,NULL,NULL,1)",
                    (
                        *OWNER, report["report_id"], report["body_digest"],
                        json.dumps(declared, separators=(",", ":"), sort_keys=True),
                        manifest,
                    ),
                )
        assert rows(case) == []


def test_one_delivery_key_never_rewrites_an_earlier_decision(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        report = closed_report(case)
        deliveries = service(case)
        first = deliveries.deliver(
            OPERATOR, TASK, report_key=report["report_id"],
            delivery_key="delivery-stable", profile=profile(body_requirement()),
        )
        again = deliveries.deliver(
            OPERATOR, TASK, report_key=report["report_id"],
            delivery_key="delivery-stable", profile=profile(body_requirement()),
        )
        assert again.delivery_id == first.delivery_id
        assert again.document["manifest_digest"] == first.document["manifest_digest"]
        with pytest.raises(DomainError) as refused:
            deliveries.deliver(
                OPERATOR, TASK, report_key=report["report_id"],
                delivery_key="delivery-stable",
                profile=profile(body_requirement(), screenshot_requirement(required=False)),
            )
        assert refused.value.code == "INPUT_DIGEST_CONFLICT"
        assert refused.value.status == 409
        assert len(rows(case)) == 1


def test_an_offline_delivery_cannot_carry_an_http_exchange(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        report = closed_report(case)
        deliveries = service(case)
        with pytest.raises(DomainError) as refused:
            deliveries.deliver(
                OPERATOR, TASK, report_key=report["report_id"],
                delivery_key="delivery-offline-exchange", profile=profile(body_requirement()),
                exchange={"status": 200, "url": "https://sink.invalid/deliver"},
            )
        assert refused.value.code == "INVALID_SCHEMA"

        # An http profile cannot claim to have happened before any exchange did.
        with pytest.raises(DomainError) as pending:
            deliveries.deliver(
                OPERATOR, TASK, report_key=report["report_id"],
                delivery_key="delivery-http", profile=profile(
                    body_requirement(), profile_id="http-bundle-v1", mode="http"
                ),
            )
        assert pending.value.code == "delivery_exchange_required"
        assert rows(case) == []


def test_a_failed_delivery_names_a_bounded_reason(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        report = closed_report(case)
        deliveries = service(case)
        receipt = deliveries.fail(
            OPERATOR, TASK, report_key=report["report_id"],
            delivery_key="delivery-failed", profile=profile(body_requirement()),
            error_code="sink_unavailable",
        )
        assert receipt.state == "failed"
        assert receipt.document["error_code"] == "sink_unavailable"
        assert receipt.document["manifest"] is None
        with pytest.raises(DomainError) as refused:
            deliveries.fail(
                OPERATOR, TASK, report_key=report["report_id"],
                delivery_key="delivery-failed-2", profile=profile(body_requirement()),
                error_code="because I said so",
            )
        assert refused.value.code == "INVALID_SCHEMA"
        assert len(rows(case)) == 1


def test_only_an_actor_with_control_over_this_task_delivers(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        report = closed_report(case)
        deliveries = service(case)
        for actor in (
            access("reader-fixture", role="reader"),
            access("agent-fixture", role="operator"),
            access("observer-fixture", role="controller"),
        ):
            with pytest.raises(DomainError) as refused:
                deliveries.deliver(
                    actor, TASK, report_key=report["report_id"],
                    delivery_key="delivery-refused", profile=profile(body_requirement()),
                )
            assert refused.value.code == "NOT_FOUND_OR_FORBIDDEN"
        assert rows(case) == []


def test_the_signed_http_routes_record_list_and_read_one_delivery(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        report = closed_report(case)
        token = case.provider.issue(
            subject="operator-fixture", tenant_id=OWNER[0], roles=["operator"]
        )
        client = RecordedTestClient(
            create_app(
                token_verifier=case.verifier,
                routers=[create_delivery_router(service(case))],
            ),
            audit_path=audit_directory / "report-delivery-http.jsonl",
        )
        headers = {"Authorization": "Bearer " + token}
        base = f"/api/v2/tasks/{TASK}/reports/{report['report_id']}/deliveries"
        try:
            empty = client.get(base, headers=headers)
            assert empty.status_code == 200, empty.text
            assert empty.json() == []

            key = str(uuid4())
            created = client.post(
                base,
                json={"profile": profile(body_requirement(), screenshot_requirement())},
                headers={**headers, "Idempotency-Key": key},
            )
            assert created.status_code == 200, created.text
            document = created.json()
            assert document["state"] == "incomplete"
            assert document["mode"] == "offline"
            assert document["report_digest"] == report["body_digest"]
            assert document["missing"][0]["role"] == "screenshot"
            assert document["exchange"] is None
            assert document["manifest"]["state"] == "incomplete"

            replay = client.post(
                base,
                json={"profile": profile(body_requirement(), screenshot_requirement())},
                headers={**headers, "Idempotency-Key": key},
            )
            assert replay.status_code == 200, replay.text
            assert replay.json()["delivery_id"] == document["delivery_id"]
            assert replay.json()["manifest_digest"] == document["manifest_digest"]

            listed = client.get(base, headers=headers)
            assert listed.status_code == 200, listed.text
            assert [item["delivery_id"] for item in listed.json()] == [
                document["delivery_id"]
            ]
            assert listed.json()[0]["missing_required"] == 1
            assert listed.json()[0]["state"] == "incomplete"

            fetched = client.get(
                base + "/" + document["delivery_id"], headers=headers
            )
            assert fetched.status_code == 200, fetched.text
            assert fetched.json()["manifest_digest"] == document["manifest_digest"]

            absent = client.get(base + "/delivery-absent", headers=headers)
            assert absent.status_code == 404

            # A reader never learns whether a delivery exists, and the command
            # still requires an explicit idempotency key.
            assert client.post(
                base,
                json={"profile": profile(body_requirement())},
                headers={
                    "Authorization": "Bearer " + case.tokens.reader,
                    "Idempotency-Key": str(uuid4()),
                },
            ).status_code == 404
            assert client.post(
                base,
                json={"profile": profile(body_requirement())},
                headers=headers,
            ).status_code == 422

            # A profile that asks for an HTTP delivery before any exchange
            # happened is refused with its own bounded public code.
            http_refused = client.post(
                base,
                json={
                    "profile": profile(
                        body_requirement(), profile_id="http-bundle-v1", mode="http"
                    )
                },
                headers={**headers, "Idempotency-Key": str(uuid4())},
            )
            assert http_refused.status_code == 409, http_refused.text
            assert http_refused.json()["code"] == "DELIVERY_EXCHANGE_REQUIRED"
        finally:
            client.close()


# ---- P16-B: retention, purge and the tombstone a reader can see -------------

SENSITIVE = b"fixture-sensitive-bytes-must-not-survive-purge"
SENSITIVE_TYPE = "text/x-fixture-sensitive"


def allow_retention(case, *, subject="operator-fixture"):
    """Grant the fixture operator the retention permission this test exercises."""

    with case.env.migration_connection() as connection:
        connection.execute(
            "UPDATE vnext.task_access SET can_gc=true"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND subject=%s",
            (*OWNER, subject),
        )


def purgeable_artifact(case, body=SENSITIVE, media_type=SENSITIVE_TYPE):
    """A sealed artifact of this Task that no publication or relation retains.

    Sealing alone keeps the staging lease, and a live lease is a commitment:
    the stager therefore releases it here exactly as a completed commit does.
    """

    staged = case.store.stage_model_output(
        WORKER, TASK, "run-fixture", body, media_type, access_level=1
    )
    case.store.seal(WORKER, TASK, staged)
    case.store.release_lease(WORKER, TASK, staged, lease_owner="staging")
    return staged


def publish_fixture(case, ref, *, publication_id="publication-fixture"):
    """Record a real publication reference (fixture header, not a claim)."""

    with case.env.migration_connection() as connection:
        connection.execute(
            "INSERT INTO vnext.publication(tenant_id,project_id,task_id,publication_id,kind)"
            " VALUES(%s,%s,%s,%s,'session')",
            (*OWNER, publication_id),
        )
        connection.execute(
            "INSERT INTO vnext.publication_ref(tenant_id,project_id,task_id,publication_id,"
            "artifact_id,artifact_revision,access_level) VALUES(%s,%s,%s,%s,%s,1,1)",
            (*OWNER, publication_id, ref.id),
        )


def artifact_row(case, artifact_id):
    with case.env.migration_connection() as connection:
        return connection.execute(
            "SELECT state,body_removed,access_level,storage_key,sha256 FROM vnext.artifact"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND entity_id=%s AND revision=1",
            (*OWNER, artifact_id),
        ).fetchone()


def purge_rows(case):
    with case.env.migration_connection() as connection:
        return connection.execute(
            "SELECT purge_id,artifact_id,reason,authority FROM vnext.artifact_purge"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s ORDER BY created_at",
            OWNER,
        ).fetchall()


def test_purge_leaves_an_explicit_tombstone_and_the_frozen_report_stays_honest(
    db_environment, tmp_path, audit_directory
):
    """AC-067: the bytes go, the record of their absence stays."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        report = closed_report(case)
        sealed = purgeable_artifact(case)
        ReportService(case.uow, artifacts=case.store).amend(
            ASSESSOR,
            TASK,
            report_key=report["report_id"],
            amendment_key="amendment-purge",
            reason="late counter-evidence that must be preserved as a record",
            evidence_refs=[sealed.model_dump(mode="json")],
        )
        allow_retention(case)
        blob = case.store.root / (str(artifact_row(case, sealed.id)[3]) + ".blob")
        assert blob.exists()

        receipt = RetentionService(case.uow, artifacts=case.store).purge(
            OPERATOR,
            TASK,
            artifact_id=sealed.id,
            revision=1,
            reason="approved_retention_action",
            purge_key="purge-1",
        )
        assert receipt.document["state"] == "tombstoned"
        assert receipt.document["body_removed"] is True
        assert receipt.document["artifact_sha256"] == sha256(SENSITIVE).hexdigest()
        assert receipt.document["authority"] == "operator"
        assert not blob.exists(), "the bytes must actually be gone"
        assert artifact_row(case, sealed.id)[:2] == ("tombstoned", True)
        assert purge_rows(case) == [
            ("purge-1", sealed.id, "approved_retention_action", "operator")
        ]

        # The content is unreadable, and nothing re-collected or repaired it.
        with pytest.raises(DomainError):
            case.store.read(WORKER, sealed.id, str(sealed.version.root))

        stored = portal(case).read_report(OPERATOR, TASK, report["report_id"])
        assert stored["body_digest"] == report["body_digest"], "正文摘要不变"
        assert stored["unavailable_evidence"] == [
            {
                "source_ref": f"{sealed.id}@1",
                "sha256": sha256(SENSITIVE).hexdigest(),
                "state": "tombstoned",
                "reason": "approved_retention_action",
                "purge_id": "purge-1",
            }
        ]

        # Purging the same version again is a bounded refusal, not a second act.
        with pytest.raises(DomainError) as again:
            RetentionService(case.uow, artifacts=case.store).purge(
                OPERATOR,
                TASK,
                artifact_id=sealed.id,
                revision=1,
                reason="approved_retention_action",
                purge_key="purge-2",
            )
        assert again.value.code == "STALE_EXECUTION"


def test_a_purge_waits_for_the_live_lease_and_retires_cited_evidence(
    db_environment, tmp_path, audit_directory
):
    """AC-066/067: in-flight bytes are untouchable, cited bytes retire only by decision."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        sealed = purgeable_artifact(case)
        publish_fixture(case, sealed)
        allow_retention(case)
        retention = RetentionService(case.uow, artifacts=case.store)
        blob = case.store.root / (str(artifact_row(case, sealed.id)[3]) + ".blob")

        # A live lease is an in-flight commit: neither GC nor purge may take it.
        case.store.acquire_lease(
            WORKER, TASK, sealed, lease_owner="publisher-fixture", seconds=300
        )
        with pytest.raises(DomainError) as leased:
            retention.purge(
                OPERATOR,
                TASK,
                artifact_id=sealed.id,
                revision=1,
                reason="approved_retention_action",
                purge_key="purge-leased",
            )
        assert leased.value.code == "LIMIT_BLOCKED"
        assert leased.value.status == 409
        assert artifact_row(case, sealed.id)[:2] == ("sealed", False)
        assert purge_rows(case) == []
        assert blob.exists(), "in-flight bytes stay"

        # Nobody may purge without both the retention and the control bit.
        with case.env.migration_connection() as connection:
            connection.execute(
                "UPDATE vnext.task_access SET can_gc=false"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND subject='operator-fixture'",
                OWNER,
            )
        with pytest.raises(DomainError) as forbidden:
            retention.purge(
                OPERATOR,
                TASK,
                artifact_id=sealed.id,
                revision=1,
                reason="approved_retention_action",
                purge_key="purge-without-retention",
            )
        assert forbidden.value.code == "NOT_FOUND_OR_FORBIDDEN"
        assert purge_rows(case) == []
        allow_retention(case)

        # Once the writer stopped, an explicit purge may retire published
        # evidence -- the citation stays, its content becomes unavailable.
        case.store.release_lease(WORKER, TASK, sealed, lease_owner="publisher-fixture")
        receipt = retention.purge(
            OPERATOR,
            TASK,
            artifact_id=sealed.id,
            revision=1,
            reason="approved_retention_action",
            purge_key="purge-published",
        )
        assert receipt.document["state"] == "tombstoned"
        assert artifact_row(case, sealed.id)[:2] == ("tombstoned", True)
        assert purge_rows(case) == [
            ("purge-published", sealed.id, "approved_retention_action", "operator")
        ]
        assert not blob.exists()
        with case.env.migration_connection() as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext.publication_ref WHERE tenant_id=%s"
                " AND project_id=%s AND task_id=%s AND artifact_id=%s",
                (*OWNER, sealed.id),
            ).fetchone() == (1,)


def test_garbage_collection_keeps_committed_evidence_and_collects_true_orphans(
    db_environment, tmp_path, audit_directory
):
    """AC-066: staged orphans go, published and leased objects stay."""

    from datetime import datetime, timezone

    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        allow_retention(case)
        # A staging attempt that gave up: the lease is released, nothing else
        # references the object, so it is a true orphan.
        orphan = case.store.stage_model_output(
            WORKER, TASK, "run-fixture", b"orphan-bytes", "application/json",
            access_level=1,
        )
        case.store.release_lease(WORKER, TASK, orphan, lease_owner="staging")
        published = purgeable_artifact(case)
        leased = purgeable_artifact(case, body=b"leased-bytes")
        case.store.acquire_lease(
            WORKER, TASK, leased, lease_owner="publisher-fixture", seconds=300
        )
        publish_fixture(case, published)
        orphan_blob = case.store.root / (str(artifact_row(case, orphan.id)[3]) + ".blob")
        published_blob = case.store.root / (str(artifact_row(case, published.id)[3]) + ".blob")
        leased_blob = case.store.root / (str(artifact_row(case, leased.id)[3]) + ".blob")

        removed = case.store.collect_garbage(
            OPERATOR, TASK, older_than=datetime.now(timezone.utc), limit=10
        )
        assert removed == [orphan.id]
        assert not orphan_blob.exists()
        assert artifact_row(case, orphan.id)[:2] == ("tombstoned", True)
        assert published_blob.exists() and leased_blob.exists()
        assert artifact_row(case, published.id)[:2] == ("sealed", False)
        assert artifact_row(case, leased.id)[:2] == ("sealed", False)
        # A collected orphan has no purge record: it was never a decision.
        assert purge_rows(case) == []


def test_a_purged_material_stays_indexed_but_reads_as_unavailable(
    db_environment, tmp_path, audit_directory
):
    """AC-067: the delivery keeps its digest and stops claiming the bytes."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        report = closed_report(case)
        sealed = purgeable_artifact(case)
        allow_retention(case)
        declared = profile(
            body_requirement(),
            {
                "role": "sensitive",
                "media_type": SENSITIVE_TYPE,
                "min_count": 1,
                "required": True,
            },
        )
        deliveries = service(case)
        receipt = deliveries.deliver(
            OPERATOR, TASK, report_key=report["report_id"],
            delivery_key="delivery-before-purge", profile=declared,
        )
        assert receipt.state == "ready"
        indexed = [
            item
            for item in receipt.document["manifest"]["materials"]
            if item["source"] == "artifact"
        ]
        assert [item["source_ref"] for item in indexed] == [f"{sealed.id}@1"]

        RetentionService(case.uow, artifacts=case.store).purge(
            OPERATOR,
            TASK,
            artifact_id=sealed.id,
            revision=1,
            reason="approved_retention_action",
            purge_key="purge-delivery",
        )
        after = deliveries.read(
            OPERATOR, TASK, report["report_id"], receipt.delivery_id
        )
        assert after["manifest_digest"] == receipt.document["manifest_digest"]
        assert after["state"] == "ready", "the frozen decision is never rewritten"
        assert after["unavailable_materials"] == [
            {
                "source_ref": f"{sealed.id}@1",
                "sha256": sha256(SENSITIVE).hexdigest(),
                "state": "tombstoned",
                "reason": "approved_retention_action",
                "purge_id": "purge-delivery",
            }
        ]
        listed = deliveries.list(OPERATOR, TASK, report["report_id"])
        assert listed[0]["unavailable_materials"] == after["unavailable_materials"]


def test_the_signed_purge_route_records_a_bounded_tombstone(
    db_environment, tmp_path, audit_directory
):
    """AC-067 through the product boundary: purge, replay, refuse, refuse."""

    with control_case(db_environment, tmp_path, audit_directory) as case:
        ready_goal(case)
        sealed = purgeable_artifact(case)
        allow_retention(case)
        token = case.provider.issue(
            subject="operator-fixture", tenant_id=OWNER[0], roles=["operator"]
        )
        client = RecordedTestClient(
            create_app(
                token_verifier=case.verifier,
                routers=[
                    create_retention_router(
                        RetentionService(case.uow, artifacts=case.store)
                    )
                ],
            ),
            audit_path=audit_directory / "artifact-purge-http.jsonl",
        )
        headers = {"Authorization": "Bearer " + token}
        path = f"/api/v2/tasks/{TASK}/artifacts/{sealed.id}/purges"
        body = {"revision": str(sealed.version.root), "reason": "approved_retention_action"}
        key = str(uuid4())
        try:
            purged = client.post(path, json=body, headers={**headers, "Idempotency-Key": key})
            assert purged.status_code == 200, purged.text
            document = purged.json()
            assert document["state"] == "tombstoned"
            assert document["body_removed"] is True
            assert document["authority"] == "operator"
            assert document["reason"] == "approved_retention_action"
            assert document["artifact_revision"] == str(sealed.version.root)

            replay = client.post(path, json=body, headers={**headers, "Idempotency-Key": key})
            assert replay.status_code == 200, replay.text
            assert replay.json()["purge_id"] == document["purge_id"]

            again = client.post(
                path,
                json=body,
                headers={**headers, "Idempotency-Key": str(uuid4())},
            )
            assert again.status_code == 409, again.text
            assert again.json()["code"] == "STALE_EXECUTION"

            assert client.post(
                path,
                json=body,
                headers={**headers, "Idempotency-Key": str(uuid4())},
            ).status_code == 409
            assert client.post(
                path,
                json=body,
                headers={
                    "Authorization": "Bearer " + case.tokens.reader,
                    "Idempotency-Key": str(uuid4()),
                },
            ).status_code == 404
            assert client.post(path, json=body, headers=headers).status_code == 422
            assert client.post(
                path,
                json={"revision": "0", "reason": "approved_retention_action"},
                headers={**headers, "Idempotency-Key": str(uuid4())},
            ).status_code == 422
        finally:
            client.close()
