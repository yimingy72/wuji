"""Explicit local LiteLLM lifecycle. Never calls a model or starts the Wuji API."""
from __future__ import annotations

import argparse
import base64
import json
import secrets
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

import psycopg
from psycopg import sql

from common import (
    KUBECTL_CONTEXT, OWNER_LABEL, REPOSITORY_ROOT, LifecycleError,
    assert_run_ownership, exclusive_lock, json_output, load_manifest,
    minimal_environment, mutate_manifest, preflight_ports, process_group_exists, record_is_owned,
    require_context, require_owned_resource, run_command, safe_error_payload,
    spawn_registered, terminate_record, update_process, wait_http,
)

IMAGE = "ghcr.io/berriai/litellm@sha256:c8756e7b9a61fe45df2ccb5b781d388c3b2f3a21ef9e4956630caef20f9f03aa"
INSTANCE_LABEL = "wuji.dev/gateway-instance"


def metadata(run: dict[str, Any], name: str) -> dict[str, Any]:
    return {"name": name, "namespace": run["namespace"], "labels": {
        "wuji.dev/owner": OWNER_LABEL,
        "app.kubernetes.io/part-of": "wuji",
        INSTANCE_LABEL: run["model_gateway"]["instance_id"],
    }}


def owned(run: dict[str, Any], kind: str, name: str) -> dict[str, Any] | None:
    resource = require_owned_resource(kind, name, namespace=run["namespace"])
    if resource is not None and resource["metadata"].get("labels", {}).get(INSTANCE_LABEL) != run["model_gateway"]["instance_id"]:
        raise LifecycleError("gateway resource belongs to another instance")
    return resource


def write_resource(run: dict[str, Any], resource: dict[str, Any]) -> dict[str, Any]:
    kind, name = resource["kind"], resource["metadata"]["name"]
    previous = owned(run, kind, name)
    if previous:
        resource["metadata"]["resourceVersion"] = previous["metadata"]["resourceVersion"]
        resource["metadata"]["uid"] = previous["metadata"]["uid"]
    run_command(["kubectl", "--context", KUBECTL_CONTEXT, "--namespace", run["namespace"],
                 "replace" if previous else "create", "-f", "-"], input_text=json.dumps(resource))
    current = owned(run, kind, name)
    if current is None:
        raise LifecycleError("gateway resource write could not be verified")
    return current


def secret_value(run: dict[str, Any], kind: str, generate: bool) -> str:
    name = run["model_gateway"][f"{kind}_secret_name"]
    resource = owned(run, "Secret", name)
    if resource is None:
        if not generate:
            raise LifecycleError("gateway persistent Secret is absent; refusing rotation")
        value = ("sk-" if kind == "master" else "") + secrets.token_urlsafe(48)
        resource = write_resource(run, {"apiVersion": "v1", "kind": "Secret",
            "metadata": metadata(run, name), "type": "Opaque", "immutable": True,
            "stringData": {"value": value}})
    try:
        if set(resource["data"]) != {"value"}:
            raise ValueError("shape")
        value = base64.b64decode(resource["data"]["value"], validate=True).decode()
        if not value:
            raise ValueError("empty")
        return value
    except (KeyError, ValueError, UnicodeDecodeError) as error:
        raise LifecycleError("gateway persistent Secret is malformed") from error


def prepare_database(run: dict[str, Any], password: str) -> None:
    gateway = run["model_gateway"]
    role, database = gateway["database_role"], gateway["database_name"]
    marker = f"wuji-model-gateway:{gateway['instance_id']}"
    dsn = run["credentials"]["database"]["admin_dsn"].replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(dsn, autocommit=True, connect_timeout=10) as connection:
        # A server-side lock serializes preparation even across local lifecycle processes.
        connection.execute("SELECT pg_advisory_lock(hashtextextended(%s, 0))", (marker,))
        row = connection.execute("SELECT shobj_description(oid, 'pg_authid'), rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls FROM pg_roles WHERE rolname=%s", (role,)).fetchone()
        if row is None:
            connection.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}").format(sql.Identifier(role), sql.Literal(password)))
            connection.execute(sql.SQL("COMMENT ON ROLE {} IS {}").format(sql.Identifier(role), sql.Literal(marker)))
        elif row != (marker, False, False, False, False, False):
            raise LifecycleError("gateway database role ownership or privilege mismatch")
        memberships = connection.execute("SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=%s) LIMIT 1", (role,)).fetchone()
        if memberships:
            raise LifecycleError("gateway database role has unexpected memberships")
        row = connection.execute("SELECT pg_get_userbyid(datdba), shobj_description(oid, 'pg_database') FROM pg_database WHERE datname=%s", (database,)).fetchone()
        if row is None:
            connection.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(database), sql.Identifier(role)))
            connection.execute(sql.SQL("COMMENT ON DATABASE {} IS {}").format(sql.Identifier(database), sql.Literal(marker)))
        elif row != (role, marker):
            raise LifecycleError("gateway database belongs to another authority")
        connection.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database)))


