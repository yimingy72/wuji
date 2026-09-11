"""Isolated native LiteLLM fixture; synthetic upstreams, no external network."""
from __future__ import annotations

import asyncio
import json
import os
import httpx
import secrets
import socket
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib.error import URLError
from urllib.request import urlopen
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "ghcr.io/berriai/litellm@sha256:c8756e7b9a61fe45df2ccb5b781d388c3b2f3a21ef9e4956630caef20f9f03aa"
LABEL = "wuji.test/native-gateway"
UPSTREAM = r'''
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
count = 0
lock = threading.Lock()
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def reply(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_GET(self):
        if self.path == '/stats':
            with lock: value = count
            return self.reply(200, {'inference_count': value})
        return self.reply(404, {'error': 'not found'})
    def do_POST(self):
        global count
        try:
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))))
        except Exception:
            return self.reply(400, {'error': 'invalid body'})
        path = self.path.split('?')[0]
        if path in ('/anthropic/v1/messages/count_tokens', '/anthropic/token-count', '/token-count'):
            return self.reply(200, {'input_tokens': 8})
        if path not in ('/openai/chat/completions', '/anthropic/v1/messages'):
            return self.reply(404, {'error': 'not found'})
        with lock: count += 1
        if path == '/openai/chat/completions':
            return self.reply(200, {'id':'chatcmpl-synthetic', 'object':'chat.completion', 'created':1,
                'model':body.get('model','synthetic'), 'choices':[{'index':0,
                'message':{'role':'assistant','content':'OK'},'finish_reason':'stop'}],
                'usage':{'prompt_tokens':8,'completion_tokens':1,'total_tokens':9}})
        return self.reply(200, {'id':'msg_synthetic','type':'message','role':'assistant',
            'model':body.get('model','synthetic'), 'content':[{'type':'text','text':'OK'}],
            'stop_reason':'end_turn','stop_sequence':None,
            'usage':{'input_tokens':8,'output_tokens':1}})
ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
'''


