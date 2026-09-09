"""Shared local lifecycle primitives for the isolated Phase 1A platform."""

from __future__ import annotations

import base64
import fcntl
import json
import os
import secrets
import select
import signal
import socket
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

import yaml

from wuji_api.run_file import (
    create_run_file,
    load_run_file,
    mutate_run_file,
    run_file_lock,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = REPOSITORY_ROOT / "work" / "run"
ARTIFACT_ROOT = REPOSITORY_ROOT / "artifacts" / "phase-1a" / "platform"
KUBECTL_CONTEXT = "docker-desktop"
DOCKER_CONTEXT = "desktop-linux"
OWNER_LABEL = "phase-1a"
SECRET_NAME = "wuji-platform-secrets"
EXPECTED_IMAGE_DIGESTS = {
    "postgres": "sha256:7341002d2b8c7c5bdd7542a671a95b36196c0b5b888daf454ae4fc33ba5346d7",
    "keycloak": "sha256:c2a17fe407e892196d0b7cf9cef54e60952d6c372a9205f661a9efa0911463b0",
}


class LifecycleError(RuntimeError):
    def __init__(self, message: str, *, code: str = "LIFECYCLE_ERROR"):
        self.code = code
        super().__init__(message)


def json_output(payload: Mapping[str, Any], *, ok: bool = True) -> str:
    body: dict[str, Any] = {"ok": ok}
    body.update(payload)
    return json.dumps(body, separators=(",", ":"), sort_keys=True)


def safe_error_payload(*, run_id: str | None, error: BaseException) -> dict[str, Any]:
    known = isinstance(error, LifecycleError)
    return {
        "ok": False,
        "run_id": run_id,
        "error": {
            "code": error.code if known else error.__class__.__name__,
            "message": str(error) if known else "platform operation failed safely",
        },
    }


def run_command(
    command: Sequence[str],
    *,
    input_text: str | None = None,
    timeout: float = 300,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(command),
        cwd=REPOSITORY_ROOT,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        env=None if env is None else dict(env),
        check=False,
    )
    if result.returncode:
        raise LifecycleError(f"command failed without a successful exit: {command[0]}")
    return result


def git_sha() -> str:
    return run_command(["git", "rev-parse", "HEAD"], timeout=10).stdout.strip()


def private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def private_file(path: Path, *, truncate: bool = False) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True, mode=0o700)
    if path.is_symlink():
        raise LifecycleError("private output path must not be a symbolic link")
    flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if truncate else 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
    finally:
        os.close(descriptor)


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, separators=(",", ":"), sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        temporary.unlink(missing_ok=True)


def initialize_event_file(path: Path) -> Path:
    if not path.is_absolute():
        raise LifecycleError("--event-file must be absolute")
    path = path.resolve()
    private_file(path, truncate=True)
    return path


def append_event(path: Path, event: Mapping[str, Any]) -> None:
    encoded = (json.dumps(event, separators=(",", ":"), sort_keys=True) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND)
    try:
        if os.write(descriptor, encoded) != len(encoded):
            raise LifecycleError("event record was not written completely")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def load_manifest(path: Path, *, require_source_sha: bool = True) -> dict[str, Any]:
    try:
        _, payload = load_run_file(path, require_source_sha=require_source_sha)
        return payload
    except (OSError, ValueError, PermissionError) as error:
        raise LifecycleError("private run file validation failed") from error


def load_manifest_locked(path: Path, *, require_source_sha: bool = True) -> dict[str, Any]:
    with run_file_lock(path):
        return load_manifest(path, require_source_sha=require_source_sha)


