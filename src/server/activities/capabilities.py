"""
Capability validation and enforcement.

Checks plugin calls against the manifest to enforce security boundaries.
"""

from urllib.parse import urlparse

from server.activities.manifest_types import (
    Access,
    Capabilities,
    Scope,
    Type,
    ValueDefinition,
)

__all__ = [
    "Access",
    "CapabilityChecker",
    "CapabilityError",
    "ValueChecker",
    "ValueType",
    "ValueValidationError",
]

# Type alias for values that can be stored
ValueType = int | float | str | bool

# Allowed value types and their Python equivalents
VALUE_TYPES: dict[Type, type | tuple[type, ...]] = {
    Type.integer: int,
    Type.float: (int, float),  # int is acceptable for float
    Type.string: str,
    Type.boolean: bool,
}

# Default values for each type (used when no explicit default is provided)
TYPE_DEFAULTS: dict[Type, ValueType] = {
    Type.integer: 0,
    Type.float: 0.0,
    Type.string: "",
    Type.boolean: False,
}

# Access level hierarchy (higher number = more privileged)
ACCESS_HIERARCHY: dict[Access, int] = {
    Access.user: 0,
    Access.unit: 1,
    Access.course: 2,
    Access.platform: 3,
}


class CapabilityError(Exception):
    """Raised when a capability check fails."""


class ValueValidationError(Exception):
    """Raised when a value validation fails."""


class ValueChecker:
    """Validates values against their manifest definitions."""

    def __init__(self, values: dict[str, ValueDefinition] | None) -> None:
        self._definitions = values or {}

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
        if definition.default is not None:
            result: ValueType = definition.default
            return result
        return TYPE_DEFAULTS[definition.type]

    def validate(self, name: str, value: ValueType) -> None:
        """Validate a value against its manifest definition.

        Raises:
            ValueValidationError: If the value is invalid.
        """
        definition = self.get_definition(name)
        expected_type = VALUE_TYPES[definition.type]

        if not isinstance(value, expected_type):
            raise ValueValidationError(
                f"Value '{name}' must be {definition.type.value}, "
                f"got {type(value).__name__}"
            )

    def is_user_scoped(self, name: str) -> bool:
        """Check if a value is user-scoped."""
        definition = self.get_definition(name)
        return definition.scope == Scope.user_unit

    def user_value_names(self) -> list[str]:
        """Return names of user-scoped values."""
        return [name for name in self.value_names if self.is_user_scoped(name)]

    def shared_value_names(self) -> list[str]:
        """Return names of non-user-scoped (shared) values."""
        return [name for name in self.value_names if not self.is_user_scoped(name)]

    def get_access_level(self, name: str) -> Access:
        """Get the access level for a value."""
        definition = self.get_definition(name)
        return definition.access

    def can_access(self, name: str, user_access_level: Access) -> bool:
        """Check if a user with given access level can see this value.

        Access levels are hierarchical: a user with higher access can see
        values with lower or equal access requirements.
        """
        value_access = self.get_access_level(name)
        user_rank = ACCESS_HIERARCHY[user_access_level]
        value_rank = ACCESS_HIERARCHY[value_access]
        return user_rank >= value_rank


class CapabilityChecker:
    """Validates operations against declared capabilities."""

    def __init__(self, capabilities: Capabilities | None) -> None:
        """Initialize the checker.

        Args:
            capabilities: The capabilities from manifest (may be None).
        """
        self._caps = capabilities

    def check_http_request(self, url: str) -> None:
        """Check if HTTP request to URL is allowed.

        Args:
            url: The URL being requested.

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

        Args:
            model: The model being requested.

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
