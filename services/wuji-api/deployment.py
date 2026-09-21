"""Public vNext API composition from explicit deployment files."""

from deployment_common import Deployment, load_settings
from wuji_core.audit.delivery import ReportDeliveryService
from wuji_core.audit.retention import RetentionService
from wuji_core.completion.portal import TaskCompletionPortal
from wuji_core.completion.precheck import CompletionService
from wuji_core.completion.reports import ReportService
from wuji_core.http import JsonBoundaryLimits, create_app
from wuji_core.execution.tasks import TaskService
from wuji_core.execution.launch import LaunchService
from wuji_core.execution.control_api import ControlAPI
from wuji_core.http.commands import create_command_router
from wuji_core.http.launch import create_launch_router
from wuji_core.http.completion import create_completion_router
from wuji_core.http.delivery import create_delivery_router
from wuji_core.http.evidence import create_artifact_router
from wuji_core.evidence.material import ArtifactMaterialService
from wuji_core.http.material import create_material_router
from wuji_core.http.retention import create_retention_router
from wuji_core.http.layouts import create_layout_router
from wuji_core.http.tasks import create_task_router
from wuji_core.http.views import create_view_router
from wuji_core.http.topology import create_topology_router
from wuji_core.http.inputs import create_input_router
from wuji_core.projection.layouts import LayoutRepository
from wuji_core.projection.snapshots import ProjectionRepository


def build_api():
    settings = load_settings("api")
    deployment = Deployment(settings)
    projection = ProjectionRepository(deployment.uow, ledger=deployment.ledger)
    layouts = LayoutRepository(deployment.uow)
    tasks = TaskService(deployment.uow)
    launch = LaunchService(deployment.uow, control=deployment.control)
    completion = CompletionService(deployment.uow, control=deployment.control)
    reports = ReportService(deployment.uow, artifacts=deployment.artifacts)
    portal = TaskCompletionPortal(
        deployment.uow, completion=completion, reports=reports
    )
    deliveries = ReportDeliveryService(deployment.uow)
    retention = RetentionService(deployment.uow, artifacts=deployment.artifacts)
    return create_app(
        token_verifier=deployment.verifier,
        routers=[
            create_topology_router(projection),
            create_view_router(projection),
            create_layout_router(layouts),
            create_task_router(tasks),
            create_launch_router(launch),
            create_command_router(ControlAPI(deployment.control, launch_service=launch)),
            create_input_router(deployment.inputs),
            create_completion_router(portal),
            create_delivery_router(deliveries),
            create_retention_router(retention),
            create_artifact_router(deployment.artifacts),
            create_material_router(ArtifactMaterialService(deployment.artifacts)),
        ],
        json_limits=JsonBoundaryLimits(max_body_bytes=settings.max_transport_bytes),
    )
