from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from app.config import get_settings
from app.domains.accounts import Account  # noqa: F401
from app.domains.audit import AuditLog  # noqa: F401
from app.domains.balances import BalanceSnapshot  # noqa: F401
from app.domains.categories import Category  # noqa: F401
from app.domains.ingestion import RawEvent  # noqa: F401
from app.domains.merchants import Merchant, MerchantPattern  # noqa: F401
from app.domains.transactions import Transaction  # noqa: F401
from app.domains.transfers import Transfer  # noqa: F401
from app.domains.users import User, UserSettings  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def get_database_url() -> str:
    """Return the configured database URL for Alembic."""
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live database connection."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
