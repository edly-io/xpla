"""Capability validation and enforcement for HTTP, storage, grading access."""

from enum import Enum
from urllib.parse import urlparse

from xpla.lib.manifest_types import Capabilities, Scope

__all__ = [
    "CapabilityChecker",
    "CapabilityError",
    "InterfaceName",
]


class InterfaceName(str, Enum):
    """WIT host interface names wired by SandboxComponentExecutor."""

    state = "state"
    grading = "grading"
    http = "http"
    storage = "storage"


class CapabilityError(Exception):
    """Raised when a capability check fails."""


class CapabilityChecker:
    """Validates operations against declared capabilities."""

    def __init__(self, capabilities: Capabilities | None) -> None:
        self._caps = capabilities or Capabilities()

    def is_interface_requested(self, interface: InterfaceName) -> bool:
        """Whether the manifest requests the given host interface.

        `state` is always available. Other interfaces opt in via the matching
        entry under `capabilities` in the manifest.
        """
        if interface is InterfaceName.state:
            return True
        if interface is InterfaceName.http:
            return bool(self._caps.http and self._caps.http.allowed_hosts)
        if interface is InterfaceName.storage:
            return bool(self._caps.storage)
        if interface is InterfaceName.grading:
            return self._caps.grading is not None
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

    def check_storage(self, name: str) -> None:
        """Check if the named storage is declared.

        Raises:
            CapabilityError: If storage not declared or name not in the declared list.
        """
        storage = self._caps.storage or {}
        if name not in storage:
            raise CapabilityError(
                f"Storage '{name}' not declared. " f"Declared: {sorted(storage.keys())}"
            )

    def get_storage_scope(self, name: str) -> Scope:
        """Get the scope for a declared storage bucket.

        Raises:
            CapabilityError: If storage not declared or name not in the declared list.
        """
        self.check_storage(name)
        assert self._caps.storage is not None
        return self._caps.storage[name].scope
