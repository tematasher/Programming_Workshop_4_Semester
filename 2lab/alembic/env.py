from logging.config import fileConfig
from sqlalchemy import create_engine
from alembic import context
import sys
import os

sys.path.append(os.getcwd())

from app.db.base import Base
from app.core.config import settings
from app.models.user import User

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    """Запуск миграций в offline режиме."""
    url = settings.SQLALCHEMY_DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Запуск миграций в online режиме."""
    connectable = create_engine(settings.SQLALCHEMY_DATABASE_URL)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
    