from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from xpla.notebook.app import app
from xpla.notebook.db import get_session


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


def _signup(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 201


def _create_course_with_activity(client: TestClient) -> tuple[str, str, str]:
    course = client.post("/api/courses", json={"title": "Course A"}).json()
    page = client.post(
        f"/api/courses/{course['id']}/pages", json={"title": "Page 1"}
    ).json()
    activity = client.post(
        f"/api/pages/{page['id']}/activities",
        json={"activity_type": "markdown"},
    ).json()
    return course["id"], page["id"], activity["id"]


def test_list_courses_only_returns_own(client: TestClient) -> None:
    _signup(client, "a@example.com")
    client.post("/api/courses", json={"title": "A's course"})
    client.cookies.clear()
    _signup(client, "b@example.com")
    response = client.get("/api/courses")
    assert response.status_code == 200
    assert response.json() == []


def test_non_owner_cannot_view_course(client: TestClient) -> None:
    _signup(client, "a@example.com")
    course_id, page_id, _ = _create_course_with_activity(client)
    client.cookies.clear()
    _signup(client, "b@example.com")

    assert client.get(f"/api/courses/{course_id}").status_code == 404
    assert client.get(f"/api/pages/{page_id}").status_code == 404


def test_non_owner_cannot_run_activity(client: TestClient) -> None:
    _signup(client, "a@example.com")
    _course_id, _page_id, activity_id = _create_course_with_activity(client)
    client.cookies.clear()
    _signup(client, "b@example.com")

    play = client.post(
        f"/api/activity/{activity_id}/play/actions",
        json={"name": "config.save", "value": {"markdown_content": "hi"}},
    )
    assert play.status_code == 403

    edit = client.post(
        f"/api/activity/{activity_id}/edit/actions",
        json={"name": "config.save", "value": {"markdown_content": "hi"}},
    )
    assert edit.status_code == 403


def test_non_owner_cannot_load_activity_asset(client: TestClient) -> None:
    _signup(client, "a@example.com")
    _course_id, _page_id, activity_id = _create_course_with_activity(client)
    client.cookies.clear()
    _signup(client, "b@example.com")

    response = client.get(f"/a/{activity_id}/client.js")
    assert response.status_code == 403


def test_owner_can_edit_own_activity(client: TestClient) -> None:
    _signup(client, "a@example.com")
    _course_id, _page_id, activity_id = _create_course_with_activity(client)

    edit = client.post(
        f"/api/activity/{activity_id}/edit/actions",
        json={"name": "config.save", "value": {"markdown_content": "hello"}},
    )
    assert edit.status_code == 200


def test_unauthenticated_cannot_list_courses(client: TestClient) -> None:
    response = client.get("/api/courses")
    assert response.status_code == 401
