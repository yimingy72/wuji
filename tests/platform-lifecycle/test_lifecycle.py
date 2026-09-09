from __future__ import annotations

import concurrent.futures
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import shlex
import signal
import socket
import stat
import subprocess
import sys
import threading
import time
from typing import Any, Callable
from uuid import uuid4

import httpx
import psycopg
import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SERVE_ONLY = REPOSITORY_ROOT / "scripts" / "platform" / "test-platform.sh"
CONTROL = REPOSITORY_ROOT / "scripts" / "platform" / "control.sh"
FIXED_PORTS = (4182, 8002, 18082, 15434, 18083, 8003)
EVIDENCE_ROOT = REPOSITORY_ROOT / "artifacts" / "phase-1a" / "lifecycle-independent"
TEST_LOCK = REPOSITORY_ROOT / "work" / "run" / "test-platform.lock"


def private_case(name: str) -> Path:
    path = EVIDENCE_ROOT / f"{name}-{uuid4().hex}"
    path.mkdir(parents=True, mode=0o700)
    path.chmod(0o700)
    return path


def invoke_serve_only(case: Path, *, env: dict[str, str] | None = None) -> subprocess.Popen[str]:
    run_file = case / "run.json"
    event_file = case / "events.jsonl"
    command = [
        str(SERVE_ONLY),
        "--serve-only",
        "--run-file-out",
        str(run_file),
        "--event-file",
        str(event_file),
    ]
    return subprocess.Popen(
        command,
        cwd=REPOSITORY_ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def events(case: Path) -> list[dict[str, Any]]:
    path = case / "events.jsonl"
    if not path.exists():
        return []
    observed: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            assert isinstance(value, dict)
            observed.append(value)
    return observed


def wait_event(
    process: subprocess.Popen[str],
    case: Path,
    predicate: Callable[[dict[str, Any]], bool],
    *,
    timeout: float = 600,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for event in events(case):
            if predicate(event):
                return event
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=5)
            save_parent_output(case, stdout, stderr)
            raise AssertionError(
                f"serve-only exited {process.returncode} before the required lifecycle event"
            )
        time.sleep(0.05)
    raise AssertionError("serve-only did not emit the required lifecycle event")


def stop_owned_processes(process: subprocess.Popen[str], case: Path) -> None:
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    for event in reversed(events(case)):
        if event.get("event") != "process_registered" or event.get("name") == "test_supervisor":
            continue
        try:
            if process_identity(int(event["pid"])) is not None:
                kill_owned_event_process(event)
        except (ProcessLookupError, PermissionError):
            pass


def save_parent_output(case: Path, stdout: str, stderr: str) -> None:
    for name, value in (("parent.stdout.log", stdout), ("parent.stderr.log", stderr)):
        path = case / name
        path.write_text(value, encoding="utf-8")
        path.chmod(0o600)


def complete_process(
    process: subprocess.Popen[str], case: Path, *, timeout: float = 180
) -> int:
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        stop_owned_processes(process, case)
        stdout, stderr = process.communicate(timeout=10)
        save_parent_output(case, stdout, stderr)
        raise AssertionError("serve-only did not exit within its bounded cleanup time")
    save_parent_output(case, stdout, stderr)
    assert process.returncode is not None
    return process.returncode


def read_manifest(case: Path) -> dict[str, Any]:
    path = case / "run.json"
    assert path.is_file()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    value = json.loads(path.read_text(encoding="utf-8"))
    assert value["source_sha"] == subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, text=True
    ).strip()
    return value


