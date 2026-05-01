"""Build LTI Deep Linking response JWTs."""

import secrets
import time
from typing import Any

from pxc.lti.core.keys import KeySet


def build_deep_link_response(
    key_set: KeySet,
    *,
    issuer: str,
    client_id: str,
    deployment_id: str,
    items: list[dict[str, Any]],
) -> str:
    """Build a signed JWT for a Deep Linking response.

    Args:
        key_set: Tool's RSA key set for signing.
        issuer: The tool's base URL (we are the issuer of this JWT).
        client_id: The platform's client_id (audience).
        deployment_id: LTI deployment ID.
        items: List of content items to return.

    Returns:
        Signed JWT string.
    """
    now = int(time.time())
    payload: dict[str, Any] = {
        "iss": issuer,
        "aud": client_id,
        "iat": now,
        "exp": now + 300,
        "nonce": secrets.token_urlsafe(16),
        "https://purl.imsglobal.org/spec/lti/claim/message_type": "LtiDeepLinkingResponse",
        "https://purl.imsglobal.org/spec/lti/claim/version": "1.3.0",
        "https://purl.imsglobal.org/spec/lti/claim/deployment_id": deployment_id,
        "https://purl.imsglobal.org/spec/lti-dl/claim/content_items": items,
    }
    return key_set.sign_jwt(payload)
