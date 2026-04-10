from collections.abc import Generator
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import event
from sqlmodel import Session, create_engine

from xpla.notebook.constants import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


_ALEMBIC_INI = Path(__file__).parent / "alembic.ini"


def run_migrations() -> None:
    cfg = Config(str(_ALEMBIC_INI))
    command.upgrade(cfg, "head")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
