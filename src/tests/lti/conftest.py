"""Pytest fixtures for LTI 1.3 tests."""

import secrets
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient
from jwcrypto import jwk
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from pxc.lti.core.db import create_db
from pxc.lti.core.keys import KeySet, load_or_create_key
from pxc.lti.core.models import Platform, Deployment


@pytest.fixture
def db_engine() -> Generator[Engine, None, None]:
    """In-memory SQLite database for tests."""
    from sqlalchemy.pool import StaticPool

    # Use StaticPool to ensure all connections share the same in-memory database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Database session for tests."""
    with Session(db_engine) as session:
        yield session


@pytest.fixture
def test_platform(db_session: Session) -> Platform:
    """Create a test platform in the database."""
    platform = Platform(
        name="Test LMS",
        issuer="https://lms.example.com",
        client_id="test-client-id",
        oidc_auth_url="https://lms.example.com/auth",
        jwks_url="https://lms.example.com/.well-known/jwks.json",
        access_token_url="https://lms.example.com/token",
    )
    db_session.add(platform)
    db_session.commit()
    db_session.refresh(platform)
    return platform


@pytest.fixture
def test_deployment(db_session: Session, test_platform: Platform) -> Deployment:
    """Create a test deployment."""
    deployment = Deployment(
        platform_id=test_platform.id or 0,
        deployment_id="test-deployment-1",
    )
    db_session.add(deployment)
    db_session.commit()
    db_session.refresh(deployment)
    return deployment


@pytest.fixture
def test_key_set(tmp_path: Path) -> KeySet:
    """Generate temporary RSA key for tests."""
    key_path = tmp_path / "test_key.pem"
    return load_or_create_key(key_path)


@pytest.fixture
def platform_key_set() -> KeySet:
    """Generate a platform RSA key (simulating the LMS)."""
    key = jwk.JWK.generate(kty="RSA", size=2048)
    return KeySet(private_key=key)


@pytest.fixture(autouse=True)
def clear_jwks_cache() -> Generator[None, None, None]:
    """Clear JWKS client cache before each test."""
    from pxc.lti.core import launch

    yield
    launch._jwks_clients.clear()


@pytest.fixture
def mock_platform_jwks(platform_key_set: KeySet) -> Generator[str, None, None]:
    """Mock PyJWKClient to avoid real HTTP requests during JWT validation."""
    from unittest.mock import Mock, patch

    jwks_url = "https://lms.example.com/.well-known/jwks.json"

    # Create a mock signing key with the platform's public key
    mock_signing_key = Mock()
    mock_signing_key.key = platform_key_set.public_pem

    # Mock the PyJWKClient class
    with patch("pxc.lti.core.launch.PyJWKClient") as mock_client_class:
        mock_client = Mock()
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_client_class.return_value = mock_client
        yield jwks_url


@pytest.fixture
def valid_id_token(test_platform: Platform, platform_key_set: KeySet) -> str:
    """Generate a valid LTI launch JWT signed by the platform."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "iss": test_platform.issuer,
        "aud": test_platform.client_id,
        "sub": "user-123",
        "iat": now,
        "exp": now + 300,
        "nonce": secrets.token_urlsafe(16),
        "https://purl.imsglobal.org/spec/lti/claim/message_type": "LtiResourceLinkRequest",
        "https://purl.imsglobal.org/spec/lti/claim/version": "1.3.0",
        "https://purl.imsglobal.org/spec/lti/claim/deployment_id": "test-deployment-1",
        "https://purl.imsglobal.org/spec/lti/claim/target_link_uri": "https://tool.example.com/launch",
        "https://purl.imsglobal.org/spec/lti/claim/roles": [
            "http://purl.imsglobal.org/vocab/lis/v2/membership#Learner"
        ],
        "https://purl.imsglobal.org/spec/lti/claim/context": {
            "id": "course-101",
            "title": "Introduction to Testing",
        },
        "https://purl.imsglobal.org/spec/lti/claim/resource_link": {
            "id": "link-1",
        },
        "https://purl.imsglobal.org/spec/lti/claim/custom": {
            "activity_type": "quiz",
        },
    }
    token: str = jwt.encode(
        payload,
        platform_key_set.private_pem,
        algorithm="RS256",
        headers={"kid": platform_key_set.kid},
    )
    return token


@pytest.fixture
def deep_linking_id_token(test_platform: Platform, platform_key_set: KeySet) -> str:
    """Generate a valid LTI deep linking JWT."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "iss": test_platform.issuer,
        "aud": test_platform.client_id,
        "sub": "user-123",
        "iat": now,
        "exp": now + 300,
        "nonce": secrets.token_urlsafe(16),
        "https://purl.imsglobal.org/spec/lti/claim/message_type": "LtiDeepLinkingRequest",
        "https://purl.imsglobal.org/spec/lti/claim/version": "1.3.0",
        "https://purl.imsglobal.org/spec/lti/claim/deployment_id": "test-deployment-1",
        "https://purl.imsglobal.org/spec/lti/claim/roles": [
            "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Instructor"
        ],
        "https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings": {
            "deep_link_return_url": "https://lms.example.com/deep_link/return",
            "accept_types": ["ltiResourceLink"],
            "accept_presentation_document_targets": ["iframe", "window"],
        },
    }
    token: str = jwt.encode(
        payload,
        platform_key_set.private_pem,
        algorithm="RS256",
        headers={"kid": platform_key_set.kid},
    )
    return token


@pytest.fixture
def lti_client(tmp_path: Path) -> Generator[TestClient, None, None]:
    """FastAPI TestClient for LTI app with isolated test database."""
    from unittest.mock import patch
    from pxc.lti import config

    # Create temporary paths
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir()
    test_db_path = test_data_dir / "test.db"
    test_key_path = test_data_dir / "test_key.pem"

    # Create test database and key (initializes files for app to use)
    create_db(str(test_db_path))
    load_or_create_key(test_key_path)

    # Patch the app's dependencies
    with patch.object(config, "DATA_DIR", test_data_dir):
        with patch.object(config, "DB_PATH", test_db_path):
            with patch.object(config, "KEY_PATH", test_key_path):
                # Import app after patching to ensure it uses test config
                from pxc.lti.app import app as patched_app

                client = TestClient(patched_app)
                yield client
