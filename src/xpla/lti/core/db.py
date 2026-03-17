"""Database engine and session helpers for LTI."""

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.engine import Engine


def create_db(db_path: str) -> Engine:
    """Create engine and initialize tables."""
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


def get_session(engine: Engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
