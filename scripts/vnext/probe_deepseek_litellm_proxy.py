#!/usr/bin/env python3
"""Run the real LiteLLM Proxy HTTP path through the A6 hook and fake peer."""

from __future__ import annotations

import json
import os
import socket
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from probe_deepseek_litellm import FakeProvider


ALIAS = "wuji-deepseek-observe-v1"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def http_json(url: str, *, body: dict | None = None, token: str | None = None) -> tuple[int, bytes]:
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} if data is not None else {}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except urllib.error.URLError:
        return 0, b""


def main() -> None:
    provider = FakeProvider()
    port = free_port()
    master_key = "sk-a6-proxy-fake"
    config = {
        "model_list": [
            {
                "model_name": ALIAS,
                "litellm_params": {
                    "model": "deepseek/deepseek-flash",
                    "api_base": provider.url,
                    "api_key": "fake-provider-key",
                    "timeout": 15,
                    "max_retries": 0,
                },
                "model_info": {
                    "mode": "chat",
                    "input_cost_per_token": 0.0000003,
                    "cache_read_input_token_cost": 0.000000006,
                    "cache_creation_input_token_cost": 0.0000003,
                    "output_cost_per_token": 0.0000012,
                },
            }
        ],
        "general_settings": {"master_key": "os.environ/LITELLM_MASTER_KEY"},
        "litellm_settings": {
            "callbacks": ["ops.vnext.litellm_hooks.proxy_handler_instance"],
            "telemetry": False,
            "num_retries": 0,
            "cache": False,
        },
        "router_settings": {"num_retries": 0, "fallbacks": []},
    }
    with tempfile.TemporaryDirectory(prefix="wuji-a6-proxy-") as directory:
        config_path = Path(directory) / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        log_path = Path(directory) / "proxy.log"
        with log_path.open("w", encoding="utf-8") as log:
            env = {
                **os.environ,
                "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
                "LITELLM_MASTER_KEY": master_key,
                "LITELLM_LOG": "ERROR",
                "NO_COLOR": "1",
                "DO_NOT_TRACK": "1",
                "OTEL_SDK_DISABLED": "true",
            }
            process = subprocess.Popen(
                [shutil.which("litellm") or str(Path(sys.executable).with_name("litellm")), "--config", str(config_path), "--port", str(port), "--num_workers", "1"],
                cwd=Path(__file__).resolve().parents[2],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                status, _ = http_json(f"http://127.0.0.1:{port}/health/readiness")
                if status == 200:
                    break
                if process.poll() is not None:
                    raise RuntimeError(log_path.read_text(encoding="utf-8")[-8000:])
                time.sleep(0.25)
            else:
                raise RuntimeError("LiteLLM Proxy readiness timed out")

            status, response = http_json(
                f"http://127.0.0.1:{port}/v1/chat/completions",
                token=master_key,
                body={
                    "model": ALIAS,
                    "messages": [{"role": "user", "content": "fixture"}],
                    "stream": True,
                    "stream_options": {"include_usage": True},
                    "parallel_tool_calls": False,
                    "max_completion_tokens": 32,
                },
            )
            if status != 200:
                raise AssertionError(f"proxy status={status} body={response[:4000]!r}")
            if b"data: [DONE]" not in response:
                raise AssertionError("proxy response did not contain terminal SSE")
            if provider.request is None:
                raise AssertionError("fake provider observed no outbound request")
            body = provider.request["body"]
            assert isinstance(body, dict)
            assert body["model"] == "deepseek-flash", body
            assert body["max_tokens"] == 32, body
            assert "max_completion_tokens" not in body, body
            assert body["thinking"] == {"type": "disabled"}, body
            before_rejection = provider.request
            rejected = []
            for invalid in (
                {"max_completion_tokens": 32, "max_tokens": 31},
                {"max_completion_tokens": 4097},
            ):
                invalid_body = {
                    "model": ALIAS,
                    "messages": [{"role": "user", "content": "fixture"}],
                    "stream": True,
                    **invalid,
                }
                invalid_status, _ = http_json(
                    f"http://127.0.0.1:{port}/v1/chat/completions",
                    token=master_key,
                    body=invalid_body,
                )
                rejected.append(invalid_status)
                if invalid_status == 200:
                    raise AssertionError(f"invalid request was accepted: {invalid}")
                if provider.request != before_rejection:
                    raise AssertionError("invalid request reached the fake provider")
            print(
                json.dumps(
                    {
                        "status": "pass",
                        "proxy_http": status,
                        "rejected_statuses": rejected,
                        "provider": provider.request,
                    },
                    sort_keys=True,
                )
            )
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            provider.close()


if __name__ == "__main__":
    main()
