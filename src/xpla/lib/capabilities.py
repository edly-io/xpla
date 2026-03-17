"""Capability validation and enforcement for HTTP and AI access."""

from urllib.parse import urlparse

from xpla.lib.manifest_types import Capabilities

__all__ = [
    "CapabilityChecker",
    "CapabilityError",
]


class CapabilityError(Exception):
    """Raised when a capability check fails."""


class CapabilityChecker:
    """Validates operations against declared capabilities."""

    def __init__(self, capabilities: Capabilities | None) -> None:
        self._caps = capabilities

    def check_http_request(self, url: str) -> None:
        """Check if HTTP request to URL is allowed.

        Raises:
            CapabilityError: If HTTP not allowed or host not in allowlist.
        """
        if self._caps is None or self._caps.http is None:
            raise CapabilityError("http capability not declared in manifest")

        # If allowed_hosts is empty or None, allow all (permissive mode)
        allowed = self._caps.http.allowed_hosts
        if allowed:
            parsed = urlparse(url)
            if parsed.hostname not in allowed:
                raise CapabilityError(
                    f"HTTP requests to {parsed.hostname} not allowed. "
                    f"Allowed hosts: {sorted(allowed)}"
                )

    def check_ai_model(self, model: str) -> None:
        """Check if AI model is allowed.

        Raises:
            CapabilityError: If AI not allowed or model restricted.
        """
        if self._caps is None or self._caps.ai is None:
            raise CapabilityError("ai capability not declared in manifest")

        # If allowed_models is empty or None, allow all
        allowed = self._caps.ai.models
        if allowed:
            if model not in allowed:
                raise CapabilityError(
                    f"AI model '{model}' not allowed. " f"Allowed: {sorted(allowed)}"
                )
