"""Kali configuration: legacy bearer mode or public-key-only action mode."""

import importlib.util
import os
from pathlib import Path
import signal
from threading import Thread
import time

from deployment_common import read_file, token
from wuji_core.admission.remote_workspace import (
    ExecutorActionVerifier,
    ExecutorDeploymentBinding,
    RemoteToolAdmission,
)
from wuji_core.evidence.workspace_transfer import WorkspaceTransferHandler
from wuji_core.execution.process_supervisor import ProcessSupervisor
from wuji_core.http import JsonBoundaryLimits, strict_json_loads
from wuji_core.http.auth import TokenVerifier


def build_kali():
    config = strict_json_loads(read_file(os.environ.get("WUJI_DEPLOYMENT_CONFIG", "/config/kali.json")))
    version = config.get("schema_version")
    common = {
        "schema_version", "binding", "public_key_file", "issuer", "audience",
        "root", "receipt_root",
    }
    legacy_fields = {"tool_routes", "platform_url", "ca_file", "collector_token_file"}
    process_fields = {"action_subject", "process_limits", "image_digest"}
    if (
        version not in {"wuji.kali.deployment.v1", "wuji.kali.deployment.v2"}
        or set(config)
        != common | (process_fields if version.endswith("v2") else legacy_fields)
    ):
        raise ValueError("explicit Kali configuration without database/key material required")
    binding = ExecutorDeploymentBinding(**config["binding"])
    module_path = Path(__file__).resolve().parents[2] / "services/wuji-kali-executor/main.py"
    spec = importlib.util.spec_from_file_location("wuji_kali_service", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    public_key = read_file(config["public_key_file"])
    admission = None
    tool_routes = {}
    options = {}
    if version.endswith("v2"):
        limits = config["process_limits"]
        if set(limits) != {
            "max_active_execs", "max_output_bytes", "stop_grace_seconds"
        }:
            raise ValueError("fixed Kali process limits are required")
        verifier = ExecutorActionVerifier(
            public_key_pem=public_key,
            issuer=config["issuer"],
            audience=config["audience"],
            subject=config["action_subject"],
            binding=binding,
        )
        supervisor = ProcessSupervisor(
            root=config["root"],
            spool_root=Path(config["receipt_root"]) / "processes",
            max_active=limits["max_active_execs"],
            max_output_bytes=limits["max_output_bytes"],
            stop_grace_seconds=limits["stop_grace_seconds"],
        )

        def shutdown_pid1():
            def terminate():
                time.sleep(0.1)
                os.kill(os.getpid(), signal.SIGTERM)

            Thread(target=terminate, name="wuji-kali-exit", daemon=True).start()

        options = {
            "process_supervisor": supervisor,
            "action_verifier": verifier,
            "workspace_transfer_handler": WorkspaceTransferHandler(
                root=config["root"],
                environment_ref=binding.environment_ref,
                image_digest=config["image_digest"],
            ),
            "shutdown_callback": shutdown_pid1,
        }
    else:
        admission = RemoteToolAdmission(
            binding=binding,
            base_url=config["platform_url"],
            ca_file=config["ca_file"],
            bearer_token=lambda: token(config["collector_token_file"]),
        )
        tool_routes = config["tool_routes"]
    return module.create_kali_executor_app(
        token_verifier=TokenVerifier(public_key_pem=public_key,
            issuer=config["issuer"], audience=config["audience"]),
        binding=binding, admission=admission, root=config["root"],
        receipt_root=config["receipt_root"], tool_routes=tool_routes,
        json_limits=JsonBoundaryLimits(max_body_bytes=67108864),
        **options)