def create_manifest(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return create_run_file(path, payload)
    except (OSError, ValueError, PermissionError) as error:
        raise LifecycleError("private run file creation failed") from error


def mutate_manifest(
    path: Path,
    mutate: Callable[[dict[str, Any]], Any],
    *,
    require_source_sha: bool = True,
) -> tuple[dict[str, Any], Any]:
    try:
        return mutate_run_file(path, mutate, require_source_sha=require_source_sha)
    except (OSError, ValueError, PermissionError) as error:
        raise LifecycleError("private run file update failed") from error


@contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    private_directory(path.parent)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise LifecycleError(
                "another platform lifecycle owns this lock", code="LOCK_CONFLICT"
            ) from error
        os.ftruncate(descriptor, 0)
        os.write(descriptor, f"{os.getpid()}\n".encode())
        yield
    finally:
        os.close(descriptor)


def require_context() -> None:
    kubectl = run_command(["kubectl", "config", "current-context"], timeout=10).stdout.strip()
    docker = run_command(["docker", "context", "show"], timeout=10).stdout.strip()
    if kubectl != KUBECTL_CONTEXT or docker != DOCKER_CONTEXT:
        raise LifecycleError("Docker Desktop context does not match the Phase 1A plan")
    run_command(["kubectl", "--context", KUBECTL_CONTEXT, "get", "nodes"], timeout=30)


def preflight_ports(ports: Sequence[int]) -> None:
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError as error:
                raise LifecycleError(
                    f"required loopback port {port} is already owned", code="PORT_CONFLICT"
                ) from error


def wait_port(port: int, *, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.5)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.2)
    raise LifecycleError(f"loopback port {port} did not become ready")


