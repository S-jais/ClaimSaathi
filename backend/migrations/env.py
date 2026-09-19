"""
migrations/env.py
Alembic environment — async-compatible, uses DATABASE_URL_SYNC for migrations.
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import Base so all models are registered before autogenerate
from app.core.db import Base  # noqa: F401
import app.auth.models  # noqa: F401 — register User, Role, Session

# Register remaining models as they are created in later phases
# import app.policies.models
# import app.claims.models
# import app.documents.models
# import app.consent.models
# import app.audit.models
# import app.notifications.models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from environment variable (never read from alembic.ini in production)
config.set_main_option(
    "sqlalchemy.url",
    os.environ.get("DATABASE_URL_SYNC", config.get_main_option("sqlalchemy.url")),
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
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
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