def prepare(path: Path) -> dict[str, Any]:
    run = load_manifest(path)
    if require_owned_resource("namespace", run["namespace"]) is None:
        raise LifecycleError("prepare the owned platform infrastructure first")
    if require_owned_resource("service", "postgres", namespace=run["namespace"]) is None:
        raise LifecycleError("owned PostgreSQL service is absent")
    if "model_gateway" not in run:
        common_git = Path(run_command(["git", "rev-parse", "--git-common-dir"]).stdout.strip())
        if not common_git.is_absolute():
            common_git = (REPOSITORY_ROOT / common_git).resolve()
        # Development restarts/new source runs retain the same native data identity.
        # Tests use their run ID to keep fixtures independent.
        scope = run["namespace"] + (":" + run["run_id"] if run["profile"] == "test" else "")
        instance = str(uuid5(NAMESPACE_URL, f"{common_git}:{scope}:model-gateway"))
        suffix = instance.replace("-", "")
        gateway = {"instance_id": instance, "url": f"http://127.0.0.1:{18400 if run['profile'] == 'dev' else 18402}",
                   "database_name": f"wuji_gateway_{suffix}", "database_role": f"wg_{suffix}",
                   "master_key": "pending"}
        gateway.update({f"{kind}_secret_name": f"wg-{suffix}-{kind}" for kind in ("master", "salt", "database")})
        run["model_gateway"] = gateway
        # Recovery from an interrupted first prepare reuses the same immutable Secrets.
        master = secret_value(run, "master", True)
        secret_value(run, "salt", True)
        password = secret_value(run, "database", True)
        prepare_database(run, password)
        gateway["master_key"] = master
        run, _ = mutate_manifest(path, lambda value: value.update(model_gateway=gateway))
    else:
        if secret_value(run, "master", False) != run["model_gateway"]["master_key"]:
            raise LifecycleError("gateway management key no longer matches its persistent Secret")
        secret_value(run, "salt", False)
        prepare_database(run, secret_value(run, "database", False))
    return run


def resources(run: dict[str, Any]) -> list[dict[str, Any]]:
    gateway = run["model_gateway"]
    name = "wg-" + gateway["instance_id"].replace("-", "")
    labels = metadata(run, name)["labels"]
    config = (REPOSITORY_ROOT / "infra/kubernetes/model-gateway/config.yaml").read_text()
    env = [{"name": key, "value": value} for key, value in {
        "LITELLM_TELEMETRY": "False", "DO_NOT_TRACK": "1",
        "STORE_MODEL_IN_DB": "True", "LITELLM_LOG": "ERROR",
    }.items()]
    env += [{"name": key, "valueFrom": {"secretKeyRef": {"name": gateway[f"{kind}_secret_name"], "key": "value"}}}
            for key, kind in (("LITELLM_MASTER_KEY", "master"), ("LITELLM_SALT_KEY", "salt"), ("PGPASSWORD", "database"))]
    # Kubernetes expands a prior env variable without writing the DB password to the run file.
    env.append({"name": "DATABASE_URL", "value": f"postgresql://{gateway['database_role']}:$(PGPASSWORD)@postgres:5432/{gateway['database_name']}"})
    return [
        {"apiVersion": "v1", "kind": "ConfigMap", "metadata": metadata(run, name), "data": {"config.yaml": config}},
        {"apiVersion": "v1", "kind": "Service", "metadata": metadata(run, name),
         "spec": {"selector": labels, "ports": [{"name": "http", "port": 4000, "targetPort": 4000}]}},
        {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": metadata(run, name), "spec": {
            "replicas": 1, "strategy": {"type": "Recreate"}, "selector": {"matchLabels": labels},
            "template": {"metadata": {"labels": labels}, "spec": {
                "automountServiceAccountToken": False,
                "containers": [{"name": "model-gateway", "image": IMAGE, "imagePullPolicy": "IfNotPresent",
                    "args": ["--config", "/etc/litellm/config.yaml", "--port", "4000", "--num_workers", "1"],
                    "env": env, "ports": [{"containerPort": 4000}],
                    "volumeMounts": [{"name": "config", "mountPath": "/etc/litellm", "readOnly": True}],
                    "readinessProbe": {"httpGet": {"path": "/health/readiness", "port": 4000}, "initialDelaySeconds": 10, "periodSeconds": 5},
                    "livenessProbe": {"httpGet": {"path": "/health/liveliness", "port": 4000}, "initialDelaySeconds": 60, "periodSeconds": 15},
                    "resources": {"requests": {"cpu": "100m", "memory": "512Mi"}, "limits": {"cpu": "2", "memory": "2Gi"}},
                }], "volumes": [{"name": "config", "configMap": {"name": name}}],
            }}}},
    ]