def wait_http(url: str, *, expected: int = 200, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            request = Request(url, headers={"User-Agent": "wuji-lifecycle/1"})
            with urlopen(request, timeout=2) as response:
                if response.status == expected:
                    return
        except HTTPError as error:
            if error.code == expected:
                return
        except (OSError, URLError):
            pass
        time.sleep(0.25)
    raise LifecycleError("HTTP dependency did not reach the required status")


def process_start_marker(pid: int) -> str:
    result = subprocess.run(
        ["ps", "-o", "lstart=", "-p", str(pid)], text=True, capture_output=True, check=False
    )
    if result.returncode or not result.stdout.strip():
        raise LifecycleError("owned process is no longer running")
    return result.stdout.strip()


def process_command(pid: int) -> str:
    result = subprocess.run(
        ["ps", "-ww", "-o", "command=", "-p", str(pid)],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def process_state(pid: int) -> str:
    result = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(pid)], text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def process_record(
    process: subprocess.Popen[Any],
    *,
    command: Sequence[str],
    command_marker: str,
    **fields: Any,
) -> dict[str, Any]:
    observed = ""
    stable_observations = 0
    for _ in range(30):
        current = process_command(process.pid)
        if current and current == observed:
            stable_observations += 1
            if stable_observations >= 5:
                break
        else:
            stable_observations = 0
        observed = current
        time.sleep(0.01)
    if not observed:
        raise LifecycleError("spawned process exited before it could be registered")
    return {
        "pid": process.pid,
        "process_group": os.getpgid(process.pid),
        "start_id": process_start_marker(process.pid),
        "command_marker": command_marker,
        "command": list(command),
        "observed_command": observed,
        "lifecycle_state": "running",
        **fields,
    }


def record_is_owned(record: Mapping[str, Any]) -> bool:
    try:
        pid = int(record["pid"])
        try:
            reaped, _ = os.waitpid(pid, os.WNOHANG)
            if reaped == pid:
                return False
        except ChildProcessError:
            pass
        if "Z" in process_state(pid):
            return False
        os.kill(pid, 0)
        if process_start_marker(pid) != record["start_id"]:
            return False
        if os.getpgid(pid) != int(record["process_group"]):
            return False
        return process_command(pid) == record["observed_command"]
    except (KeyError, OSError, TypeError, ValueError, LifecycleError):
        return False


def process_group_exists(process_group: int) -> bool:
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def reap_process_if_child(pid: int) -> None:
    try:
        os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        pass


def _forward_operation_lock_path(run_path: Path, service: str) -> Path:
    if service not in {"postgres", "keycloak"}:
        raise LifecycleError("unsupported port-forward service")
    if not run_path.is_absolute() or run_path.is_symlink():
        raise LifecycleError("forward operation requires an absolute private run file")
    return run_path.with_name(f".{run_path.name}.{service}-forward.lock")


@contextmanager
def forward_operation_lock(run_path: Path, service: str) -> Iterator[None]:
    lock_path = _forward_operation_lock_path(run_path, service)
    if lock_path.is_symlink():
        raise LifecycleError("forward operation lock must not be a symbolic link")
    descriptor = os.open(
        lock_path,
        os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def terminate_record(
    record: Mapping[str, Any],
    *,
    timeout: float = 8,
    process: subprocess.Popen[Any] | None = None,
) -> bool:
    if not record_is_owned(record):
        return False
    pid = int(record["pid"])
    process_group = int(record["process_group"])
    if process_group != os.getpgid(pid) or process_group == os.getpgrp():
        raise LifecycleError("owned process group could not be safely terminated")
    try:
        os.killpg(process_group, signal.SIGTERM)
    except ProcessLookupError:
        return True
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process is not None:
            process.poll()
        else:
            reap_process_if_child(pid)
        if not process_group_exists(process_group):
            return True
        time.sleep(0.1)
    if process_group_exists(process_group):
        os.killpg(process_group, signal.SIGKILL)
    kill_deadline = time.monotonic() + 2
    while time.monotonic() < kill_deadline:
        if process is not None:
            process.poll()
        else:
            reap_process_if_child(pid)
        if not process_group_exists(process_group):
            return True
        time.sleep(0.05)
    raise LifecycleError("owned process group did not terminate")


def spawn_logged(
    command: Sequence[str],
    *,
    log_path: Path,
    command_marker: str,
    env: Mapping[str, str] | None = None,
) -> tuple[subprocess.Popen[Any], dict[str, Any]]:
    private_file(log_path)
    stream = log_path.open("a", encoding="utf-8")
    process: subprocess.Popen[Any] | None = None
    ready_read, ready_write = os.pipe()
    try:
        launcher = [
            os.fspath(REPOSITORY_ROOT / ".venv" / "bin" / "python"),
            os.fspath(REPOSITORY_ROOT / "scripts" / "platform" / "exec-child.py"),
            *command,
        ]
        child_environment = dict(os.environ if env is None else env)
        child_environment["WUJI_CHILD_EXEC_READY_FD"] = str(ready_write)
        process = subprocess.Popen(
            launcher,
            cwd=REPOSITORY_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=subprocess.STDOUT,
            env=child_environment,
            start_new_session=True,
            pass_fds=(ready_write,),
        )
        os.close(ready_write)
        ready_write = -1
        readable, _, _ = select.select([ready_read], [], [], 2)
        if not readable or os.read(ready_read, 1) != b"":
            raise LifecycleError("child launcher did not complete its exec handshake")
        record = process_record(
            process,
            command=command,
            command_marker=command_marker,
            log_path=str(log_path),
        )
        return process, record
    except BaseException:
        if process is not None and process.poll() is None:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        raise
    finally:
        os.close(ready_read)
        if ready_write >= 0:
            os.close(ready_write)
        stream.close()


@contextmanager
def blocked_lifecycle_signals() -> Iterator[None]:
    blocked = {signal.SIGINT, signal.SIGTERM}
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, blocked)
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def spawn_registered(
    run_path: Path,
    name: str,
    command: Sequence[str],
    *,
    log_path: Path,
    command_marker: str,
    env: Mapping[str, str] | None = None,
    fields: Mapping[str, Any] | None = None,
) -> tuple[subprocess.Popen[Any], dict[str, Any]]:
    process: subprocess.Popen[Any] | None = None
    record: dict[str, Any] | None = None
    try:
        with blocked_lifecycle_signals():
            process, record = spawn_logged(
                command,
                log_path=log_path,
                command_marker=command_marker,
                env=env,
            )
            if fields:
                record.update(fields)
            register_process(run_path, name, record)
        return process, record
    except BaseException:
        if record is not None:
            terminate_record(record, process=process)
        elif process is not None and process.poll() is None:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        raise


def register_process(run_path: Path, name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    def register(run: dict[str, Any]) -> None:
        run["processes"][name] = dict(record)

    updated, _ = mutate_manifest(run_path, register)
    event_path = updated.get("control", {}).get("event_file")
    if event_path:
        append_event(
            Path(event_path),
            {
                "event": "process_registered",
                "name": name,
                "pid": record["pid"],
                "pgid": record["process_group"],
                "start_marker": record["start_id"],
            },
        )
    return updated


def update_process(run_path: Path, name: str, changes: Mapping[str, Any]) -> dict[str, Any]:
    def update(run: dict[str, Any]) -> None:
        record = run["processes"].get(name)
        if not isinstance(record, dict):
            raise LifecycleError("process record is missing")
        record.update(changes)

    updated, _ = mutate_manifest(run_path, update)
    return updated


def _kubectl_json(arguments: Sequence[str]) -> dict[str, Any]:
    output = run_command(["kubectl", "--context", KUBECTL_CONTEXT, *arguments], timeout=60).stdout
    try:
        return json.loads(output)
    except json.JSONDecodeError as error:
        raise LifecycleError("Kubernetes returned invalid JSON") from error


def _read_optional_resource(
    kind: str, name: str, *, namespace: str | None = None
) -> dict[str, Any] | None:
    command = ["kubectl", "--context", KUBECTL_CONTEXT]
    if namespace is not None:
        command.extend(["--namespace", namespace])
    command.extend(["get", kind, name, "--ignore-not-found=true", "-o", "json"])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        raise LifecycleError(
            "Kubernetes ownership read failed", code="KUBERNETES_OWNERSHIP_READ_FAILED"
        )
    if not result.stdout.strip():
        return None
    try:
        resource = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise LifecycleError("Kubernetes ownership read returned invalid JSON") from error
    metadata = resource.get("metadata", {})
    if metadata.get("name") != name or (namespace and metadata.get("namespace") != namespace):
        raise LifecycleError("Kubernetes ownership read returned another object")
    return resource


def require_owned_resource(
    kind: str, name: str, *, namespace: str | None = None
) -> dict[str, Any] | None:
    resource = _read_optional_resource(kind, name, namespace=namespace)
    if resource is None:
        return None
    labels = resource.get("metadata", {}).get("labels", {})
    if labels.get("wuji.dev/owner") != OWNER_LABEL:
        raise LifecycleError(
            "existing Kubernetes object has unexpected ownership",
            code="KUBERNETES_OWNERSHIP_MISMATCH",
        )
    return resource


def _render_resources(overlay: str) -> list[dict[str, Any]]:
    overlay_path = REPOSITORY_ROOT / "infra" / "kubernetes" / "overlays" / overlay
    rendered = run_command(
        ["kubectl", "--context", KUBECTL_CONTEXT, "kustomize", str(overlay_path)], timeout=30
    ).stdout
    resources = [value for value in yaml.safe_load_all(rendered) if isinstance(value, dict)]
    expected_kinds = {"Namespace", "Secret", "Deployment", "Service", "ConfigMap", "PersistentVolumeClaim"}
    for resource in resources:
        if resource.get("kind") not in expected_kinds - {"Secret"}:
            raise LifecycleError("Kustomize produced an unexpected object kind")
        labels = resource.get("metadata", {}).get("labels", {})
        if labels.get("wuji.dev/owner") != OWNER_LABEL:
            raise LifecycleError("desired Kubernetes object lacks the ownership label")
    return resources


def _cluster_secrets(namespace: str) -> dict[str, str] | None:
    secret = require_owned_resource("secret", SECRET_NAME, namespace=namespace)
    if secret is None:
        return None
    try:
        values = {
            key: base64.b64decode(value, validate=True).decode("utf-8")
            for key, value in secret.get("data", {}).items()
        }
    except (ValueError, UnicodeDecodeError) as error:
        raise LifecycleError("existing platform Secret is malformed") from error
    required = {
        "postgres-admin-password",
        "keycloak-db-password",
        "keycloak-admin-username",
        "keycloak-admin-password",
    }
    if set(values) != required:
        raise LifecycleError("existing platform Secret has an unexpected shape")
    return values


def ensure_infrastructure(namespace: str, overlay: str) -> dict[str, str]:
    require_context()
    resources = _render_resources(overlay)
    desired_namespace = next(
        (
            resource
            for resource in resources
            if resource.get("kind") == "Namespace"
            and resource.get("metadata", {}).get("name") == namespace
        ),
        None,
    )
    if desired_namespace is None:
        raise LifecycleError("overlay does not declare its expected namespace")

    existing_namespace = require_owned_resource("namespace", namespace)
    if existing_namespace is not None:
        for resource in resources:
            kind = str(resource["kind"]).lower()
            name = str(resource["metadata"]["name"])
            if kind != "namespace":
                require_owned_resource(kind, name, namespace=namespace)
        cluster_credentials = _cluster_secrets(namespace)
    else:
        cluster_credentials = None

    namespace_manifest = (
        REPOSITORY_ROOT / "infra" / "kubernetes" / "overlays" / overlay / "namespace.yaml"
    )
    if existing_namespace is None:
        run_command(
            ["kubectl", "--context", KUBECTL_CONTEXT, "apply", "-f", str(namespace_manifest)]
        )
        if require_owned_resource("namespace", namespace) is None:
            raise LifecycleError("created namespace could not be verified")
        cluster_credentials = _cluster_secrets(namespace)

    if cluster_credentials is None:
        cluster_credentials = {
            "postgres-admin-password": secrets.token_urlsafe(32),
            "keycloak-db-password": secrets.token_urlsafe(32),
            "keycloak-admin-username": "wuji-admin",
            "keycloak-admin-password": secrets.token_urlsafe(32),
        }
        secret_manifest = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": SECRET_NAME,
                "namespace": namespace,
                "labels": {
                    "app.kubernetes.io/part-of": "wuji",
                    "app.kubernetes.io/managed-by": "wuji-platform",
                    "wuji.dev/owner": OWNER_LABEL,
                },
            },
            "type": "Opaque",
            "stringData": cluster_credentials,
        }
        run_command(
            [
                "kubectl",
                "--context",
                KUBECTL_CONTEXT,
                "--namespace",
                namespace,
                "apply",
                "-f",
                "-",
            ],
            input_text=json.dumps(secret_manifest),
        )

    run_command(
        [
            "kubectl",
            "--context",
            KUBECTL_CONTEXT,
            "apply",
            "-k",
            str(REPOSITORY_ROOT / "infra" / "kubernetes" / "overlays" / overlay),
        ]
    )
    wait_infrastructure(namespace)
    pvc = require_owned_resource("pvc", "postgres-data", namespace=namespace)
    if pvc is None or pvc.get("status", {}).get("phase") != "Bound":
        raise LifecycleError("PostgreSQL persistent volume is not bound")
    _verify_runtime_resources(namespace)
    return cluster_credentials


