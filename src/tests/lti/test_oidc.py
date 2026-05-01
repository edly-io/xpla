"""Tests for OIDC login flow."""

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from sqlmodel import Session, select

from pxc.lti.core.models import Nonce, Platform
from pxc.lti.core.oidc import build_auth_redirect, consume_nonce, store_nonce


class TestBuildAuthRedirect:
    """Tests for build_auth_redirect function."""

    def test_generates_correct_auth_url(self, test_platform: Platform) -> None:
        """Should generate a valid OIDC authorization URL."""
        url, state, nonce = build_auth_redirect(
            test_platform,
            login_hint="user-123",
            target_link_uri="https://tool.example.com/launch",
            lti_message_hint=None,
            redirect_uri="https://tool.example.com/callback",
        )

        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "lms.example.com"
        assert parsed.path == "/auth"

        params = parse_qs(parsed.query)
        assert params["scope"] == ["openid"]
        assert params["response_type"] == ["id_token"]
        assert params["client_id"] == [test_platform.client_id]
        assert params["redirect_uri"] == ["https://tool.example.com/callback"]
        assert params["login_hint"] == ["user-123"]
        assert params["state"] == [state]
        assert params["nonce"] == [nonce]
        assert params["response_mode"] == ["form_post"]
        assert params["prompt"] == ["none"]
        assert params["target_link_uri"] == ["https://tool.example.com/launch"]

    def test_includes_lti_message_hint_when_provided(
        self, test_platform: Platform
    ) -> None:
        """Should include lti_message_hint parameter when provided."""
        url, _, _ = build_auth_redirect(
            test_platform,
            login_hint="user-123",
            target_link_uri="https://tool.example.com/launch",
            lti_message_hint="hint-data",
            redirect_uri="https://tool.example.com/callback",
        )

        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        assert params["lti_message_hint"] == ["hint-data"]

    def test_omits_lti_message_hint_when_none(self, test_platform: Platform) -> None:
        """Should omit lti_message_hint parameter when None."""
        url, _, _ = build_auth_redirect(
            test_platform,
            login_hint="user-123",
            target_link_uri="https://tool.example.com/launch",
            lti_message_hint=None,
            redirect_uri="https://tool.example.com/callback",
        )

        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        assert "lti_message_hint" not in params

    def test_generates_unique_state_and_nonce(self, test_platform: Platform) -> None:
        """Should generate unique state and nonce values."""
        _, state1, nonce1 = build_auth_redirect(
            test_platform,
            login_hint="user-123",
            target_link_uri="https://tool.example.com/launch",
            lti_message_hint=None,
            redirect_uri="https://tool.example.com/callback",
        )

        _, state2, nonce2 = build_auth_redirect(
            test_platform,
            login_hint="user-123",
            target_link_uri="https://tool.example.com/launch",
            lti_message_hint=None,
            redirect_uri="https://tool.example.com/callback",
        )

        assert state1 != state2
        assert nonce1 != nonce2


class TestStoreNonce:
    """Tests for store_nonce function."""

    def test_stores_nonce_in_database(
        self, db_session: Session, test_platform: Platform
    ) -> None:
        """Should store nonce with expiration time."""
        nonce_value = "test-nonce-123"
        store_nonce(db_session, nonce_value, test_platform.id or 0)

        stmt = select(Nonce).where(Nonce.value == nonce_value)
        nonce_record = db_session.exec(stmt).first()

        assert nonce_record is not None
        assert nonce_record.value == nonce_value
        assert nonce_record.platform_id == test_platform.id

    def test_sets_expiration_10_minutes(
        self, db_session: Session, test_platform: Platform
    ) -> None:
        """Should set expiration time approximately 10 minutes in the future."""
        nonce_value = "test-nonce-expires"
        now = datetime.now(timezone.utc)

        store_nonce(db_session, nonce_value, test_platform.id or 0)

        stmt = select(Nonce).where(Nonce.value == nonce_value)
        nonce_record = db_session.exec(stmt).first()

        assert nonce_record is not None
        expected_expiry = now + timedelta(minutes=10)
        # SQLite may strip timezone, so add it back for comparison
        stored_dt = (
            nonce_record.expires_at.replace(tzinfo=timezone.utc)
            if nonce_record.expires_at.tzinfo is None
            else nonce_record.expires_at
        )
        # Allow 1 second tolerance
        assert abs((stored_dt - expected_expiry).total_seconds()) < 1


