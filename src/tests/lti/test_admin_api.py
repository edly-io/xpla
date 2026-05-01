"""Tests for LTI admin CRUD API endpoints."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient
from fastapi.templating import Jinja2Templates
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, Session, create_engine, select

from pxc.lti.core.keys import load_or_create_key
from pxc.lti.core.models import Platform
from pxc.lti.core.routes import create_lti_router


@pytest.fixture
def admin_test_engine() -> Engine:
    """Create a fresh in-memory database for admin tests."""
    from sqlalchemy.pool import StaticPool

    # Use StaticPool to ensure all connections share the same in-memory database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def admin_client(admin_test_engine: Engine, tmp_path: Path) -> TestClient:
    """Create a TestClient with admin routes."""
    # Ensure tables exist in the engine
    SQLModel.metadata.create_all(admin_test_engine)

    key_set = load_or_create_key(tmp_path / "test_key.pem")
    templates_dir = Path(__file__).parent.parent.parent / "pxc" / "lti" / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))

    # Create a simple launch handler
    async def dummy_launch_handler(
        launch_data: object, request: object
    ) -> HTMLResponse:
        return HTMLResponse("Launch handled")

    from contextlib import contextmanager
    from collections.abc import Iterator

    @contextmanager
    def session_factory() -> Iterator[Session]:
        with Session(admin_test_engine) as session:
            yield session

    router = create_lti_router(
        session_factory=session_factory,
        key_set=key_set,
        launch_handler=dummy_launch_handler,
        base_url="http://testserver",
        templates=templates,
    )

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestAdminPlatformList:
    """Tests for GET /admin/platforms."""

    def test_empty_list_initially(self, admin_client: TestClient) -> None:
        """Should return empty platform list on fresh database."""
        response = admin_client.get("/admin/platforms")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Page should render even with no platforms
        assert "Platform" in response.text or "platform" in response.text

    def test_shows_created_platform(
        self, admin_client: TestClient, admin_test_engine: Engine
    ) -> None:
        """Should display platforms in the list."""
        # Create a platform directly in the database
        with Session(admin_test_engine) as session:
            platform = Platform(
                name="Test LMS",
                issuer="https://lms.example.com",
                client_id="test-client",
                oidc_auth_url="https://lms.example.com/auth",
                jwks_url="https://lms.example.com/jwks",
            )
            session.add(platform)
            session.commit()

        response = admin_client.get("/admin/platforms")
        assert response.status_code == 200
        assert "Test LMS" in response.text


class TestAdminPlatformCreate:
    """Tests for platform creation."""

    def test_get_new_platform_form(self, admin_client: TestClient) -> None:
        """Should render the new platform form."""
        response = admin_client.get("/admin/platforms/new")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_create_platform(
        self, admin_client: TestClient, admin_test_engine: Engine
    ) -> None:
        """Should create a new platform via POST."""
        response = admin_client.post(
            "/admin/platforms",
            data={
                "name": "Canvas LMS",
                "issuer": "https://canvas.instructure.com",
                "client_id": "12345",
                "oidc_auth_url": "https://canvas.instructure.com/api/lti/authorize",
                "jwks_url": "https://canvas.instructure.com/api/lti/jwks",
                "access_token_url": "https://canvas.instructure.com/login/oauth2/token",
            },
            follow_redirects=False,
        )

        # Should redirect to platform list
        assert response.status_code == 303
        assert response.headers["location"] == "/admin/platforms"

        # Verify platform was created in database
        with Session(admin_test_engine) as session:
            stmt = select(Platform).where(Platform.name == "Canvas LMS")
            platform = session.exec(stmt).first()
            assert platform is not None
            assert platform.issuer == "https://canvas.instructure.com"
            assert platform.client_id == "12345"

    def test_create_platform_shows_in_list(self, admin_client: TestClient) -> None:
        """Created platform should appear in the list."""
        admin_client.post(
            "/admin/platforms",
            data={
                "name": "Moodle",
                "issuer": "https://moodle.example.com",
                "client_id": "moodle-client",
                "oidc_auth_url": "https://moodle.example.com/auth",
                "jwks_url": "https://moodle.example.com/jwks",
                "access_token_url": "",
            },
        )

        response = admin_client.get("/admin/platforms")
        assert response.status_code == 200
        assert "Moodle" in response.text


class TestAdminPlatformEdit:
    """Tests for platform editing."""

    def test_get_edit_form(
        self, admin_client: TestClient, admin_test_engine: Engine
    ) -> None:
        """Should render the edit form with platform data."""
        # Create a platform
        with Session(admin_test_engine) as session:
            platform = Platform(
                name="Original Name",
                issuer="https://original.example.com",
                client_id="original-client",
                oidc_auth_url="https://original.example.com/auth",
                jwks_url="https://original.example.com/jwks",
            )
            session.add(platform)
            session.commit()
            session.refresh(platform)
            platform_id = platform.id

        response = admin_client.get(f"/admin/platforms/{platform_id}/edit")
        assert response.status_code == 200
        assert "Original Name" in response.text

    def test_edit_nonexistent_platform_404(self, admin_client: TestClient) -> None:
        """Should return 404 for nonexistent platform."""
        response = admin_client.get("/admin/platforms/99999/edit")
        assert response.status_code == 404

    def test_update_platform(
        self, admin_client: TestClient, admin_test_engine: Engine
    ) -> None:
        """Should update platform fields."""
        # Create a platform
        with Session(admin_test_engine) as session:
            platform = Platform(
                name="Old Name",
                issuer="https://old.example.com",
                client_id="old-client",
                oidc_auth_url="https://old.example.com/auth",
                jwks_url="https://old.example.com/jwks",
            )
            session.add(platform)
            session.commit()
            session.refresh(platform)
            platform_id = platform.id

        # Update the platform
        response = admin_client.post(
            f"/admin/platforms/{platform_id}",
            data={
                "name": "Updated Name",
                "issuer": "https://updated.example.com",
                "client_id": "updated-client",
                "oidc_auth_url": "https://updated.example.com/auth",
                "jwks_url": "https://updated.example.com/jwks",
                "access_token_url": "https://updated.example.com/token",
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/admin/platforms"

        # Verify changes in database
        with Session(admin_test_engine) as session:
            updated: Platform | None = session.get(Platform, platform_id)
            assert updated is not None
            assert updated.name == "Updated Name"
            assert updated.issuer == "https://updated.example.com"
            assert updated.client_id == "updated-client"

    def test_update_nonexistent_platform_404(self, admin_client: TestClient) -> None:
        """Should return 404 when updating nonexistent platform."""
        response = admin_client.post(
            "/admin/platforms/99999",
            data={
                "name": "Test",
                "issuer": "https://test.com",
                "client_id": "test",
                "oidc_auth_url": "https://test.com/auth",
                "jwks_url": "https://test.com/jwks",
            },
        )
        assert response.status_code == 404


class TestAdminPlatformDelete:
    """Tests for platform deletion."""

    def test_delete_platform(
        self, admin_client: TestClient, admin_test_engine: Engine
    ) -> None:
        """Should delete a platform."""
        # Create a platform
        with Session(admin_test_engine) as session:
            platform = Platform(
                name="To Delete",
                issuer="https://delete.example.com",
                client_id="delete-client",
                oidc_auth_url="https://delete.example.com/auth",
                jwks_url="https://delete.example.com/jwks",
            )
            session.add(platform)
            session.commit()
            session.refresh(platform)
            platform_id = platform.id

        # Delete the platform
        response = admin_client.post(
            f"/admin/platforms/{platform_id}/delete",
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/admin/platforms"

        # Verify platform was deleted
        with Session(admin_test_engine) as session:
            deleted: Platform | None = session.get(Platform, platform_id)
            assert deleted is None

    def test_delete_nonexistent_platform(self, admin_client: TestClient) -> None:
        """Should handle deleting nonexistent platform gracefully."""
        response = admin_client.post(
            "/admin/platforms/99999/delete",
            follow_redirects=False,
        )
        # Should still redirect successfully (idempotent)
        assert response.status_code == 303
