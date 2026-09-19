"""Private launch composition. No HTTP process receives owner credentials."""

from functools import partial
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field

from deployment_common import read_file, token
from launch_adapter import DeploymentLaunchAdapter, KubernetesConfigMapStore
from task_model_keys import KubernetesTaskKeyStore, NativeTaskBudget
import task_launch
from wuji_core.execution.control import ControlService
from wuji_core.execution.launch import LaunchWorker
from wuji_core.http import strict_json_loads
from wuji_core.http.auth import TokenVerifier
from wuji_core.persistence.uow import AccessContext, UnitOfWork


class LaunchSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "wuji.launch-deployment.v1"
    owner_config_file: str
    service_token_file: str
    namespace: str = "wuji-vnext-test"
    agent_image: str = Field(pattern=r"^.+@sha256:[a-f0-9]{64}$")
    kali_image: str = Field(pattern=r"^.+@sha256:[a-f0-9]{64}$")
    runtime_origin: str
    gate_url: str
    evidence_ref: str = Field(min_length=1, max_length=256)
    agent_auth_dir: str = "/run/wuji/task-agent-auth"
    kali_auth_dir: str = "/run/wuji/task-kali-auth"
    deployment_auth_dir: str = "/run/wuji/deployment-signing"
    gates_auth_dir: str = "/run/wuji/gates-credentials"
    signing_key_file: str = "/run/wuji/deployment-signing/signing.key"
    gateway_url: str | None = None
    gateway_management_key_file: str | None = None
    gateway_ca_file: str | None = None
    lease_seconds: int = Field(default=30, ge=5, le=300)


class _OwnedAdapter:
    def __init__(self, adapter, api, gateway):
        self.adapter, self.api, self.gateway = adapter, api, gateway

    def __getattr__(self, name):
        return getattr(self.adapter, name)

    def close(self):
        if self.gateway is not None:
            self.gateway.close()
        self.api.close()


def build_launch_worker():
    from kubernetes import client, config

    path = os.environ.get("WUJI_LAUNCH_CONFIG", "/config/launch.json")
    settings = LaunchSettings.model_validate(strict_json_loads(read_file(path)))
    if settings.schema_version != "wuji.launch-deployment.v1" or settings.namespace != "wuji-vnext-test":
        raise ValueError("an isolated launch deployment is required")
    owner = strict_json_loads(read_file(settings.owner_config_file))
    if not isinstance(owner, dict) or len(owner.get("owner", [])) != 3:
        raise ValueError("a published owner template is required")
    verifier = TokenVerifier(public_key_pem=read_file(owner["public_key_file"]),
                             issuer=owner["identity"]["issuer"], audience=owner["identity"]["audience"])
    access = AccessContext(verifier.verify(token(settings.service_token_file)), "launch-worker")
    if "controller" not in access.principal.roles or "agent" in access.principal.roles or access.principal.tenant_id != owner["owner"][0]:
        raise ValueError("a matching platform controller is required")
    # Registration is a deployment-owner action scoped to one project. Restart
    # must not re-enable an operator-revoked worker row.
    with task_launch.owner_connection(owner) as connection:
        connection.execute(
            "INSERT INTO vnext.task_launch_worker(tenant_id,project_id,subject) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
            (*owner["owner"][:2], access.principal.subject),
        )
        enabled = connection.execute(
            "SELECT enabled FROM vnext.task_launch_worker WHERE tenant_id=%s AND project_id=%s AND subject=%s",
            (*owner["owner"][:2], access.principal.subject),
        ).fetchone()
        if not enabled or enabled[0] is not True:
            raise ValueError("launch worker was revoked")
    config.load_incluster_config()
    api = client.ApiClient()
    core = client.CoreV1Api(api)
    gateway = None
    try:
        budget = None
        if settings.gateway_url is not None:
            parsed = urlsplit(settings.gateway_url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
                raise ValueError("a verified gateway origin is required")
            if not settings.gateway_management_key_file or not settings.gateway_ca_file:
                raise ValueError("gateway management credential and trusted CA are required")
            import ssl
            gateway = httpx.Client(
                base_url=settings.gateway_url.rstrip("/"),
                headers={"Authorization": "Bearer " + token(settings.gateway_management_key_file)},
                verify=ssl.create_default_context(cafile=settings.gateway_ca_file),
                trust_env=False, follow_redirects=False, timeout=15,
            )
            budget = NativeTaskBudget(KubernetesTaskKeyStore(core), gateway)
        if task_launch.configured_evaluation_mode(owner) == "real_model" and budget is None:
            raise ValueError("real-model Tasks require native persistent gateway budgets")
        options = settings.model_dump(exclude={"owner_config_file", "service_token_file", "schema_version",
                                               "gateway_url", "gateway_management_key_file", "gateway_ca_file", "lease_seconds"})
        options.update(core_api=core, batch_api=client.BatchV1Api(api),
                       store=KubernetesConfigMapStore(core, namespace=settings.namespace), task_budget=budget)
        adapter = _OwnedAdapter(DeploymentLaunchAdapter({**owner, "namespace": settings.namespace}, options), api, gateway)
        uow = UnitOfWork(partial(task_launch.application_connection, owner))
        return LaunchWorker(uow, access=access, control=ControlService(uow), adapter=adapter,
                            worker_id=os.environ.get("POD_UID", "launch-local"), lease_seconds=settings.lease_seconds)
    except BaseException:
        if gateway is not None:
            gateway.close()
        api.close()
        raise
