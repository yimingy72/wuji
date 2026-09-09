"""Alembic environment for the Phase 1A authority database."""

from __future__ import annotations

import os
import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

ROLE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


def required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required for migrations")
    return value


def role_environment(name: str) -> str:
    value = required_environment(name)
    if not ROLE_PATTERN.fullmatch(value):
        raise RuntimeError(f"{name} is not a safe PostgreSQL role identifier")
    return value


config.set_main_option(
    "sqlalchemy.url", required_environment("WUJI_MIGRATION_DATABASE_URL").replace("%", "%%")
)
config.attributes["auth_role"] = role_environment("WUJI_AUTH_DB_ROLE")
config.attributes["project_role"] = role_environment("WUJI_PROJECT_DB_ROLE")


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
