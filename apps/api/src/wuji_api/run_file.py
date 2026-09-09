"""Strict, serialized access to secret local lifecycle run records."""

from __future__ import annotations

import fcntl
import json
import os
import stat
import subprocess
import tempfile
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeVar
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

PROJECT_ROOT = Path(__file__).resolve().parents[4]
RUN_FILE_SCHEMA = PROJECT_ROOT / "scripts" / "platform" / "run-file.schema.json"
T = TypeVar("T")


def _current_source_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode or len(result.stdout.strip()) != 40:
        raise ValueError("unable to resolve the current candidate revision")
    return result.stdout.strip()


def _record_lock_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.record.lock")


@contextmanager
def run_file_lock(path: Path) -> Iterator[None]:
    if not path.is_absolute():
        raise ValueError("run file path must be absolute")
    if path.is_symlink():
        raise ValueError("run file must not be a symbolic link")
    lock_path = _record_lock_path(path)
    if lock_path.is_symlink():
        raise ValueError("run file mutex must not be a symbolic link")
    if not lock_path.parent.exists():
        lock_path.parent.mkdir(parents=True, mode=0o700)
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
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


def _require_private_regular_file(path: Path) -> os.stat_result:
    if path.is_symlink():
        raise ValueError("run file must not be a symbolic link")
    file_stat = path.stat()
    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError("run file must be a regular file")
    if stat.S_IMODE(file_stat.st_mode) != 0o600:
        raise PermissionError("run file must have mode 0600")
    if hasattr(os, "getuid") and file_stat.st_uid != os.getuid():
        raise PermissionError("run file must be owned by the current user")
    return file_stat


def _expected_ports(profile: str) -> dict[str, int]:
    if profile == "dev":
        return {
            "web": 4180,
            "api": 8000,
            "idp": 18080,
            "database": 15432,
            "issuer_fixture": 18083,
            "unmigrated_api": 8003,
        }
    if profile == "test":
        return {
            "web": 4182,
            "api": 8002,
            "idp": 18082,
            "database": 15434,
            "issuer_fixture": 18083,
            "unmigrated_api": 8003,
        }
    raise ValueError("run file has an unsupported profile")


