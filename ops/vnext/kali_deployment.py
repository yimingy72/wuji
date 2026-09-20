"""Kali process configuration: public verification material and collector bearer only."""

import importlib.util
import os
from pathlib import Path

from deployment_common import read_file, token
from wuji_core.admission.remote_workspace import ExecutorDeploymentBinding, RemoteToolAdmission
from wuji_core.http import JsonBoundaryLimits, strict_json_loads
from wuji_core.http.auth import TokenVerifier


def build_kali():
    config = strict_json_loads(read_file(os.environ.get("WUJI_DEPLOYMENT_CONFIG", "/config/kali.json")))
    required = {"schema_version", "binding", "tool_routes", "platform_url", "ca_file", "collector_token_file",
                "public_key_file", "issuer", "audience", "root", "receipt_root"}
    if set(config) != required or config["schema_version"] != "wuji.kali.deployment.v1":
        raise ValueError("explicit Kali configuration without database/key material required")
    binding = ExecutorDeploymentBinding(**config["binding"])
    admission = RemoteToolAdmission(binding=binding, base_url=config["platform_url"],
        ca_file=config["ca_file"], bearer_token=lambda: token(config["collector_token_file"]))
    module_path = Path(__file__).resolve().parents[2] / "services/wuji-kali-executor/main.py"
    spec = importlib.util.spec_from_file_location("wuji_kali_service", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.create_kali_executor_app(
        token_verifier=TokenVerifier(public_key_pem=read_file(config["public_key_file"]),
            issuer=config["issuer"], audience=config["audience"]),
        binding=binding, admission=admission, root=config["root"],
        receipt_root=config["receipt_root"], tool_routes=config["tool_routes"],
        json_limits=JsonBoundaryLimits(max_body_bytes=1048576))