def command(args: list[str], *, timeout: float = 30) -> str:
    try:
        result = subprocess.run(["docker", *args], capture_output=True, text=True,
                                timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("native fixture Docker operation unavailable or timed out") from None
    if result.returncode:
        raise RuntimeError("native fixture Docker operation failed")
    return result.stdout.strip()


def private_write(path: Path, content: str) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(content)


class NativeGateway:
    def __init__(self, directory: Path):
        self.url = "http://127.0.0.1:18402"
        self.master_key = "sk-" + secrets.token_urlsafe(32)
        self.instance_id: UUID = uuid4()
        self.upstream_bases = ["http://upstream:8080/openai", "http://upstream:8080/anthropic"]
        self.directory = directory
        self.owner = str(self.instance_id)
        self.prefix = "wuji-native-" + self.instance_id.hex
        self.container_ids: list[str] = []
        self.network_id: str | None = None
        self.gateway_id: str | None = None
        self.upstream_id: str | None = None

    def owned(self, kind: str, identifier: str) -> bool:
        raw = command([kind, "inspect", "--format", '{{json .}}', identifier])
        data = json.loads(raw)
        labels = data.get("Labels", {}) if kind == "network" else data.get("Config", {}).get("Labels", {})
        return labels.get(LABEL) == self.owner

    def container(self, suffix: str, image: str, args: list[str], options: list[str]) -> str:
        # create returns a concrete ID before any start/readiness work.
        identifier = command(["container", "create", "--pull=never", "--name", self.prefix + "-" + suffix,
            "--label", f"{LABEL}={self.owner}", "--network", self.network_id,
            *options, image, *args])
        self.container_ids.append(identifier)
        command(["container", "start", identifier])
        return identifier

    def start(self) -> None:
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", 18402))
            except OSError:
                raise RuntimeError("native fixture port 18402 is already in use") from None
        # Cached images only: even setup cannot pull from a registry.
        for image in ("postgres:16-alpine", "python:3.12-slim", IMAGE):
            command(["image", "inspect", image])
        password = secrets.token_urlsafe(32)
        private_write(self.directory / "postgres.env", f"POSTGRES_DB=postgres\nPOSTGRES_USER=postgres\nPOSTGRES_PASSWORD={secrets.token_urlsafe(32)}\n")
        private_write(self.directory / "gateway.env", "\n".join([
            f"DATABASE_URL=postgresql://litellm:{password}@database:5432/litellm",
            f"LITELLM_MASTER_KEY={self.master_key}", f"LITELLM_SALT_KEY={secrets.token_urlsafe(32)}",
            "STORE_MODEL_IN_DB=True", "LITELLM_TELEMETRY=False", "DO_NOT_TRACK=1", "LITELLM_LOG=ERROR", "",
        ]))
        private_write(self.directory / "upstream.py", UPSTREAM)
        self.network_id = command(["network", "create", "--internal", "--label", f"{LABEL}={self.owner}", self.prefix])
        database_id = self.container("database", "postgres:16-alpine", [], [
            "--network-alias", "database", "--env-file", str(self.directory / "postgres.env")])
        deadline = time.monotonic() + 120
        while True:
            try:
                command(["exec", database_id, "pg_isready", "-U", "postgres", "-d", "postgres"], timeout=5)
                break
            except RuntimeError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("native fixture database readiness timed out") from None
                time.sleep(.5)
        sql_input = ("CREATE ROLE litellm LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD '" + password + "';\nCREATE DATABASE litellm OWNER litellm;\nREVOKE ALL ON DATABASE litellm FROM PUBLIC;\n")
        prepared = subprocess.run(["docker", "exec", "-i", database_id, "psql", "-U", "postgres", "-v", "ON_ERROR_STOP=1"],
                                  input=sql_input, capture_output=True, text=True, timeout=15)
        if prepared.returncode:
            raise RuntimeError("native fixture database role preparation failed")
        self.upstream_id = self.container("upstream", "python:3.12-slim", ["python", "/fixture/upstream.py"], [
            "--network-alias", "upstream", "--mount", f"type=bind,source={self.directory / 'upstream.py'},target=/fixture/upstream.py,readonly"])
        self.gateway_id = self.container("gateway", IMAGE, ["--config", "/etc/litellm/config.yaml", "--port", "4000", "--num_workers", "1"], [
            "--publish", "127.0.0.1:18402:4000", "--env-file", str(self.directory / "gateway.env"),
            "--mount", f"type=bind,source={ROOT / 'infra/kubernetes/model-gateway/config.yaml'},target=/etc/litellm/config.yaml,readonly"])
        self.wait_ready()

    def request(self, method, path, headers=None, body="", timeout=30):
        if not self.gateway_id:
            raise RuntimeError("native gateway not created")
        script = """import json,sys,urllib.request,urllib.error
v=json.load(sys.stdin)
r=urllib.request.Request('http://127.0.0.1:4000'+v['path'],data=v['body'].encode() if v['body'] else None,headers=v['headers'],method=v['method'])
try:
 with urllib.request.urlopen(r,timeout=v['timeout']) as response:
  print(json.dumps({'status':response.status,'headers':dict(response.headers),'body':response.read().decode()}))
except urllib.error.HTTPError as response:
 print(json.dumps({'status':response.code,'headers':dict(response.headers),'body':response.read().decode()}))
"""
        response = subprocess.run(["docker", "exec", "-i", self.gateway_id, "python", "-c", script],
            input=json.dumps({"method":method,"path":path,"headers":headers or {},"body":body,"timeout":timeout}),
            capture_output=True,text=True,timeout=timeout+5)
        if response.returncode:
            raise RuntimeError("native HTTP request not available")
        return json.loads(response.stdout)

    def transport(self):
        fixture = self
        class NativeTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                result = await asyncio.to_thread(fixture.request, request.method,
                    request.url.raw_path.decode(), dict(request.headers), request.content.decode())
                return httpx.Response(result['status'], headers=result['headers'], content=result['body'], request=request)
        return NativeTransport()

    def wait_ready(self) -> None:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            try:
                if self.request("GET", "/health/readiness", timeout=2)['status'] == 200:
                    return
            except (RuntimeError, OSError, subprocess.TimeoutExpired):
                pass
            time.sleep(.5)
        raise RuntimeError("native gateway readiness timed out; redacted diagnostics will be retained")

    def restart(self) -> None:
        if not self.gateway_id or not self.owned("container", self.gateway_id):
            raise RuntimeError("native gateway ownership could not be verified")
        command(["container", "restart", self.gateway_id], timeout=40)
        self.wait_ready()

    def request_count(self) -> int:
        if not self.upstream_id or not self.owned("container", self.upstream_id):
            raise RuntimeError("synthetic upstream ownership could not be verified")
        raw = command(["exec", self.upstream_id, "python", "-c",
            "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/stats',timeout=2).read().decode())"])
        return int(json.loads(raw)["inference_count"])

    def diagnostics(self):
        output = []
        redactions = [self.master_key, "synthetic-native-credential"]
        for file in self.directory.glob("*.env"):
            for line in file.read_text().splitlines():
                if "=" in line:
                    value = line.split("=", 1)[1]
                    if value and any(k in line.split("=", 1)[0] for k in ("KEY", "PASSWORD", "DATABASE_URL")):
                        redactions.append(value)
        for identifier in self.container_ids:
            result = subprocess.run(["docker", "logs", "--tail", "50", identifier], capture_output=True, text=True, timeout=10)
            message = result.stdout + result.stderr
            for value in sorted(redactions, key=len, reverse=True):
                message = message.replace(value, "[REDACTED]")
            output.append(message)
        target = ROOT / "artifacts/phase-1c-model-config/native-diagnostics.log"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(output))
        target.chmod(0o600)

    def close(self) -> None:
        failed = False
        for identifier in reversed(self.container_ids):
            try:
                if not self.owned("container", identifier):
                    failed = True
                    continue
                command(["container", "rm", "--force", "--volumes", identifier], timeout=30)
            except (RuntimeError, ValueError):
                failed = True
        if self.network_id:
            try:
                if self.owned("network", self.network_id):
                    command(["network", "rm", self.network_id])
                else:
                    failed = True
            except (RuntimeError, ValueError):
                failed = True
        if failed:
            raise RuntimeError("native fixture cleanup incomplete; ownership-safe removal required")


@contextmanager
def native_gateway() -> Iterator[NativeGateway]:
    with tempfile.TemporaryDirectory(prefix="wuji-native-") as directory:
        fixture = NativeGateway(Path(directory))
        try:
            fixture.start()
            yield fixture
        except BaseException:
            fixture.diagnostics()
            raise
        finally:
            fixture.close()
