"""Platform Gates plus the C0 permit callback, using real admission services.

The Gate reads its projected ConfigMap on each request.  A launch worker can
therefore add a Task executor without rolling this shared Deployment.  Refresh
is monotonic: removal is refused, an existing binding is immutable within an
attempt, and only a guarded next attempt may replace it.
"""

from hashlib import sha256
import json
from pathlib import Path

import httpx

from deployment_common import Deployment, Settings, load_settings, token
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

    def resolve_for_task(self, secret_ref, *, tenant_id, task_id):
        settings = self.deployment.settings
        if settings.task_model_key_ref is None:
            return self.resolve(secret_ref)
        if secret_ref != settings.task_model_key_ref:
            raise ValueError("unregistered Task model key reference")
        from pathlib import Path
        from task_model_keys import task_key_filename

        directory = settings.task_model_keys_directory
        if not isinstance(directory, str) or not Path(directory).is_absolute():
            raise ValueError("an absolute Task key mount is required")
        return token(str(Path(directory) / task_key_filename(tenant_id, task_id)))


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _binding_key(binding):
    return tuple(binding.owner) + (binding.executor_ref,)


def _attempt(binding):
    value = getattr(binding, "runtime_attempt", None)
    return value if type(value) is int and value > 0 else None


class TrustedGateConfig:
    """Bounded reader for the ConfigMap projection; raw config is never logged."""

    def __init__(self, path="/config/deployment.json", *, max_bytes=1 << 20):
        path = Path(path)
        if not path.is_absolute() or type(max_bytes) is not int or not 1 <= max_bytes <= 16 << 20:
            raise ValueError("bounded absolute Gate ConfigMap path required")
        self.path, self.max_bytes = path, max_bytes
        self._digest = None

    def read(self):
        try:
            raw = self.path.read_bytes()
        except OSError as error:
            raise ValueError("trusted Gate configuration is unavailable") from error
        if not 0 < len(raw) <= self.max_bytes:
            raise ValueError("trusted Gate configuration exceeds its bound")
        digest = sha256(raw).hexdigest()
        if digest == self._digest:
            return None
        try:
            value = Settings.model_validate(json.loads(raw))
        except (TypeError, ValueError) as error:
            raise ValueError("trusted Gate configuration is invalid") from error
        self._digest = digest
        return value


def _gate_bindings(deployment, settings):
    bindings, executors, collectors = [], {}, {}
    for entry in settings.executors:
        binding = ExecutorDeploymentBinding(**entry["binding"])
        key = _binding_key(binding)
        if key in executors:
            raise ValueError("duplicate deployment executor")
        bindings.append(binding)
        executors[key] = RemoteWorkspaceExecutor(
            binding=binding, base_url=entry["base_url"], ca_file=settings.ca_file,
            bearer_token=lambda path=entry["gate_token_file"]: token(path))
        collectors[key] = deployment.access(entry["collector_token_file"])
    if not bindings:
        raise ValueError("a real remote Kali executor is required")
    return bindings, executors, collectors


