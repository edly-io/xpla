"""Value validation."""

from typing import Any

import jsonschema

from server.activities.manifest_types import (
    Scope,
    Type,
    TypeSchema,
    ValueDefinition,
)

__all__ = [
    "ValueChecker",
    "ValueType",
    "ValueValidationError",
]

# Type alias for values that can be stored
ValueType = int | float | str | bool | list[Any] | dict[str, Any]

# Default values for each type (used when no explicit default is provided)
TYPE_DEFAULTS: dict[Type, ValueType] = {
    Type.integer: 0,
    Type.number: 0.0,
    Type.string: "",
    Type.boolean: False,
    Type.array: [],
    Type.object: {},
}

# Map from our type names to JSON Schema type names
_JSON_SCHEMA_TYPE: dict[Type, str] = {
    Type.integer: "integer",
    Type.number: "number",
    Type.string: "string",
    Type.boolean: "boolean",
    Type.array: "array",
    Type.object: "object",
}


def build_type_schema(definition: ValueDefinition | TypeSchema) -> dict[str, Any]:
    """Build a JSON Schema fragment from a value/type definition."""
    schema: dict[str, Any] = {"type": _JSON_SCHEMA_TYPE[definition.type]}
    if definition.type == Type.array and definition.items is not None:
        schema["items"] = build_type_schema(definition.items)
    if definition.type == Type.object and definition.properties is not None:
        schema["properties"] = {
            k: build_type_schema(v) for k, v in definition.properties.items()
        }
    return schema


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
        """Validate a value against its manifest definition using JSON Schema.

        Raises:
            ValueValidationError: If the value is invalid.
        """
        definition = self.get_definition(name)
        schema = build_type_schema(definition)
        try:
            jsonschema.validate(value, schema)
        except jsonschema.ValidationError as e:
            raise ValueValidationError(
                f"Value '{name}' failed validation: {e.message}"
            ) from e

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
