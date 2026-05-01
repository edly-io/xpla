"""Tests for LTI JWT validation and claim extraction."""

import secrets
import time
from typing import Any

import jwt
import pytest

from pxc.lti.core.keys import KeySet
from pxc.lti.core.launch import LaunchData, LaunchError, validate_launch_jwt
from pxc.lti.core.models import Platform


class TestValidateLaunchJWT:
    """Tests for validate_launch_jwt function."""

    def test_validates_valid_jwt(
        self,
        test_platform: Platform,
        platform_key_set: KeySet,
        mock_platform_jwks: str,
        valid_id_token: str,
    ) -> None:
        """Should successfully validate a valid JWT."""
        launch_data = validate_launch_jwt(
            valid_id_token,
            jwks_url=test_platform.jwks_url,
            client_id=test_platform.client_id,
            issuer=test_platform.issuer,
        )

        assert isinstance(launch_data, LaunchData)
        assert launch_data.issuer == test_platform.issuer
        assert launch_data.client_id == test_platform.client_id
        assert launch_data.user_id == "user-123"
        assert launch_data.deployment_id == "test-deployment-1"

    def test_raises_error_for_invalid_signature(
        self, test_platform: Platform, mock_platform_jwks: str
    ) -> None:
        """Should raise LaunchError for JWT with invalid signature."""
        # Create a JWT signed with a different key
        from jwcrypto import jwk

        wrong_key = jwk.JWK.generate(kty="RSA", size=2048)
        wrong_key_set = KeySet(private_key=wrong_key)
        now = int(time.time())
        payload = {
            "iss": test_platform.issuer,
            "aud": test_platform.client_id,
            "sub": "user-123",
            "iat": now,
            "exp": now + 300,
            "nonce": secrets.token_urlsafe(16),
        }
        bad_token = wrong_key_set.sign_jwt(payload)

        with pytest.raises(LaunchError, match="JWT validation failed"):
            validate_launch_jwt(
                bad_token,
                jwks_url=test_platform.jwks_url,
                client_id=test_platform.client_id,
                issuer=test_platform.issuer,
            )

    def test_raises_error_for_expired_token(
        self,
        test_platform: Platform,
        platform_key_set: KeySet,
        mock_platform_jwks: str,
    ) -> None:
        """Should raise LaunchError for expired token."""
        now = int(time.time())
        payload: dict[str, Any] = {
            "iss": test_platform.issuer,
            "aud": test_platform.client_id,
            "sub": "user-123",
            "iat": now - 400,
            "exp": now - 100,  # Expired
            "nonce": secrets.token_urlsafe(16),
        }
        expired_token: str = jwt.encode(
            payload,
            platform_key_set.private_pem,
            algorithm="RS256",
            headers={"kid": platform_key_set.kid},
        )

        with pytest.raises(LaunchError, match="JWT validation failed"):
            validate_launch_jwt(
                expired_token,
                jwks_url=test_platform.jwks_url,
                client_id=test_platform.client_id,
                issuer=test_platform.issuer,
            )

    def test_raises_error_for_wrong_audience(
        self,
        test_platform: Platform,
        platform_key_set: KeySet,
        mock_platform_jwks: str,
    ) -> None:
        """Should raise LaunchError when audience doesn't match."""
        now = int(time.time())
        payload: dict[str, Any] = {
            "iss": test_platform.issuer,
            "aud": "wrong-client-id",
            "sub": "user-123",
            "iat": now,
            "exp": now + 300,
            "nonce": secrets.token_urlsafe(16),
        }
        wrong_aud_token: str = jwt.encode(
            payload,
            platform_key_set.private_pem,
            algorithm="RS256",
            headers={"kid": platform_key_set.kid},
        )

        with pytest.raises(LaunchError, match="JWT validation failed"):
            validate_launch_jwt(
                wrong_aud_token,
                jwks_url=test_platform.jwks_url,
                client_id=test_platform.client_id,
                issuer=test_platform.issuer,
            )

    def test_raises_error_for_wrong_issuer(
        self,
        test_platform: Platform,
        platform_key_set: KeySet,
        mock_platform_jwks: str,
    ) -> None:
        """Should raise LaunchError when issuer doesn't match."""
        now = int(time.time())
        payload: dict[str, Any] = {
            "iss": "https://wrong-issuer.com",
            "aud": test_platform.client_id,
            "sub": "user-123",
            "iat": now,
            "exp": now + 300,
            "nonce": secrets.token_urlsafe(16),
        }
        wrong_iss_token: str = jwt.encode(
            payload,
            platform_key_set.private_pem,
            algorithm="RS256",
            headers={"kid": platform_key_set.kid},
        )

        with pytest.raises(LaunchError, match="JWT validation failed"):
            validate_launch_jwt(
                wrong_iss_token,
                jwks_url=test_platform.jwks_url,
                client_id=test_platform.client_id,
                issuer=test_platform.issuer,
            )


