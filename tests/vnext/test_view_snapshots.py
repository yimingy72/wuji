from __future__ import annotations

from wuji_core.projection.snapshots import ProjectionRepository


def test_projection_repository_exposes_existing_transaction_composition() -> None:
    """A persistent view must compose inside its caller's stable transaction."""

    assert callable(ProjectionRepository.create_in_transaction)
