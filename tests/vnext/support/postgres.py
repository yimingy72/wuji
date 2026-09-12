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
        self._iteration_complete = False

    def execute(self, query: Any, params: object = None, **kwargs: Any):
        rendered = _render_query(self._cursor.connection, query)
        _append_event(
            self._audit_path,
            {
                "operation": "cursor_execute",
                "request": {"sql": rendered, "params": params},
            },
        )
        try:
            self._cursor.execute(query, params, **kwargs)
        except Exception as error:
            _append_event(
                self._audit_path,
                {"operation": "cursor_execute_error", "response": _error_record(error)},
            )
            raise
        _append_event(
            self._audit_path,
            {
                "operation": "cursor_execute_receipt",
                "response": {
                    "statusmessage": self._cursor.statusmessage,
                    "rowcount": self._cursor.rowcount,
                },
            },
        )
        self._iteration_complete = False
        return self

    def executemany(self, query: Any, params_seq: Any, **kwargs: Any):
        rendered = _render_query(self._cursor.connection, query)
        materialized_params = list(params_seq)
        _append_event(
            self._audit_path,
            {
                "operation": "cursor_executemany",
                "request": {"sql": rendered, "params": materialized_params},
            },
        )
        try:
            self._cursor.executemany(query, materialized_params, **kwargs)
        except Exception as error:
            _append_event(
                self._audit_path,
                {
                    "operation": "cursor_executemany_error",
                    "response": _error_record(error),
                },
            )
            raise
        _append_event(
            self._audit_path,
            {
                "operation": "cursor_executemany_receipt",
                "response": {
                    "statusmessage": self._cursor.statusmessage,
                    "rowcount": self._cursor.rowcount,
                },
            },
        )
        self._iteration_complete = False
        return self

    def fetchone(self):
        try:
            row = self._cursor.fetchone()
        except Exception as error:
            _append_event(
                self._audit_path,
                {"operation": "fetchone_error", "response": _error_record(error)},
            )
            raise
        _append_event(self._audit_path, {"operation": "fetchone", "response": row})
        return row

    def fetchmany(self, size: int | None = None):
        try:
            rows = (
                self._cursor.fetchmany(size)
                if size is not None
                else self._cursor.fetchmany()
            )
        except Exception as error:
            _append_event(
                self._audit_path,
                {"operation": "fetchmany_error", "response": _error_record(error)},
            )
            raise
        _append_event(self._audit_path, {"operation": "fetchmany", "response": rows})
        return rows

    def fetchall(self):
        try:
            rows = self._cursor.fetchall()
        except Exception as error:
            _append_event(
                self._audit_path,
                {"operation": "fetchall_error", "response": _error_record(error)},
            )
            raise
        _append_event(self._audit_path, {"operation": "fetchall", "response": rows})
        return rows

    def __iter__(self):
        return self

    def __next__(self):
        try:
            row = next(self._cursor)
        except StopIteration:
            if not self._iteration_complete:
                _append_event(
                    self._audit_path,
                    {"operation": "iteration_complete", "response": "exhausted"},
                )
                self._iteration_complete = True
            raise
        except Exception as error:
            _append_event(
                self._audit_path,
                {"operation": "iteration_error", "response": _error_record(error)},
            )
            raise
        _append_event(self._audit_path, {"operation": "iteration_row", "response": row})
        return row

    def __enter__(self):
        self._cursor.__enter__()
        _append_event(self._audit_path, {"operation": "cursor_enter"})
        return self

    def __exit__(self, exception_type, exception, traceback):
        try:
            result = self._cursor.__exit__(exception_type, exception, traceback)
        except Exception as error:
            _append_event(
                self._audit_path,
                {"operation": "cursor_exit_error", "response": _error_record(error)},
            )
            raise
        _append_event(
            self._audit_path,
            {
                "operation": "cursor_exit",
                "response": "closed",
                "exception": exception_type.__name__ if exception_type else None,
            },
        )
        return result

    def __getattr__(self, name: str):
        return getattr(self._cursor, name)


class RecordedDbConnection:
    """Thin recorder over a real psycopg connection."""

    def __init__(
        self, connection: psycopg.Connection[Any], *, audit_path: Path
    ) -> None:
        self._connection = connection
        self.audit_path = audit_path

    def execute(self, query: str, params: object = None) -> RecordedCursor:
        rendered = _render_query(self._connection, query)
        _append_event(
            self.audit_path,
            {
                "operation": "execute",
                "request": {"sql": rendered, "params": params},
            },
        )
        try:
            cursor = self._connection.execute(query, params)
        except Exception as error:
            _append_event(
                self.audit_path,
                {"operation": "execute_error", "response": _error_record(error)},
            )
            raise
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

    def cursor(self, *args: Any, **kwargs: Any) -> RecordedCursor:
        _append_event(self.audit_path, {"operation": "cursor_create"})
        try:
            cursor = self._connection.cursor(*args, **kwargs)
        except Exception as error:
            _append_event(
                self.audit_path,
                {"operation": "cursor_create_error", "response": _error_record(error)},
            )
            raise
        return RecordedCursor(cursor, audit_path=self.audit_path)

    def transaction(self, *args: Any, **kwargs: Any):
        transaction = self._connection.transaction(*args, **kwargs)
        return RecordedTransaction(transaction, audit_path=self.audit_path)

    def commit(self) -> None:
        try:
            self._connection.commit()
        except Exception as error:
            _append_event(
                self.audit_path,
                {"operation": "commit_error", "response": _error_record(error)},
            )
            raise
        _append_event(self.audit_path, {"operation": "commit", "response": "ok"})

    def rollback(self) -> None:
        try:
            self._connection.rollback()
        except Exception as error:
            _append_event(
                self.audit_path,
                {"operation": "rollback_error", "response": _error_record(error)},
            )
            raise
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


