"""Capability validation and enforcement for HTTP, AI, and storage access."""

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

    def check_storage(self, name: str) -> None:
        """Check if the named storage is declared.

        Raises:
            CapabilityError: If storage not declared or name not in the declared list.
        """
        if self._caps is None or self._caps.storage is None:
            raise CapabilityError("storage capability not declared in manifest")
        if name not in self._caps.storage:
            raise CapabilityError(
                f"Storage '{name}' not declared. "
                f"Declared: {sorted(self._caps.storage)}"
            )
