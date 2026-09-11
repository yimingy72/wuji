"""One owned loopback PostgreSQL cluster; no existing service or OIDC dependency."""
from __future__ import annotations

import secrets
import shutil
import socket
import subprocess
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
import pytest

from wuji_api.database_admin import database_url, migrate_database, prepare_database
from wuji_api.main import create_app
from wuji_api.security import token_hash
from wuji_api.settings import Settings


@dataclass(repr=False)
class DraftDatabase:
    admin_url: str = field(repr=False)
    auth_url: str = field(repr=False)
    project_url: str = field(repr=False)

    def connect(self, role="admin"):
        url = getattr(self, f"{role}_url")
        return psycopg.connect(url.replace("postgresql+psycopg://", "postgresql://", 1))


def _pg(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=60)
    if result.returncode:
        # Do not print process output, connection strings, or temporary secrets.
        pytest.fail(f"owned PostgreSQL {Path(arguments[0]).name} failed ({result.returncode})")


@pytest.fixture(scope="session")
def draft_database():
    initdb, pg_ctl = Path("/usr/local/bin/initdb"), Path("/usr/local/bin/pg_ctl")
    assert initdb.is_file() and pg_ctl.is_file(), "local PostgreSQL binaries are required"
    root = Path(tempfile.mkdtemp(prefix="wuji-drafts-"))
    root.chmod(0o700)
    data = root / "data"
    data.mkdir(mode=0o700)
    password_file = root / "password"
    passwords = {name: secrets.token_urlsafe(32) for name in ("admin", "migration", "auth", "project")}
    password_file.touch(mode=0o600)
    password_file.write_text(passwords["admin"] + "\n", encoding="utf-8")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    try:
        _pg([str(initdb), "-D", str(data), "-U", "draft_admin", "--auth=scram-sha-256",
             "--pwfile", str(password_file), "--encoding=UTF8", "--no-locale"])
        password_file.unlink()
        # Disable Unix sockets and statement logging; all access uses the owned TCP port.
        _pg([str(pg_ctl), "-D", str(data), "-l", str(root / "postgres.log"), "-w", "-t", "30",
             "-o", f"-h 127.0.0.1 -p {port} -k '' -c log_statement=none -c log_min_error_statement=panic", "start"])
        admin = database_url("127.0.0.1", port, "postgres", "draft_admin", passwords["admin"])
        prepare_database(admin_database_url=admin, database="draft_test",
                         migration_role="draft_migration", migration_password=passwords["migration"],
                         auth_role="draft_auth", auth_password=passwords["auth"],
                         project_role="draft_project", project_password=passwords["project"])
        migration = database_url("127.0.0.1", port, "draft_test", "draft_migration", passwords["migration"])
        migrate_database(migration_database_url=migration, auth_role="draft_auth", project_role="draft_project")
        database = DraftDatabase(
            database_url("127.0.0.1", port, "draft_test", "draft_admin", passwords["admin"]),
            database_url("127.0.0.1", port, "draft_test", "draft_auth", passwords["auth"]),
            database_url("127.0.0.1", port, "draft_test", "draft_project", passwords["project"]),
        )
        with database.connect() as connection:
            assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20260911_0004"
            roles = connection.execute(
                "SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb FROM pg_roles "
                "WHERE rolname IN ('draft_auth', 'draft_project')"
            ).fetchall()
            assert roles == [(False, False, False, False)] * 2
        yield database
    finally:
        # Even a partially successful start is stopped, solely by this private datadir.
        # If stop fails, retain the directory instead of deleting a live database.
        if (data / "postmaster.pid").exists():
            _pg([str(pg_ctl), "-D", str(data), "-m", "fast", "-w", "-t", "30", "stop"])
        shutil.rmtree(root)


@dataclass(repr=False)
class DraftCase:
    database: DraftDatabase
    tenant: str
    other_tenant: str
    project: str
    second_project: str
    other_project: str
    users: dict
    tokens: dict = field(repr=False)
    csrf: dict = field(repr=False)

    def path(self, draft_id=None, project=None):
        base = f"/api/v1/projects/{project or self.project}/task-drafts"
        return f"{base}/{draft_id}" if draft_id else base

    @asynccontextmanager
    async def client(self, user="owner"):
        settings = Settings(
            _env_file=None, profile="local-test", auth_database_url=self.database.auth_url,
            project_database_url=self.database.project_url, public_origin="http://127.0.0.1:48123",
            oidc_issuer="http://127.0.0.1:48124", oidc_client_id="draft-test",
            oidc_client_secret=secrets.token_urlsafe(32), cursor_signing_key="d" * 40,
            cursor_ttl_seconds=900,
        )
        app = create_app(settings=settings)
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=settings.public_origin,
                                        cookies={"wuji_session": self.tokens[user]},
                                        headers={"Origin": settings.public_origin, "X-CSRF-Token": self.csrf[user]}) as client:
                yield client, app
        finally:
            await app.state.runtime.close()


@pytest.fixture
def draft_case(draft_database, monkeypatch):
    async def reject_async_network(*args, **kwargs):
        raise AssertionError("draft API attempted an external HTTP request")

    def reject_network(*args, **kwargs):
        raise AssertionError("draft API attempted an external HTTP request")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", reject_async_network)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", reject_network)
    case = DraftCase(draft_database, *[str(uuid4()) for _ in range(5)],
                     users={name: str(uuid4()) for name in ("owner", "peer", "outsider")},
                     tokens={name: secrets.token_urlsafe(32) for name in ("owner", "peer", "outsider")},
                     csrf={name: secrets.token_urlsafe(32) for name in ("owner", "peer", "outsider")})
    with draft_database.connect() as connection:
        for tenant in (case.tenant, case.other_tenant):
            connection.execute("INSERT INTO tenants (id, name) VALUES (%s, 'Draft test')", (tenant,))
        for project, tenant in ((case.project, case.tenant), (case.second_project, case.tenant),
                                (case.other_project, case.other_tenant)):
            connection.execute("INSERT INTO projects (id, tenant_id, name) VALUES (%s, %s, 'Draft test')", (project, tenant))
        for name, user_id in case.users.items():
            tenant = case.other_tenant if name == "outsider" else case.tenant
            projects = [case.other_project] if name == "outsider" else [case.project, case.second_project]
            connection.execute("INSERT INTO users (id, display_name) VALUES (%s, %s)", (user_id, name))
            connection.execute("INSERT INTO tenant_memberships (tenant_id, user_id, role) VALUES (%s, %s, 'operator')", (tenant, user_id))
            for project in projects:
                connection.execute("INSERT INTO project_memberships (tenant_id, project_id, user_id, role) VALUES (%s, %s, %s, 'operator')", (tenant, project, user_id))
            connection.execute("INSERT INTO sessions (id, token_hash, user_id, csrf_token, absolute_expires_at) "
                               "VALUES (%s, %s, %s, %s, clock_timestamp() + interval '1 hour')",
                               (uuid4(), token_hash(case.tokens[name]), user_id, case.csrf[name]))
    return case
