from __future__ import annotations

from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from conftest import RunManifest


pytestmark = pytest.mark.platform


def dsn(manifest: RunManifest, role: str) -> str:
    return manifest.data["credentials"]["database"][f"{role}_dsn"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )


def test_runtime_roles_have_no_superuser_bypass_or_role_escalation(run_manifest: RunManifest) -> None:
    role_names = run_manifest.data["database"]["roles"]
    with psycopg.connect(dsn(run_manifest, "admin")) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls "
            "FROM pg_roles WHERE rolname = ANY(%s) ORDER BY rolname",
            ([role_names["auth"], role_names["project"]],),
        )
        observed = cursor.fetchall()
    assert {row[0] for row in observed} == {role_names["auth"], role_names["project"]}
    assert all(row[1:] == (False, False, False, False) for row in observed)

    for role in ("auth", "project"):
        with psycopg.connect(dsn(run_manifest, role), autocommit=True) as connection:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                connection.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role_names["migration"])))


def test_project_role_has_no_auth_data_write_truncate_or_ddl(run_manifest: RunManifest) -> None:
    with psycopg.connect(dsn(run_manifest, "project"), autocommit=True) as connection:
        for table in ("users", "external_identities", "sessions", "oidc_handshakes", "identity_audit"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                connection.execute(sql.SQL("SELECT * FROM {} LIMIT 0").format(sql.Identifier(table)))
        for statement in (
            "DELETE FROM projects WHERE false",
            "TRUNCATE projects",
            f"CREATE TABLE phase1a_runtime_ddl_probe_{uuid4().hex} (id integer)",
            f"CREATE TEMP TABLE phase1a_runtime_temp_probe_{uuid4().hex} (id integer)",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege) as denied:
                connection.execute(statement)
            assert denied.value.sqlstate == "42501"


def test_auth_role_cannot_read_or_modify_project_authority(run_manifest: RunManifest) -> None:
    with psycopg.connect(dsn(run_manifest, "auth"), autocommit=True) as connection:
        for table in ("tenants", "tenant_memberships", "projects", "project_memberships"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                connection.execute(sql.SQL("SELECT * FROM {} LIMIT 0").format(sql.Identifier(table)))
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                connection.execute(sql.SQL("DELETE FROM {} WHERE false").format(sql.Identifier(table)))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(f"CREATE TABLE phase1a_auth_ddl_probe_{uuid4().hex} (id integer)")
        with pytest.raises(psycopg.errors.InsufficientPrivilege) as denied:
            connection.execute(f"CREATE TEMP TABLE phase1a_auth_temp_probe_{uuid4().hex} (id integer)")
        assert denied.value.sqlstate == "42501"


def test_rls_defaults_to_zero_rows_and_transaction_context_does_not_leak_from_pool(
    run_manifest: RunManifest,
) -> None:
    tables = ("tenants", "tenant_memberships", "projects", "project_memberships")
    user = run_manifest.seed("dual_ab")
    with psycopg.connect(dsn(run_manifest, "project")) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                for table in tables:
                    cursor.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table)))
                    assert cursor.fetchone()[0] == 0
                cursor.execute("SELECT set_config('app.user_id', %s, true)", (user["id"],))
                cursor.execute("SELECT id::text FROM projects ORDER BY id")
                assert {row[0] for row in cursor.fetchall()} == set(user["project_ids"])

        # Same physical connection, new transaction: transaction-local context must be gone.
        with connection.transaction():
            with connection.cursor() as cursor:
                assert cursor.execute("SELECT current_setting('app.user_id', true)").fetchone()[0] == ""
                for table in tables:
                    cursor.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table)))
                    assert cursor.fetchone()[0] == 0


@pytest.mark.parametrize("user_symbol", ["tenant_split_u1", "tenant_split_u2"])
def test_same_tenant_split_users_see_only_their_own_membership_and_project(
    user_symbol: str, run_manifest: RunManifest
) -> None:
    user = run_manifest.seed(user_symbol)
    assert len(user["project_ids"]) == 1
    with psycopg.connect(dsn(run_manifest, "project")) as connection, connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.user_id', %s, true)", (user["id"],))
            cursor.execute("SELECT user_id::text, project_id::text FROM project_memberships")
            assert cursor.fetchall() == [(user["id"], user["project_ids"][0])]
            cursor.execute("SELECT id::text FROM projects")
            assert cursor.fetchall() == [(user["project_ids"][0],)]
            cursor.execute("SELECT user_id::text FROM tenant_memberships")
            assert cursor.fetchall() == [(user["id"],)]


