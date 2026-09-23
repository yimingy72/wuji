"""Platform Gates plus the C0 permit callback, using real admission services.

The Gate reads its projected ConfigMap on each request.  A launch worker can
therefore add a Task executor without rolling this shared Deployment.  Refresh
is monotonic: removal is refused, an existing binding is immutable within an
attempt, and only a guarded next attempt may replace it.
"""

from hashlib import sha256
import asyncio
from contextlib import AsyncExitStack
import json
import re
from threading import RLock
from pathlib import Path
import time
from urllib.parse import urlsplit

import httpx

from deployment_common import Deployment, Settings, load_settings, token
from wuji_core.admission.ledger import AdmissionLedger
from wuji_core.admission.models import HttpxModelTransport, ModelAdmission, ModelGate
from wuji_core.admission.remote_workspace import (
    ExecutorActionSigner, ExecutorDeploymentBinding, ExecutorPermitAuthority,
    RemoteProcessExecutor, RemoteWorkspaceExecutor,
)
from wuji_core.admission.tools import ToolAdmission, ToolCapabilityResolver, ToolGate
from wuji_core.evidence.observations import EvidenceService
from wuji_core.evidence.workspace_bundles import WorkspaceBundleService
from wuji_core.evidence.workspace_transfer import WorkspaceTransferExecutor
from wuji_core.blackboard.knowledge_reads import KnowledgeReadService
from wuji_core.blackboard.notifications import BoardPublishService
from wuji_core.execution.process_gate import ProcessToolGate
from wuji_core.execution.workspace_gate import WorkspaceToolGate
from wuji_core.http import JsonBoundaryLimits, create_app
from wuji_core.http.executor_host import create_executor_host_router
from wuji_core.http.model_gate import create_model_router
from wuji_core.http.process_cleanup import create_process_cleanup_router
from wuji_core.http.tool_gate import create_tool_router
from wuji_core.http.native_mcp import create_native_mcp_app
from wuji_core.persistence.uow import DomainError


class KeyResolver:
    def __init__(self, deployment):
        self.deployment = deployment
        self._task_keys = self._key_api = None
        self._key_lock = RLock()

    def resolve(self, secret_ref):
        return self.deployment.secret(secret_ref).decode().strip()

    def resolve_for_task(self, secret_ref, *, tenant_id, task_id):
        settings = self.deployment.settings
        if settings.task_model_key_ref is None:
            return self.resolve(secret_ref)
        if secret_ref != settings.task_model_key_ref:
            raise ValueError("unregistered Task model key reference")
        if settings.task_model_keys_secret is not None:
            if settings.task_model_keys_secret != "task-model-keys":
                raise ValueError("unregistered Task key store")
            with self._key_lock:
                if self._task_keys is None:
                    from kubernetes import client, config
                    from task_model_keys import ReadOnlyKubernetesTaskKeys
                    config.load_incluster_config()
                    self._key_api = client.ApiClient()
                    self._task_keys = ReadOnlyKubernetesTaskKeys(client.CoreV1Api(self._key_api))
            return self._task_keys.resolve(tenant_id, task_id)
        from pathlib import Path
        from task_model_keys import task_key_filename

        directory = settings.task_model_keys_directory
        if not isinstance(directory, str) or not Path(directory).is_absolute():
            raise ValueError("an absolute Task key mount is required")
        return token(str(Path(directory) / task_key_filename(tenant_id, task_id)))

    def close(self):
        if self._key_api is not None:
            self._key_api.close()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _binding_key(binding):
    return tuple(binding.owner) + (binding.executor_ref,)