def _verify_runtime_resources(namespace: str) -> None:
    for kind, name in (
        ("deployment", "postgres"),
        ("deployment", "keycloak"),
        ("service", "postgres"),
        ("service", "keycloak"),
        ("pvc", "postgres-data"),
    ):
        if require_owned_resource(kind, name, namespace=namespace) is None:
            raise LifecycleError("required Kubernetes object is absent")
    for application, digest in EXPECTED_IMAGE_DIGESTS.items():
        pods = _kubectl_json(
            [
                "--namespace",
                namespace,
                "get",
                "pod",
                "--selector",
                f"app.kubernetes.io/name={application}",
                "-o",
                "json",
            ]
        ).get("items", [])
        if len(pods) != 1:
            raise LifecycleError("runtime deployment does not have exactly one pod")
        pod = pods[0]
        if pod.get("metadata", {}).get("labels", {}).get("wuji.dev/owner") != OWNER_LABEL:
            raise LifecycleError("runtime pod has unexpected ownership")
        statuses = pod.get("status", {}).get("containerStatuses", [])
        if len(statuses) != 1 or digest not in statuses[0].get("imageID", ""):
            raise LifecycleError("runtime image does not match the pinned linux/amd64 digest")
        node_name = pod.get("spec", {}).get("nodeName")
        node = _kubectl_json(["get", "node", node_name, "-o", "json"])
        if node.get("metadata", {}).get("labels", {}).get("kubernetes.io/arch") != "amd64":
            raise LifecycleError("runtime pod is not scheduled to linux/amd64")


