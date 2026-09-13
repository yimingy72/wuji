from __future__ import annotations

from inspect import Parameter, signature

from wuji_core.http.topology import create_topology_router
from wuji_core.projection.snapshots import ProjectionRepository


def _shape(callable_object) -> tuple[tuple[str, Parameter], ...]:
    return tuple(signature(callable_object).parameters.items())


def test_projection_repository_has_the_frozen_assembly_shape() -> None:
    parameters = _shape(ProjectionRepository)

    assert tuple(name for name, _ in parameters) == (
        "uow",
        "snapshots",
        "ledger",
        "ttl_seconds",
        "max_records",
        "history_page_size",
    )
    assert parameters[0][1].kind is Parameter.POSITIONAL_OR_KEYWORD
    assert all(item.kind is Parameter.KEYWORD_ONLY for _, item in parameters[1:])
    assert tuple(item.default for _, item in parameters[1:]) == (
        None,
        None,
        3600,
        5000,
        100,
    )


def test_projection_repository_has_the_frozen_read_method_shapes() -> None:
    assert tuple(signature(ProjectionRepository.create_in_transaction).parameters) == (
        "self",
        "tx",
        "query",
    )
    assert tuple(signature(ProjectionRepository.topology).parameters) == (
        "self",
        "task_id",
        "access",
        "query",
    )
    assert tuple(signature(ProjectionRepository.record).parameters) == (
        "self",
        "task_id",
        "access",
        "ref",
        "snapshot_id",
    )
    assert tuple(signature(ProjectionRepository.history).parameters) == (
        "self",
        "task_id",
        "access",
        "cursor",
    )


def test_topology_router_factory_accepts_only_the_projection_service() -> None:
    assert tuple(signature(create_topology_router).parameters) == ("projection",)