class RecordedTransaction:
    def __init__(self, transaction: Any, *, audit_path: Path) -> None:
        self._transaction = transaction
        self._audit_path = audit_path

    def __enter__(self):
        try:
            self._transaction.__enter__()
        except Exception as error:
            _append_event(
                self._audit_path,
                {
                    "operation": "transaction_enter_error",
                    "response": _error_record(error),
                },
            )
            raise
        _append_event(self._audit_path, {"operation": "transaction_enter"})
        return self

    def __exit__(self, exception_type, exception, traceback):
        try:
            result = self._transaction.__exit__(exception_type, exception, traceback)
        except Exception as error:
            _append_event(
                self._audit_path,
                {
                    "operation": "transaction_exit_error",
                    "response": _error_record(error),
                },
            )
            raise
        _append_event(
            self._audit_path,
            {
                "operation": (
                    "transaction_rollback" if exception_type else "transaction_commit"
                ),
                "response": "ok",
                "exception": exception_type.__name__ if exception_type else None,
            },
        )
        return result


class IsolatedDatabaseEnvironment:
    """Connection hooks scoped to one generated database and its fixed roles."""

    def __init__(
        self,
        *,
        connection_args: dict[str, object],
        database_name: str,
        migration_role: str,
        application_role: str,
        audit_path: Path,
    ) -> None:
        self._connection_args = connection_args
        self.database_name = database_name
        self.migration_role = migration_role
        self.application_role = application_role
        self.audit_path = audit_path

    @contextmanager
    def additional_app_connection(self) -> Iterator[RecordedDbConnection]:
        connection_args = {**self._connection_args, "user": self.application_role}
        raw = psycopg.connect(**connection_args, dbname=self.database_name)
        connection = RecordedDbConnection(raw, audit_path=self.audit_path)
        _append_event(
            self.audit_path,
            {
                "operation": "additional_app_connect",
                "request": {
                    "database": self.database_name,
                    "user": self.application_role,
                    "network": "unix_socket",
                },
                "response": "connected",
            },
        )
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def migration_connection(self) -> Iterator[RecordedDbConnection]:
        raw = psycopg.connect(
            **self._connection_args, dbname=self.database_name, autocommit=True
        )
        try:
            _admin_execute(
                raw,
                sql.SQL("SET ROLE {}").format(sql.Identifier(self.migration_role)),
                self.audit_path,
                phase="migration_connect",
            )
            connection = RecordedDbConnection(raw, audit_path=self.audit_path)
            _append_event(
                self.audit_path,
                {
                    "operation": "migration_connect",
                    "request": {
                        "database": self.database_name,
                        "role": self.migration_role,
                        "network": "unix_socket",
                    },
                    "response": "connected_with_set_role",
                },
            )
            yield connection
        finally:
            if not raw.closed:
                raw.close()
                _append_event(
                    self.audit_path,
                    {"operation": "migration_close", "response": "ok"},
                )


@contextmanager
def isolated_database_environment(
    *, manifest_path: Path, audit_path: Path
) -> Iterator[IsolatedDatabaseEnvironment]:
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

        yield IsolatedDatabaseEnvironment(
            connection_args=connection_args,
            database_name=database_name,
            migration_role=migration_role,
            application_role=application_role,
            audit_path=audit_path,
        )
    finally:
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


@contextmanager
def isolated_database(
    *, manifest_path: Path, audit_path: Path
) -> Iterator[RecordedDbConnection]:
    with isolated_database_environment(
        manifest_path=manifest_path, audit_path=audit_path
    ) as environment:
        with environment.additional_app_connection() as connection:
            yield connection


def _admin_execute(
    connection: psycopg.Connection[Any],
    query: str | sql.Composable,
    audit_path: Path,
    *,
    phase: str,
    params: object = None,
) -> None:
    rendered = (
        query.as_string(connection) if isinstance(query, sql.Composable) else query
    )
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


def _render_query(connection: psycopg.Connection[Any], query: Any) -> str:
    if isinstance(query, sql.Composable):
        return query.as_string(connection)
    if isinstance(query, bytes):
        return query.decode("utf-8", errors="replace")
    return str(query)


def _error_record(error: Exception) -> dict[str, object]:
    return {
        "type": type(error).__name__,
        "message": str(error),
        "sqlstate": getattr(error, "sqlstate", None),
    }