def wait_infrastructure(namespace: str) -> None:
    for deployment in ("postgres", "keycloak"):
        run_command(
            [
                "kubectl",
                "--context",
                KUBECTL_CONTEXT,
                "--namespace",
                namespace,
                "rollout",
                "status",
                f"deployment/{deployment}",
                "--timeout=300s",
            ],
            timeout=330,
        )


def replace_database(url: str, database: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, f"/{database}", "", ""))


def database_url(host: str, port: int, database: str, role: str, password: str) -> str:
    return (
        f"postgresql+psycopg://{quote(role, safe='')}:{quote(password, safe='')}"
        f"@{host}:{port}/{database}"
    )


def minimal_environment() -> dict[str, str]:
    allowed = ("HOME", "LANG", "LC_ALL", "PATH", "TMPDIR", "SYSTEMROOT")
    return {key: os.environ[key] for key in allowed if key in os.environ}


def api_environment(run: Mapping[str, Any], *, profile: str, ttl: int = 900) -> dict[str, str]:
    if profile not in {"keycloak", "issuer_fixture"}:
        raise LifecycleError("unknown API identity profile")
    if not 1 <= ttl <= 900:
        raise LifecycleError("cursor lifetime must be between 1 and 900 seconds")
    local_profile = "local-test" if run["namespace"] == "wuji-test" else "local-dev"
    if local_profile != "local-test" and ttl != 900:
        raise LifecycleError("development cursor lifetime is fixed at 900 seconds")
    identity = run["credentials"]["oidc_keycloak" if profile == "keycloak" else "oidc_fixture"]
    issuer = run["realm"]["issuer"] if profile == "keycloak" else run["urls"]["issuer_fixture"]
    environment = minimal_environment()
    environment.update(
        {
            "PYTHONUNBUFFERED": "1",
            "WUJI_PROFILE": local_profile,
            "WUJI_AUTH_DATABASE_URL": run["credentials"]["database"]["auth_dsn"],
            "WUJI_PROJECT_DATABASE_URL": run["credentials"]["database"]["project_dsn"],
            "WUJI_PUBLIC_ORIGIN": run["urls"]["web"],
            "WUJI_OIDC_ISSUER": issuer,
            "WUJI_OIDC_CLIENT_ID": identity["client_id"],
            "WUJI_OIDC_CLIENT_SECRET": identity["client_secret"],
            "WUJI_CURSOR_SIGNING_KEY": run["credentials"]["app"]["cursor_signing_key"],
            "WUJI_CURSOR_TTL_SECONDS": str(ttl),
            "WUJI_API_PORT": str(urlsplit(run["urls"]["api"]).port),
        }
    )
    if "WUJI_TEST_RUN_FILE" in environment:
        raise LifecycleError("API environment must not receive the test run file")
    return environment


