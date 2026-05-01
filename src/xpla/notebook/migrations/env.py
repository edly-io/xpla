# pylint: disable=no-member
from alembic import context
from sqlmodel import SQLModel

from xpla.notebook.db import _engine

# Import all models so metadata is populated
from xpla.notebook import models as _models  # noqa: F401
from xpla.notebook import field_store as _field_store  # noqa: F401

target_metadata = SQLModel.metadata


def run_migrations_online() -> None:
    with _engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
