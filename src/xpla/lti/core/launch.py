"""LTI 1.3 JWT validation and claim extraction."""

import logging
from dataclasses import dataclass, field
from typing import Any

import jwt
from jwt import PyJWKClient

logger = logging.getLogger(__name__)

# Cache JWKS clients per URL to avoid refetching
_jwks_clients: dict[str, PyJWKClient] = {}


@dataclass
class LaunchData:
    """Parsed LTI 1.3 launch claims."""

    message_type: str
    issuer: str
    client_id: str
    deployment_id: str
    user_id: str
    roles: list[str]
    context_id: str | None = None
    context_title: str | None = None
    resource_link_id: str | None = None
    custom: dict[str, str] = field(default_factory=dict)
    deep_link_return_url: str | None = None
    deep_link_settings: dict[str, Any] | None = None


class LaunchError(Exception):
    """Raised when JWT validation fails."""


def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    if jwks_url not in _jwks_clients:
        _jwks_clients[jwks_url] = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_clients[jwks_url]


def validate_launch_jwt(
    id_token: str,
    *,
    jwks_url: str,
    client_id: str,
    issuer: str,
) -> LaunchData:
    """Validate an LTI 1.3 id_token JWT and extract claims.

    Raises LaunchError on any validation failure.
    """
    try:
        jwks_client = _get_jwks_client(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)
        claims: dict[str, Any] = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=issuer,
        )
    except jwt.PyJWTError as e:
        raise LaunchError(f"JWT validation failed: {e}") from e

    message_type = claims.get(
        "https://purl.imsglobal.org/spec/lti/claim/message_type", ""
    )
    deployment_id = claims.get(
        "https://purl.imsglobal.org/spec/lti/claim/deployment_id", ""
    )
    roles = claims.get("https://purl.imsglobal.org/spec/lti/claim/roles", [])

    context = claims.get("https://purl.imsglobal.org/spec/lti/claim/context", {})
    resource_link = claims.get(
        "https://purl.imsglobal.org/spec/lti/claim/resource_link", {}
    )
    custom = claims.get("https://purl.imsglobal.org/spec/lti/claim/custom", {})

    dl_settings = claims.get(
        "https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings"
    )

    return LaunchData(
        message_type=message_type,
        issuer=claims.get("iss", ""),
        client_id=client_id,
        deployment_id=deployment_id,
        user_id=claims.get("sub", ""),
        roles=roles,
        context_id=context.get("id") if context else None,
        context_title=context.get("title") if context else None,
        resource_link_id=resource_link.get("id") if resource_link else None,
        custom=custom or {},
        deep_link_return_url=(
            dl_settings.get("deep_link_return_url") if dl_settings else None
        ),
        deep_link_settings=dl_settings,
    )
