"""Kali tool-executor application; TLS listener and secret loading belong to deployment."""

from wuji_core.admission.remote_workspace import RemoteToolAdmission
from wuji_core.admission.tools import (
    HttpTargetExecutor,
    ToolExecutorRouter,
    WorkspaceReadExecutor,
)
from wuji_core.http import JsonBoundaryLimits, create_app
from wuji_core.http.executor_host import create_workspace_executor_router


def create_kali_executor_app(*, token_verifier, binding, admission, root, receipt_root,
                             tool_routes,
                             json_limits=JsonBoundaryLimits(),
                             max_response_bytes=2097152, max_output_bytes=1048576,
                             target_timeout_seconds=30):
    """Compose the signed, bounded executor routes in a Kali process.

    Two published kinds are served: a workspace read of the Task's own files and a
    read-only HTTP exchange against the exact target the platform approved in the
    permit. The CA and public issuer key are public configuration. Admission holds
    only a collector bearer credential, not a DB connection, issuer key or model
    key. Receipts live outside /workspace on Kali's separately retained volume.
    """
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
    return create_app(
        token_verifier=token_verifier, json_limits=json_limits,
        routers=[create_workspace_executor_router(
            executor, binding=binding, max_response_bytes=max_response_bytes,
            max_output_bytes=max_output_bytes,
        )],
    )
