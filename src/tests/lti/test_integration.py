"""Integration tests for LTI 1.3 end-to-end flows."""

import secrets
import time
from pathlib import Path
from typing import Any

import jwt
import pytest
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient
from fastapi.templating import Jinja2Templates
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, select

from pxc.lti.core.keys import KeySet, load_or_create_key
from pxc.lti.core.launch import LaunchData
from pxc.lti.core.models import Platform
from pxc.lti.core.routes import create_lti_router


@pytest.fixture
def integration_engine() -> Engine:
    """Create a fresh in-memory database for integration tests."""
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
def integration_key_set(tmp_path: Path) -> KeySet:
    """Generate RSA key for integration tests."""
    return load_or_create_key(tmp_path / "integration_key.pem")


@pytest.fixture
def integration_platform_key() -> KeySet:
    """Generate platform RSA key for integration tests."""
    from jwcrypto import jwk

    key = jwk.JWK.generate(kty="RSA", size=2048)
    return KeySet(private_key=key)


@pytest.fixture
def integration_client(
    integration_engine: Engine,
    integration_key_set: KeySet,
    tmp_path: Path,
) -> TestClient:
    """Create TestClient with full LTI routes."""
    templates_dir = Path(__file__).parent.parent.parent / "pxc" / "lti" / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))

    # Track launch calls
    launch_calls: list[LaunchData] = []

    async def test_launch_handler(
        launch_data: LaunchData, request: Request
    ) -> Response:
        """Capture launch data for verification."""
        launch_calls.append(launch_data)
        return HTMLResponse(
            f"<html><body>Launched: {launch_data.user_id}</body></html>"
        )

    from contextlib import contextmanager
    from collections.abc import Iterator

    @contextmanager
    def session_factory() -> Iterator[Session]:
        with Session(integration_engine) as session:
            yield session

    router = create_lti_router(
        session_factory=session_factory,
        key_set=integration_key_set,
        launch_handler=test_launch_handler,
        base_url="http://testserver",
        templates=templates,
    )

    app = FastAPI()
    app.include_router(router)

    # Attach launch_calls for test access
    app.state.launch_calls = launch_calls

    return TestClient(app)


class TestJWKSEndpoint:
    """Tests for JWKS endpoint."""

    def test_jwks_returns_json(self, integration_client: TestClient) -> None:
        """Should return valid JSON at JWKS endpoint."""
        response = integration_client.get("/.well-known/jwks.json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_jwks_structure(
        self, integration_client: TestClient, integration_key_set: KeySet
    ) -> None:
        """Should return valid JWKS structure with public key."""
        response = integration_client.get("/.well-known/jwks.json")
        jwks = response.json()

        assert "keys" in jwks
        assert len(jwks["keys"]) == 1

        key = jwks["keys"][0]
        assert key["kty"] == "RSA"
        assert key["use"] == "sig"
        assert key["alg"] == "RS256"
        assert key["kid"] == integration_key_set.kid
        assert "n" in key
        assert "e" in key
        # Private components should not be exposed
        assert "d" not in key


