"""P13 real signed-HTTP/PostgreSQL composition over existing P03/P04 fixtures."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

from support.http_capture import RecordedTestClient
from support.p09 import scheduler_case
from test_knowledge_admission import (
    assess,
    captured,
    case as knowledge_case,
    exact,
    headers as knowledge_headers,
    post_claim,
)
from wuji_core.http import create_app
from wuji_core.http.topology import create_topology_router
from wuji_core.projection.snapshots import ProjectionRepository


TASK = "task-fixture"
OWNER = ("tenant-fixture", "project-fixture", TASK)
BASE = "/api/v2/tasks/" + TASK


@contextmanager
def projection_case(
    environment,
    tmp_path,
    audit_directory,
    *,
    history_page_size: int = 100,
):
    with knowledge_case(environment, tmp_path, audit_directory) as knowledge:
        projection = ProjectionRepository(
            knowledge.uow, history_page_size=history_page_size
        )
        client = RecordedTestClient(
            create_app(
                token_verifier=knowledge.verifier,
                routers=[create_topology_router(projection)],
            ),
            audit_path=audit_directory / "p13-http-exchanges.jsonl",
        )
        try:
            yield SimpleNamespace(
                environment=environment,
                knowledge=knowledge,
                projection=projection,
                client=client,
            )
        finally:
            client.close()


@contextmanager
def scheduled_projection_case(environment, tmp_path, audit_directory):
    with scheduler_case(environment, tmp_path, audit_directory) as scheduler:
        projection = ProjectionRepository(scheduler.control.uow)
        client = RecordedTestClient(
            create_app(
                token_verifier=scheduler.control.verifier,
                routers=[create_topology_router(projection)],
            ),
            audit_path=audit_directory / "p13-run-http-exchanges.jsonl",
        )
        try:
            yield SimpleNamespace(
                environment=environment,
                scheduler=scheduler,
                projection=projection,
                client=client,
            )
        finally:
            client.close()


def headers(case, role: str = "reader") -> dict[str, str]:
    return knowledge_headers(case.knowledge, role)


def topology(case, *, token_role: str = "reader", **params):
    query = {
        "mode": "live",
        "node_limit": 300,
        "edge_limit": 600,
        **params,
    }
    return case.client.get(BASE + "/topology", params=query, headers=headers(case, token_role))


def supported_claim(case, *, access_level: int = 0):
    artifact, observation = captured(case.knowledge, access_level=access_level)
    body = exact(artifact, observation)
    accepted = post_claim(case.knowledge, body)
    if accepted.status_code != 202:
        raise AssertionError(accepted.text)
    ref = accepted.json()["canonical_ref"]
    checked = assess(case.knowledge, ref, [observation])
    if checked.status_code != 202:
        raise AssertionError(checked.text)
    return SimpleNamespace(
        artifact=artifact,
        observation=observation,
        body=body,
        ref=ref,
    )


def revise_claim(case, claim, *, text: str):
    body = {**claim.body, "text": text, "revises": claim.ref}
    accepted = post_claim(case.knowledge, body)
    if accepted.status_code != 202:
        raise AssertionError(accepted.text)
    return accepted.json()["canonical_ref"]


def set_reader_access(case, *, can_read: bool = True, clearance: int = 1) -> None:
    with case.environment.migration_connection() as connection:
        connection.execute(
            """UPDATE vnext.task_access SET can_read=%s,clearance=%s
            WHERE tenant_id=%s AND project_id=%s AND task_id=%s
            AND subject='reader-fixture'""",
            (can_read, clearance, *OWNER),
        )


def set_actor_clearance(case, subjects: tuple[str, ...], clearance: int) -> None:
    with case.environment.migration_connection() as connection:
        connection.execute(
            """UPDATE vnext.task_access SET clearance=%s
            WHERE tenant_id=%s AND project_id=%s AND task_id=%s
            AND subject=ANY(%s)""",
            (clearance, *OWNER, list(subjects)),
        )


def add_reader(case, subject: str, *, clearance: int = 1) -> str:
    with case.environment.migration_connection() as connection:
        connection.execute(
            """INSERT INTO vnext.task_access(
            tenant_id,project_id,task_id,subject,can_read,clearance)
            VALUES(%s,%s,%s,%s,true,%s)""",
            (*OWNER, subject, clearance),
        )
    return case.knowledge.provider.issue(
        subject=subject,
        tenant_id=OWNER[0],
        roles=["reader"],
    )
