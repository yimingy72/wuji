"""Platform Gates plus the C0 permit callback, using real admission services."""

import httpx

from deployment_common import Deployment, load_settings, token
from wuji_core.admission.ledger import AdmissionLedger
from wuji_core.admission.models import HttpxModelTransport, ModelAdmission, ModelGate
from wuji_core.admission.remote_workspace import (
    ExecutorDeploymentBinding, ExecutorPermitAuthority, RemoteWorkspaceExecutor,
)
from wuji_core.admission.tools import ToolAdmission, ToolCapabilityResolver, ToolGate
from wuji_core.evidence.observations import EvidenceService
from wuji_core.http import JsonBoundaryLimits, create_app
from wuji_core.http.executor_host import create_executor_host_router
from wuji_core.http.model_gate import create_model_router
from wuji_core.http.tool_gate import create_tool_router


class KeyResolver:
    def __init__(self, deployment):
        self.deployment = deployment

    def resolve(self, secret_ref):
        return self.deployment.secret(secret_ref).decode().strip()


def build_gates():
    deployment = Deployment(load_settings("gates"))
    settings = deployment.settings
    ledger = AdmissionLedger(deployment.uow)
    admission = ToolAdmission(deployment.uow, registry=deployment.registry,
        ledger=ledger, approvals=deployment.approvals)
    bindings, executors, collectors = [], {}, {}
    for entry in settings.executors:
        binding = ExecutorDeploymentBinding(**entry["binding"])
        # Several Tasks may share one deployment executor ref; the owning Task
        # is part of the key, and an exact duplicate is still refused.
        key = (*binding.owner, binding.executor_ref)
        if key in executors:
            raise ValueError("duplicate deployment executor")
        bindings.append(binding)
        executors[key] = RemoteWorkspaceExecutor(
            binding=binding, base_url=entry["base_url"], ca_file=settings.ca_file,
            bearer_token=lambda path=entry["gate_token_file"]: token(path))
        collectors[key] = deployment.access(entry["collector_token_file"])
    if not bindings:
        raise ValueError("a real remote Kali executor is required")
    tools = ToolGate(admission, registry=deployment.registry, ledger=ledger,
        artifacts=deployment.artifacts,
        evidence=EvidenceService(deployment.uow, deployment.artifacts),
        executors=executors, collector_accesses=collectors)
    client = httpx.AsyncClient(verify=deployment.tls, trust_env=False,
        follow_redirects=False, transport=httpx.AsyncHTTPTransport(verify=deployment.tls, retries=0))
    models = ModelGate(ModelAdmission(deployment.uow, registry=deployment.registry, ledger=ledger),
        registry=deployment.registry, ledger=ledger, key_resolver=KeyResolver(deployment),
        transport=HttpxModelTransport(client), tool_capabilities=ToolCapabilityResolver(tools))
    app = create_app(token_verifier=deployment.verifier, routers=[
        create_model_router(models), create_tool_router(tools),
        create_executor_host_router(ExecutorPermitAuthority(admission, bindings=bindings)),
    ], json_limits=JsonBoundaryLimits(max_body_bytes=settings.max_transport_bytes))

    # ASGI wrapper closes the only pooled upstream HTTP client at service exit.
    async def application(scope, receive, send):
        if scope["type"] != "lifespan":
            return await app(scope, receive, send)
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await client.aclose()
                await send({"type": "lifespan.shutdown.complete"})
                return
    return application
