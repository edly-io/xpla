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
        self._caps = capabilities or Capabilities()

    def is_http_requested(self) -> bool:
        """
        Check if http access is requested for this activity.
        """
        if self._caps.http and self._caps.http.allowed_hosts:
            return True
        return False

    def check_http_request(self, url: str) -> None:
        """Check if HTTP request to URL is allowed.

        Raises:
            CapabilityError: If HTTP not allowed or host not in allowlist.
        """
        allowed_hosts = []
        if self._caps.http and self._caps.http.allowed_hosts:
            allowed_hosts = self._caps.http.allowed_hosts
        parsed = urlparse(url)
        if parsed.hostname not in allowed_hosts:
            raise CapabilityError(
                f"HTTP requests to {parsed.hostname} not allowed. "
                f"Allowed hosts: {sorted(allowed_hosts)}"
            )

    def is_storage_requested(self) -> bool:
        """
        Check if storage access is requested for this activity.
        """
        if self._caps and self._caps.storage:
            return True
        return False

    def check_storage(self, name: str) -> None:
        """Check if the named storage is declared.

        Raises:
            CapabilityError: If storage not declared or name not in the declared list.
        """
        storage = self._caps.storage or []
        if name not in storage:
            raise CapabilityError(
                f"Storage '{name}' not declared. " f"Declared: {sorted(storage)}"
            )