class TestConsumeNonce:
    """Tests for consume_nonce function."""

    def test_returns_true_for_valid_nonce(
        self, db_session: Session, test_platform: Platform
    ) -> None:
        """Should return True and delete valid, unexpired nonce."""
        nonce_value = "valid-nonce"
        store_nonce(db_session, nonce_value, test_platform.id or 0)

        result = consume_nonce(db_session, nonce_value, test_platform.id or 0)

        assert result is True

        # Verify nonce was deleted
        stmt = select(Nonce).where(Nonce.value == nonce_value)
        nonce_record = db_session.exec(stmt).first()
        assert nonce_record is None

    def test_returns_false_for_nonexistent_nonce(
        self, db_session: Session, test_platform: Platform
    ) -> None:
        """Should return False when nonce doesn't exist."""
        result = consume_nonce(db_session, "nonexistent", test_platform.id or 0)
        assert result is False

    def test_returns_false_for_expired_nonce(
        self, db_session: Session, test_platform: Platform
    ) -> None:
        """Should return False and delete expired nonce."""
        nonce_value = "expired-nonce"
        expires = datetime.now(timezone.utc) - timedelta(minutes=1)
        nonce = Nonce(
            value=nonce_value,
            platform_id=test_platform.id or 0,
            expires_at=expires,
        )
        db_session.add(nonce)
        db_session.commit()

        result = consume_nonce(db_session, nonce_value, test_platform.id or 0)

        assert result is False

        # Verify nonce was deleted
        stmt = select(Nonce).where(Nonce.value == nonce_value)
        nonce_record = db_session.exec(stmt).first()
        assert nonce_record is None

    def test_prevents_replay_attacks(
        self, db_session: Session, test_platform: Platform
    ) -> None:
        """Should only allow nonce to be consumed once (replay protection)."""
        nonce_value = "one-time-nonce"
        store_nonce(db_session, nonce_value, test_platform.id or 0)

        # First consumption should succeed
        result1 = consume_nonce(db_session, nonce_value, test_platform.id or 0)
        assert result1 is True

        # Second consumption should fail
        result2 = consume_nonce(db_session, nonce_value, test_platform.id or 0)
        assert result2 is False

    def test_platform_isolation(self, db_session: Session) -> None:
        """Should not consume nonce from different platform."""
        platform1 = Platform(
            name="Platform 1",
            issuer="https://platform1.example.com",
            client_id="client-1",
            oidc_auth_url="https://platform1.example.com/auth",
            jwks_url="https://platform1.example.com/jwks",
        )
        platform2 = Platform(
            name="Platform 2",
            issuer="https://platform2.example.com",
            client_id="client-2",
            oidc_auth_url="https://platform2.example.com/auth",
            jwks_url="https://platform2.example.com/jwks",
        )
        db_session.add(platform1)
        db_session.add(platform2)
        db_session.commit()
        db_session.refresh(platform1)
        db_session.refresh(platform2)

        nonce_value = "platform1-nonce"
        store_nonce(db_session, nonce_value, platform1.id or 0)

        # Try to consume with platform2's ID
        result = consume_nonce(db_session, nonce_value, platform2.id or 0)
        assert result is False

        # Nonce should still exist for platform1
        stmt = select(Nonce).where(
            Nonce.value == nonce_value, Nonce.platform_id == platform1.id
        )
        nonce_record = db_session.exec(stmt).first()
        assert nonce_record is not None