def _attempt(binding):
    prefix = "task-" + binding.task_id + "-a"
    value = binding.receiver_id.removeprefix(prefix)
    if binding.receiver_id.startswith(prefix) and re.fullmatch(r"[1-9][0-9]*", value):
        attempt = int(value)
        if binding.environment_ref == f"pod-environment-{binding.task_id}-a{attempt}":
            return attempt
    return None


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
            with self.path.open("rb") as stream:
                raw = stream.read(self.max_bytes + 1)
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
        action = entry.get("action")
        expected = {
            "binding",
            "base_url",
            "collector_token_file",
        } | ({"gate_token_file"} if action is None else {"action"})
        if set(entry) != expected:
            raise ValueError("fixed executor transport configuration required")
        binding = ExecutorDeploymentBinding(**entry["binding"])
        key = _binding_key(binding)
        if key in executors:
            raise ValueError("duplicate deployment executor")
        bindings.append(binding)
        if action is None:
            executors[key] = RemoteWorkspaceExecutor(
                binding=binding,
                base_url=entry["base_url"],
                ca_file=settings.ca_file,
                bearer_token=lambda path=entry["gate_token_file"]: token(path),
            )
        else:
            required = {
                "signing_key_ref", "kid", "issuer", "audience", "subject",
                "image_digest", "max_output_bytes",
            }
            if set(action) != required:
                raise ValueError("fixed executor action configuration required")
            if action["audience"] == settings.audience:
                raise ValueError("executor actions require a separate audience")
            signer = ExecutorActionSigner(
                private_key_pem=deployment.secret(action["signing_key_ref"]),
                kid=action["kid"], issuer=action["issuer"],
                audience=action["audience"], subject=action["subject"],
            )
            process = RemoteProcessExecutor(
                binding=binding, base_url=entry["base_url"],
                ca_file=settings.ca_file, signer=signer,
                max_output_bytes=action["max_output_bytes"],
            )
            workspace = WorkspaceTransferExecutor(
                binding=binding, base_url=entry["base_url"],
                ca_file=settings.ca_file, signer=signer,
                image_digest=action["image_digest"],
                max_request_bytes=64 * 1024 * 1024,
                max_response_bytes=64 * 1024 * 1024,
            )
            executors[key] = ExecutorMux(process, workspace)
        collectors[key] = deployment.access(entry["collector_token_file"])
    return bindings, executors, collectors


class ExecutorMux:
    def __init__(self, process, workspace):
        self.process, self.workspace = process, workspace
        self.max_output_bytes = process.max_output_bytes

    async def invoke(self, permit, *, action, parent_handle=None):
        return await self.process.invoke(
            permit, action=action, parent_handle=parent_handle
        )

    async def query_process(self, permit, *, cursor, max_bytes):
        return await self.process.query_process(
            permit, cursor=cursor, max_bytes=max_bytes
        )

    async def shutdown(self, **kwargs):
        return await self.process.shutdown(**kwargs)

    async def drain(self, **kwargs):
        return await self.process.drain(**kwargs)

    async def export(self, permit, request):
        return await self.workspace.export(permit, request)

    async def import_publication(self, permit, request):
        return await self.workspace.import_publication(permit, request)


class WorkspaceTransferDispatch:
    def __init__(self, gate):
        self.gate = gate

    def require_available(self, owner, executor_ref):
        key = (*owner, executor_ref)
        executor = self.gate.executors.get(key)
        if executor is None or not all(
            callable(getattr(executor, name, None))
            for name in ("export", "import_publication")
        ):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        return executor

    def _executor(self, permit):
        identity = permit.identity
        return self.require_available(
            (identity.tenant_id, identity.project_id, identity.task_id),
            permit.executor_ref,
        )

    async def export(self, permit, request):
        return await self._executor(permit).export(permit, request)

    async def import_publication(self, permit, request):
        return await self._executor(permit).import_publication(permit, request)


