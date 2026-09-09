"""Owned-process and failure-fixture controls for one private Phase 1A run."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Sequence

from common import (
    KUBECTL_CONTEXT,
    OWNER_LABEL,
    REPOSITORY_ROOT,
    LifecycleError,
    load_manifest,
    mutate_manifest,
    pause_forward,
    record_is_owned,
    replace_database,
    require_owned_resource,
    run_command,
    safe_error_payload,
    resume_forward,
    start_api,
    terminate_record,
    update_process,
    wait_http,
    wait_infrastructure,
)

DELEGATED = {"database", "identity", "permissions", "user", "session", "cursor"}


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise LifecycleError("control arguments are invalid", code="ARGUMENT_INVALID")


def _load_owned(path_value: str) -> tuple[Path, dict[str, Any]]:
    path = Path(path_value)
    if not path.is_absolute():
        raise LifecycleError("--run-file must be absolute")
    run = load_manifest(path)
    return path, run


def _manager(path: Path, arguments: Sequence[str]) -> tuple[int, dict[str, Any]]:
    executable = REPOSITORY_ROOT / ".venv" / "bin" / "wuji-manage"
    result = subprocess.run(
        [str(executable), "--run-file", str(path), *arguments],
        cwd=REPOSITORY_ROOT,
        stdin=subprocess.DEVNULL,
        text=True,
        capture_output=True,
        check=False,
    )
    raw = result.stdout if result.returncode == 0 else result.stderr
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise LifecycleError("management command returned invalid JSON") from error
    if not isinstance(payload, dict) or payload.get("ok") != (result.returncode == 0):
        raise LifecycleError("management command returned an invalid envelope")
    return result.returncode, payload


def _api(path: Path, run: dict[str, Any], arguments: Sequence[str]) -> dict[str, Any]:
    parser = SafeArgumentParser(prog="control api")
    actions = parser.add_subparsers(dest="action", required=True)
    restart = actions.add_parser("restart")
    restart.add_argument("--profile", choices=("keycloak", "issuer_fixture"), required=True)
    restart.add_argument("--cursor-ttl-seconds", type=int, default=900)
    actions.add_parser("wait-ready")
    args = parser.parse_args(list(arguments))
    if args.action == "wait-ready":
        record = run.get("processes", {}).get("api")
        if not isinstance(record, dict) or not record_is_owned(record):
            raise LifecycleError("API process is not owned by this run")
        wait_http(f"{run['urls']['api']}/health/ready", timeout=60)
        return {"ready": True}
    if run["namespace"] != "wuji-test":
        raise LifecycleError("API restart control is limited to wuji-test")
    existing = run.get("processes", {}).get("api")
    if not isinstance(existing, dict) or "pid" not in existing or not record_is_owned(existing):
        raise LifecycleError("recorded API process does not match its ownership data")
    update_process(
        path,
        "api",
        {"lifecycle_state": "restarting", "state_deadline": time.time() + 30},
    )
    if not terminate_record(existing):
        raise LifecycleError("owned API process could not be stopped")
    record = start_api(path, profile=args.profile, ttl=args.cursor_ttl_seconds)
    wait_http(f"{run['urls']['api']}/health/ready", timeout=60)
    return {
        "pid": record["pid"],
        "profile": args.profile,
        "cursor_ttl_seconds": args.cursor_ttl_seconds,
        "ready": True,
    }


def _db_forward(path: Path, run: dict[str, Any], arguments: Sequence[str]) -> dict[str, Any]:
    if run["namespace"] != "wuji-test":
        raise LifecycleError("database fault control is limited to wuji-test")
    if list(arguments) not in (["pause"], ["resume"]):
        raise LifecycleError("db-forward requires pause or resume")
    action = arguments[0]
    if action == "pause":
        pause_forward(path, "postgres")
        return {"paused": True}
    record = resume_forward(path, "postgres")
    return {"paused": False, "pid": record["pid"]}


def _ensure_forward(path: Path, service: str) -> dict[str, Any]:
    return resume_forward(path, service)


def _owned_postgres_pod(namespace: str) -> dict[str, Any]:
    pods = json.loads(
        run_command(
            [
                "kubectl",
                "--context",
                KUBECTL_CONTEXT,
                "--namespace",
                namespace,
                "get",
                "pod",
                "--selector",
                "app.kubernetes.io/name=postgres",
                "-o",
                "json",
            ]
        ).stdout
    ).get("items", [])
    if len(pods) != 1:
        raise LifecycleError("PostgreSQL deployment must have exactly one pod")
    pod = pods[0]
    metadata = pod.get("metadata", {})
    if metadata.get("namespace") != namespace:
        raise LifecycleError("PostgreSQL pod belongs to another namespace")
    if metadata.get("labels", {}).get("wuji.dev/owner") != OWNER_LABEL:
        raise LifecycleError("PostgreSQL pod has unexpected ownership")
    deployment = require_owned_resource("deployment", "postgres", namespace=namespace)
    if deployment is None:
        raise LifecycleError("owned PostgreSQL deployment is absent")
    deployment_uid = deployment.get("metadata", {}).get("uid")
    owners = [
        owner
        for owner in metadata.get("ownerReferences", [])
        if owner.get("kind") == "ReplicaSet" and owner.get("controller") is True
    ]
    if len(owners) != 1 or not owners[0].get("name") or not owners[0].get("uid"):
        raise LifecycleError("PostgreSQL pod controller ownership is invalid")
    if not deployment_uid:
        raise LifecycleError("PostgreSQL deployment UID is absent")
    replica_set = require_owned_resource(
        "replicaset", str(owners[0]["name"]), namespace=namespace
    )
    if replica_set is None or replica_set.get("metadata", {}).get("uid") != owners[0]["uid"]:
        raise LifecycleError("PostgreSQL ReplicaSet ownership is invalid")
    deployment_owners = [
        owner
        for owner in replica_set.get("metadata", {}).get("ownerReferences", [])
        if owner.get("kind") == "Deployment" and owner.get("controller") is True
    ]
    if (
        len(deployment_owners) != 1
        or deployment_owners[0].get("name") != "postgres"
        or deployment_owners[0].get("uid") != deployment_uid
    ):
        raise LifecycleError("PostgreSQL ReplicaSet is not owned by the platform deployment")
    return pod


def _postgres(path: Path, run: dict[str, Any], arguments: Sequence[str]) -> dict[str, Any]:
    if run["namespace"] != "wuji-test":
        raise LifecycleError("PostgreSQL recreation control is limited to wuji-test")
    if list(arguments) == ["pod-recreate"]:
        pod = _owned_postgres_pod(run["namespace"])
        metadata = pod["metadata"]
        name, uid = str(metadata["name"]), str(metadata["uid"])
        confirmed = require_owned_resource("pod", name, namespace=run["namespace"])
        if confirmed is None or confirmed.get("metadata", {}).get("uid") != uid:
            raise LifecycleError("PostgreSQL pod changed during ownership verification")
        run_command(
            [
                "kubectl",
                "--context",
                KUBECTL_CONTEXT,
                "delete",
                "--raw",
                f"/api/v1/namespaces/{run['namespace']}/pods/{name}",
                "-f",
                "-",
            ],
            input_text=json.dumps(
                {
                    "apiVersion": "v1",
                    "kind": "DeleteOptions",
                    "preconditions": {"uid": uid},
                }
            ),
            timeout=30,
        )

        def record_recreation(current: dict[str, Any]) -> None:
            current["control"]["recreated_postgres_pod"] = {"name": name, "uid": uid}

        mutate_manifest(path, record_recreation)
        return {"namespace": run["namespace"], "name": name, "uid": uid, "requested": True}
    if list(arguments) == ["wait-all-ready"]:
        previous = run.get("control", {}).get("recreated_postgres_pod")
        if not isinstance(previous, dict):
            raise LifecycleError("no PostgreSQL recreation request is recorded")
        deadline = time.monotonic() + 300
        current_pod: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            try:
                candidate = _owned_postgres_pod(run["namespace"])
                if candidate.get("metadata", {}).get("uid") != previous["uid"]:
                    current_pod = candidate
                    break
            except LifecycleError:
                pass
            time.sleep(0.5)
        if current_pod is None:
            raise LifecycleError("PostgreSQL pod replacement did not complete")
        wait_infrastructure(run["namespace"])
        _ensure_forward(path, "postgres")
        _ensure_forward(path, "keycloak")
        wait_http(f"{run['urls']['api']}/health/ready", timeout=120)
        return {
            "namespace": run["namespace"],
            "ready": True,
            "name": current_pod["metadata"]["name"],
            "uid": current_pod["metadata"]["uid"],
        }
    raise LifecycleError("postgres requires pod-recreate or wait-all-ready")


def _unmigrated(path: Path, run: dict[str, Any], arguments: Sequence[str]) -> dict[str, Any]:
    if list(arguments) == ["wait-ready"]:
        record = run.get("processes", {}).get("unmigrated")
        if not isinstance(record, dict) or not record_is_owned(record):
            raise LifecycleError("unmigrated API process is not owned by this run")
        wait_http(f"{run['urls']['unmigrated_api']}/health/live", timeout=60)
        wait_http(f"{run['urls']['unmigrated_api']}/health/ready", expected=503, timeout=60)
        return {"live": True, "ready": False}
    if list(arguments) == ["stop"]:
        record = run.get("processes", {}).get("unmigrated")
        stopped = isinstance(record, dict) and "pid" in record and terminate_record(record)
        if isinstance(record, dict):
            update_process(path, "unmigrated", {"lifecycle_state": "stopped"})
        return {"stopped": bool(stopped)}
    if list(arguments) != ["start"]:
        raise LifecycleError("unmigrated requires start, stop, or wait-ready")
    if run["namespace"] != "wuji-test":
        raise LifecycleError("unmigrated API is limited to wuji-test")
    existing = run.get("processes", {}).get("unmigrated")
    if isinstance(existing, dict) and "pid" in existing and record_is_owned(existing):
        if not terminate_record(existing):
            raise LifecycleError("existing unmigrated API could not be stopped")
    database_name = f"{run['database']['name']}_unmigrated"
    credentials = run["credentials"]["database"]

    def record_database(current: dict[str, Any]) -> None:
        current["control"].update(
            {
                "unmigrated_database": database_name,
                "unmigrated_admin_dsn": replace_database(credentials["admin_dsn"], "postgres"),
                "unmigrated_auth_dsn": replace_database(credentials["auth_dsn"], database_name),
                "unmigrated_project_dsn": replace_database(credentials["project_dsn"], database_name),
            }
        )

    mutate_manifest(path, record_database)
    from wuji_api.database_admin import credentials_from_database_url, prepare_database

    migration_role, migration_password = credentials_from_database_url(credentials["management_dsn"])
    auth_role, auth_password = credentials_from_database_url(credentials["auth_dsn"])
    project_role, project_password = credentials_from_database_url(credentials["project_dsn"])
    prepare_database(
        admin_database_url=replace_database(credentials["admin_dsn"], "postgres"),
        database=database_name,
        migration_role=migration_role,
        migration_password=migration_password,
        auth_role=auth_role,
        auth_password=auth_password,
        project_role=project_role,
        project_password=project_password,
    )
    record = start_api(path, profile="issuer_fixture", unmigrated=True)
    wait_http(f"{run['urls']['unmigrated_api']}/health/live", timeout=60)
    wait_http(f"{run['urls']['unmigrated_api']}/health/ready", expected=503, timeout=60)
    return {"database": database_name, "pid": record["pid"], "live": True, "ready": False}


def _query_unmigrated(run: dict[str, Any]) -> dict[str, Any]:
    database_name = run.get("control", {}).get("unmigrated_database")
    if not database_name:
        raise LifecycleError("unmigrated database has not been created")
    import psycopg

    dsn = replace_database(run["credentials"]["database"]["admin_dsn"], database_name)
    dsn = dsn.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.alembic_version') IS NOT NULL")
        alembic = bool(cursor.fetchone()[0])
        cursor.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = ANY(%s)",
            (["users", "sessions", "projects", "project_memberships"],),
        )
        business = int(cursor.fetchone()[0]) > 0
    return {"alembic_version_present": alembic, "business_tables_present": business}


def main() -> None:
    top = SafeArgumentParser(prog="wuji-platform-control")
    top.add_argument("--run-file", required=True)
    top.add_argument("arguments", nargs=argparse.REMAINDER)
    run_id: str | None = None
    try:
        args = top.parse_args()
        path, run = _load_owned(args.run_file)
        run_id = run["run_id"]
        if not args.arguments:
            raise LifecycleError("a control command is required")
        command, rest = args.arguments[0], args.arguments[1:]
        if command in DELEGATED or (command == "query" and rest != ["unmigrated-revision"]):
            exit_code, payload = _manager(path, args.arguments)
            output = json.dumps(payload, separators=(",", ":"), sort_keys=True)
            print(output, file=sys.stdout if exit_code == 0 else sys.stderr)
            raise SystemExit(exit_code)
        if command == "api":
            result = _api(path, run, rest)
        elif command == "db-forward":
            result = _db_forward(path, run, rest)
        elif command == "postgres":
            result = _postgres(path, run, rest)
        elif command == "unmigrated":
            result = _unmigrated(path, run, rest)
        elif command == "query" and rest == ["unmigrated-revision"]:
            result = _query_unmigrated(run)
        else:
            raise LifecycleError("unknown control command")
        print(json.dumps({"ok": True, "run_id": run_id, "result": result}, separators=(",", ":"), sort_keys=True))
    except SystemExit:
        raise
    except Exception as error:
        print(json.dumps(safe_error_payload(run_id=run_id, error=error), separators=(",", ":"), sort_keys=True), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
