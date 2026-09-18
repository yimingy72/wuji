"""Read-only v2 archive query route.

The route is intentionally independent of ``wuji_api.main`` and of Cairn.
Callers mount the returned router in the vNext ASGI composition with an
``ArchiveStore`` that points at an offline archive copy.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from wuji_core.archive import ArchiveStore
from wuji_core.contracts.generated import ArchiveView
from wuji_core.http.auth import AuthenticationError, current_principal

try:
    from wuji_core.http import VNextAPIRouter
except ImportError:  # pragma: no cover - keeps the module usable in API-only tooling
    VNextAPIRouter = APIRouter  # type: ignore[misc,assignment]


def read_archive(
    store: ArchiveStore, archive_id: str, *, principal: Any | None = None
) -> ArchiveView:
    """Read one immutable archive or raise the public not-found response."""

    view = store.view(archive_id, principal=principal)
    if view is None:
        raise HTTPException(status_code=404, detail="archive not found")
    return view


def create_archive_router(store: ArchiveStore) -> APIRouter:
    """Build the v2 GET route without registering any write or cutover action."""

    router = VNextAPIRouter()

    @router.get("/api/v2/archives/{archive_id}", response_model=ArchiveView, tags=["Views"])
    def get_archive(request: Request, archive_id: str) -> ArchiveView:
        try:
            principal = current_principal(request)
        except AuthenticationError as error:
            raise HTTPException(status_code=401, detail="authentication required") from error
        return read_archive(store, archive_id, principal=principal)

    return router


def register_archive_routes(application: Any, store: ArchiveStore) -> None:
    """Compatibility helper for app factories that register routers directly."""

    application.include_router(create_archive_router(store))


__all__ = ["create_archive_router", "read_archive", "register_archive_routes"]
