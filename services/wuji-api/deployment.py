"""Public vNext API composition from explicit deployment files."""

from deployment_common import Deployment, load_settings
from wuji_core.http import JsonBoundaryLimits, create_app
from wuji_core.http.topology import create_topology_router
from wuji_core.projection.snapshots import ProjectionRepository


def build_api():
    settings = load_settings("api")
    deployment = Deployment(settings)
    projection = ProjectionRepository(deployment.uow, ledger=deployment.ledger)
    return create_app(
        token_verifier=deployment.verifier,
        routers=[create_topology_router(projection)],
        json_limits=JsonBoundaryLimits(max_body_bytes=settings.max_transport_bytes),
    )