def test_tenant_and_project_context_further_restrict_authorized_rows(run_manifest: RunManifest) -> None:
    user = run_manifest.seed("dual_ab")
    project_id = user["project_ids"][0]
    project = run_manifest.project(project_id)
    with psycopg.connect(dsn(run_manifest, "project")) as connection, connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.user_id', %s, true)", (user["id"],))
            cursor.execute("SELECT set_config('app.tenant_id', %s, true)", (project["tenant_id"],))
            cursor.execute("SELECT set_config('app.project_id', %s, true)", (project_id,))
            cursor.execute("SELECT id::text FROM projects")
            assert cursor.fetchall() == [(project_id,)]
            cursor.execute("SELECT project_id::text FROM project_memberships")
            assert cursor.fetchall() == [(project_id,)]


def test_management_role_is_separate_and_composite_foreign_keys_reject_mixed_authority(
    run_manifest: RunManifest,
) -> None:
    project_a_id = run_manifest.seed("single_a")["project_ids"][0]
    project_b_id = run_manifest.seed("single_b")["project_ids"][0]
    project_a = run_manifest.project(project_a_id)
    project_b = run_manifest.project(project_b_id)
    user_a = run_manifest.seed("single_a")
    user_b = run_manifest.seed("single_b")
    with psycopg.connect(dsn(run_manifest, "management")) as connection:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO project_memberships "
                        "(tenant_id, project_id, user_id, role) VALUES (%s, %s, %s, 'viewer')",
                        (project_a["tenant_id"], project_a_id, user_b["id"]),
                    )
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO project_memberships "
                        "(tenant_id, project_id, user_id, role) VALUES (%s, %s, %s, 'viewer')",
                        (project_a["tenant_id"], project_b_id, user_a["id"]),
                    )


def test_rls_tables_are_enabled_and_forced_for_nonowners(run_manifest: RunManifest) -> None:
    with psycopg.connect(dsn(run_manifest, "management")) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT relname, relrowsecurity, pg_get_userbyid(relowner) FROM pg_class "
            "WHERE relname = ANY(%s) ORDER BY relname",
            (["tenants", "tenant_memberships", "projects", "project_memberships"],),
        )
        rows = cursor.fetchall()
    assert len(rows) == 4
    assert all(enabled is True for _, enabled, _ in rows)
    runtime_roles = {
        run_manifest.data["database"]["roles"]["auth"],
        run_manifest.data["database"]["roles"]["project"],
    }
    assert all(owner not in runtime_roles for _, _, owner in rows)


def test_external_identity_key_is_issuer_and_subject_not_username_or_email(
    run_manifest: RunManifest,
) -> None:
    first_user, second_user = str(uuid4()), str(uuid4())
    issuer = "http://127.0.0.1:18083/identity-key-probe"
    with psycopg.connect(dsn(run_manifest, "management")) as connection:
        with connection.transaction(force_rollback=True):
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (id, display_name) VALUES (%s, 'Probe One'), (%s, 'Probe Two')",
                    (first_user, second_user),
                )
                for identity_id, subject, user_id in (
                    (str(uuid4()), "subject-one", first_user),
                    (str(uuid4()), "subject-two", second_user),
                ):
                    cursor.execute(
                        "INSERT INTO external_identities "
                        "(id, issuer, subject, user_id, username, email) "
                        "VALUES (%s, %s, %s, %s, 'same-name', 'same@example.invalid')",
                        (identity_id, issuer, subject, user_id),
                    )
                cursor.execute(
                    "SELECT user_id::text FROM external_identities WHERE issuer = %s ORDER BY subject",
                    (issuer,),
                )
                assert cursor.fetchall() == [(first_user,), (second_user,)]
                with pytest.raises(psycopg.errors.UniqueViolation):
                    with connection.transaction():
                        cursor.execute(
                            "INSERT INTO external_identities "
                            "(id, issuer, subject, user_id) VALUES (%s, %s, 'subject-one', %s)",
                            (str(uuid4()), issuer, second_user),
                        )