class TestLaunchData:
    """Tests for LaunchData claim extraction."""

    def test_extracts_message_type(
        self,
        test_platform: Platform,
        mock_platform_jwks: str,
        valid_id_token: str,
    ) -> None:
        """Should extract LTI message type."""
        launch_data = validate_launch_jwt(
            valid_id_token,
            jwks_url=test_platform.jwks_url,
            client_id=test_platform.client_id,
            issuer=test_platform.issuer,
        )

        assert launch_data.message_type == "LtiResourceLinkRequest"

    def test_extracts_user_and_roles(
        self,
        test_platform: Platform,
        mock_platform_jwks: str,
        valid_id_token: str,
    ) -> None:
        """Should extract user ID and roles."""
        launch_data = validate_launch_jwt(
            valid_id_token,
            jwks_url=test_platform.jwks_url,
            client_id=test_platform.client_id,
            issuer=test_platform.issuer,
        )

        assert launch_data.user_id == "user-123"
        assert (
            "http://purl.imsglobal.org/vocab/lis/v2/membership#Learner"
            in launch_data.roles
        )

    def test_extracts_context_claims(
        self,
        test_platform: Platform,
        mock_platform_jwks: str,
        valid_id_token: str,
    ) -> None:
        """Should extract context ID and title."""
        launch_data = validate_launch_jwt(
            valid_id_token,
            jwks_url=test_platform.jwks_url,
            client_id=test_platform.client_id,
            issuer=test_platform.issuer,
        )

        assert launch_data.context_id == "course-101"
        assert launch_data.context_title == "Introduction to Testing"

    def test_extracts_resource_link(
        self,
        test_platform: Platform,
        mock_platform_jwks: str,
        valid_id_token: str,
    ) -> None:
        """Should extract resource link ID."""
        launch_data = validate_launch_jwt(
            valid_id_token,
            jwks_url=test_platform.jwks_url,
            client_id=test_platform.client_id,
            issuer=test_platform.issuer,
        )

        assert launch_data.resource_link_id == "link-1"

    def test_extracts_custom_parameters(
        self,
        test_platform: Platform,
        mock_platform_jwks: str,
        valid_id_token: str,
    ) -> None:
        """Should extract custom parameters."""
        launch_data = validate_launch_jwt(
            valid_id_token,
            jwks_url=test_platform.jwks_url,
            client_id=test_platform.client_id,
            issuer=test_platform.issuer,
        )

        assert launch_data.custom["activity_type"] == "quiz"

    def test_extracts_deep_linking_settings(
        self,
        test_platform: Platform,
        mock_platform_jwks: str,
        deep_linking_id_token: str,
    ) -> None:
        """Should extract deep linking settings when present."""
        launch_data = validate_launch_jwt(
            deep_linking_id_token,
            jwks_url=test_platform.jwks_url,
            client_id=test_platform.client_id,
            issuer=test_platform.issuer,
        )

        assert launch_data.message_type == "LtiDeepLinkingRequest"
        assert (
            launch_data.deep_link_return_url
            == "https://lms.example.com/deep_link/return"
        )
        assert launch_data.deep_link_settings is not None
        assert "accept_types" in launch_data.deep_link_settings

    def test_handles_missing_optional_claims(
        self,
        test_platform: Platform,
        platform_key_set: KeySet,
        mock_platform_jwks: str,
    ) -> None:
        """Should handle JWTs with missing optional claims."""
        now = int(time.time())
        minimal_payload: dict[str, Any] = {
            "iss": test_platform.issuer,
            "aud": test_platform.client_id,
            "sub": "user-456",
            "iat": now,
            "exp": now + 300,
            "nonce": secrets.token_urlsafe(16),
            "https://purl.imsglobal.org/spec/lti/claim/message_type": "LtiResourceLinkRequest",
            "https://purl.imsglobal.org/spec/lti/claim/version": "1.3.0",
            "https://purl.imsglobal.org/spec/lti/claim/deployment_id": "minimal-deployment",
            "https://purl.imsglobal.org/spec/lti/claim/roles": [],
        }
        minimal_token: str = jwt.encode(
            minimal_payload,
            platform_key_set.private_pem,
            algorithm="RS256",
            headers={"kid": platform_key_set.kid},
        )

        launch_data = validate_launch_jwt(
            minimal_token,
            jwks_url=test_platform.jwks_url,
            client_id=test_platform.client_id,
            issuer=test_platform.issuer,
        )

        assert launch_data.user_id == "user-456"
        assert launch_data.context_id is None
        assert launch_data.context_title is None
        assert launch_data.resource_link_id is None
        assert not launch_data.custom
        assert launch_data.deep_link_return_url is None