def process_identity(pid: int) -> tuple[str, str] | None:
    start = subprocess.run(
        ["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True, check=False
    )
    command = subprocess.run(
        ["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True, check=False
    )
    if start.returncode or command.returncode or not command.stdout.strip():
        return None
    return start.stdout.strip(), command.stdout.strip()


def process_group_exists(process_group: int) -> bool:
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def assert_event_process_owned(event: dict[str, Any]) -> None:
    identity = process_identity(int(event["pid"]))
    assert identity is not None
    assert identity[0] == str(event["start_marker"])
    expected_command_markers = {
        "postgres_forward": ("port-forward", "postgres"),
        "keycloak_forward": ("port-forward", "keycloak"),
        "api": ("uvicorn",),
        "web": ("vite",),
        "issuer_fixture": ("tests/fixtures/oidc/issuer.py",),
        "unmigrated": ("uvicorn",),
    }
    assert all(
        marker in identity[1] for marker in expected_command_markers[str(event["name"])]
    )
    assert os.getpgid(int(event["pid"])) == int(event["pgid"])


def kill_owned_event_process(event: dict[str, Any]) -> None:
    assert_event_process_owned(event)
    os.killpg(int(event["pgid"]), signal.SIGTERM)


def assert_fixed_ports_reusable() -> None:
    for port in FIXED_PORTS:
        assert listening_pids(port) == set()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))


def assert_lock_reusable(manifest: dict[str, Any]) -> None:
    assert_file_lock_reusable(Path(manifest["control"]["lock_file"]))


def assert_file_lock_reusable(lock_path: Path) -> None:
    with lock_path.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def assert_cleanup(
    case: Path,
    manifest: dict[str, Any],
    *,
    reason: str,
    exit_code: int,
) -> None:
    cleanup = next(value for value in reversed(events(case)) if value.get("event") == "cleanup_complete")
    assert cleanup == {
        "event": "cleanup_complete",
        "run_id": manifest["run_id"],
        "reason": reason,
        "exit_code": exit_code,
    }
    report_path = Path(manifest["artifacts_dir"]) / "lifecycle-report.json"
    assert report_path.is_file()
    assert stat.S_IMODE(report_path.stat().st_mode) == 0o600
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["run_id"] == manifest["run_id"]
    assert report["source_sha"] == manifest["source_sha"]
    assert report["exit_code"] == exit_code
    assert report["reason"] == reason
    for record in manifest.get("processes", {}).values():
        if not isinstance(record, dict) or not {
            "pid",
            "process_group",
            "start_id",
            "command_marker",
        }.issubset(record):
            continue
        pid = int(record["pid"])
        process_group = int(record["process_group"])
        identity = process_identity(pid)
        if identity is None:
            if pid == process_group:
                assert not process_group_exists(process_group)
            continue
        try:
            current_group = os.getpgid(pid)
        except ProcessLookupError:
            if pid == process_group:
                assert not process_group_exists(process_group)
            continue
        same_owned_process = (
            identity[0] == str(record["start_id"])
            and str(record["command_marker"]) in identity[1]
            and current_group == process_group
        )
        assert not same_owned_process
        if pid == process_group:
            assert not process_group_exists(process_group)
    assert_fixed_ports_reusable()
    assert_lock_reusable(manifest)


