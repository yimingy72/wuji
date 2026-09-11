"""Trusted database initialization and Phase 1A seed operations.

This module is used only by the local management process. The API runtime never
imports migration credentials and never changes PostgreSQL roles.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit
from uuid import UUID, uuid5

import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql

from wuji_api.scope_policy import normalize_approved_scope, normalize_origin, policy_hash
from wuji_api.scopes import ScopeImportDocument

ROLE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
DATABASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
ROLES = frozenset({"operator", "viewer"})
SEED_NAMESPACE = UUID("dd2f1cf7-19f9-4c71-8db8-398e59384cb3")
USER_LOCK_SEED = 0x57554A49


def safe_identifier(value: str, *, kind: str) -> str:
    pattern = DATABASE_PATTERN if kind == "database" else ROLE_PATTERN
    if not pattern.fullmatch(value):
        raise ValueError(f"invalid {kind} identifier")
    return value


def database_url(host: str, port: int, database: str, role: str, password: str) -> str:
    safe_identifier(database, kind="database")
    safe_identifier(role, kind="role")
    return (
        f"postgresql+psycopg://{quote(role, safe='')}:{quote(password, safe='')}"
        f"@{host}:{port}/{database}"
    )


def _psycopg_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def prepare_database(
    *,
    admin_database_url: str,
    database: str,
    migration_role: str,
    migration_password: str,
    auth_role: str,
    auth_password: str,
    project_role: str,
    project_password: str,
) -> None:
    database = safe_identifier(database, kind="database")
    roles = (
        (safe_identifier(migration_role, kind="role"), migration_password, True),
        (safe_identifier(auth_role, kind="role"), auth_password, False),
        (safe_identifier(project_role, kind="role"), project_password, False),
    )
    with psycopg.connect(_psycopg_url(admin_database_url), autocommit=True) as connection:
        with connection.cursor() as cursor:
            for role, password, bypass_rls in roles:
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
                if cursor.fetchone() is None:
                    cursor.execute(
                        sql.SQL("CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE {}")
                        .format(
                            sql.Identifier(role),
                            sql.SQL("BYPASSRLS") if bypass_rls else sql.SQL("NOBYPASSRLS"),
                        )
                    )
                cursor.execute(
                    sql.SQL(
                        "ALTER ROLE {} WITH LOGIN NOINHERIT NOSUPERUSER NOCREATEDB "
                        "NOCREATEROLE {} PASSWORD {}"
                    ).format(
                        sql.Identifier(role),
                        sql.SQL("BYPASSRLS") if bypass_rls else sql.SQL("NOBYPASSRLS"),
                        sql.Literal(password),
                    )
                )

            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
            if cursor.fetchone() is None:
                cursor.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}")
                    .format(sql.Identifier(database), sql.Identifier(migration_role))
                )
            else:
                cursor.execute(
                    sql.SQL("ALTER DATABASE {} OWNER TO {}")
                    .format(sql.Identifier(database), sql.Identifier(migration_role))
                )
            cursor.execute(
                sql.SQL("REVOKE CONNECT, CREATE, TEMPORARY ON DATABASE {} FROM PUBLIC").format(
                    sql.Identifier(database)
                )
            )
            cursor.execute(
                sql.SQL("REVOKE TEMPORARY ON DATABASE {} FROM {}, {}").format(
                    sql.Identifier(database),
                    sql.Identifier(auth_role),
                    sql.Identifier(project_role),
                )
            )
            cursor.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}, {}, {}").format(
                    sql.Identifier(database),
                    sql.Identifier(migration_role),
                    sql.Identifier(auth_role),
                    sql.Identifier(project_role),
                )
            )
    target_admin_url = database_url(
        urlsplit(admin_database_url).hostname or "",
        urlsplit(admin_database_url).port or 5432,
        database,
        *credentials_from_database_url(admin_database_url),
    )
    with psycopg.connect(_psycopg_url(target_admin_url), autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("REVOKE CREATE ON SCHEMA public FROM PUBLIC, {}, {}").format(
                    sql.Identifier(auth_role),
                    sql.Identifier(project_role),
                )
            )


def migrate_database(
    *, migration_database_url: str, auth_role: str, project_role: str
) -> None:
    app_root = Path(__file__).resolve().parents[2]
    config = Config(str(app_root / "alembic.ini"))
    previous = {
        name: os.environ.get(name)
        for name in ("WUJI_MIGRATION_DATABASE_URL", "WUJI_AUTH_DB_ROLE", "WUJI_PROJECT_DB_ROLE")
    }
    os.environ["WUJI_MIGRATION_DATABASE_URL"] = migration_database_url
    os.environ["WUJI_AUTH_DB_ROLE"] = safe_identifier(auth_role, kind="role")
    os.environ["WUJI_PROJECT_DB_ROLE"] = safe_identifier(project_role, kind="role")
    try:
        command.upgrade(config, "head")
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def seed_uuid(seed_key: str, symbol: str) -> UUID:
    return uuid5(SEED_NAMESPACE, f"{seed_key}:{symbol}")


def credentials_from_database_url(url: str) -> tuple[str, str]:
    parsed = urlsplit(url)
    if parsed.username is None or parsed.password is None:
        raise ValueError("database URL must include a role and password")
    return unquote(parsed.username), unquote(parsed.password)


def build_seed_entities(seed_key: str) -> dict[str, dict[str, Any]]:
    tenant_ids = {
        symbol: str(seed_uuid(seed_key, f"tenants:{symbol}"))
        for symbol in ("tenant_a", "tenant_b")
    }
    project_specs = {
        "project_a_primary": ("tenant_a", "A Primary"),
        "project_a_secondary": ("tenant_a", "A Secondary"),
        "project_b_primary": ("tenant_b", "B Primary"),
        "split_project_u1": ("tenant_a", "A Split One"),
        "split_project_u2": ("tenant_a", "A Split Two"),
        **{
            f"dual_page_{index:02d}": ("tenant_a", f"Dual Page {index:02d}")
            for index in range(1, 53)
        },
    }
    return {
        "tenants": {
            "tenant_a": {"id": tenant_ids["tenant_a"], "name": "Tenant A"},
            "tenant_b": {"id": tenant_ids["tenant_b"], "name": "Tenant B"},
        },
        "projects": {
            symbol: {
                "id": str(seed_uuid(seed_key, f"projects:{symbol}")),
                "tenant_id": tenant_ids[tenant_symbol],
                "name": name,
            }
            for symbol, (tenant_symbol, name) in project_specs.items()
        },
    }


def seed_database(*, migration_database_url: str, run: Mapping[str, Any]) -> dict[str, int]:
    entities = run["seed_entities"]
    seed_users = run["seed_users"]
    tenant_ids = {symbol: value["id"] for symbol, value in entities["tenants"].items()}
    project_ids = {symbol: value["id"] for symbol, value in entities["projects"].items()}
    user_ids = {symbol: value["id"] for symbol, value in seed_users.items()}

    tenants = ((tenant_ids["tenant_a"], "Tenant A"), (tenant_ids["tenant_b"], "Tenant B"))
    projects = tuple(
        (project["id"], project["tenant_id"], project["name"])
        for project in entities["projects"].values()
    )
    tenant_memberships = (
        ("single_a", "tenant_a", "operator"),
        ("viewer_a", "tenant_a", "viewer"),
        ("single_b", "tenant_b", "operator"),
        ("dual_ab", "tenant_a", "viewer"),
        ("dual_ab", "tenant_b", "operator"),
        ("no_projects", "tenant_a", "viewer"),
        ("tenant_split_u1", "tenant_a", "viewer"),
        ("tenant_split_u2", "tenant_a", "viewer"),
    )
    project_memberships = (
        ("single_a", "tenant_a", "project_a_primary", "operator"),
        ("viewer_a", "tenant_a", "project_a_secondary", "viewer"),
        ("single_b", "tenant_b", "project_b_primary", "operator"),
        ("dual_ab", "tenant_a", "project_a_primary", "viewer"),
        ("dual_ab", "tenant_b", "project_b_primary", "operator"),
        ("tenant_split_u1", "tenant_a", "split_project_u1", "viewer"),
        ("tenant_split_u2", "tenant_a", "split_project_u2", "viewer"),
        *(
            ("dual_ab", "tenant_a", f"dual_page_{index:02d}", "viewer")
            for index in range(1, 53)
        ),
    )

    fixture_origin = normalize_origin(run["urls"]["issuer_fixture"])
    seed_scope = normalize_approved_scope(
        {
            "label": "Development HTTP fixture",
            "origins": [fixture_origin],
            "allowed_path_prefixes": ["/"],
            "excluded_path_prefixes": ["/admin"],
            "allowed_methods": ["GET", "HEAD"],
            "limits": {
                "max_total_requests": 20,
                "requests_per_second": 1.0,
                "max_concurrent_requests": 1,
                "request_timeout_seconds": 5,
                "max_response_bytes": 262_144,
                "max_runtime_seconds": 120,
            },
        }
    )
    seed_scope_projects = ("project_a_primary", "project_a_secondary", "project_b_primary")
    counts = {
        "users": 0,
        "external_identities": 0,
        "tenants": 0,
        "projects": 0,
        "authorization_records": 0,
        "scope_policy_versions": 0,
    }
    with psycopg.connect(_psycopg_url(migration_database_url)) as connection:
        with connection.cursor() as cursor:
            for tenant_id, name in tenants:
                cursor.execute(
                    "INSERT INTO tenants (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                    (tenant_id, name),
                )
                counts["tenants"] += cursor.rowcount
            for project_id, tenant_id, name in projects:
                cursor.execute(
                    "INSERT INTO projects (id, tenant_id, name) VALUES (%s, %s, %s) "
                    "ON CONFLICT (id) DO NOTHING",
                    (project_id, tenant_id, name),
                )
                counts["projects"] += cursor.rowcount
            for symbol, user in seed_users.items():
                user_id = user_ids[symbol]
                cursor.execute(
                    "INSERT INTO users (id, display_name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                    (user_id, user["display_name"]),
                )
                counts["users"] += cursor.rowcount
                for identity_kind, issuer, subject in (
                    ("keycloak", run["realm"]["issuer"], user["sub"]),
                    ("fixture", run["urls"]["issuer_fixture"], user["fixture_sub"]),
                ):
                    cursor.execute(
                        "INSERT INTO external_identities "
                        "(id, issuer, subject, user_id, username, email) VALUES (%s, %s, %s, %s, %s, %s) "
                        "ON CONFLICT (issuer, subject) DO UPDATE SET "
                        "username = EXCLUDED.username, email = EXCLUDED.email, updated_at = clock_timestamp() "
                        "WHERE external_identities.user_id = EXCLUDED.user_id "
                        "AND (external_identities.username, external_identities.email) "
                        "IS DISTINCT FROM (EXCLUDED.username, EXCLUDED.email) "
                        "RETURNING user_id",
                        (
                            str(
                                seed_uuid(
                                    run["run_id"],
                                    f"identity:{identity_kind}:{symbol}:{issuer}:{subject}",
                                )
                            ),
                            issuer,
                            subject,
                            user_id,
                            user["username"],
                            user.get("email"),
                        ),
                    )
                    identity_row = cursor.fetchone()
                    if identity_row is not None:
                        counts["external_identities"] += 1
                    else:
                        cursor.execute(
                            "SELECT user_id FROM external_identities WHERE issuer = %s AND subject = %s",
                            (issuer, subject),
                        )
                        existing = cursor.fetchone()
                        if existing is None or str(existing[0]) != user_id:
                            raise RuntimeError("external identity is already bound to another user")
            for user_symbol, tenant_symbol, role in tenant_memberships:
                cursor.execute(
                    "INSERT INTO tenant_memberships (tenant_id, user_id, role) VALUES (%s, %s, %s) "
                    "ON CONFLICT (tenant_id, user_id) DO NOTHING",
                    (tenant_ids[tenant_symbol], user_ids[user_symbol], role),
                )
            for user_symbol, tenant_symbol, project_symbol, role in project_memberships:
                cursor.execute(
                    "INSERT INTO project_memberships (tenant_id, project_id, user_id, role) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT (tenant_id, project_id, user_id) DO NOTHING",
                    (
                        tenant_ids[tenant_symbol],
                        project_ids[project_symbol],
                        user_ids[user_symbol],
                        role,
                    ),
                )
            for project_symbol in seed_scope_projects:
                project = entities["projects"][project_symbol]
                authorization_id = str(
                    seed_uuid(run["run_id"], f"scope-authorization:{project_symbol}")
                )
                policy_id = str(seed_uuid(run["run_id"], f"scope-policy:{project_symbol}"))
                authorization = {
                    "id": authorization_id,
                    "tenant_id": project["tenant_id"],
                    "project_id": project["id"],
                    "subject": "Development fixture HTTP observation",
                    "basis": "Self-managed non-destructive development fixture",
                    "approved_by": "development-seed",
                    "valid_from": "2026-01-01T00:00:00+00:00",
                    "valid_until": "2036-01-01T00:00:00+00:00",
                }
                immutable = {
                    "authorization": authorization,
                    "policy_id": policy_id,
                    "scope": seed_scope,
                    "version": 1,
                }
                cursor.execute(
                    "INSERT INTO authorization_records "
                    "(id, tenant_id, project_id, subject, basis, approved_by, valid_from, valid_until) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz) "
                    "ON CONFLICT (id) DO NOTHING",
                    (
                        authorization_id,
                        project["tenant_id"],
                        project["id"],
                        authorization["subject"],
                        authorization["basis"],
                        authorization["approved_by"],
                        authorization["valid_from"],
                        authorization["valid_until"],
                    ),
                )
                counts["authorization_records"] += cursor.rowcount
                cursor.execute(
                    "INSERT INTO scope_policy_versions "
                    "(policy_id, version, tenant_id, project_id, authorization_id, scope, policy_hash) "
                    "VALUES (%s, 1, %s, %s, %s, %s::jsonb, %s) "
                    "ON CONFLICT (policy_id, version) DO NOTHING",
                    (
                        policy_id,
                        project["tenant_id"],
                        project["id"],
                        authorization_id,
                        json.dumps(seed_scope, separators=(",", ":"), sort_keys=True),
                        policy_hash(immutable),
                    ),
                )
                counts["scope_policy_versions"] += cursor.rowcount
        connection.commit()
    return counts


def import_scope(
    *, database_url_value: str, document: ScopeImportDocument
) -> dict[str, Any]:
    """Import one immutable approved scope version through the trusted role."""

    authorization = document.authorization
    scope = document.normalized_scope()
    immutable = {
        "authorization": authorization.model_dump(mode="json"),
        "policy_id": str(document.scope.policy_id),
        "scope": scope,
        "version": document.scope.version,
    }
    digest = policy_hash(immutable)
    with management_transaction(database_url_value) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, %s))",
                (str(document.scope.policy_id), USER_LOCK_SEED + 1),
            )
            cursor.execute(
                "SELECT tenant_id FROM projects WHERE id = %s",
                (authorization.project_id,),
            )
            project_row = cursor.fetchone()
            if project_row is None or project_row[0] != authorization.tenant_id:
                raise ValueError("scope project does not exist in the supplied tenant")

            cursor.execute(
                "SELECT tenant_id, project_id, subject, basis, approved_by, valid_from, "
                "valid_until, revoked_at FROM authorization_records WHERE id = %s FOR UPDATE",
                (authorization.id,),
            )
            existing_authorization = cursor.fetchone()
            expected_authorization = (
                authorization.tenant_id,
                authorization.project_id,
                authorization.subject,
                authorization.basis,
                authorization.approved_by,
                authorization.valid_from,
                authorization.valid_until,
                None,
            )
            if existing_authorization is None:
                cursor.execute(
                    "INSERT INTO authorization_records "
                    "(id, tenant_id, project_id, subject, basis, approved_by, valid_from, valid_until) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        authorization.id,
                        authorization.tenant_id,
                        authorization.project_id,
                        authorization.subject,
                        authorization.basis,
                        authorization.approved_by,
                        authorization.valid_from,
                        authorization.valid_until,
                    ),
                )
            elif existing_authorization != expected_authorization:
                raise ValueError("authorization ID already exists with different immutable content")

            cursor.execute(
                "SELECT tenant_id, project_id, authorization_id, policy_hash "
                "FROM scope_policy_versions WHERE policy_id = %s AND version = %s FOR UPDATE",
                (document.scope.policy_id, document.scope.version),
            )
            existing_policy = cursor.fetchone()
            if existing_policy is not None:
                if existing_policy != (
                    authorization.tenant_id,
                    authorization.project_id,
                    authorization.id,
                    digest,
                ):
                    raise ValueError("scope policy version already exists with different content")
                return {
                    "status": "noop",
                    "policy_id": str(document.scope.policy_id),
                    "version": document.scope.version,
                    "policy_hash": digest,
                }
            cursor.execute(
                "SELECT tenant_id, project_id FROM scope_policy_versions "
                "WHERE policy_id = %s LIMIT 1 FOR UPDATE",
                (document.scope.policy_id,),
            )
            existing_binding = cursor.fetchone()
            if existing_binding is not None and existing_binding != (
                authorization.tenant_id,
                authorization.project_id,
            ):
                raise ValueError("scope policy ID is already bound to another project")
            cursor.execute(
                "INSERT INTO scope_policy_versions "
                "(policy_id, version, tenant_id, project_id, authorization_id, scope, policy_hash) "
                "VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)",
                (
                    document.scope.policy_id,
                    document.scope.version,
                    authorization.tenant_id,
                    authorization.project_id,
                    authorization.id,
                    json.dumps(scope, separators=(",", ":"), sort_keys=True),
                    digest,
                ),
            )
    return {
        "status": "imported",
        "policy_id": str(document.scope.policy_id),
        "version": document.scope.version,
        "policy_hash": digest,
    }


@contextmanager
def management_transaction(database_url_value: str):
    with psycopg.connect(_psycopg_url(database_url_value)) as connection:
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def _audit(cursor: psycopg.Cursor[Any], user_id: str, action: str, actor: str, details: Mapping[str, Any]) -> None:
    cursor.execute(
        "INSERT INTO identity_audit (user_id, action, actor, details) VALUES (%s, %s, %s, %s::jsonb)",
        (user_id, action, actor, json.dumps(dict(details), separators=(",", ":"), sort_keys=True)),
    )


def _lock_user(cursor: psycopg.Cursor[Any], user_id: str) -> None:
    """Coordinate session creation with user disable without granting User writes to auth."""

    cursor.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended(%s, %s))",
        (user_id, USER_LOCK_SEED),
    )


def set_user_enabled(
    *, database_url_value: str, user_id: str, enabled: bool, actor: str = "platform-control"
) -> bool:
    with management_transaction(database_url_value) as connection:
        with connection.cursor() as cursor:
            _lock_user(cursor, user_id)
            cursor.execute(
                "UPDATE users SET enabled = %s, permissions_version = permissions_version + 1, "
                "updated_at = clock_timestamp() WHERE id = %s AND enabled IS DISTINCT FROM %s "
                "RETURNING permissions_version",
                (enabled, user_id, enabled),
            )
            changed = cursor.fetchone() is not None
            if changed:
                if not enabled:
                    cursor.execute(
                        "UPDATE sessions SET revoked_at = clock_timestamp() "
                        "WHERE user_id = %s AND revoked_at IS NULL",
                        (user_id,),
                    )
                _audit(cursor, user_id, "user.enabled" if enabled else "user.disabled", actor, {})
            return changed


def change_membership(
    *,
    database_url_value: str,
    scope: str,
    enabled: bool,
    user_id: str,
    tenant_id: str,
    project_id: str | None,
    role: str,
    actor: str = "platform-control",
    simulate_failure: bool = False,
) -> bool:
    if role not in ROLES:
        raise ValueError("role must be operator or viewer")
    if scope not in {"tenant", "project"}:
        raise ValueError("scope must be tenant or project")
    if scope == "project" and project_id is None:
        raise ValueError("project_id is required for project membership")

    with management_transaction(database_url_value) as connection:
        with connection.cursor() as cursor:
            _lock_user(cursor, user_id)
            if scope == "tenant":
                cursor.execute(
                    "INSERT INTO tenant_memberships (tenant_id, user_id, role, enabled) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON CONFLICT (tenant_id, user_id) DO UPDATE SET "
                    "role = EXCLUDED.role, enabled = EXCLUDED.enabled, updated_at = clock_timestamp() "
                    "WHERE (tenant_memberships.role, tenant_memberships.enabled) "
                    "IS DISTINCT FROM (EXCLUDED.role, EXCLUDED.enabled) RETURNING 1",
                    (tenant_id, user_id, role, enabled),
                )
            else:
                cursor.execute(
                    "INSERT INTO project_memberships (tenant_id, project_id, user_id, role, enabled) "
                    "VALUES (%s, %s, %s, %s, %s) "
                    "ON CONFLICT (tenant_id, project_id, user_id) DO UPDATE SET "
                    "role = EXCLUDED.role, enabled = EXCLUDED.enabled, updated_at = clock_timestamp() "
                    "WHERE (project_memberships.role, project_memberships.enabled) "
                    "IS DISTINCT FROM (EXCLUDED.role, EXCLUDED.enabled) RETURNING 1",
                    (tenant_id, project_id, user_id, role, enabled),
                )
            changed = cursor.fetchone() is not None
            if changed:
                cursor.execute(
                    "UPDATE users SET permissions_version = permissions_version + 1, "
                    "updated_at = clock_timestamp() WHERE id = %s",
                    (user_id,),
                )
                _audit(
                    cursor,
                    user_id,
                    f"{scope}_membership.{'granted' if enabled else 'revoked'}",
                    actor,
                    {"tenant_id": tenant_id, "project_id": project_id, "role": role},
                )
                if simulate_failure:
                    raise RuntimeError("simulated audit transaction failure")
            return changed


def bump_permissions_version(
    *, database_url_value: str, user_id: str, actor: str = "platform-control"
) -> int:
    with management_transaction(database_url_value) as connection:
        with connection.cursor() as cursor:
            _lock_user(cursor, user_id)
            cursor.execute(
                "UPDATE users SET permissions_version = permissions_version + 1, "
                "updated_at = clock_timestamp() WHERE id = %s RETURNING permissions_version",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("unknown user")
            version = int(row[0])
            _audit(cursor, user_id, "permissions_version.bumped", actor, {"version": version})
            return version


def set_session_times(
    *,
    database_url_value: str,
    user_id: str,
    last_seen_at: str | None,
    absolute_expires_at: str | None,
) -> bool:
    if last_seen_at is None and absolute_expires_at is None:
        raise ValueError("at least one session timestamp is required")
    assignments: list[str] = []
    values: list[Any] = []
    if last_seen_at is not None:
        assignments.append("last_seen_at = %s::timestamptz")
        values.append(last_seen_at)
    if absolute_expires_at is not None:
        assignments.append("absolute_expires_at = %s::timestamptz")
        values.append(absolute_expires_at)
    values.append(user_id)
    with management_transaction(database_url_value) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE sessions SET {', '.join(assignments)} WHERE id = ("
                "SELECT id FROM sessions WHERE user_id = %s ORDER BY created_at DESC LIMIT 1"
                ") RETURNING id",
                values,
            )
            return cursor.fetchone() is not None


def inspect_authority(*, database_url_value: str, user_id: str | None = None) -> dict[str, Any]:
    with psycopg.connect(_psycopg_url(database_url_value)) as connection:
        with connection.cursor() as cursor:
            counts: dict[str, int] = {}
            for table in (
                "users",
                "external_identities",
                "tenants",
                "tenant_memberships",
                "projects",
                "project_memberships",
                "sessions",
                "oidc_handshakes",
                "identity_audit",
                "authorization_records",
                "scope_policy_versions",
                "task_previews",
                "tasks",
                "command_receipts",
                "task_events",
            ):
                cursor.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table)))
                counts[table] = int(cursor.fetchone()[0])
            output: dict[str, Any] = {"counts": counts}
            if user_id is not None:
                cursor.execute(
                    "SELECT enabled, permissions_version FROM users WHERE id = %s", (user_id,)
                )
                row = cursor.fetchone()
                output["user"] = None if row is None else {"enabled": row[0], "permissions_version": row[1]}
                cursor.execute(
                    "SELECT action, count(*) FROM identity_audit WHERE user_id = %s GROUP BY action ORDER BY action",
                    (user_id,),
                )
                output["audit_counts"] = {action: count for action, count in cursor.fetchall()}
            return output


def set_tenant_admin(
    *, database_url_value: str, user_id: str, tenant_id: str, enabled: bool,
    actor: str = "platform-control",
) -> bool:
    """Explicit trusted grant; never changes membership or project access."""
    with management_transaction(database_url_value) as connection:
        with connection.cursor() as cursor:
            _lock_user(cursor, user_id)
            if enabled:
                cursor.execute(
                    "SELECT 1 FROM tenant_memberships tm JOIN tenants t ON t.id=tm.tenant_id "
                    "JOIN users u ON u.id=tm.user_id WHERE tm.tenant_id=%s AND tm.user_id=%s "
                    "AND tm.enabled AND t.enabled AND u.enabled", (tenant_id, user_id),
                )
                if cursor.fetchone() is None:
                    raise ValueError("enabled tenant membership required")
                cursor.execute(
                    "INSERT INTO tenant_admin_grants(tenant_id,user_id,enabled) VALUES(%s,%s,true) "
                    "ON CONFLICT(tenant_id,user_id) DO UPDATE SET enabled=true,updated_at=clock_timestamp() "
                    "WHERE NOT tenant_admin_grants.enabled RETURNING 1", (tenant_id, user_id),
                )
            else:
                cursor.execute(
                    "UPDATE tenant_admin_grants SET enabled=false,updated_at=clock_timestamp() "
                    "WHERE tenant_id=%s AND user_id=%s AND enabled RETURNING 1", (tenant_id, user_id),
                )
            changed = cursor.fetchone() is not None
            if changed:
                cursor.execute(
                    "UPDATE users SET permissions_version=permissions_version+1,updated_at=clock_timestamp() "
                    "WHERE id=%s", (user_id,),
                )
                _audit(cursor, user_id, "tenant_admin.granted" if enabled else "tenant_admin.revoked",
                       actor, {"tenant_id": tenant_id})
            return changed
