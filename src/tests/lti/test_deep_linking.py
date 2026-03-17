"""Tests for LTI Deep Linking response generation."""

from typing import Any

import jwt

from xpla.lti.core.deep_linking import build_deep_link_response
from xpla.lti.core.keys import KeySet


class TestBuildDeepLinkResponse:
    """Tests for build_deep_link_response function."""

    def test_creates_valid_jwt(self, test_key_set: KeySet) -> None:
        """Should create a valid signed JWT."""
        items = [
            {
                "type": "ltiResourceLink",
                "title": "Test Activity",
                "url": "https://tool.example.com/activity/quiz",
            }
        ]

        jwt_token = build_deep_link_response(
            test_key_set,
            issuer="https://tool.example.com",
            client_id="test-client-id",
            deployment_id="deploy-123",
            items=items,
        )

        # Verify it's a valid JWT
        decoded = jwt.decode(jwt_token, options={"verify_signature": False})
        assert isinstance(decoded, dict)

    def test_includes_required_claims(self, test_key_set: KeySet) -> None:
        """Should include all required LTI Deep Linking claims."""
        items = [{"type": "ltiResourceLink"}]

        jwt_token = build_deep_link_response(
            test_key_set,
            issuer="https://tool.example.com",
            client_id="test-client-id",
            deployment_id="deploy-123",
            items=items,
        )

        decoded: dict[str, Any] = jwt.decode(
            jwt_token, options={"verify_signature": False}
        )

        # Standard JWT claims
        assert decoded["iss"] == "https://tool.example.com"
        assert decoded["aud"] == "test-client-id"
        assert "iat" in decoded
        assert "exp" in decoded
        assert "nonce" in decoded

        # LTI-specific claims
        assert (
            decoded["https://purl.imsglobal.org/spec/lti/claim/message_type"]
            == "LtiDeepLinkingResponse"
        )
        assert decoded["https://purl.imsglobal.org/spec/lti/claim/version"] == "1.3.0"
        assert (
            decoded["https://purl.imsglobal.org/spec/lti/claim/deployment_id"]
            == "deploy-123"
        )

    def test_includes_content_items(self, test_key_set: KeySet) -> None:
        """Should include content items in the response."""
        items = [
            {
                "type": "ltiResourceLink",
                "title": "Activity 1",
                "url": "https://tool.example.com/activity1",
            },
            {
                "type": "ltiResourceLink",
                "title": "Activity 2",
                "url": "https://tool.example.com/activity2",
            },
        ]

        jwt_token = build_deep_link_response(
            test_key_set,
            issuer="https://tool.example.com",
            client_id="test-client-id",
            deployment_id="deploy-123",
            items=items,
        )

        decoded: dict[str, Any] = jwt.decode(
            jwt_token, options={"verify_signature": False}
        )

        content_items = decoded[
            "https://purl.imsglobal.org/spec/lti-dl/claim/content_items"
        ]
        assert len(content_items) == 2
        assert content_items[0]["title"] == "Activity 1"
        assert content_items[1]["title"] == "Activity 2"

    def test_signed_with_tool_key(self, test_key_set: KeySet) -> None:
        """Should sign JWT with the tool's private key."""
        items = [{"type": "ltiResourceLink"}]

        jwt_token = build_deep_link_response(
            test_key_set,
            issuer="https://tool.example.com",
            client_id="test-client-id",
            deployment_id="deploy-123",
            items=items,
        )

        # Verify signature with public key
        decoded = jwt.decode(
            jwt_token,
            test_key_set.public_pem,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        assert decoded["iss"] == "https://tool.example.com"

    def test_header_includes_kid(self, test_key_set: KeySet) -> None:
        """Should include key ID in JWT header."""
        items = [{"type": "ltiResourceLink"}]

        jwt_token = build_deep_link_response(
            test_key_set,
            issuer="https://tool.example.com",
            client_id="test-client-id",
            deployment_id="deploy-123",
            items=items,
        )

        header = jwt.get_unverified_header(jwt_token)
        assert header["kid"] == test_key_set.kid
        assert header["alg"] == "RS256"

    def test_expiration_is_5_minutes(self, test_key_set: KeySet) -> None:
        """Should set expiration to 5 minutes from issuance."""
        items = [{"type": "ltiResourceLink"}]

        jwt_token = build_deep_link_response(
            test_key_set,
            issuer="https://tool.example.com",
            client_id="test-client-id",
            deployment_id="deploy-123",
            items=items,
        )

        decoded: dict[str, Any] = jwt.decode(
            jwt_token, options={"verify_signature": False}
        )

        # exp should be iat + 300 seconds (5 minutes)
        assert decoded["exp"] == decoded["iat"] + 300

    def test_empty_items_list(self, test_key_set: KeySet) -> None:
        """Should handle empty items list."""
        jwt_token = build_deep_link_response(
            test_key_set,
            issuer="https://tool.example.com",
            client_id="test-client-id",
            deployment_id="deploy-123",
            items=[],
        )

        decoded: dict[str, Any] = jwt.decode(
            jwt_token, options={"verify_signature": False}
        )

        content_items = decoded[
            "https://purl.imsglobal.org/spec/lti-dl/claim/content_items"
        ]
        assert content_items == []
