"""
Capability validation and enforcement.

Checks plugin calls against the manifest to enforce security boundaries.
"""

from dataclasses import dataclass, field
from typing import Any, Required, TypedDict
from urllib.parse import urlparse

# Type alias for values that can be stored
ValueType = int | float | str | bool


class ValueDefinition(TypedDict, total=False):
    """Definition of an activity value."""

    type: Required[str]  # "integer", "float", "string", "boolean"
    scope: Required[str]  # "unit" or "user,unit"
    access: Required[str]  # "user", "unit", "course", "platform"
    default: ValueType


# Valid scopes for values
VALID_SCOPES = {"unit", "user,unit"}

# Valid access levels for values
VALID_ACCESS_LEVELS = {"user", "unit", "course", "platform"}

# Access level hierarchy (higher number = more privileged)
ACCESS_HIERARCHY: dict[str, int] = {
    "user": 0,
    "unit": 1,
    "course": 2,
    "platform": 3,
}


# Allowed value types and their Python equivalents
VALUE_TYPES: dict[str, type | tuple[type, ...]] = {
    "integer": int,
    "float": (int, float),  # int is acceptable for float
    "string": str,
    "boolean": bool,
}

# Default values for each type (used when no explicit default is provided)
TYPE_DEFAULTS: dict[str, ValueType] = {
    "integer": 0,
    "float": 0.0,
    "string": "",
    "boolean": False,
}


class Manifest(TypedDict, total=False):
    """Activity manifest structure."""

    name: Required[str]
    capabilities: dict[str, Any]
    values: dict[str, ValueDefinition]


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


class ValueValidationError(Exception):
    """Raised when a value validation fails."""


def parse_value_definition(name: str, definition: ValueDefinition) -> ValueDefinition:
    """Validate a value definition.

    Args:
        name: The value name (for error messages).
        definition: The value definition dict.

    Returns:
        The validated ValueDefinition.

    Raises:
        ValueValidationError: If type/scope is missing/invalid or default doesn't
            match type.
    """
    if "type" not in definition:
        raise ValueValidationError(f"Value '{name}' is missing required 'type' field")

    type_name = definition["type"]
    if type_name not in VALUE_TYPES:
        raise ValueValidationError(
            f"Invalid type '{type_name}' for value '{name}'. "
            f"Allowed: {list(VALUE_TYPES.keys())}"
        )

    # Validate scope
    if "scope" not in definition:
        raise ValueValidationError(f"Value '{name}' is missing required 'scope' field")

    scope = definition["scope"]
    if scope not in VALID_SCOPES:
        raise ValueValidationError(
            f"Invalid scope '{scope}' for value '{name}'. "
            f"Allowed: {sorted(VALID_SCOPES)}"
        )

    # Validate access level
    if "access" not in definition:
        raise ValueValidationError(f"Value '{name}' is missing required 'access' field")

    access = definition["access"]
    if access not in VALID_ACCESS_LEVELS:
        raise ValueValidationError(
            f"Invalid access '{access}' for value '{name}'. "
            f"Allowed: {sorted(VALID_ACCESS_LEVELS)}"
        )

    # Validate default value type if provided
    if "default" in definition:
        default = definition["default"]
        expected_type = VALUE_TYPES[type_name]
        if not isinstance(default, expected_type):
            raise ValueValidationError(
                f"Default for '{name}' must be {type_name}, "
                f"got {type(default).__name__}"
            )

    return definition


def validate_value(name: str, value: ValueType, definition: ValueDefinition) -> None:
    """Validate a value against its definition.

    Args:
        name: The value name (for error messages).
        value: The value to validate.
        definition: The value definition from the manifest.

    Raises:
        ValueValidationError: If the value doesn't match the definition.
    """
    type_name = definition["type"]
    expected_type = VALUE_TYPES[type_name]

    if not isinstance(value, expected_type):
        raise ValueValidationError(
            f"Value '{name}' must be {type_name}, got {type(value).__name__}"
        )


class ValueChecker:
    """Validates values against their manifest definitions."""

    @classmethod
    def load_from_manifest(cls, manifest: Manifest) -> "ValueChecker":
        raw_values = manifest.get("values", {})
        definitions: dict[str, ValueDefinition] = {}
        for name, definition in raw_values.items():
            definitions[name] = parse_value_definition(name, definition)
        return cls(definitions)

    def __init__(self, definitions: dict[str, ValueDefinition]) -> None:
        self._definitions = definitions

    @property
    def value_names(self) -> list[str]:
        """Return the list of declared value names."""
        return list(self._definitions.keys())

    def get_definition(self, name: str) -> ValueDefinition:
        """Get the definition for a value.

        Raises:
            ValueValidationError: If the value is not declared.
        """
        if name not in self._definitions:
            raise ValueValidationError(
                f"Value '{name}' not declared in manifest. "
                f"Declared: {self.value_names}"
            )
        return self._definitions[name]

    def get_default(self, name: str) -> ValueType:
        """Get the default value for a declared value."""
        definition = self.get_definition(name)
        if "default" in definition:
            return definition["default"]
        return TYPE_DEFAULTS[definition["type"]]

    def validate(self, name: str, value: ValueType) -> None:
        """Validate a value against its manifest definition.

        Raises:
            ValueValidationError: If the value is invalid.
        """
        definition = self.get_definition(name)
        validate_value(name, value, definition)

    def is_user_scoped(self, name: str) -> bool:
        """Check if a value is user-scoped."""
        definition = self.get_definition(name)
        return definition["scope"] == "user,unit"

    def user_value_names(self) -> list[str]:
        """Return names of user-scoped values."""
        return [name for name in self.value_names if self.is_user_scoped(name)]

    def shared_value_names(self) -> list[str]:
        """Return names of non-user-scoped (shared) values."""
        return [name for name in self.value_names if not self.is_user_scoped(name)]

    def get_access_level(self, name: str) -> str:
        """Get the access level for a value."""
        definition = self.get_definition(name)
        return definition["access"]

    def can_access(self, name: str, user_access_level: str) -> bool:
        """Check if a user with given access level can see this value.

        Access levels are hierarchical: a user with higher access can see
        values with lower or equal access requirements.
        """
        value_access = self.get_access_level(name)
        user_rank = ACCESS_HIERARCHY.get(user_access_level, 0)
        value_rank = ACCESS_HIERARCHY.get(value_access, 0)
        return user_rank >= value_rank


class CapabilityChecker:
    """Validates operations against declared capabilities."""

    @classmethod
    def load_from_manifest(cls, manifest: Manifest) -> "CapabilityChecker":
        capabilities = parse_capabilities(manifest)
        return CapabilityChecker(capabilities)

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
