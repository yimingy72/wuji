"""Kali tool-executor application; TLS listener and secret loading belong to deployment."""

from wuji_core.admission.remote_workspace import RemoteToolAdmission
from wuji_core.admission.tools import (
    HttpTargetExecutor,
    ToolExecutorRouter,
    WorkspaceReadExecutor,
)
from wuji_core.http import JsonBoundaryLimits, create_app
from wuji_core.http.executor_host import create_workspace_executor_router
from wuji_core.http.process_executor import create_process_executor_router
from wuji_core.http.workspace_executor import create_workspace_transfer_router


def create_kali_executor_app(*, token_verifier, binding, admission, root, receipt_root,
                             tool_routes,
                             process_supervisor=None, action_verifier=None,
                             workspace_transfer_handler=None,
                             shutdown_callback=None,
                             json_limits=JsonBoundaryLimits(),
                             max_response_bytes=2097152, max_output_bytes=1048576,
                             target_timeout_seconds=30):
    """Compose the signed, bounded executor routes in a Kali process.

    The legacy deployment serves its fixed workspace/HTTP routes. The action-only
    deployment serves process and workspace-transfer routes from signed permits and
    receives no platform bearer. Receipts live outside /workspace on Kali's
    separately retained volume.
    """
    routers = []
    if admission is not None:
        if not isinstance(admission, RemoteToolAdmission) or admission.binding != binding:
            raise ValueError("Kali requires the exact deployment-bound remote authority")
        workspace = WorkspaceReadExecutor(
            root=root, receipt_root=receipt_root, admission=admission,
            receiver_id=binding.receiver_id, environment_ref=binding.environment_ref,
        )
        target = HttpTargetExecutor(
            receipt_root=receipt_root, admission=admission,
            receiver_id=binding.receiver_id, environment_ref=binding.environment_ref,
            timeout_seconds=target_timeout_seconds,
        )
        adapters = {"workspace_read": workspace, "http_target": target}
        if (
            not isinstance(tool_routes, dict)
            or not tool_routes
            or any(
                not isinstance(ref, str)
                or not ref
                or not isinstance(route, dict)
                or set(route) != {"revision", "executor_ref", "kind"}
                or not isinstance(route["revision"], str)
                or not route["revision"].isdigit()
                or route["executor_ref"] != binding.executor_ref
                or route["kind"] not in adapters
                for ref, route in tool_routes.items()
            )
        ):
            raise ValueError("Kali requires fixed published built-in tool routes")
        executor = ToolExecutorRouter(
            executor_ref=binding.executor_ref,
            routes={ref: adapters[route["kind"]] for ref, route in tool_routes.items()},
        )
        routers.append(create_workspace_executor_router(
            executor, binding=binding, max_response_bytes=max_response_bytes,
            max_output_bytes=max_output_bytes,
        ))
    elif tool_routes not in ({}, None):
        raise ValueError("action-only Kali cannot expose legacy bearer routes")
    process_values = (
        process_supervisor,
        action_verifier,
        shutdown_callback,
    )
    if any(value is not None for value in process_values):
        if not all(value is not None for value in process_values):
            raise ValueError("complete process executor assembly is required")
        routers.append(
            create_process_executor_router(
                process_supervisor,
                verifier=action_verifier,
                binding=binding,
                shutdown_callback=shutdown_callback,
            )
        )
    if workspace_transfer_handler is not None:
        if action_verifier is None:
            raise ValueError("workspace transfer requires the action verifier")
        routers.append(
            create_workspace_transfer_router(
                workspace_transfer_handler,
                verifier=action_verifier,
                binding=binding,
            )
        )
    if not routers:
        raise ValueError("Kali requires one fixed executor capability")
    return create_app(
        token_verifier=token_verifier, json_limits=json_limits,
        routers=routers,
    )
