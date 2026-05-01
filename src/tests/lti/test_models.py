"""Tests for LTI SQLModel definitions."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session, select

from pxc.lti.core.models import Deployment, Nonce, Platform


class TestPlatformModel:
    """Tests for Platform model."""

    def test_create_platform(self, db_session: Session) -> None:
        """Should create a platform with valid fields."""
        platform = Platform(
            name="Canvas LMS",
            issuer="https://canvas.instructure.com",
            client_id="12345",
            oidc_auth_url="https://canvas.instructure.com/api/lti/authorize_redirect",
            jwks_url="https://canvas.instructure.com/api/lti/security/jwks",
            access_token_url="https://canvas.instructure.com/login/oauth2/token",
        )
        db_session.add(platform)
        db_session.commit()
        db_session.refresh(platform)

        assert platform.id is not None
        assert platform.name == "Canvas LMS"
        assert platform.issuer == "https://canvas.instructure.com"

    def test_unique_constraint_issuer_client_id(
        self, db_session: Session, test_platform: Platform
    ) -> None:
        """Should enforce unique constraint on (issuer, client_id)."""
        duplicate = Platform(
            name="Duplicate",
            issuer=test_platform.issuer,
            client_id=test_platform.client_id,
            oidc_auth_url="https://example.com/auth",
            jwks_url="https://example.com/jwks",
        )
        db_session.add(duplicate)

        with pytest.raises(Exception):  # SQLite raises IntegrityError
            db_session.commit()

    def test_different_client_id_same_issuer_allowed(
        self, db_session: Session, test_platform: Platform
    ) -> None:
        """Should allow same issuer with different client_id."""
        platform2 = Platform(
            name="Same Issuer Different Client",
            issuer=test_platform.issuer,
            client_id="different-client-id",
            oidc_auth_url="https://example.com/auth",
            jwks_url="https://example.com/jwks",
        )
        db_session.add(platform2)
        db_session.commit()
        db_session.refresh(platform2)

        assert platform2.id is not None
        assert platform2.id != test_platform.id


class TestDeploymentModel:
    """Tests for Deployment model."""

    def test_create_deployment(
        self, db_session: Session, test_platform: Platform
    ) -> None:
        """Should create a deployment with foreign key to platform."""
        deployment = Deployment(
            platform_id=test_platform.id or 0,
            deployment_id="deploy-123",
        )
        db_session.add(deployment)
        db_session.commit()
        db_session.refresh(deployment)

        assert deployment.id is not None
        assert deployment.platform_id == test_platform.id
        assert deployment.deployment_id == "deploy-123"

    def test_multiple_deployments_per_platform(
        self, db_session: Session, test_platform: Platform
    ) -> None:
        """Should allow multiple deployments for the same platform."""
        d1 = Deployment(platform_id=test_platform.id or 0, deployment_id="deploy-1")
        d2 = Deployment(platform_id=test_platform.id or 0, deployment_id="deploy-2")
        db_session.add(d1)
        db_session.add(d2)
        db_session.commit()

        stmt = select(Deployment).where(Deployment.platform_id == test_platform.id)
        deployments = db_session.exec(stmt).all()
        assert len(deployments) == 2


class TestNonceModel:
    """Tests for Nonce model."""

    def test_create_nonce(self, db_session: Session, test_platform: Platform) -> None:
        """Should create a nonce with expiration datetime."""
        expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        nonce = Nonce(
            value="test-nonce-123",
            platform_id=test_platform.id or 0,
            expires_at=expires,
        )
        db_session.add(nonce)
        db_session.commit()
        db_session.refresh(nonce)

        assert nonce.id is not None
        assert nonce.value == "test-nonce-123"
        assert nonce.platform_id == test_platform.id
        # SQLite may strip timezone info, compare timestamps
        assert (
            abs(
                (
                    nonce.expires_at.replace(tzinfo=timezone.utc) - expires
                ).total_seconds()
            )
            < 1
        )

    def test_query_expired_nonces(
        self, db_session: Session, test_platform: Platform
    ) -> None:
        """Should be able to query expired nonces."""
        now = datetime.now(timezone.utc)
        expired_nonce = Nonce(
            value="expired",
            platform_id=test_platform.id or 0,
            expires_at=now - timedelta(minutes=1),
        )
        valid_nonce = Nonce(
            value="valid",
            platform_id=test_platform.id or 0,
            expires_at=now + timedelta(minutes=10),
        )
        db_session.add(expired_nonce)
        db_session.add(valid_nonce)
        db_session.commit()

        # Query expired nonces
        stmt = select(Nonce).where(Nonce.expires_at < now)
        expired = db_session.exec(stmt).all()
        assert len(expired) == 1
        assert expired[0].value == "expired"
