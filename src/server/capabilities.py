"""
Capability validation and enforcement.

Checks plugin calls against the manifest to enforce security boundaries.
"""

from dataclasses import dataclass, field
from typing import Any, Required, TypedDict
from urllib.parse import urlparse


class Manifest(TypedDict, total=False):
    """Activity manifest structure."""

    name: Required[str]
    version: str
    title: str
    capabilities: dict[str, Any]


class CapabilityError(Exception):
    """Raised when a capability check fails."""


@dataclass
class Capabilities:
    """Parsed capability requirements from manifest."""

    # KV storage
    kv_enabled: bool = False
    kv_namespace: str = ""
    kv_max_bytes: int = 0

    # HTTP requests
    http_enabled: bool = False
    http_allowed_hosts: set[str] = field(default_factory=set)

    # LMS functions
    lms_enabled: bool = False
    lms_allowed_functions: set[str] = field(default_factory=set)

    # AI (placeholder for future)
    ai_enabled: bool = False
    ai_allowed_models: set[str] = field(default_factory=set)


def parse_capabilities(manifest: Manifest) -> Capabilities:
    """Parse capabilities from a manifest dict.

    Args:
        manifest: The activity manifest dictionary.

    Returns:
        Parsed Capabilities object.

    Example manifest:
        {
            "name": "my-activity",
            "capabilities": {
                "kv": {"namespace": "my-activity", "max_bytes": 1048576},
                "http": {"allowed_hosts": ["api.example.com"]},
                "lms": ["get_user", "submit_grade"]
            }
        }
    """
    caps_dict = manifest.get("capabilities", {})
    caps = Capabilities()

    # KV storage
    if "kv" in caps_dict:
        kv = caps_dict["kv"]
        caps.kv_enabled = True
        if isinstance(kv, dict):
            caps.kv_namespace = kv.get("namespace", manifest.get("name", "default"))
            caps.kv_max_bytes = kv.get("max_bytes", 1024 * 1024)  # 1MB default
        else:
            # Simple boolean or empty - use defaults
            caps.kv_namespace = str(manifest.get("name", "default"))
            caps.kv_max_bytes = 1024 * 1024

    # HTTP requests
    if "http" in caps_dict:
        http = caps_dict["http"]
        caps.http_enabled = True
        if isinstance(http, dict):
            caps.http_allowed_hosts = set(http.get("allowed_hosts", []))

    # LMS functions
    if "lms" in caps_dict:
        lms = caps_dict["lms"]
        caps.lms_enabled = True
        if isinstance(lms, list):
            caps.lms_allowed_functions = set(lms)
        # If dict or True, allow all functions

    # AI (placeholder)
    if "ai" in caps_dict:
        ai = caps_dict["ai"]
        caps.ai_enabled = True
        if isinstance(ai, dict):
            caps.ai_allowed_models = set(ai.get("models", []))

    return caps


class CapabilityChecker:
    """Validates operations against declared capabilities."""

    def __init__(self, capabilities: Capabilities) -> None:
        """Initialize the checker.

        Args:
            capabilities: The parsed capabilities from manifest.
        """
        self._caps = capabilities
        self._kv_bytes_used = 0

    def check_kv_access(self) -> None:
        """Check if KV access is allowed.

        Raises:
            CapabilityError: If KV capability not declared.
        """
        if not self._caps.kv_enabled:
            raise CapabilityError("kv capability not declared in manifest")

    def check_kv_write(self, key: str, value: str) -> None:
        """Check if KV write is allowed within limits.

        Args:
            key: The key being written.
            value: The value being written.

        Raises:
            CapabilityError: If access denied or limits exceeded.
        """
        self.check_kv_access()

        # Check namespace prefix if specified
        if self._caps.kv_namespace:
            expected_prefix = f"{self._caps.kv_namespace}:"
            if not key.startswith(expected_prefix):
                raise CapabilityError(
                    f"Key must start with namespace prefix: {expected_prefix}"
                )

        # Check size limit
        new_bytes = len(key.encode()) + len(value.encode())
        if self._kv_bytes_used + new_bytes > self._caps.kv_max_bytes:
            raise CapabilityError(
                f"KV storage limit exceeded ({self._caps.kv_max_bytes} bytes)"
            )
        self._kv_bytes_used += new_bytes

    def check_http_request(self, url: str) -> None:
        """Check if HTTP request to URL is allowed.

        Args:
            url: The URL being requested.

        Raises:
            CapabilityError: If HTTP not allowed or host not in allowlist.
        """
        if not self._caps.http_enabled:
            raise CapabilityError("http capability not declared in manifest")

        # If allowed_hosts is empty, allow all (permissive mode)
        if self._caps.http_allowed_hosts:
            parsed = urlparse(url)
            if parsed.hostname not in self._caps.http_allowed_hosts:
                raise CapabilityError(
                    f"HTTP requests to {parsed.hostname} not allowed. "
                    f"Allowed hosts: {sorted(self._caps.http_allowed_hosts)}"
                )

    def check_lms_function(self, function_name: str) -> None:
        """Check if LMS function is allowed.

        Args:
            function_name: The LMS function being called.

        Raises:
            CapabilityError: If LMS not allowed or function restricted.
        """
        if not self._caps.lms_enabled:
            raise CapabilityError("lms capability not declared in manifest")

        # If allowed_functions is empty, allow all
        if self._caps.lms_allowed_functions:
            if function_name not in self._caps.lms_allowed_functions:
                raise CapabilityError(
                    f"LMS function '{function_name}' not allowed. "
                    f"Allowed: {sorted(self._caps.lms_allowed_functions)}"
                )

    def check_ai_model(self, model: str) -> None:
        """Check if AI model is allowed.

        Args:
            model: The model being requested.

        Raises:
            CapabilityError: If AI not allowed or model restricted.
        """
        if not self._caps.ai_enabled:
            raise CapabilityError("ai capability not declared in manifest")

        # If allowed_models is empty, allow all
        if self._caps.ai_allowed_models:
            if model not in self._caps.ai_allowed_models:
                raise CapabilityError(
                    f"AI model '{model}' not allowed. "
                    f"Allowed: {sorted(self._caps.ai_allowed_models)}"
                )
