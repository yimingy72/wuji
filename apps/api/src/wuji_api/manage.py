"""Non-interactive trusted management CLI for local Phase 1A runs."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import psycopg

from wuji_api.database_admin import (
    bump_permissions_version,
    change_membership,
    credentials_from_database_url,
    inspect_authority,
    migrate_database,
    prepare_database,
    seed_database,
    set_session_times,
    set_user_enabled,
)
from wuji_api.keycloak_admin import provision_keycloak
from wuji_api.run_file import load_run_file


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wuji-manage")
    parser.add_argument("--run-file", required=True)
    commands = parser.add_subparsers(dest="command", required=True)

    database = commands.add_parser("database")
    database_actions = database.add_subparsers(dest="database_command", required=True)
    prepare = database_actions.add_parser("prepare")
    prepare.add_argument("--migrate", action="store_true")
    database_actions.add_parser("migrate")
    database_actions.add_parser("seed")

    identity = commands.add_parser("identity")
    identity.add_subparsers(dest="identity_command", required=True).add_parser("provision")

    permissions = commands.add_parser("permissions")
    permissions_actions = permissions.add_subparsers(dest="permission_action", required=True)
    for action in ("grant", "revoke"):
        command = permissions_actions.add_parser(action)
        command.add_argument("--scope", choices=("tenant", "project"), required=True)
        command.add_argument("--user", required=True)
        command.add_argument("--tenant", required=True)
        command.add_argument("--project")
        command.add_argument("--role", choices=("operator", "viewer"), required=True)
        command.add_argument("--simulate-audit-failure", action="store_true")

    user = commands.add_parser("user")
    user_actions = user.add_subparsers(dest="user_action", required=True)
    for action in ("enable", "disable"):
        command = user_actions.add_parser(action)
        command.add_argument("--user", required=True)

    session = commands.add_parser("session")
    session_actions = session.add_subparsers(dest="session_action", required=True)
    set_times = session_actions.add_parser("set-times")
    set_times.add_argument("--user", required=True)
    set_times.add_argument("--last-seen")
    set_times.add_argument("--absolute-expires")

    cursor = commands.add_parser("cursor")
    cursor_actions = cursor.add_subparsers(dest="cursor_action", required=True)
    bump = cursor_actions.add_parser("bump-permissions-version")
    bump.add_argument("--user", required=True)

    query = commands.add_parser("query")
    query_actions = query.add_subparsers(dest="query_action", required=True)
    authority = query_actions.add_parser("authority")
    authority.add_argument("--user")
    roles = query_actions.add_parser("roles")
    roles.add_argument("--include-migration", action="store_true")
    rls = query_actions.add_parser("rls")
    rls.add_argument("--user", required=True)
    return parser


def _database_credentials(run: dict[str, Any]) -> dict[str, str]:
    return run["credentials"]["database"]


def _resolve_user(run: dict[str, Any], symbol: str) -> str:
    try:
        return run["seed_users"][symbol]["id"]
    except KeyError as error:
        raise ValueError("unknown seed user symbol") from error


def _resolve_tenant(run: dict[str, Any], symbol: str) -> str:
    try:
        return run["seed_entities"]["tenants"][symbol]["id"]
    except KeyError as error:
        raise ValueError("unknown tenant symbol") from error


def _resolve_project(run: dict[str, Any], symbol: str | None) -> str | None:
    if symbol is None:
        return None
    try:
        return run["seed_entities"]["projects"][symbol]["id"]
    except KeyError as error:
        raise ValueError("unknown project symbol") from error


def _prepare(run: dict[str, Any], *, migrate: bool) -> dict[str, Any]:
    credentials = _database_credentials(run)
    roles = run["database"]["roles"]
    migration_role, migration_password = credentials_from_database_url(credentials["management_dsn"])
    auth_role, auth_password = credentials_from_database_url(credentials["auth_dsn"])
    project_role, project_password = credentials_from_database_url(credentials["project_dsn"])
    if (migration_role, auth_role, project_role) != (
        roles["migration"],
        roles["auth"],
        roles["project"],
    ):
        raise ValueError("database URL roles do not match the ownership record")
    prepare_database(
        admin_database_url=credentials["admin_dsn"],
        database=run["database"]["name"],
        migration_role=migration_role,
        migration_password=migration_password,
        auth_role=auth_role,
        auth_password=auth_password,
        project_role=project_role,
        project_password=project_password,
    )
    if migrate:
        _migrate(run)
    return {"prepared": True, "migrated": migrate, "database": run["database"]["name"]}


def _migrate(run: dict[str, Any]) -> dict[str, Any]:
    credentials = _database_credentials(run)
    migrate_database(
        migration_database_url=credentials["management_dsn"],
        auth_role=run["database"]["roles"]["auth"],
        project_role=run["database"]["roles"]["project"],
    )
    return {"migrated": True, "revision": "20260909_0001"}


def _query_roles(run: dict[str, Any], include_migration: bool) -> dict[str, Any]:
    roles = run["database"]["roles"]
    role_names = [roles["auth"], roles["project"]]
    if include_migration:
        role_names.append(roles["migration"])
    dsn = _database_credentials(run)["admin_dsn"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT rolname, rolsuper, rolinherit, rolcreaterole, rolcreatedb, rolbypassrls "
            "FROM pg_roles WHERE rolname = ANY(%s) ORDER BY rolname",
            (role_names,),
        )
        result = [
            {
                "name": row[0],
                "superuser": row[1],
                "inherit": row[2],
                "create_role": row[3],
                "create_database": row[4],
                "bypass_rls": row[5],
            }
            for row in cursor.fetchall()
        ]
    return {"roles": result}


def _query_rls(run: dict[str, Any], user_id: str) -> dict[str, Any]:
    dsn = _database_credentials(run)["project_dsn"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM projects")
        without_context = int(cursor.fetchone()[0])
        cursor.execute("SELECT set_config('app.user_id', %s, true)", (user_id,))
        cursor.execute("SELECT id::text FROM projects ORDER BY id")
        project_ids = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT user_id::text, project_id::text FROM project_memberships ORDER BY project_id")
        memberships = [{"user_id": row[0], "project_id": row[1]} for row in cursor.fetchall()]
    return {
        "without_context_project_count": without_context,
        "project_ids": project_ids,
        "project_memberships": memberships,
    }


def execute(args: argparse.Namespace, run_path, run: dict[str, Any]) -> dict[str, Any]:
    credentials = _database_credentials(run)
    if args.command == "database":
        if args.database_command == "prepare":
            return _prepare(run, migrate=args.migrate)
        if args.database_command == "migrate":
            return _migrate(run)
        return {"seeded": seed_database(migration_database_url=credentials["management_dsn"], run=run)}
    if args.command == "identity":
        return {"provisioned": provision_keycloak(run_path, run)}
    if args.command == "permissions":
        changed = change_membership(
            database_url_value=credentials["management_dsn"],
            scope=args.scope,
            enabled=args.permission_action == "grant",
            user_id=_resolve_user(run, args.user),
            tenant_id=_resolve_tenant(run, args.tenant),
            project_id=_resolve_project(run, args.project),
            role=args.role,
            simulate_failure=args.simulate_audit_failure,
        )
        return {"changed": changed}
    if args.command == "user":
        return {
            "changed": set_user_enabled(
                database_url_value=credentials["management_dsn"],
                user_id=_resolve_user(run, args.user),
                enabled=args.user_action == "enable",
            )
        }
    if args.command == "session":
        return {
            "changed": set_session_times(
                database_url_value=credentials["management_dsn"],
                user_id=_resolve_user(run, args.user),
                last_seen_at=args.last_seen,
                absolute_expires_at=args.absolute_expires,
            )
        }
    if args.command == "cursor":
        return {
            "permissions_version": bump_permissions_version(
                database_url_value=credentials["management_dsn"],
                user_id=_resolve_user(run, args.user),
            )
        }
    if args.query_action == "authority":
        user_id = None if args.user is None else _resolve_user(run, args.user)
        return inspect_authority(database_url_value=credentials["management_dsn"], user_id=user_id)
    if args.query_action == "roles":
        return _query_roles(run, args.include_migration)
    return _query_rls(run, _resolve_user(run, args.user))


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    run_id: str | None = None
    try:
        run_path, run = load_run_file(args.run_file)
        run_id = run["run_id"]
        result = execute(args, run_path, run)
    except Exception as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "run_id": run_id,
                    "error": {
                        "code": error.__class__.__name__,
                        "message": "management operation failed safely",
                    },
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    print(
        json.dumps(
            {"ok": True, "run_id": run_id, "result": result},
            separators=(",", ":"),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