class GateBindingRefresher:
    """Apply an incrementally updated, trusted Gate ConfigMap in place."""

    def __init__(self, deployment, settings, *, path="/config/deployment.json"):
        self.deployment = deployment
        self.settings = settings
        self.reader = TrustedGateConfig(path)
        self._lock = RLock()
        # The initial Settings object was validated by load_settings.  Keep an
        # immutable snapshot of identity fields to guard later reloads.
        self._known = {key: binding for binding in _gate_bindings(deployment, settings)[0]
                       for key in (_binding_key(binding),)}
        self._digest = sha256(_canonical(settings.model_dump(mode="json"))).hexdigest()

    def refresh(self, tools, authority):
        with self._lock:
            try:
                return self._refresh(tools, authority)
            except Exception:
                self.reader._digest = None
                raise

    def _refresh(self, tools, authority):
        settings = self.reader.read()
        if settings is None:
            return False
        if settings.role != "gates" or settings.schema_version != "wuji.deployment.v1":
            raise ValueError("trusted Gate configuration role/version changed")
        if settings.model_dump(exclude={"executors"}) != self.settings.model_dump(exclude={"executors"}):
            raise ValueError("only Task executor bindings may refresh")
        bindings, executors, collectors = _gate_bindings(self.deployment, settings)
        current = {_binding_key(binding): binding for binding in bindings}
        if set(self._known) - set(current):
            raise ValueError("active Task Gate binding removal is refused")
        for key, old in self._known.items():
            new = current[key]
            old_entry = next(e for e in self.settings.executors if _binding_key(ExecutorDeploymentBinding(**e["binding"])) == key)
            new_entry = next(e for e in settings.executors if _binding_key(ExecutorDeploymentBinding(**e["binding"])) == key)
            if {k:v for k,v in old_entry.items() if k != "binding"} != {k:v for k,v in new_entry.items() if k != "binding"}:
                raise ValueError("existing Task executor transport changed")
            if _canonical(vars(old)) == _canonical(vars(new)):
                continue
            old_attempt, new_attempt = _attempt(old), _attempt(new)
            if old_attempt is None or new_attempt != old_attempt + 1:
                raise ValueError("fixed Task Gate binding changed outside a new attempt")
            if old.owner != new.owner or old.executor_ref != new.executor_ref:
                raise ValueError("fixed Task Gate owner changed")
        tools.executors = executors
        tools.collector_accesses = collectors
        authority.bindings = current
        self.settings = settings
        self._known = current
        self._digest = sha256(_canonical(settings.model_dump(mode="json"))).hexdigest()
        return True


