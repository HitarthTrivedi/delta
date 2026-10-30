"""Alembic environment: uses the app's own DATABASE_URL and model metadata.

Create a migration after changing a model (from backend/):
    alembic revision --autogenerate -m "add x to y"
Review the generated file, then apply it:
    alembic upgrade head
Production runs `alembic upgrade head` on every container start (Dockerfile).
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.database import Base
import app.models  # noqa: F401 — registers every model on Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=settings.DATABASE_URL.startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        {"sqlalchemy.url": settings.DATABASE_URL},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        if connection.dialect.name == "postgresql":
            # Every API replica runs migrations on start: the first takes this lock,
            # the others wait, then find nothing left to do. Freed when the connection closes.
            from sqlalchemy import text
            from app.services.cluster_lock import _key
            connection.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _key("migrations")})
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite can't ALTER most things in place; batch mode copies the table.
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