def up(path: Path) -> dict[str, Any]:
    initial = load_manifest(path)
    if not record_is_owned(initial["processes"].get("model_gateway_forward", {})):
        preflight_ports([18400 if initial["profile"] == "dev" else 18402])
    run = prepare(path)
    name = "wg-" + run["model_gateway"]["instance_id"].replace("-", "")
    desired = resources(run)
    for resource in desired:
        owned(run, resource["kind"], resource["metadata"]["name"])
    existing = run["processes"].get("model_gateway_forward", {})
    port = urlsplit(run["model_gateway"]["url"]).port
    if not record_is_owned(existing):
        preflight_ports([port])
    for resource in desired:
        write_resource(run, resource)
    run_command(["kubectl", "--context", KUBECTL_CONTEXT, "--namespace", run["namespace"],
                 "rollout", "status", f"deployment/{name}", "--timeout=300s"], timeout=330)
    existing = run["processes"].get("model_gateway_forward", {})
    if not record_is_owned(existing):
        port = urlsplit(run["model_gateway"]["url"]).port
        preflight_ports([port])
        command = ["kubectl", "--context", KUBECTL_CONTEXT, "--namespace", run["namespace"],
                   "port-forward", "--address", "127.0.0.1", f"service/{name}", f"{port}:4000"]
        process, record = spawn_registered(path, "model_gateway_forward", command,
            log_path=Path(run["artifacts_dir"]) / "model-gateway-forward.log",
            command_marker=f"kubectl port-forward service/{name}", env=minimal_environment())
        try:
            wait_http(run["model_gateway"]["url"] + "/health/readiness", timeout=60)
        except BaseException:
            terminate_record(record, process=process)
            update_process(path, "model_gateway_forward", {"lifecycle_state": "exited", "exit_code": 1})
            raise
    return status(path)


def down(path: Path) -> dict[str, Any]:
    run = load_manifest(path)
    if "model_gateway" not in run:
        return {"configured": False}
    record = run["processes"].get("model_gateway_forward", {})
    if record_is_owned(record):
        terminate_record(record)
        update_process(path, "model_gateway_forward", {"lifecycle_state": "stopped"})
    name = "wg-" + run["model_gateway"]["instance_id"].replace("-", "")
    deployment = owned(run, "Deployment", name)
    if deployment:
        endpoint = f"/apis/apps/v1/namespaces/{run['namespace']}/deployments/{name}"
        run_command(["kubectl", "--context", KUBECTL_CONTEXT, "delete", "--raw", endpoint, "-f", "-"],
            input_text=json.dumps({"apiVersion": "v1", "kind": "DeleteOptions", "propagationPolicy": "Foreground",
                "preconditions": {"uid": deployment["metadata"]["uid"], "resourceVersion": deployment["metadata"]["resourceVersion"]}}))
        return {"configured": True, "state": "stopping", "persistent_data_retained": True}
    return status(path)


def status(path: Path) -> dict[str, Any]:
    run = load_manifest(path)
    if "model_gateway" not in run:
        return {"configured": False}
    gateway = run["model_gateway"]
    name = "wg-" + gateway["instance_id"].replace("-", "")
    deployment = owned(run, "Deployment", name)
    record = run["processes"].get("model_gateway_forward", {})
    forward_owned = record_is_owned(record)
    forward_stopped = not forward_owned and (
        "process_group" not in record or not process_group_exists(int(record["process_group"]))
    )
    state = "stopped" if deployment is None and forward_stopped else (
        "stopping" if deployment is not None and deployment["metadata"].get("deletionTimestamp") else "active"
    )
    return {"configured": True, "instance_id": gateway["instance_id"], "url": gateway["url"],
            "state": state, "persistent_data_retained": True,
            "deployment_present": deployment is not None,
            "ready_replicas": (deployment or {}).get("status", {}).get("readyReplicas", 0),
            "forward_owned": forward_owned, "forward_stopped": forward_stopped}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "up", "down", "status"))
    parser.add_argument("--run-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        run = load_manifest(args.run_file)
        assert_run_ownership(run)
        with exclusive_lock(args.run_file.with_name(f".{args.run_file.name}.gateway.lock")):
            require_context()
            result = {"prepared": True, "instance_id": prepare(args.run_file)["model_gateway"]["instance_id"]} if args.action == "prepare" else globals()[args.action](args.run_file)
        print(json_output(result))
        return 0
    except Exception as error:
        print(json.dumps(safe_error_payload(run_id=None, error=error)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
