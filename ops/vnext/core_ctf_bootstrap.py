"""Create an empty Core CTF tenant/project and database roles; never create a Task."""

import json
import os
from pathlib import Path

import psycopg
from psycopg import sql

from wuji_core.http import strict_json_loads
from wuji_core.persistence.schema import migrate


def initialize(config):
    if (
        not isinstance(config, dict)
        or config.get("schema_version") != "wuji.core-ctf-bootstrap.v1"
        or set(config.get("roles") or ())
        != {"wuji_migration", "wuji_app", "wuji_pod"}
    ):
        raise ValueError("fixed Core CTF bootstrap configuration required")
    database = config["database"]
    if set(database) != {"host", "port", "dbname", "user", "password"}:
        raise ValueError("explicit bootstrap database binding required")
    tls = {
        "sslmode": "verify-full",
        "sslrootcert": config["ca_file"],
        "connect_timeout": 5,
    }
    with psycopg.connect(**database, **tls, autocommit=True) as admin:
        for role, password in config["roles"].items():
            if not admin.execute(
                "SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)
            ).fetchone():
                admin.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD {}"
                    ).format(sql.Identifier(role), sql.Literal(password))
                )
        admin.execute(
            sql.SQL("GRANT CONNECT,CREATE ON DATABASE {} TO wuji_migration").format(
                sql.Identifier(database["dbname"])
            )
        )
        admin.execute("GRANT wuji_app TO wuji_pod")
    migration = {
        key: database[key] for key in ("host", "port", "dbname")
    } | {
        "user": "wuji_migration",
        "password": config["roles"]["wuji_migration"],
    }
    with psycopg.connect(**migration, **tls, autocommit=True) as connection:
        migrate(connection, application_role="wuji_app")
        tenant_id, project_id = config["tenant_id"], config["project_id"]
        subject = config["operator_subject"]
        with connection.transaction():
            connection.execute(
                "INSERT INTO vnext.tenant(tenant_id) VALUES(%s) ON CONFLICT DO NOTHING",
                (tenant_id,),
            )
            connection.execute(
                "INSERT INTO vnext.project(tenant_id,project_id) VALUES(%s,%s) "
                "ON CONFLICT DO NOTHING",
                (tenant_id, project_id),
            )
            connection.execute(
                "INSERT INTO vnext.project_access(tenant_id,project_id,subject,"
                "can_create,clearance) VALUES(%s,%s,%s,true,1) "
                "ON CONFLICT(tenant_id,project_id,subject) DO UPDATE SET "
                "can_create=true,clearance=GREATEST(vnext.project_access.clearance,1)",
                (tenant_id, project_id, subject),
            )
    return {"event": "core_ctf_empty_project_ready", "project_id": project_id}


if __name__ == "__main__":
    path = Path(os.environ.get("WUJI_CORE_CTF_BOOTSTRAP", "/run/wuji/bootstrap/config.json"))
    try:
        print(json.dumps(initialize(strict_json_loads(path.read_bytes())), sort_keys=True))
    except Exception as error:
        print(json.dumps({"event": "core_ctf_bootstrap_failed", "error": type(error).__name__}))
        raise SystemExit(1) from None
