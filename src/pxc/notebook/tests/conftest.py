"""Shared pytest fixtures for notebook tests."""

from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.engine import Engine
from sqlmodel.pool import StaticPool

from pxc.notebook import db
from pxc.notebook.app import app


def _make_engine() -> Engine:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Session, None, None]:
    engine = _make_engine()
    monkeypatch.setattr(db, "_engine", engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    del session  # the monkeypatch in session_fixture is what makes this work
    yield TestClient(app)
