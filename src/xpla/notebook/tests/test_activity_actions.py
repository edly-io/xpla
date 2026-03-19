from collections.abc import Generator
from unittest.mock import MagicMock, patch

from httpx import Response
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from xpla.lib.actions import ActionValidationError
from xpla.notebook.app import app
from xpla.notebook.db import get_session
from xpla.notebook.models import Course, Page, PageActivity


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(name="activity")
def activity_fixture(session: Session) -> PageActivity:
    course = Course(title="Test Course")
    session.add(course)
    session.commit()
    page = Page(title="Test Page", course_id=course.id)
    session.add(page)
    session.commit()
    pa = PageActivity(page_id=page.id, activity_type="markdown")
    session.add(pa)
    session.commit()
    session.refresh(pa)
    return pa


def post_action(
    client: TestClient, activity_id: str, permission: str = "edit"
) -> Response:
    return client.post(
        f"/api/activity/{activity_id}/{permission}/actions",
        json={"name": "config.save", "value": {"markdown_content": "hello"}},
    )


def test_activity_not_found(client: TestClient) -> None:
    response = post_action(client, "nonexistent")
    assert response.status_code == 404


def test_invalid_permission(client: TestClient, activity: PageActivity) -> None:
    response = post_action(client, activity.id, permission="invalid")
    assert response.status_code == 422


def test_action_validation_error(client: TestClient, activity: PageActivity) -> None:
    mock_ctx = MagicMock()
    mock_ctx.on_action.side_effect = ActionValidationError("bad action")
    with patch("xpla.notebook.app.load_activity", return_value=mock_ctx):
        response = post_action(client, activity.id)
    assert response.status_code == 400
    assert "bad action" in response.json()["detail"]


def test_action_success(client: TestClient, activity: PageActivity) -> None:
    mock_ctx = MagicMock()
    with patch("xpla.notebook.app.load_activity", return_value=mock_ctx):
        response = post_action(client, activity.id)
    assert response.status_code == 200
    mock_ctx.on_action.assert_called_once_with(
        "config.save", {"markdown_content": "hello"}
    )
