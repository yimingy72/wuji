from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

import psycopg
from psycopg import sql


class RecordedCursor:
    def __init__(self, cursor: psycopg.Cursor[Any], *, audit_path: Path) -> None:
        self._cursor = cursor
        self._audit_path = audit_path

    def fetchone(self):
        row = self._cursor.fetchone()
        _append_event(self._audit_path, {"operation": "fetchone", "response": row})
        return row

    def fetchall(self):
        rows = self._cursor.fetchall()
        _append_event(self._audit_path, {"operation": "fetchall", "response": rows})
        return rows

    def __iter__(self):
        return iter(self._cursor)

    def __getattr__(self, name: str):
        return getattr(self._cursor, name)


class RecordedDbConnection:
    """Thin recorder over a real psycopg connection."""

    def __init__(self, connection: psycopg.Connection[Any], *, audit_path: Path) -> None:
        self._connection = connection
        self.audit_path = audit_path

    def execute(self, query: str, params: object = None) -> RecordedCursor:
        _append_event(
            self.audit_path,
            {"operation": "execute", "request": {"sql": query, "params": params}},
        )
        cursor = self._connection.execute(query, params)
        _append_event(
            self.audit_path,
            {
                "operation": "execute_receipt",
                "response": {
                    "statusmessage": cursor.statusmessage,
                    "rowcount": cursor.rowcount,
                },
            },
        )
        return RecordedCursor(cursor, audit_path=self.audit_path)

    def commit(self) -> None:
        self._connection.commit()
        _append_event(self.audit_path, {"operation": "commit", "response": "ok"})

    def rollback(self) -> None:
        self._connection.rollback()
        _append_event(self.audit_path, {"operation": "rollback", "response": "ok"})

    def close(self) -> None:
        self._connection.close()
        _append_event(self.audit_path, {"operation": "close", "response": "ok"})

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback) -> None:
        if exception_type is None:
            self.commit()
        else:
            self.rollback()

    def __getattr__(self, name: str):
        return getattr(self._connection, name)


@contextmanager
def isolated_database(
    *, manifest_path: Path, audit_path: Path
) -> Iterator[RecordedDbConnection]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    suffix = uuid4().hex[:12]
    database_name = f"wuji_p02_{suffix}"
    migration_role = f"wuji_migration_{suffix}"
    application_role = f"wuji_app_{suffix}"
    connection_args = {
        "host": manifest["socket_dir"],
        "port": manifest["port"],
        "user": manifest["user"],
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    created_database = False
    created_migration_role = False
    created_application_role = False
    application_connection: RecordedDbConnection | None = None

    try:
        with psycopg.connect(
            **connection_args, dbname=manifest["database"], autocommit=True
        ) as admin:
            _admin_execute(
                admin,
                sql.SQL(
                    "CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                    "NOINHERIT NOBYPASSRLS"
                ).format(sql.Identifier(migration_role)),
                audit_path,
                phase="setup",
            )
            created_migration_role = True
            _admin_execute(
                admin,
                sql.SQL(
                    "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                    "NOINHERIT NOBYPASSRLS"
                ).format(sql.Identifier(application_role)),
                audit_path,
                phase="setup",
            )
            created_application_role = True
            _admin_execute(
                admin,
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(database_name), sql.Identifier(migration_role)
                ),
                audit_path,
                phase="setup",
            )
            created_database = True
            _admin_execute(
                admin,
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(database_name), sql.Identifier(application_role)
                ),
                audit_path,
                phase="setup",
            )

        with psycopg.connect(
            **connection_args, dbname=database_name, autocommit=True
        ) as database_admin:
            _admin_execute(
                database_admin,
                sql.SQL("CREATE SCHEMA vnext AUTHORIZATION {}").format(
                    sql.Identifier(migration_role)
                ),
                audit_path,
                phase="setup",
            )
            _admin_execute(
                database_admin,
                sql.SQL("GRANT USAGE ON SCHEMA vnext TO {}").format(
                    sql.Identifier(application_role)
                ),
                audit_path,
                phase="setup",
            )

        application_connection_args = {**connection_args, "user": application_role}
        raw_application_connection = psycopg.connect(
            **application_connection_args, dbname=database_name
        )
        application_connection = RecordedDbConnection(
            raw_application_connection, audit_path=audit_path
        )
        _append_event(
            audit_path,
            {
                "operation": "application_connect",
                "request": {
                    "database": database_name,
                    "user": application_role,
                    "network": "unix_socket",
                },
                "response": "connected",
            },
        )
        yield application_connection
    finally:
        if application_connection is not None:
            application_connection.close()
        with psycopg.connect(
            **connection_args, dbname=manifest["database"], autocommit=True
        ) as admin:
            if created_database:
                _admin_execute(
                    admin,
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid()",
                    audit_path,
                    phase="cleanup",
                    params=(database_name,),
                )
                _admin_execute(
                    admin,
                    sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name)),
                    audit_path,
                    phase="cleanup",
                )
            if created_application_role:
                _admin_execute(
                    admin,
                    sql.SQL("DROP ROLE {}").format(sql.Identifier(application_role)),
                    audit_path,
                    phase="cleanup",
                )
            if created_migration_role:
                _admin_execute(
                    admin,
                    sql.SQL("DROP ROLE {}").format(sql.Identifier(migration_role)),
                    audit_path,
                    phase="cleanup",
                )


def _admin_execute(
    connection: psycopg.Connection[Any],
    query: str | sql.Composable,
    audit_path: Path,
    *,
    phase: str,
    params: object = None,
) -> None:
    rendered = query.as_string(connection) if isinstance(query, sql.Composable) else query
    _append_event(
        audit_path,
        {
            "operation": "admin_execute",
            "phase": phase,
            "request": {"sql": rendered, "params": params},
        },
    )
    cursor = connection.execute(query, params)
    _append_event(
        audit_path,
        {
            "operation": "admin_execute_receipt",
            "phase": phase,
            "response": {
                "statusmessage": cursor.statusmessage,
                "rowcount": cursor.rowcount,
            },
        },
    )


def _append_event(path: Path, event: object) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, default=str, sort_keys=True) + "\n")