class GateBindingRefresher:
    """Apply an incrementally updated, trusted Gate ConfigMap in place."""

    def __init__(self, deployment, settings, *, path="/config/deployment.json"):
        self.deployment = deployment
        self.settings = settings
        self.reader = TrustedGateConfig(path)
        # The initial Settings object was validated by load_settings.  Keep an
        # immutable snapshot of identity fields to guard later reloads.
        self._known = {key: binding for binding in _gate_bindings(deployment, settings)[0]
                       for key in (_binding_key(binding),)}
        self._digest = sha256(_canonical(settings.model_dump(mode="json"))).hexdigest()

    def refresh(self, tools, authority):
        settings = self.reader.read()
        if settings is None:
            return False
        if settings.role != "gates" or settings.schema_version != "wuji.deployment.v1":
            raise ValueError("trusted Gate configuration role/version changed")
        bindings, executors, collectors = _gate_bindings(self.deployment, settings)
        current = {_binding_key(binding): binding for binding in bindings}
        if set(self._known) - set(current):
            raise ValueError("active Task Gate binding removal is refused")
        for key, old in self._known.items():
            new = current[key]
            if _canonical(vars(old)) == _canonical(vars(new)):
                continue
            old_attempt, new_attempt = _attempt(old), _attempt(new)
            if old_attempt is None or new_attempt != old_attempt + 1:
                raise ValueError("fixed Task Gate binding changed outside a new attempt")
            if old.owner != new.owner or old.executor_ref != new.executor_ref:
                raise ValueError("fixed Task Gate owner changed")
        tools.executors.clear()
        tools.executors.update(executors)
        tools.collector_accesses.clear()
        tools.collector_accesses.update(collectors)
        authority.bindings.clear()
        authority.bindings.update(current)
        self.settings = settings
        self._known = current
        self._digest = sha256(_canonical(settings.model_dump(mode="json"))).hexdigest()
        return True


class RefreshingToolGate:
    """Compatibility view that refreshes before model/tool request assembly."""

    def __init__(self, gate, refresher, authority):
        self._gate, self._refresher, self._authority = gate, refresher, authority

    def _refresh(self):
        return self._refresher.refresh(self._gate, self._authority)

    def _assembly(self, access, ref):
        self._refresh()
        return self._gate._assembly(access, ref)

    async def invoke(self, access, request):
        self._refresh()
        return await self._gate.invoke(access, request)

    def close_operations(self, access, request):
        self._refresh()
        return self._gate.close_operations(access, request)

    def result_material(self, access, tool_call_id):
        self._refresh()
        return self._gate.result_material(access, tool_call_id)

    async def cancel(self, access, tool_call_id, *, operation_id, reason):
        self._refresh()
        return await self._gate.cancel(access, tool_call_id, operation_id=operation_id, reason=reason)

    def __getattr__(self, name):
        return getattr(self._gate, name)


class RefreshingExecutorAuthority:
    def __init__(self, authority, refresher, tools):
        self._authority, self._refresher, self._tools = authority, refresher, tools

    def check(self, access, executor_ref, payload):
        self._refresher.refresh(self._tools, self._authority)
        return self._authority.check(access, executor_ref, payload)


def build_gates():
    deployment = Deployment(load_settings("gates"))
    settings = deployment.settings
    ledger = AdmissionLedger(deployment.uow)
    admission = ToolAdmission(deployment.uow, registry=deployment.registry,
        ledger=ledger, approvals=deployment.approvals)
    bindings, executors, collectors = _gate_bindings(deployment, settings)
    tools = ToolGate(admission, registry=deployment.registry, ledger=ledger,
        artifacts=deployment.artifacts,
        evidence=EvidenceService(deployment.uow, deployment.artifacts),
        executors=executors, collector_accesses=collectors)
    authority = ExecutorPermitAuthority(admission, bindings=bindings)
    refresher = GateBindingRefresher(deployment, settings)
    refreshing_tools = RefreshingToolGate(tools, refresher, authority)
    refreshing_authority = RefreshingExecutorAuthority(authority, refresher, tools)
    client = httpx.AsyncClient(verify=deployment.tls, trust_env=False,
        follow_redirects=False, transport=httpx.AsyncHTTPTransport(verify=deployment.tls, retries=0))
    models = ModelGate(ModelAdmission(deployment.uow, registry=deployment.registry, ledger=ledger),
        registry=deployment.registry, ledger=ledger, key_resolver=KeyResolver(deployment),
        transport=HttpxModelTransport(client), tool_capabilities=ToolCapabilityResolver(refreshing_tools))
    app = create_app(token_verifier=deployment.verifier, routers=[
        create_model_router(models), create_tool_router(refreshing_tools),
        create_executor_host_router(refreshing_authority),
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
