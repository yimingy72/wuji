"""Kali read-executor application; TLS listener and secret loading belong to deployment."""

from wuji_core.admission.remote_workspace import RemoteToolAdmission
from wuji_core.admission.tools import WorkspaceReadExecutor
from wuji_core.http import JsonBoundaryLimits, create_app
from wuji_core.http.executor_host import create_workspace_executor_router


def create_kali_executor_app(*, token_verifier, binding, admission, root, receipt_root,
                             json_limits=JsonBoundaryLimits(),
                             max_response_bytes=2097152, max_output_bytes=1048576):
    """Compose only the three signed, bounded workspace routes in a Kali process.

    The CA and public issuer key are public configuration. Admission holds only a
    collector bearer credential, not a DB connection, issuer key or model key.
    Receipts live outside /workspace on Kali's separately retained state volume.
    """
    if not isinstance(admission, RemoteToolAdmission) or admission.binding != binding:
        raise ValueError("Kali requires the exact deployment-bound remote authority")
    executor = WorkspaceReadExecutor(
        root=root, receipt_root=receipt_root, admission=admission,
        receiver_id=binding.receiver_id, environment_ref=binding.environment_ref,
    )
    return create_app(
        token_verifier=token_verifier, json_limits=json_limits,
        routers=[create_workspace_executor_router(
            executor, binding=binding, max_response_bytes=max_response_bytes,
            max_output_bytes=max_output_bytes,
        )],
    )
