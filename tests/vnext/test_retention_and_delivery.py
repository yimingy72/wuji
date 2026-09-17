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
from test_completion_protocol import WORKER
from test_work_state_guards import OPERATOR, OWNER, TASK, control_case
from wuji_core.audit.delivery import (
    PROFILE_SCHEMA,
    REPORT_MEDIA_TYPE,
    ReportDeliveryService,
)
from wuji_core.http import create_app
from wuji_core.http.delivery import create_delivery_router
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
        finally:
            client.close()