def control(manifest: dict[str, Any], *arguments: str) -> dict[str, Any]:
    result = subprocess.run(
        [str(CONTROL), "--run-file", manifest["control"]["run_file"], *arguments],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["run_id"] == manifest["run_id"]
    return payload["result"]


def manifest_sensitive_values(manifest: dict[str, Any]) -> set[str]:
    values = set(manifest["credentials"]["database"].values())
    values.add(manifest["credentials"]["app"]["cursor_signing_key"])
    for profile in ("oidc_keycloak", "oidc_fixture"):
        for name, value in manifest["credentials"][profile].items():
            if any(marker in name for marker in ("password", "secret", "token")):
                values.add(value)
    values.update(user["password"] for user in manifest["seed_users"].values())
    return {str(value) for value in values if isinstance(value, str) and len(value) >= 8}


def redact_manifest_copy(manifest: dict[str, Any], label: str) -> tuple[dict[str, Any], set[str]]:
    copied = json.loads(json.dumps(manifest))
    canaries: set[str] = set()
    for name, dsn in copied["credentials"]["database"].items():
        prefix, authority = dsn.split("://", 1)
        user, location = authority.split(":", 1)
        _, endpoint = location.split("@", 1)
        canary = f"phase1a-{label}-{name}-dsn-canary"
        copied["credentials"]["database"][name] = f"{prefix}://{user}:{canary}@{endpoint}"
        canaries.add(canary)
    copied["credentials"]["app"]["cursor_signing_key"] = (
        f"phase1a-{label}-cursor-signing-canary"
    )
    canaries.add(copied["credentials"]["app"]["cursor_signing_key"])
    for profile in ("oidc_keycloak", "oidc_fixture"):
        for name in tuple(copied["credentials"][profile]):
            if any(marker in name for marker in ("password", "secret", "token")):
                canary = f"phase1a-{label}-{profile}-{name}-canary"
                copied["credentials"][profile][name] = canary
                canaries.add(canary)
    for symbol, user in copied["seed_users"].items():
        canary = f"phase1a-{label}-{symbol}-password-canary"
        user["password"] = canary
        canaries.add(canary)
    return copied, canaries


def assert_invalid_run_files_are_rejected_before_business_operation(
    manifest: dict[str, Any], case: Path
) -> None:
    original_sensitive_values = manifest_sensitive_values(manifest)
    another_worktree = case / "another-worktree"
    another_worktree.mkdir(mode=0o700)

    def invalid_schema(value: dict[str, Any]) -> None:
        value["credentials"]["oidc_fixture"]["client_id"] = 7

    def wrong_mode(_: dict[str, Any]) -> None:
        return None

    def wrong_worktree(value: dict[str, Any]) -> None:
        value["repository_root"] = str(another_worktree.resolve())

    def wrong_sha(value: dict[str, Any]) -> None:
        value["source_sha"] = "0" * 40

    def wrong_profile_namespace(value: dict[str, Any]) -> None:
        assert value["profile"] == "test"
        value["namespace"] = "wuji-dev"

    def wrong_dsn_port(value: dict[str, Any]) -> None:
        original = value["credentials"]["database"]["auth_dsn"]
        changed = original.replace("@127.0.0.1:15434/", "@127.0.0.1:15432/", 1)
        assert changed != original
        value["credentials"]["database"]["auth_dsn"] = changed

    variants: tuple[tuple[str, Callable[[dict[str, Any]], None], int], ...] = (
        ("schema", invalid_schema, 0o600),
        ("mode", wrong_mode, 0o644),
        ("worktree", wrong_worktree, 0o600),
        ("source-sha", wrong_sha, 0o600),
        ("profile-namespace", wrong_profile_namespace, 0o600),
        ("dsn-port", wrong_dsn_port, 0o600),
    )
    for label, mutate, mode in variants:
        invalid_path = (case / f"invalid-{label}-run.json").resolve()
        invalid, canaries = redact_manifest_copy(manifest, label)
        invalid["control"]["run_file"] = str(invalid_path)
        invalid["control"]["record_lock_file"] = str(
            invalid_path.with_name(f".{invalid_path.name}.record.lock")
        )
        mutate(invalid)
        invalid_path.write_text(json.dumps(invalid), encoding="utf-8")
        invalid_path.chmod(mode)
        try:
            result = subprocess.run(
                [str(CONTROL), "--run-file", str(invalid_path), "query", "authority"],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        finally:
            invalid_path.chmod(0o600)
        evidence = case / f"invalid-{label}.stderr.log"
        evidence.write_text(result.stderr, encoding="utf-8")
        evidence.chmod(0o600)
        assert result.returncode == 1
        assert result.stdout == ""
        if any(value in result.stderr for value in original_sensitive_values | canaries):
            pytest.fail("control failure output leaked a sensitive manifest value", pytrace=False)
        payload = json.loads(result.stderr)
        assert payload["ok"] is False
        assert isinstance(payload.get("error"), dict)
        assert set(payload["error"]) == {"code", "message"}


def assert_retained(previous: list[dict[str, Any]]) -> None:
    for manifest in previous:
        dsn = manifest["credentials"]["database"]["management_dsn"].replace(
            "postgresql+psycopg://", "postgresql://", 1
        )
        with psycopg.connect(dsn, connect_timeout=5) as connection:
            database, users = connection.execute(
                "SELECT current_database(), (SELECT count(*) FROM users)"
            ).fetchone()
        assert database == manifest["database"]["name"]
        assert users > 0
        discovery = httpx.get(
            f'{manifest["realm"]["issuer"]}/.well-known/openid-configuration', timeout=10
        )
        assert discovery.status_code == 200
        assert discovery.json()["issuer"] == manifest["realm"]["issuer"]


def fake_cluster_environment(case: Path, mode: str) -> dict[str, str]:
    command_log = case / "cluster-commands.jsonl"
    kubectl = case / "kubectl"
    docker = case / "docker"
    kubectl_driver = case / "fake-kubectl.py"
    docker_driver = case / "fake-docker.py"
    script = f"""import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ['WUJI_FAKE_CLUSTER_LOG']).open('a', encoding='utf-8') as stream:
    stream.write(json.dumps({{'tool':'kubectl','args':args}}, separators=(',', ':')) + '\\n')
if args == ['config', 'current-context']:
    print('docker-desktop')
    raise SystemExit(0)
if 'get' in args and 'nodes' in args:
    print('{{"items":[]}}')
    raise SystemExit(0)
if 'kustomize' in args:
    print('''apiVersion: v1
kind: Namespace
metadata:
  name: wuji-test
  labels:
    wuji.dev/owner: phase-1a
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: wuji-test
  labels:
    wuji.dev/owner: phase-1a
spec: {{}}
''')
    raise SystemExit(0)
if {mode!r} == 'forbidden':
    print('{{"kind":"Status","reason":"Forbidden","code":403}}', file=sys.stderr)
    raise SystemExit(1)
kind = args[args.index('get') + 1] if 'get' in args else ''
name = args[args.index('get') + 2] if 'get' in args and len(args) > args.index('get') + 2 else ''
if kind == 'namespace':
    print('{{"metadata":{{"name":"wuji-test","labels":{{"wuji.dev/owner":"phase-1a"}}}}}}')
    raise SystemExit(0)
if kind == 'deployment' and name == 'postgres':
    print('{{"metadata":{{"name":"postgres","namespace":"wuji-test","uid":"foreign-uid","labels":{{"wuji.dev/owner":"someone-else"}}}}}}')
    raise SystemExit(0)
if '--ignore-not-found=true' in args:
    raise SystemExit(0)
print('{{"kind":"Status","reason":"NotFound","code":404}}', file=sys.stderr)
raise SystemExit(1)
"""
    kubectl_driver.write_text(script, encoding="utf-8")
    kubectl_driver.chmod(0o600)
    kubectl.write_text(
        f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(kubectl_driver))} \"$@\"\n",
        encoding="utf-8",
    )
    kubectl.chmod(0o700)
    docker_driver.write_text(
        """import json, os, sys
from pathlib import Path
with Path(os.environ['WUJI_FAKE_CLUSTER_LOG']).open('a', encoding='utf-8') as stream:
    stream.write(json.dumps({'tool':'docker','args':sys.argv[1:]}, separators=(',', ':')) + '\\n')
print('desktop-linux')
""",
        encoding="utf-8",
    )
    docker_driver.chmod(0o600)
    docker.write_text(
        f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(docker_driver))} \"$@\"\n",
        encoding="utf-8",
    )
    docker.chmod(0o700)
    environment = os.environ.copy()
    environment["PATH"] = f"{case}:{environment['PATH']}"
    environment["WUJI_FAKE_CLUSTER_LOG"] = str(command_log)
    kubectl_probe = subprocess.run(
        [str(kubectl), "config", "current-context"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    docker_probe = subprocess.run(
        [str(docker), "context", "show"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert (kubectl_probe.returncode, kubectl_probe.stdout.strip()) == (0, "docker-desktop")
    assert (docker_probe.returncode, docker_probe.stdout.strip()) == (0, "desktop-linux")
    assert [entry["tool"] for entry in fake_commands(case)] == ["kubectl", "docker"]
    command_log.write_text("", encoding="utf-8")
    command_log.chmod(0o600)
    return environment


def fake_commands(case: Path) -> list[dict[str, Any]]:
    path = case / "cluster-commands.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def forward_events(case: Path, service: str = "postgres") -> list[dict[str, Any]]:
    return [
        event
        for event in events(case)
        if event.get("event") == "process_registered"
        and event.get("name") == f"{service}_forward"
    ]


def listening_pids(port: int) -> set[int]:
    result = subprocess.run(
        ["lsof", "-nP", "-t", f"-iTCP:{port}", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode in {0, 1}
    return {int(line) for line in result.stdout.splitlines() if line.strip()}


def assert_forward_matches_manifest_and_listener(
    case: Path, manifest: dict[str, Any], event: dict[str, Any]
) -> None:
    record = manifest["processes"]["postgres_forward"]
    assert record["pid"] == event["pid"]
    assert record["process_group"] == event["pgid"]
    assert record["start_id"] == event["start_marker"]
    assert_event_process_owned(event)
    assert listening_pids(15434) == {int(event["pid"])}


def test_fixed_port_conflict_fails_without_touching_owner_and_releases_lifecycle_lock() -> None:
    case = private_case("port-conflict")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as owner:
        owner.bind(("127.0.0.1", 18083))
        owner.listen()
        results = []
        reasons = []
        for _ in range(2):
            process = invoke_serve_only(case)
            results.append(complete_process(process, case, timeout=30))
            assert owner.getsockname()[1] == 18083
            payload = json.loads((case / "parent.stderr.log").read_text(encoding="utf-8"))
            assert payload["error"]["code"] == "PORT_CONFLICT"
            assert "18083" in payload["error"]["message"]
            reasons.append(payload["error"])
            assert_file_lock_reusable(TEST_LOCK)
    assert results == [1, 1]
    assert reasons[0] == reasons[1]


@pytest.mark.parametrize("mode", ["foreign-owner", "forbidden"])
def test_cluster_read_failure_or_wrong_ownership_is_rejected_before_any_write(mode: str) -> None:
    case = private_case(f"cluster-{mode}")
    process = invoke_serve_only(case, env=fake_cluster_environment(case, mode))
    assert complete_process(process, case, timeout=30) == 1
    commands = fake_commands(case)
    kubectl_arguments = [value["args"] for value in commands if value["tool"] == "kubectl"]
    write_verbs = {"apply", "create", "delete", "patch", "replace", "scale"}
    assert kubectl_arguments
    assert not any(write_verbs.intersection(arguments) for arguments in kubectl_arguments)
    failure = json.loads((case / "parent.stderr.log").read_text(encoding="utf-8"))
    assert failure["error"]["code"] == (
        "KUBERNETES_OWNERSHIP_MISMATCH"
        if mode == "foreign-owner"
        else "KUBERNETES_OWNERSHIP_READ_FAILED"
    )
    if mode == "foreign-owner":
        assert any("get" in arguments and "postgres" in arguments for arguments in kubectl_arguments)


class InjectedLifecycleSignal(BaseException):
    pass


@pytest.mark.parametrize(
    "injected_error",
    [InjectedLifecycleSignal("SIGTERM"), RuntimeError("registration failed")],
    ids=["early-signal", "registration-failure"],
)
def test_spawned_child_is_cleaned_if_registration_does_not_complete(
    monkeypatch: pytest.MonkeyPatch, injected_error: BaseException
) -> None:
    case = private_case(f"spawn-registration-{type(injected_error).__name__}")
    module_path = REPOSITORY_ROOT / "scripts" / "platform" / "common.py"
    spec = importlib.util.spec_from_file_location("wuji_platform_common_under_test", module_path)
    assert spec is not None and spec.loader is not None
    common = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common)
    captured: dict[str, Any] = {}
    original_spawn = common.spawn_logged

    def capture_spawn(*args: Any, **kwargs: Any) -> tuple[subprocess.Popen[Any], dict[str, Any]]:
        process, record = original_spawn(*args, **kwargs)
        captured.update(process=process, record=record)
        return process, record

    def reject_registration(*_args: Any, **_kwargs: Any) -> None:
        raise injected_error

    monkeypatch.setattr(common, "spawn_logged", capture_spawn)
    monkeypatch.setattr(common, "register_process", reject_registration)
    marker = "phase1a-lifecycle-registration-probe"
    with pytest.raises(type(injected_error)):
        common.spawn_registered(
            case / "unused-run.json",
            "probe",
            [sys.executable, "-c", "import time; time.sleep(300)", marker],
            log_path=case / "probe.log",
            command_marker=marker,
        )

    process = captured["process"]
    record = captured["record"]
    try:
        try:
            returncode = process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            returncode = None
        group_gone = not process_group_exists(int(record["process_group"]))
    finally:
        if process.poll() is None:
            os.killpg(int(record["process_group"]), signal.SIGKILL)
            process.wait(timeout=10)
    assert returncode == -signal.SIGTERM
    assert group_gone
    assert stat.S_IMODE((case / "probe.log").stat().st_mode) == 0o600


def test_real_serve_only_startup_signals_child_failure_and_retention() -> None:
    retained: list[dict[str, Any]] = []

    startup_case = private_case("startup-child-exit")
    startup = invoke_serve_only(startup_case)
    try:
        child = wait_event(
            startup,
            startup_case,
            lambda event: event.get("event") == "process_registered"
            and event.get("name") != "test_supervisor",
        )
        startup_manifest = read_manifest(startup_case)
        kill_owned_event_process(child)
        assert complete_process(startup, startup_case) == 1
        assert_cleanup(
            startup_case,
            startup_manifest,
            reason=f'child_exit:{child["name"]}',
            exit_code=1,
        )
    finally:
        stop_owned_processes(startup, startup_case)

    for signum, signal_name, expected_code in (
        (signal.SIGINT, "SIGINT", 130),
        (signal.SIGTERM, "SIGTERM", 143),
    ):
        case = private_case(signal_name.lower())
        process = invoke_serve_only(case)
        try:
            wait_event(process, case, lambda event: event.get("event") == "ready")
            manifest = read_manifest(case)
            assert_retained(retained)
            if signum == signal.SIGINT:
                assert_invalid_run_files_are_rejected_before_business_operation(manifest, case)
            process.send_signal(signum)
            assert complete_process(process, case) == expected_code
            assert_cleanup(
                case,
                manifest,
                reason=f"signal:{signal_name}",
                exit_code=expected_code,
            )
            retained.append(manifest)
        finally:
            stop_owned_processes(process, case)

    concurrent_case = private_case("concurrent-record-child-exit")
    concurrent_process = invoke_serve_only(concurrent_case)
    try:
        wait_event(concurrent_process, concurrent_case, lambda event: event.get("event") == "ready")
        concurrent_manifest = read_manifest(concurrent_case)
        assert_retained(retained)

        initial_forwards = forward_events(concurrent_case)
        assert len(initial_forwards) == 1
        assert control(concurrent_manifest, "db-forward", "pause") == {"paused": True}
        pause_deadline = time.monotonic() + 2
        while time.monotonic() < pause_deadline:
            assert forward_events(concurrent_case) == initial_forwards
            assert listening_pids(15434) == set()
            time.sleep(0.1)
        paused = read_manifest(concurrent_case)
        assert paused["processes"]["postgres_forward"]["paused"] is True

        resume_barrier = threading.Barrier(3)

        def simultaneous_resume() -> dict[str, Any]:
            resume_barrier.wait(timeout=10)
            return control(concurrent_manifest, "db-forward", "resume")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            resumes = [executor.submit(simultaneous_resume) for _ in range(2)]
            resume_barrier.wait(timeout=10)
            resume_results = [future.result(timeout=180) for future in resumes]
        resumed_pids = {int(result["pid"]) for result in resume_results}
        assert len(resumed_pids) == 1
        resumed_events = forward_events(concurrent_case)
        assert len(resumed_events) == len(initial_forwards) + 1
        resumed = read_manifest(concurrent_case)
        assert_forward_matches_manifest_and_listener(
            concurrent_case, resumed, resumed_events[-1]
        )
        assert resumed_pids == {int(resumed["processes"]["postgres_forward"]["pid"])}

        service_lock = Path(concurrent_manifest["control"]["run_file"]).with_name(
            f'.{Path(concurrent_manifest["control"]["run_file"]).name}.postgres-forward.lock'
        )
        before_recovery = forward_events(concurrent_case)
        active_forward = before_recovery[-1]
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with service_lock.open("a+", encoding="utf-8") as lock_stream:
                lock_stream.flush()
                os.fchmod(lock_stream.fileno(), 0o600)
                fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)
                kill_owned_event_process(active_forward)
                recovery = executor.submit(
                    control, concurrent_manifest, "db-forward", "resume"
                )
                time.sleep(2)
                assert not recovery.done()
                assert forward_events(concurrent_case) == before_recovery
                fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)
            recovery_result = recovery.result(timeout=180)
        recovery_deadline = time.monotonic() + 30
        while (
            len(forward_events(concurrent_case)) == len(before_recovery)
            and time.monotonic() < recovery_deadline
        ):
            time.sleep(0.1)
        with service_lock.open("a+", encoding="utf-8") as lock_stream:
            fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)
            fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)
        time.sleep(0.5)
        recovered_events = forward_events(concurrent_case)
        assert len(recovered_events) == len(before_recovery) + 1
        recovered = read_manifest(concurrent_case)
        assert int(recovery_result["pid"]) == int(
            recovered["processes"]["postgres_forward"]["pid"]
        )
        assert_forward_matches_manifest_and_listener(
            concurrent_case, recovered, recovered_events[-1]
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            restart = executor.submit(
                control, concurrent_manifest, "api", "restart", "--profile", "keycloak"
            )
            unmigrated = executor.submit(control, concurrent_manifest, "unmigrated", "start")
            restart.result(timeout=180)
            unmigrated.result(timeout=180)
        control(concurrent_manifest, "api", "wait-ready")
        control(concurrent_manifest, "unmigrated", "wait-ready")
        current = read_manifest(concurrent_case)
        assert "api" in current["processes"] and "unmigrated" in current["processes"]
        control(concurrent_manifest, "unmigrated", "stop")
        current = read_manifest(concurrent_case)
        api_event = {
            "name": "api",
            "pid": current["processes"]["api"]["pid"],
            "pgid": current["processes"]["api"]["process_group"],
            "start_marker": current["processes"]["api"]["start_id"],
        }
        kill_owned_event_process(api_event)
        assert complete_process(concurrent_process, concurrent_case) == 1
        assert_cleanup(
            concurrent_case,
            current,
            reason="child_exit:api",
            exit_code=1,
        )
        retained.append(current)
    finally:
        stop_owned_processes(concurrent_process, concurrent_case)

    verification_case = private_case("retention-verification")
    verification = invoke_serve_only(verification_case)
    try:
        wait_event(verification, verification_case, lambda event: event.get("event") == "ready")
        verification_manifest = read_manifest(verification_case)
        assert_retained(retained)
        verification.send_signal(signal.SIGTERM)
        assert complete_process(verification, verification_case) == 143
        assert_cleanup(
            verification_case,
            verification_manifest,
            reason="signal:SIGTERM",
            exit_code=143,
        )
    finally:
        stop_owned_processes(verification, verification_case)
