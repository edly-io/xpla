# pylint: disable=no-member
from alembic import context
from sqlmodel import SQLModel

from xpln.db import engine

# Import all models so metadata is populated
from xpln import models as _models  # noqa: F401
from xpln import field_store as _field_store  # noqa: F401

target_metadata = SQLModel.metadata


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