class RefreshingToolGate:
    """Compatibility view that refreshes before model/tool request assembly."""

    def __init__(self, gate, refresher, authority, *, refresh_timeout_seconds=60.0,
                 refresh_interval_seconds=1.0, sleep=time.sleep,
                 monotonic=time.monotonic):
        if (not 0 < refresh_timeout_seconds <= 60
                or not 0 < refresh_interval_seconds <= refresh_timeout_seconds):
            raise ValueError("bounded Gate refresh interval required")
        self._gate, self._refresher, self._authority = gate, refresher, authority
        self._refresh_timeout = refresh_timeout_seconds
        self._refresh_interval = refresh_interval_seconds
        self._sleep, self._monotonic = sleep, monotonic

    def _refresh(self):
        return self._refresher.refresh(self._gate, self._authority)

    def _assembly(self, access, ref, *, assemble=None):
        deadline = self._monotonic() + self._refresh_timeout
        while True:
            self._refresh()
            try:
                return (assemble or self._gate._assembly)(access, ref)
            except DomainError as error:
                remaining = deadline - self._monotonic()
                if error.code != "CAPABILITY_UNAVAILABLE" or remaining <= 0:
                    raise
                # Kubernetes projects ConfigMap updates asynchronously.  A
                # newly admitted Task may reach the Gate before its executor
                # entry reaches this Pod, even though the API write succeeded.
                self._sleep(min(self._refresh_interval, remaining))

    async def invoke(self, access, request):
        self._refresh()
        return await self._gate.invoke(access, request)

    def close_operations(self, access, request):
        self._refresh()
        return self._gate.close_operations(access, request)

    def result_material(self, access, tool_call_id, *, representation=None):
        self._refresh()
        return self._gate.result_material(access, tool_call_id, representation=representation)

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
    refresh = lambda: refresher.refresh(tools, authority)
    knowledge_reads = KnowledgeReadService(
        deployment.uow, ledger=deployment.ledger, artifacts=deployment.artifacts
    )
    process_tools = ProcessToolGate(tools, refresh=refresh)
    workspace_transfer = WorkspaceTransferDispatch(tools)
    workspace_service = WorkspaceBundleService(
        deployment.uow,
        registry=deployment.registry,
        artifacts=deployment.artifacts,
        knowledge_reads=knowledge_reads,
        transfer=workspace_transfer,
    )
    workspace_tools = WorkspaceToolGate(
        tools, workspace_service, refresh=refresh
    )

    def assemble_model_tool(access, ref, kind, name):
        if kind == "process":
            return refreshing_tools._assembly(access, ref, assemble=process_tools._assembly)
        if kind == "workspace_bundle":
            def check_workspace(access, ref):
                _definition, registration = workspace_tools._definition(access, ref, name)
                identity = tools.registry.binding(access).identity
                return workspace_transfer.require_available(
                    (identity.tenant_id, identity.project_id, identity.task_id),
                    registration.ref,
                )
            return refreshing_tools._assembly(access, ref, assemble=check_workspace)
        return refreshing_tools._assembly(access, ref)
    board_publisher = BoardPublishService(
        deployment.uow,
        registry=deployment.registry,
        knowledge_reads=knowledge_reads,
    )
    client = httpx.AsyncClient(verify=deployment.tls, trust_env=False,
        follow_redirects=False, transport=httpx.AsyncHTTPTransport(verify=deployment.tls, retries=0))
    keys = KeyResolver(deployment)
    models = ModelGate(ModelAdmission(deployment.uow, registry=deployment.registry, ledger=ledger),
        registry=deployment.registry, ledger=ledger, key_resolver=keys,
        transport=HttpxModelTransport(client),
        tool_capabilities=ToolCapabilityResolver(refreshing_tools, assemble=assemble_model_tool))
    app = create_app(token_verifier=deployment.verifier, routers=[
        create_model_router(models), create_tool_router(refreshing_tools),
        create_executor_host_router(refreshing_authority),
        create_process_cleanup_router(process_tools),
    ], json_limits=JsonBoundaryLimits(max_body_bytes=settings.max_transport_bytes))
    mcp_origin = urlsplit(settings.tool_gate_url or "")
    if (
        mcp_origin.scheme not in {"http", "https"}
        or not mcp_origin.hostname
        or mcp_origin.username
        or mcp_origin.password
        or mcp_origin.query
        or mcp_origin.fragment
        or mcp_origin.path.rstrip("/") != "/internal/v2/tool-calls"
    ):
        raise ValueError("a fixed native MCP Gate origin is required")
    mcp_origin_url = mcp_origin._replace(path="", query="", fragment="").geturl().rstrip("/")
    native_mcp = create_native_mcp_app(
        token_verifier=deployment.verifier,
        process_gate=process_tools,
        board_publisher=board_publisher,
        workspace_gate=workspace_tools,
        allowed_hosts=[mcp_origin.netloc],
        allowed_origins=[mcp_origin_url],
        json_limits=JsonBoundaryLimits(max_body_bytes=settings.max_transport_bytes),
    )

    # ASGI wrapper closes the only pooled upstream HTTP client at service exit.
    async def application(scope, receive, send):
        if scope["type"] == "http":
            if scope.get("path", "").rstrip("/") == "/internal/v2/mcp":
                return await native_mcp.app(scope, receive, send)
            return await app(scope, receive, send)
        if scope["type"] != "lifespan":
            return await app(scope, receive, send)
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(
                native_mcp.starlette.router.lifespan_context(native_mcp.starlette)
            )

            async def reconcile():
                while True:
                    try:
                        await process_tools.reconcile_registered(limit=32)
                    except Exception:
                        pass
                    await asyncio.sleep(1)

            reconciliation = asyncio.create_task(reconcile())
            try:
                while True:
                    message = await receive()
                    if message["type"] == "lifespan.startup":
                        await send({"type": "lifespan.startup.complete"})
                    elif message["type"] == "lifespan.shutdown":
                        await client.aclose()
                        keys.close()
                        await send({"type": "lifespan.shutdown.complete"})
                        return
            finally:
                reconciliation.cancel()
                try:
                    await reconciliation
                except asyncio.CancelledError:
                    pass
    return application