def start_api(
    run_path: Path,
    *,
    profile: str,
    ttl: int = 900,
    unmigrated: bool = False,
) -> dict[str, Any]:
    run = load_manifest(run_path)
    port_key = "unmigrated_api" if unmigrated else "api"
    port = urlsplit(run["urls"][port_key]).port
    if port is None:
        raise LifecycleError("API URL has no port")
    preflight_ports([port])
    api_run = json.loads(json.dumps(run))
    if unmigrated:
        api_run["credentials"]["database"]["auth_dsn"] = run["control"]["unmigrated_auth_dsn"]
        api_run["credentials"]["database"]["project_dsn"] = run["control"]["unmigrated_project_dsn"]
        api_run["urls"]["api"] = run["urls"]["unmigrated_api"]
    environment = api_environment(api_run, profile=profile, ttl=ttl)
    executable = REPOSITORY_ROOT / ".venv" / "bin" / "python"
    log_name = "unmigrated-api.log" if unmigrated else "api.log"
    log_path = Path(run["artifacts_dir"]) / log_name
    command = [
        str(executable),
        "-m",
        "uvicorn",
        "wuji_api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--no-access-log",
    ]
    _, record = spawn_registered(
        run_path,
        "unmigrated" if unmigrated else "api",
        command,
        log_path=log_path,
        command_marker="uvicorn wuji_api.main:app",
        env=environment,
        fields={
            "profile": profile,
            "cursor_ttl_seconds": ttl,
            "reads_run_file": False,
            "credential_scopes": ["auth_dsn", "project_dsn", "oidc_client"],
        },
    )
    return record