def _validate_platform_identity(path: Path, payload: Mapping[str, Any]) -> None:
    repository_root = Path(str(payload["repository_root"]))
    if not repository_root.is_absolute() or repository_root.resolve() != PROJECT_ROOT:
        raise ValueError("run file belongs to another worktree")
    recorded_path = Path(str(payload["control"]["run_file"]))
    if not recorded_path.is_absolute() or recorded_path.resolve() != path:
        raise ValueError("run file ownership record does not match its path")
    expected_record_lock = _record_lock_path(path)
    if Path(str(payload["control"]["record_lock_file"])).resolve() != expected_record_lock:
        raise ValueError("run file mutex record does not match its path")

    profile = str(payload["profile"])
    namespace = str(payload["namespace"])
    run_id = str(payload["run_id"])
    database_name = str(payload["database"]["name"])
    expected_namespace = "wuji-dev" if profile == "dev" else "wuji-test"
    if namespace != expected_namespace:
        raise ValueError("run profile and namespace do not match")
    if profile == "dev":
        if (
            run_id != "dev"
            or database_name != "wuji_dev"
            or payload["realm"]["name"] != "wuji-dev"
        ):
            raise ValueError("development run identifiers do not match")
    elif (
        database_name != f"wuji_test_{run_id}"
        or payload["realm"]["name"] != f"wuji-test-{run_id}"
    ):
        raise ValueError("test run identifiers do not match")

    expected_lifecycle_lock = PROJECT_ROOT / "work" / "run" / (
        "dev-infra.lock" if profile == "dev" else "test-platform.lock"
    )
    if Path(str(payload["control"]["lock_file"])).resolve() != expected_lifecycle_lock:
        raise ValueError("run lifecycle lock does not match its profile")

    if payload["database"]["host"] != "127.0.0.1":
        raise ValueError("run database host must use loopback")
    expected_issuer = f"{str(payload['urls']['idp']).rstrip('/')}/realms/{payload['realm']['name']}"
    if payload["realm"]["issuer"] != expected_issuer:
        raise ValueError("run realm issuer does not match its identity endpoint")

    for name, expected_port in _expected_ports(profile).items():
        if name == "database":
            if int(payload["database"]["port"]) != expected_port:
                raise ValueError("run database port does not match its profile")
            value = str(payload["urls"]["database"])
        else:
            value = str(payload["urls"][name])
        parsed = urlsplit(value)
        if parsed.hostname != "127.0.0.1" or parsed.port != expected_port:
            raise ValueError("run URL does not match its loopback port assignment")
        if name != "database" and parsed.scheme != "http":
            raise ValueError("local service URLs must use HTTP")
        if name != "database" and parsed.path not in {"", "/"}:
            raise ValueError("local service URLs must use their canonical root")
        if name == "database" and parsed.scheme != "postgresql":
            raise ValueError("run database URL must use PostgreSQL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("public run URLs must not contain credentials or modifiers")
        if name == "database" and parsed.path != f"/{database_name}":
            raise ValueError("run database URL does not match its database name")

    credentials = payload["credentials"]["database"]
    roles = payload["database"]["roles"]
    expected_databases = {
        "admin_dsn": ("postgres", "postgres"),
        "management_dsn": (database_name, roles["migration"]),
        "auth_dsn": (database_name, roles["auth"]),
        "project_dsn": (database_name, roles["project"]),
    }
    expected_port = _expected_ports(profile)["database"]
    for name, (expected_database, expected_role) in expected_databases.items():
        parsed = urlsplit(str(credentials[name]))
        if (
            parsed.scheme != "postgresql+psycopg"
            or parsed.hostname != "127.0.0.1"
            or parsed.port != expected_port
            or parsed.path != f"/{expected_database}"
            or parsed.username != expected_role
            or parsed.password is None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("run database credential does not match its recorded authority")

    artifacts_dir = Path(str(payload["artifacts_dir"]))
    if not artifacts_dir.is_absolute() or not artifacts_dir.is_dir():
        raise ValueError("run artifacts directory must be absolute and present")
    artifact_stat = artifacts_dir.stat()
    if stat.S_IMODE(artifact_stat.st_mode) != 0o700:
        raise PermissionError("run artifacts directory must have mode 0700")
    if hasattr(os, "getuid") and artifact_stat.st_uid != os.getuid():
        raise PermissionError("run artifacts directory must be owned by the current user")
    for process_name in ("api", "issuer_fixture"):
        log_path = Path(str(payload["processes"][process_name]["log_path"]))
        if not log_path.is_absolute() or artifacts_dir not in log_path.parents:
            raise ValueError("run process log must be inside its artifacts directory")
        _require_private_regular_file(log_path)
    event_path_value = payload["control"].get("event_file")
    if event_path_value is not None:
        event_path = Path(str(event_path_value))
        if not event_path.is_absolute():
            raise ValueError("run event file must be absolute")
        _require_private_regular_file(event_path)


def validate_run_payload(
    path: Path, payload: Mapping[str, Any], *, require_source_sha: bool = True
) -> None:
    schema = json.loads(RUN_FILE_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)
    _validate_platform_identity(path, payload)
    if require_source_sha and payload["source_sha"] != _current_source_sha():
        raise ValueError("run file source revision differs from the checked-out candidate")


def load_run_file(
    value: str | os.PathLike[str], *, require_source_sha: bool = True
) -> tuple[Path, dict[str, Any]]:
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("run file path must be absolute")
    if path.is_symlink():
        raise ValueError("run file must not be a symbolic link")
    path = path.resolve()
    _require_private_regular_file(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_run_payload(path, payload, require_source_sha=require_source_sha)
    return path, payload


def create_run_file(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    if not path.is_absolute():
        raise ValueError("run file path must be absolute")
    if path.is_symlink():
        raise ValueError("run file must not be a symbolic link")
    path = path.resolve()
    if not path.parent.exists():
        path.parent.mkdir(parents=True, mode=0o700)
    if path.exists():
        _require_private_regular_file(path)
    validate_run_payload(path, payload)
    with run_file_lock(path):
        _atomic_write(path, payload)
        _, created = load_run_file(path)
    return created


def mutate_run_file(
    value: str | os.PathLike[str],
    mutate: Callable[[dict[str, Any]], T],
    *,
    require_source_sha: bool = True,
) -> tuple[dict[str, Any], T]:
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("run file path must be absolute")
    if path.is_symlink():
        raise ValueError("run file must not be a symbolic link")
    path = path.resolve()
    with run_file_lock(path):
        _, payload = load_run_file(path, require_source_sha=require_source_sha)
        result = mutate(payload)
        validate_run_payload(path, payload, require_source_sha=require_source_sha)
        _atomic_write(path, payload)
    return payload, result
