"""Foreground lifecycle commands for Phase 1A development and local acceptance."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from common import (
    ARTIFACT_ROOT,
    REPOSITORY_ROOT,
    RUN_ROOT,
    LifecycleError,
    append_event,
    atomic_write_json,
    create_manifest,
    database_url,
    ensure_infrastructure,
    exclusive_lock,
    git_sha,
    initialize_event_file,
    json_output,
    load_manifest,
    load_manifest_locked,
    minimal_environment,
    mutate_manifest,
    preflight_ports,
    private_directory,
    private_file,
    process_command,
    process_start_marker,
    record_is_owned,
    safe_error_payload,
    run_command,
    spawn_registered,
    start_api,
    start_forward,
    terminate_record,
    update_process,
    wait_http,
)

DEV_RUN_FILE = RUN_ROOT / "dev.json"
DEV_LOCK = RUN_ROOT / "dev-infra.lock"
DEV_PLATFORM_LOCK = RUN_ROOT / "dev-platform.lock"
TEST_LOCK = RUN_ROOT / "test-platform.lock"
TEST_PORTS = (4182, 8002, 18082, 15434, 18083, 8003)


class LifecycleSignal(BaseException):
    def __init__(self, signum: int):
        self.signum = signum
        super().__init__(signal.Signals(signum).name)

    @property
    def exit_code(self) -> int:
        return 128 + self.signum

    @property
    def reason(self) -> str:
        return f"signal:{signal.Signals(self.signum).name}"


class ChildExited(LifecycleError):
    def __init__(self, name: str):
        self.name = name
        super().__init__(
            "an owned lifecycle child exited unexpectedly", code="PROCESS_EXIT"
        )


def _seed_structure(run_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    from wuji_api.database_admin import build_seed_entities, seed_uuid

    entities = build_seed_entities(run_id)
    tenant_ids = {symbol: value["id"] for symbol, value in entities["tenants"].items()}
    project_ids = {symbol: value["id"] for symbol, value in entities["projects"].items()}
    assignments = {
        "single_a": (["tenant_a"], ["project_a_primary"]),
        "viewer_a": (["tenant_a"], ["project_a_secondary"]),
        "single_b": (["tenant_b"], ["project_b_primary"]),
        "dual_ab": (
            ["tenant_a", "tenant_b"],
            ["project_a_primary", "project_b_primary"]
            + [f"dual_page_{index:02d}" for index in range(1, 53)],
        ),
        "no_projects": (["tenant_a"], []),
        "tenant_split_u1": (["tenant_a"], ["split_project_u1"]),
        "tenant_split_u2": (["tenant_a"], ["split_project_u2"]),
        "protocol_user": ([], []),
    }
    users: dict[str, Any] = {}
    for symbol, (tenant_symbols, project_symbols) in assignments.items():
        username = f"wuji-{symbol.replace('_', '-')}"
        users[symbol] = {
            "id": str(seed_uuid(run_id, f"users:{symbol}")),
            "sub": str(seed_uuid(run_id, f"keycloak-sub:{symbol}")),
            "fixture_sub": str(seed_uuid(run_id, f"fixture-sub:{symbol}")),
            "username": username,
            "display_name": symbol.replace("_", " ").title(),
            "email": f"{username}@example.invalid",
            "password": secrets.token_urlsafe(24),
            "tenant_ids": [tenant_ids[value] for value in tenant_symbols],
            "project_ids": [project_ids[value] for value in project_symbols],
        }
    return entities, users


def _run_identifiers(kind: str) -> tuple[str, str, dict[str, str]]:
    if kind == "dev":
        return (
            "dev",
            "wuji_dev",
            {
                "migration": "wuji_dev_migration",
                "auth": "wuji_dev_auth",
                "project": "wuji_dev_project",
            },
        )
    timestamp = datetime.now(UTC).strftime("p1a%Y%m%dt%H%M%S")
    run_id = f"{timestamp}{secrets.token_hex(3)}"
    return (
        run_id,
        f"wuji_test_{run_id}",
        {
            "migration": f"wuji_{run_id}_migration",
            "auth": f"wuji_{run_id}_auth",
            "project": f"wuji_{run_id}_project",
        },
    )


def _private_output_path(value: str, *, option: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise LifecycleError(f"{option} must be absolute")
    if path.is_symlink():
        raise LifecycleError(f"{option} must not be a symbolic link")
    return path.resolve()


def build_run(
    kind: str,
    cluster: Mapping[str, str],
    *,
    run_file_out: Path | None = None,
    event_file: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    if kind not in {"dev", "test"}:
        raise LifecycleError("run kind must be dev or test")
    run_id, database_name, roles = _run_identifiers(kind)
    namespace = "wuji-dev" if kind == "dev" else "wuji-test"
    ports = (
        {"web": 4180, "api": 8000, "idp": 18080, "database": 15432}
        if kind == "dev"
        else {"web": 4182, "api": 8002, "idp": 18082, "database": 15434}
    )
    artifacts = ARTIFACT_ROOT / ("dev" if kind == "dev" else run_id)
    private_directory(artifacts)
    run_path = (
        run_file_out
        if run_file_out is not None
        else (DEV_RUN_FILE if kind == "dev" else RUN_ROOT / f"test-{run_id}.json")
    ).resolve()
    entities, users = _seed_structure(run_id)
    role_passwords = {name: secrets.token_urlsafe(32) for name in roles}
    realm_name = "wuji-dev" if kind == "dev" else f"wuji-test-{run_id}"
    urls = {
        "web": f"http://127.0.0.1:{ports['web']}",
        "api": f"http://127.0.0.1:{ports['api']}",
        "idp": f"http://127.0.0.1:{ports['idp']}",
        "issuer_fixture": "http://127.0.0.1:18083",
        "unmigrated_api": "http://127.0.0.1:8003",
        "database": f"postgresql://127.0.0.1:{ports['database']}/{database_name}",
    }
    logs = {
        name: artifacts / name
        for name in (
            "api.log",
            "issuer-fixture.log",
            "web.log",
            "postgres-forward.log",
            "keycloak-forward.log",
        )
    }
    for path in logs.values():
        private_file(path, truncate=True)
    database_credentials = {
        "admin_dsn": database_url(
            "127.0.0.1", ports["database"], "postgres", "postgres", cluster["postgres-admin-password"]
        ),
        "management_dsn": database_url(
            "127.0.0.1", ports["database"], database_name, roles["migration"], role_passwords["migration"]
        ),
        "auth_dsn": database_url(
            "127.0.0.1", ports["database"], database_name, roles["auth"], role_passwords["auth"]
        ),
        "project_dsn": database_url(
            "127.0.0.1", ports["database"], database_name, roles["project"], role_passwords["project"]
        ),
    }
    control: dict[str, Any] = {
        "run_file": str(run_path),
        "lock_file": str((DEV_LOCK if kind == "dev" else TEST_LOCK).resolve()),
        "record_lock_file": str(run_path.with_name(f".{run_path.name}.record.lock")),
    }
    if event_file is not None:
        control["event_file"] = str(event_file)
    run = {
        "schema_version": 1,
        "run_id": run_id,
        "source_sha": git_sha(),
        "repository_root": str(REPOSITORY_ROOT),
        "artifacts_dir": str(artifacts),
        "namespace": namespace,
        "profile": kind,
        "database": {
            "name": database_name,
            "host": "127.0.0.1",
            "port": ports["database"],
            "roles": roles,
        },
        "realm": {"name": realm_name, "issuer": f"{urls['idp']}/realms/{realm_name}"},
        "urls": urls,
        "seed_entities": entities,
        "seed_users": users,
        "credentials": {
            "database": database_credentials,
            "app": {"cursor_signing_key": secrets.token_urlsafe(48)},
            "oidc_keycloak": {
                "client_id": f"wuji-{run_id}",
                "client_secret": secrets.token_urlsafe(32),
                "admin_username": cluster["keycloak-admin-username"],
                "admin_password": cluster["keycloak-admin-password"],
            },
            "oidc_fixture": {
                "client_id": f"wuji-fixture-{run_id}",
                "client_secret": secrets.token_urlsafe(32),
                "control_token": secrets.token_urlsafe(32),
            },
        },
        "processes": {
            "api": {
                "log_path": str(logs["api.log"]),
                "reads_run_file": False,
                "credential_scopes": ["auth_dsn", "project_dsn", "oidc_client"],
            },
            "issuer_fixture": {"log_path": str(logs["issuer-fixture.log"])},
        },
        "control": control,
    }
    created = create_manifest(run_path, run)
    if event_file is not None:
        append_event(
            event_file,
            {
                "event": "run_file_ready",
                "path": str(run_path),
                "run_id": run_id,
                "source_sha": created["source_sha"],
            },
        )
    return run_path, created


def _manager(run_path: Path, *arguments: str) -> dict[str, Any]:
    executable = REPOSITORY_ROOT / ".venv" / "bin" / "wuji-manage"
    result = run_command([str(executable), "--run-file", str(run_path), *arguments])
    payload = json.loads(result.stdout)
    if not payload.get("ok") or payload.get("run_id") != load_manifest(run_path)["run_id"]:
        raise LifecycleError("management command returned an invalid result")
    return payload["result"]


def _record_supervisor(run_path: Path, name: str) -> None:
    pid = os.getpid()
    observed = process_command(pid)
    record = {
        "pid": pid,
        "process_group": os.getpgrp(),
        "start_id": process_start_marker(pid),
        "command_marker": observed,
        "command": [sys.executable, *sys.argv],
        "observed_command": observed,
        "lifecycle_state": "running",
    }

    def update(run: dict[str, Any]) -> None:
        run["processes"][name] = record

    mutate_manifest(run_path, update)


def _start_web(run_path: Path, *, test: bool) -> dict[str, Any]:
    run = load_manifest(run_path)
    log_path = Path(run["artifacts_dir"]) / "web.log"
    environment = minimal_environment()
    environment["WUJI_API_ORIGIN"] = run["urls"]["api"]
    if test:
        config_path = RUN_ROOT / f"vite-{run['run_id']}.mjs"
        web_root = REPOSITORY_ROOT / "apps" / "web"
        vite_url = (web_root / "node_modules" / "vite" / "dist" / "node" / "index.js").as_uri()
        react_url = (web_root / "node_modules" / "@vitejs" / "plugin-react" / "dist" / "index.js").as_uri()
        fault_path = Path(run["artifacts_dir"]) / "drop-next-created-response"
        fault_evidence = Path(run["artifacts_dir"]) / "created-response-dropped.json"
        config = (
            f"import {{ defineConfig }} from {json.dumps(vite_url)};\n"
            f"import react from {json.dumps(react_url)};\n"
            "import { existsSync, unlinkSync, writeFileSync } from 'node:fs';\n"
            "export default defineConfig({\n"
            f"  root: {json.dumps(str(web_root))}, plugins: [react()],\n"
            "  server: { host: '127.0.0.1', port: 4182, strictPort: true, "
            "proxy: { '/api': { target: 'http://127.0.0.1:8002', configure(proxy) {\n"
            "proxy.on('proxyRes', (upstream, req, res) => {\n"
            f"if (req.method === 'POST' && /\\/projects\\/[^/]+\\/tasks$/.test(req.url) && upstream.statusCode === 202 && existsSync({json.dumps(str(fault_path))})) {{\n"
            f"unlinkSync({json.dumps(str(fault_path))});\n"
            f"writeFileSync({json.dumps(str(fault_evidence))}, JSON.stringify({{path:req.url,upstream_status:202,at:new Date().toISOString()}}), {{mode:0o600}});\n"
            "res.destroy();\n"
            "} }); } } } },\n"
            "  build: { target: 'es2022' }\n"
            "});\n"
        )
        private_file(config_path, truncate=True)
        config_path.write_text(config, encoding="utf-8")
        config_path.chmod(0o600)
        command = ["pnpm", "--filter", "@wuji/web", "exec", "vite", "--config", str(config_path)]
    else:
        command = ["pnpm", "--filter", "@wuji/web", "dev"]
    _, record = spawn_registered(
        run_path,
        "web",
        command,
        log_path=log_path,
        command_marker="vite apps/web",
        env=environment,
    )
    return record


def _start_fixture(run_path: Path) -> dict[str, Any]:
    run = load_manifest(run_path)
    fixture = REPOSITORY_ROOT / "tests" / "fixtures" / "oidc" / "issuer.py"
    if not fixture.is_file():
        raise LifecycleError("the independent OIDC fixture is not present in this candidate")
    environment = minimal_environment()
    environment["WUJI_TEST_RUN_FILE"] = str(run_path)
    command = [
        str(REPOSITORY_ROOT / ".venv" / "bin" / "python"),
        str(fixture),
        "--host",
        "127.0.0.1",
        "--port",
        "18083",
        "--run-file",
        str(run_path),
    ]
    log_path = Path(run["artifacts_dir"]) / "issuer-fixture.log"
    _, record = spawn_registered(
        run_path,
        "issuer_fixture",
        command,
        log_path=log_path,
        command_marker="tests/fixtures/oidc/issuer.py",
        env=environment,
    )
    wait_http(f"{run['urls']['issuer_fixture']}/health", timeout=30)
    return record


def _prepare_test_run(run_path: Path) -> None:
    _manager(run_path, "database", "prepare", "--migrate")
    _manager(run_path, "identity", "provision")
    _manager(run_path, "database", "seed")


def _cleanup_run(run_path: Path, names: Sequence[str]) -> None:
    run = load_manifest(run_path, require_source_sha=False)
    for name in names:
        record = run.get("processes", {}).get(name)
        if isinstance(record, dict) and "pid" in record:
            terminate_record(record)


def _monitor_required(
    run_path: Path,
    required: Sequence[str],
    failures: dict[str, dict[str, float | int | None]],
) -> None:
    run = load_manifest(run_path)
    for name in required:
        record = run.get("processes", {}).get(name)
        if not isinstance(record, dict) or "pid" not in record:
            raise ChildExited(name)
        if record_is_owned(record):
            recovery = failures.get(name)
            if recovery is not None:
                healthy_since = recovery.get("healthy_since")
                if not isinstance(healthy_since, float):
                    recovery["healthy_since"] = time.monotonic()
                elif time.monotonic() - healthy_since >= 30:
                    failures.pop(name, None)
            continue
        state = record.get("lifecycle_state")
        if state == "restarting" and float(record.get("state_deadline", 0)) > time.time():
            continue
        if name == "postgres_forward" and (record.get("paused") or state == "paused"):
            continue
        if name in {"postgres_forward", "keycloak_forward"}:
            service = name.removesuffix("_forward")
            now = time.monotonic()
            recovery = failures.setdefault(
                name,
                {"attempts": 0, "deadline": now + 90, "healthy_since": None},
            )
            recovery["healthy_since"] = None
            attempts = int(recovery["attempts"])
            deadline = float(recovery["deadline"])
            if attempts >= 5 or now >= deadline:
                raise ChildExited(name)
            time.sleep(min(2**attempts, 8))
            current = load_manifest_locked(run_path)
            current_record = current.get("processes", {}).get(name)
            if isinstance(current_record, dict) and record_is_owned(current_record):
                recovery["healthy_since"] = time.monotonic()
                continue
            if isinstance(current_record, dict) and (
                current_record.get("paused")
                or current_record.get("lifecycle_state") == "paused"
            ):
                continue
            recovery["attempts"] = attempts + 1
            try:
                start_forward(run_path, service)
                recovery["healthy_since"] = time.monotonic()
            except LifecycleError as error:
                if error.code == "FORWARD_PAUSED":
                    recovery["attempts"] = attempts
                    continue
                if int(recovery["attempts"]) >= 5 or time.monotonic() >= deadline:
                    raise ChildExited(name) from None
            continue
        raise ChildExited(name)


def _wait_forever(run_path: Path, required: Sequence[str]) -> None:
    failures: dict[str, dict[str, float | int | None]] = {}
    while True:
        _monitor_required(run_path, required, failures)
        time.sleep(0.2)


def _first_dead_registered_child(run_path: Path) -> str | None:
    """Return an unexpectedly dead startup child without treating placeholders as children."""
    run = load_manifest(run_path)
    for name in (
        "postgres_forward",
        "keycloak_forward",
        "api",
        "web",
        "issuer_fixture",
    ):
        record = run.get("processes", {}).get(name)
        if not isinstance(record, dict) or "pid" not in record:
            continue
        if record.get("paused") or record.get("lifecycle_state") == "restarting":
            continue
        if not record_is_owned(record):
            return name
    return None


def _run_test_command(
    command: Sequence[str],
    *,
    name: str,
    run_path: Path,
    log_path: Path,
    required: Sequence[str],
) -> int:
    environment = os.environ.copy()
    environment["WUJI_TEST_RUN_FILE"] = str(run_path)
    private_file(log_path, truncate=True)
    process, record = spawn_registered(
        run_path,
        name,
        command,
        log_path=log_path,
        command_marker=name.removesuffix("_runner"),
        env=environment,
    )
    failures: dict[str, dict[str, float | int | None]] = {}
    try:
        while process.poll() is None:
            _monitor_required(run_path, required, failures)
            time.sleep(0.2)
        exit_code = int(process.returncode or 0)
        update_process(run_path, name, {"lifecycle_state": "exited", "exit_code": exit_code})
        return exit_code
    finally:
        current = load_manifest(run_path)
        current_record = current.get("processes", {}).get(name)
        if process.poll() is None and isinstance(current_record, dict):
            terminate_record(current_record, process=process)


def dev_infra() -> int:
    os.setpgrp()
    with exclusive_lock(DEV_LOCK):
        preflight_ports([15432, 18080])
        if DEV_RUN_FILE.exists():
            previous_run = load_manifest(DEV_RUN_FILE, require_source_sha=False)
            if any(
                isinstance(record, dict) and "pid" in record and record_is_owned(record)
                for record in previous_run.get("processes", {}).values()
            ):
                raise LifecycleError("an owned development run is still active")
        cluster = ensure_infrastructure("wuji-dev", "dev")
        run_path, run = build_run("dev", cluster)
        _record_supervisor(run_path, "infra_supervisor")
        try:
            start_forward(run_path, "postgres")
            start_forward(run_path, "keycloak")
            print(json_output({"run_id": run["run_id"], "run_file": str(run_path)}), flush=True)
            _wait_forever(run_path, ("postgres_forward", "keycloak_forward"))
        finally:
            _cleanup_run(run_path, ("keycloak_forward", "postgres_forward"))
    return 0


def dev_seed() -> int:
    run_path = DEV_RUN_FILE
    run = load_manifest(run_path)
    for service in ("postgres", "keycloak"):
        record = run.get("processes", {}).get(f"{service}_forward")
        if not isinstance(record, dict) or not record_is_owned(record):
            raise LifecycleError("development dependency is not owned by dev:infra")
    prepared = _manager(run_path, "database", "prepare", "--migrate")
    identity = _manager(run_path, "identity", "provision")
    seeded = _manager(run_path, "database", "seed")
    print(
        json_output(
            {
                "run_id": run["run_id"],
                "result": {"database": prepared, "identity": identity, "seed": seeded},
            }
        )
    )
    return 0


def dev_platform() -> int:
    os.setpgrp()
    with exclusive_lock(DEV_PLATFORM_LOCK):
        preflight_ports([4180, 8000])
        run_path = DEV_RUN_FILE
        run = load_manifest(run_path)
        for service in ("postgres", "keycloak"):
            record = run.get("processes", {}).get(f"{service}_forward")
            if not isinstance(record, dict) or not record_is_owned(record):
                raise LifecycleError("dev:infra must own both dependency forwards")
        _record_supervisor(run_path, "platform_supervisor")
        try:
            start_api(run_path, profile="keycloak")
            _start_web(run_path, test=False)
            wait_http(f"{run['urls']['api']}/health/ready", timeout=60)
            wait_http(run["urls"]["web"], timeout=60)
            print(json_output({"run_id": run["run_id"], "run_file": str(run_path)}), flush=True)
            _wait_forever(run_path, ("api", "web"))
        finally:
            _cleanup_run(run_path, ("web", "api"))
    return 0


def dev_down() -> int:
    run_path = DEV_RUN_FILE
    run = load_manifest(run_path, require_source_sha=False)
    stopped: list[str] = []
    for name in (
        "platform_supervisor",
        "infra_supervisor",
        "playwright_runner",
        "pytest_runner",
        "unmigrated",
        "api",
        "web",
        "issuer_fixture",
        "postgres_forward",
        "keycloak_forward",
    ):
        record = run.get("processes", {}).get(name)
        if isinstance(record, dict) and "pid" in record and terminate_record(record):
            stopped.append(name)
    print(
        json_output(
            {
                "run_id": run["run_id"],
                "result": {"stopped": stopped, "retained": "kubernetes-secret-and-pvc"},
            }
        )
    )
    return 0


def test_platform(
    *, serve_only: bool, run_file_out: Path | None, event_file: Path | None
) -> int:
    os.setpgrp()
    run_path: Path | None = None
    run: dict[str, Any] | None = None
    results: dict[str, int] = {}
    exit_code = 1
    reason = "startup_failure"
    error_code: str | None = None
    failure: BaseException | None = None
    cleanup_names = (
        "playwright_runner",
        "pytest_runner",
        "unmigrated",
        "issuer_fixture",
        "web",
        "api",
        "keycloak_forward",
        "postgres_forward",
    )
    with exclusive_lock(TEST_LOCK):
        try:
            preflight_ports(TEST_PORTS)
            cluster = ensure_infrastructure("wuji-test", "test")
            run_path, run = build_run(
                "test", cluster, run_file_out=run_file_out, event_file=event_file
            )
            _record_supervisor(run_path, "test_supervisor")
            start_forward(run_path, "postgres")
            start_forward(run_path, "keycloak")
            _prepare_test_run(run_path)
            start_api(run_path, profile="keycloak")
            _start_web(run_path, test=True)
            _start_fixture(run_path)
            wait_http(f"{run['urls']['api']}/health/ready", timeout=60)
            wait_http(run["urls"]["web"], timeout=60)
            required = ("postgres_forward", "keycloak_forward", "api", "web", "issuer_fixture")
            _monitor_required(run_path, required, {})
            if event_file is not None:
                append_event(event_file, {"event": "ready", "run_id": run["run_id"]})
            if serve_only:
                _wait_forever(run_path, required)
            else:
                artifacts = Path(run["artifacts_dir"])
                results["pytest"] = _run_test_command(
                    [
                        str(REPOSITORY_ROOT / ".venv" / "bin" / "python"),
                        "-m",
                        "pytest",
                        "tests/api",
                    ],
                    name="pytest_runner",
                    run_path=run_path,
                    log_path=artifacts / "pytest-platform.log",
                    required=required,
                )
                results["playwright"] = _run_test_command(
                    [
                        "pnpm",
                        "exec",
                        "playwright",
                        "test",
                        "--config",
                        "playwright.platform.config.ts",
                    ],
                    name="playwright_runner",
                    run_path=run_path,
                    log_path=artifacts / "playwright-platform.log",
                    required=required,
                )
                exit_code = 0 if results and all(code == 0 for code in results.values()) else 1
                reason = "completed" if exit_code == 0 else "tests_failed"
        except LifecycleSignal as requested:
            exit_code = requested.exit_code
            reason = requested.reason
            for signum in (signal.SIGINT, signal.SIGTERM):
                signal.signal(signum, signal.SIG_IGN)
        except ChildExited as error:
            exit_code = 1
            reason = f"child_exit:{error.name}"
            error_code = error.__class__.__name__
            failure = error
        except Exception as error:
            exit_code = 1
            dead_child = (
                _first_dead_registered_child(run_path)
                if run_path is not None and run is not None
                else None
            )
            if dead_child is not None:
                reason = f"child_exit:{dead_child}"
                failure = ChildExited(dead_child)
            else:
                reason = "startup_failure" if run is None else "lifecycle_failure"
                failure = error
            error_code = failure.__class__.__name__
        finally:
            if run_path is not None and run is not None:
                try:
                    _cleanup_run(run_path, cleanup_names)
                except Exception as cleanup_error:
                    exit_code = 1
                    reason = "cleanup_failure"
                    error_code = cleanup_error.__class__.__name__
                report = {
                    "run_id": run["run_id"],
                    "source_sha": run["source_sha"],
                    "reason": reason,
                    "exit_code": exit_code,
                    "run_file": str(run_path),
                    "artifacts_dir": run["artifacts_dir"],
                    "exit_codes": results,
                    "retained": {
                        "database": run["database"]["name"],
                        "realm": run["realm"]["name"],
                    },
                }
                if error_code is not None:
                    report["error_code"] = error_code
                atomic_write_json(Path(run["artifacts_dir"]) / "lifecycle-report.json", report)
                if event_file is not None:
                    append_event(
                        event_file,
                        {
                            "event": "cleanup_complete",
                            "run_id": run["run_id"],
                            "reason": reason,
                            "exit_code": exit_code,
                        },
                    )
                print(json_output({"run_id": run["run_id"], "result": report}), flush=True)
            elif event_file is not None:
                append_event(
                    event_file,
                    {
                        "event": "cleanup_complete",
                        "run_id": None,
                        "reason": reason,
                        "exit_code": exit_code,
                    },
                )
            if failure is not None:
                print(
                    json.dumps(safe_error_payload(run_id=None if run is None else run["run_id"], error=failure)),
                    file=sys.stderr,
                )
    return exit_code


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="wuji-platform-lifecycle")
    commands = value.add_subparsers(dest="command", required=True)
    for name in ("dev-infra", "dev-seed", "dev-platform", "dev-down"):
        commands.add_parser(name)
    test = commands.add_parser("test-platform")
    test.add_argument("--serve-only", action="store_true")
    test.add_argument("--run-file-out")
    test.add_argument("--event-file")
    return value


def main() -> None:
    args = parser().parse_args()
    previous_handlers = {
        signum: signal.signal(signum, lambda received, _frame: (_ for _ in ()).throw(LifecycleSignal(received)))
        for signum in (signal.SIGINT, signal.SIGTERM)
    }
    run_id: str | None = None
    try:
        if args.command == "test-platform":
            if bool(args.run_file_out) != bool(args.event_file):
                raise LifecycleError("serve-only output paths must be provided together")
            if (args.run_file_out or args.event_file) and not args.serve_only:
                raise LifecycleError("explicit lifecycle output paths require --serve-only")
            run_file_out = (
                _private_output_path(args.run_file_out, option="--run-file-out")
                if args.run_file_out
                else None
            )
            event_file = (
                initialize_event_file(_private_output_path(args.event_file, option="--event-file"))
                if args.event_file
                else None
            )
            raise SystemExit(
                test_platform(
                    serve_only=args.serve_only,
                    run_file_out=run_file_out,
                    event_file=event_file,
                )
            )
        commands = {
            "dev-infra": dev_infra,
            "dev-seed": dev_seed,
            "dev-platform": dev_platform,
            "dev-down": dev_down,
        }
        raise SystemExit(commands[args.command]())
    except LifecycleSignal as requested:
        print(json.dumps(safe_error_payload(run_id=run_id, error=requested)), file=sys.stderr)
        raise SystemExit(requested.exit_code) from None
    except SystemExit:
        raise
    except Exception as error:
        print(json.dumps(safe_error_payload(run_id=run_id, error=error)), file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    main()