def _start_forward_locked(
    run_path: Path, service: str, *, explicit_resume: bool
) -> dict[str, Any]:
    run = load_manifest(run_path)
    process_name = f"{service}_forward"
    existing = run.get("processes", {}).get(process_name)
    if isinstance(existing, dict) and record_is_owned(existing):
        if existing.get("paused") or existing.get("lifecycle_state") == "paused":
            if not explicit_resume:
                raise LifecycleError(
                    "port-forward remains paused", code="FORWARD_PAUSED"
                )
            update_process(
                run_path,
                process_name,
                {"paused": False, "lifecycle_state": "running"},
            )
            return {**existing, "paused": False, "lifecycle_state": "running"}
        return existing
    if isinstance(existing, dict) and (
        existing.get("paused") or existing.get("lifecycle_state") == "paused"
    ):
        if not explicit_resume:
            raise LifecycleError("port-forward remains paused", code="FORWARD_PAUSED")
        update_process(
            run_path,
            process_name,
            {
                "paused": False,
                "lifecycle_state": "restarting",
                "state_deadline": time.time() + 45,
            },
        )
    local_port = (
        run["database"]["port"]
        if service == "postgres"
        else urlsplit(run["urls"]["idp"]).port
    )
    remote_port = 5432 if service == "postgres" else 8080
    if local_port is None:
        raise LifecycleError("port-forward has no local port")
    preflight_ports([int(local_port)])
    log_path = Path(run["artifacts_dir"]) / f"{service}-forward.log"
    command = [
        "kubectl",
        "--context",
        KUBECTL_CONTEXT,
        "--namespace",
        run["namespace"],
        "port-forward",
        "--address",
        "127.0.0.1",
        f"service/{service}",
        f"{local_port}:{remote_port}",
    ]
    process, record = spawn_registered(
        run_path,
        process_name,
        command,
        log_path=log_path,
        command_marker=f"kubectl port-forward service/{service}",
        fields={"paused": False},
    )
    try:
        wait_port(int(local_port), timeout=30)
    except BaseException:
        terminate_record(record, process=process)
        update_process(
            run_path,
            process_name,
            {"lifecycle_state": "exited", "exit_code": 1},
        )
        raise
    return record


def start_forward(run_path: Path, service: str) -> dict[str, Any]:
    with forward_operation_lock(run_path, service):
        return _start_forward_locked(run_path, service, explicit_resume=False)


def pause_forward(run_path: Path, service: str) -> dict[str, Any]:
    with forward_operation_lock(run_path, service):
        run = load_manifest(run_path)
        process_name = f"{service}_forward"
        record = run.get("processes", {}).get(process_name)
        if not isinstance(record, dict) or "pid" not in record:
            raise LifecycleError("port-forward process record is missing")
        if record.get("paused") or record.get("lifecycle_state") == "paused":
            if not record_is_owned(record):
                if process_group_exists(int(record["process_group"])):
                    raise LifecycleError(
                        "paused port-forward process group is still running"
                    )
                return {**record, "paused": True, "lifecycle_state": "paused"}
        elif not record_is_owned(record):
            raise LifecycleError("port-forward process is not owned by this run")
        update_process(
            run_path,
            process_name,
            {"paused": True, "lifecycle_state": "paused"},
        )
        stopped = terminate_record(record)
        if not stopped and (
            record_is_owned(record)
            or process_group_exists(int(record["process_group"]))
        ):
            raise LifecycleError("port-forward could not be paused safely")
        return {**record, "paused": True, "lifecycle_state": "paused"}


def resume_forward(run_path: Path, service: str) -> dict[str, Any]:
    with forward_operation_lock(run_path, service):
        return _start_forward_locked(run_path, service, explicit_resume=True)


def assert_run_ownership(run: Mapping[str, Any]) -> None:
    if run.get("namespace") not in {"wuji-dev", "wuji-test"}:
        raise LifecycleError("run namespace is outside the platform boundary")
    if run.get("source_sha") != git_sha():
        raise LifecycleError("run source revision differs from the checked-out candidate")
    if run.get("repository_root") != str(REPOSITORY_ROOT):
        raise LifecycleError("run belongs to another worktree")
