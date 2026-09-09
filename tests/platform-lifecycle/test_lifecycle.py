from __future__ import annotations

import concurrent.futures
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import stat
import subprocess
import sys
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
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
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
        identity = process_identity(int(record["pid"]))
        if identity is None:
            continue
        try:
            current_group = os.getpgid(int(record["pid"]))
        except ProcessLookupError:
            continue
        same_owned_process = (
            identity[0] == str(record["start_id"])
            and str(record["command_marker"]) in identity[1]
            and current_group == int(record["process_group"])
        )
        assert not same_owned_process
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


def assert_invalid_run_file_is_rejected_without_secret_echo(
    manifest: dict[str, Any], case: Path
) -> None:
    invalid_path = (case / "invalid-run.json").resolve()
    invalid = json.loads(json.dumps(manifest))
    invalid["control"]["run_file"] = str(invalid_path)
    canaries = {
        "password": "phase1a-password-redaction-canary",
        "client_secret": "phase1a-client-secret-redaction-canary",
        "dsn": "phase1a-dsn-redaction-canary",
    }
    first_user = next(iter(invalid["seed_users"].values()))
    first_user["password"] = canaries["password"]
    invalid["credentials"]["oidc_fixture"]["client_secret"] = canaries["client_secret"]
    invalid["credentials"]["database"]["auth_dsn"] = (
        "postgresql+psycopg://role:"
        f'{canaries["dsn"]}@127.0.0.1:15434/{invalid["database"]["name"]}'
    )
    invalid["credentials"]["oidc_fixture"]["client_id"] = 7
    invalid_path.write_text(json.dumps(invalid), encoding="utf-8")
    invalid_path.chmod(0o600)

    result = subprocess.run(
        [str(CONTROL), "--run-file", str(invalid_path), "query", "authority"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert all(canary not in result.stderr for canary in canaries.values())
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
    script = f"""#!{sys.executable}
import json, os, sys
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
if {mode!r} == 'forbidden':
    print('{{"kind":"Status","reason":"Forbidden","code":403}}', file=sys.stderr)
    raise SystemExit(1)
kind = args[args.index('get') + 1] if 'get' in args else ''
name = args[args.index('get') + 2] if 'get' in args and len(args) > args.index('get') + 2 else ''
if kind == 'namespace':
    print('{{"metadata":{{"name":"wuji-test","labels":{{"wuji.dev/owner":"phase-1a"}}}}}}')
    raise SystemExit(0)
if kind == 'deployment' and name == 'postgres':
    print('{{"metadata":{{"name":"postgres","uid":"foreign-uid","labels":{{"wuji.dev/owner":"someone-else"}}}}}}')
    raise SystemExit(0)
print('{{"kind":"Status","reason":"NotFound","code":404}}', file=sys.stderr)
raise SystemExit(1)
"""
    kubectl.write_text(script, encoding="utf-8")
    kubectl.chmod(0o700)
    docker.write_text(
        f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
with Path(os.environ['WUJI_FAKE_CLUSTER_LOG']).open('a', encoding='utf-8') as stream:
    stream.write(json.dumps({{'tool':'docker','args':sys.argv[1:]}}, separators=(',', ':')) + '\\n')
print('desktop-linux')
""",
        encoding="utf-8",
    )
    docker.chmod(0o700)
    environment = os.environ.copy()
    environment["PATH"] = f"{case}:{environment['PATH']}"
    environment["WUJI_FAKE_CLUSTER_LOG"] = str(command_log)
    return environment


def fake_commands(case: Path) -> list[dict[str, Any]]:
    path = case / "cluster-commands.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


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
            reason = json.dumps(payload.get("error", {}), sort_keys=True)
            assert "port" in reason.lower()
            reasons.append(reason)
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
    if mode == "foreign-owner":
        assert any("get" in arguments and "postgres" in arguments for arguments in kubectl_arguments)


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
                assert_invalid_run_file_is_rejected_without_secret_echo(manifest, case)
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
