from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import Session, create_engine

from xpln.constants import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

_ALEMBIC_INI = Path(__file__).parent / "alembic.ini"


def run_migrations() -> None:
    cfg = Config(str(_ALEMBIC_INI))
    command.upgrade(cfg, "head")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