class TestOIDCLoginFlow:
    """Tests for OIDC login initiation."""

    def test_login_missing_params_returns_400(
        self, integration_client: TestClient
    ) -> None:
        """Should return 400 when required params are missing."""
        response = integration_client.get("/auth/login")
        assert response.status_code == 400

    def test_login_unknown_platform_returns_400(
        self, integration_client: TestClient
    ) -> None:
        """Should return 400 for unknown platform."""
        response = integration_client.get(
            "/auth/login",
            params={
                "iss": "https://unknown.example.com",
                "client_id": "unknown-client",
                "login_hint": "user-123",
            },
        )
        assert response.status_code == 400

    def test_login_redirects_to_platform(
        self, integration_client: TestClient, integration_engine: Engine
    ) -> None:
        """Should redirect to platform's OIDC auth URL."""
        # Create a platform
        with Session(integration_engine) as session:
            platform = Platform(
                name="Test Platform",
                issuer="https://platform.example.com",
                client_id="test-client",
                oidc_auth_url="https://platform.example.com/auth",
                jwks_url="https://platform.example.com/jwks",
            )
            session.add(platform)
            session.commit()

        response = integration_client.get(
            "/auth/login",
            params={
                "iss": "https://platform.example.com",
                "client_id": "test-client",
                "login_hint": "user-123",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        redirect_url = response.headers["location"]
        assert redirect_url.startswith("https://platform.example.com/auth")
        assert "state=" in redirect_url
        assert "nonce=" in redirect_url
        assert "login_hint=user-123" in redirect_url

    def test_login_sets_state_cookie(
        self, integration_client: TestClient, integration_engine: Engine
    ) -> None:
        """Should set state cookie for CSRF protection."""
        with Session(integration_engine) as session:
            platform = Platform(
                name="Test",
                issuer="https://platform.example.com",
                client_id="test-client",
                oidc_auth_url="https://platform.example.com/auth",
                jwks_url="https://platform.example.com/jwks",
            )
            session.add(platform)
            session.commit()

        response = integration_client.get(
            "/auth/login",
            params={
                "iss": "https://platform.example.com",
                "client_id": "test-client",
                "login_hint": "user-123",
            },
            follow_redirects=False,
        )

        assert "lti_state" in response.cookies


class TestLaunchCallback:
    """Tests for LTI launch callback."""

    def test_successful_launch(
        self,
        integration_client: TestClient,
        integration_engine: Engine,
        integration_platform_key: KeySet,
    ) -> None:
        """Should handle successful LTI launch end-to-end."""
        from unittest.mock import Mock, patch

        # Create platform
        with Session(integration_engine) as session:
            platform = Platform(
                name="Test Platform",
                issuer="https://platform.example.com",
                client_id="test-client",
                oidc_auth_url="https://platform.example.com/auth",
                jwks_url="https://platform.example.com/jwks",
            )
            session.add(platform)
            session.commit()

        # Mock PyJWKClient instead of HTTP requests
        mock_signing_key = Mock()
        mock_signing_key.key = integration_platform_key.public_pem

        with patch("pxc.lti.core.launch.PyJWKClient") as mock_client_class:
            mock_client = Mock()
            mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_client_class.return_value = mock_client

            self._run_successful_launch_test(
                integration_client,
                integration_engine,
                integration_platform_key,
            )

    def _run_successful_launch_test(
        self,
        integration_client: TestClient,
        integration_engine: Engine,
        integration_platform_key: KeySet,
    ) -> None:
        """Helper method for successful launch test logic."""

        # Step 1: Initiate login
        login_response = integration_client.get(
            "/auth/login",
            params={
                "iss": "https://platform.example.com",
                "client_id": "test-client",
                "login_hint": "user-456",
            },
            follow_redirects=False,
        )

        state_cookie = login_response.cookies.get("lti_state")
        assert state_cookie is not None

        # Step 2: Create valid id_token from platform
        now = int(time.time())
        id_token_payload: dict[str, Any] = {
            "iss": "https://platform.example.com",
            "aud": "test-client",
            "sub": "user-456",
            "iat": now,
            "exp": now + 300,
            "nonce": secrets.token_urlsafe(16),
            "https://purl.imsglobal.org/spec/lti/claim/message_type": "LtiResourceLinkRequest",
            "https://purl.imsglobal.org/spec/lti/claim/version": "1.3.0",
            "https://purl.imsglobal.org/spec/lti/claim/deployment_id": "deploy-1",
            "https://purl.imsglobal.org/spec/lti/claim/roles": [
                "http://purl.imsglobal.org/vocab/lis/v2/membership#Learner"
            ],
        }
        id_token: str = jwt.encode(
            id_token_payload,
            integration_platform_key.private_pem,
            algorithm="RS256",
            headers={"kid": integration_platform_key.kid},
        )

        # Store nonce before callback
        from pxc.lti.core.oidc import store_nonce

        with Session(integration_engine) as session:
            platform_record = session.exec(
                select(Platform).where(
                    Platform.issuer == "https://platform.example.com"
                )
            ).first()
            assert platform_record and platform_record.id
            store_nonce(session, id_token_payload["nonce"], platform_record.id)

        # Step 3: POST to callback
        callback_response = integration_client.post(
            "/auth/callback",
            data={
                "id_token": id_token,
                "state": state_cookie,
            },
            cookies={"lti_state": state_cookie},
        )

        assert callback_response.status_code == 200
        assert "user-456" in callback_response.text

        # Verify launch handler was called
        launch_calls = integration_client.app.state.launch_calls  # type: ignore[attr-defined]
        assert len(launch_calls) == 1
        assert launch_calls[0].user_id == "user-456"

    def test_callback_invalid_state_fails(self, integration_client: TestClient) -> None:
        """Should reject callback with mismatched state."""
        response = integration_client.post(
            "/auth/callback",
            data={
                "id_token": "fake-token",
                "state": "wrong-state",
            },
            cookies={"lti_state": "correct-state"},
        )

        assert response.status_code == 400
        assert "state" in response.text.lower()

    def test_callback_malformed_jwt_fails(self, integration_client: TestClient) -> None:
        """Should reject malformed JWT."""
        response = integration_client.post(
            "/auth/callback",
            data={
                "id_token": "not-a-jwt",
                "state": "test-state",
            },
            cookies={"lti_state": "test-state"},
        )

        assert response.status_code == 400


class TestDeepLinkingFlow:
    """Tests for deep linking flow."""

    def test_deep_linking_request(
        self,
        integration_client: TestClient,
        integration_engine: Engine,
        integration_platform_key: KeySet,
    ) -> None:
        """Should handle deep linking request."""
        from unittest.mock import Mock, patch

        # Create platform
        with Session(integration_engine) as session:
            platform = Platform(
                name="Test Platform",
                issuer="https://platform.example.com",
                client_id="dl-client",
                oidc_auth_url="https://platform.example.com/auth",
                jwks_url="https://platform.example.com/jwks",
            )
            session.add(platform)
            session.commit()

        # Mock PyJWKClient instead of HTTP requests
        mock_signing_key = Mock()
        mock_signing_key.key = integration_platform_key.public_pem

        with patch("pxc.lti.core.launch.PyJWKClient") as mock_client_class:
            mock_client = Mock()
            mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_client_class.return_value = mock_client

            self._run_deep_linking_test(
                integration_client,
                integration_engine,
                integration_platform_key,
            )

    def _run_deep_linking_test(
        self,
        integration_client: TestClient,
        integration_engine: Engine,
        integration_platform_key: KeySet,
    ) -> None:
        """Helper method for deep linking test logic."""
        # Login
        login_response = integration_client.get(
            "/auth/login",
            params={
                "iss": "https://platform.example.com",
                "client_id": "dl-client",
                "login_hint": "instructor-1",
            },
            follow_redirects=False,
        )

        state_cookie = login_response.cookies.get("lti_state")
        assert state_cookie is not None

        # Create deep linking JWT
        now = int(time.time())
        nonce = secrets.token_urlsafe(16)
        dl_payload: dict[str, Any] = {
            "iss": "https://platform.example.com",
            "aud": "dl-client",
            "sub": "instructor-1",
            "iat": now,
            "exp": now + 300,
            "nonce": nonce,
            "https://purl.imsglobal.org/spec/lti/claim/message_type": "LtiDeepLinkingRequest",
            "https://purl.imsglobal.org/spec/lti/claim/version": "1.3.0",
            "https://purl.imsglobal.org/spec/lti/claim/deployment_id": "deploy-1",
            "https://purl.imsglobal.org/spec/lti/claim/roles": [
                "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Instructor"
            ],
            "https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings": {
                "deep_link_return_url": "https://platform.example.com/deep_link/return",
                "accept_types": ["ltiResourceLink"],
            },
        }
        dl_token: str = jwt.encode(
            dl_payload,
            integration_platform_key.private_pem,
            algorithm="RS256",
            headers={"kid": integration_platform_key.kid},
        )

        # Store nonce
        from pxc.lti.core.oidc import store_nonce

        with Session(integration_engine) as session:
            platform_record = session.exec(
                select(Platform).where(
                    Platform.issuer == "https://platform.example.com"
                )
            ).first()
            assert platform_record and platform_record.id
            store_nonce(session, nonce, platform_record.id)

        # Launch
        callback_response = integration_client.post(
            "/auth/callback",
            data={
                "id_token": dl_token,
                "state": state_cookie,
            },
            cookies={"lti_state": state_cookie},
        )

        assert callback_response.status_code == 200

        # Verify deep linking launch was captured
        launch_calls = integration_client.app.state.launch_calls  # type: ignore[attr-defined]
        assert len(launch_calls) == 1
        assert launch_calls[0].message_type == "LtiDeepLinkingRequest"
        assert (
            launch_calls[0].deep_link_return_url
            == "https://platform.example.com/deep_link/return"
        )
