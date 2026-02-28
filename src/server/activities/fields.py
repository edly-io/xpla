"""Field validation."""

from typing import Any

import jsonschema

from server.activities.manifest_types import (
    Scope,
    Type,
    TypeSchema,
    FieldDefinition,
)

__all__ = [
    "FieldChecker",
    "FieldType",
    "FieldValidationError",
]

# Type alias for field data that can be stored
FieldType = int | float | str | bool | list[Any] | dict[str, Any]

# Default values for each type (used when no explicit default is provided)
TYPE_DEFAULTS: dict[Type, FieldType] = {
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


def build_type_schema(definition: FieldDefinition | TypeSchema) -> dict[str, Any]:
    """Build a JSON Schema fragment from a field/type definition."""
    schema: dict[str, Any] = {"type": _JSON_SCHEMA_TYPE[definition.type]}
    if definition.type == Type.array and definition.items is not None:
        schema["items"] = build_type_schema(definition.items)
    if definition.type == Type.object and definition.properties is not None:
        schema["properties"] = {
            k: build_type_schema(v) for k, v in definition.properties.items()
        }
    return schema


class FieldValidationError(Exception):
    """Raised when a field validation fails."""


class FieldChecker:
    """Validates fields against their manifest definitions."""

    def __init__(self, fields: dict[str, FieldDefinition] | None) -> None:
        self._definitions = fields or {}

    @property
    def field_names(self) -> list[str]:
        """Return the list of declared field names."""
        return list(self._definitions.keys())

    def get_definition(self, name: str) -> FieldDefinition:
        """Get the definition for a field.

        Raises:
            FieldValidationError: If the field is not declared.
        """
        if name not in self._definitions:
            raise FieldValidationError(
                f"Field '{name}' not declared in manifest. "
                f"Declared: {self.field_names}"
            )
        return self._definitions[name]

    def get_default(self, name: str) -> FieldType:
        """Get the default value for a declared field."""
        definition = self.get_definition(name)
        if definition.default is not None:
            result: FieldType = definition.default
            return result
        return TYPE_DEFAULTS[definition.type]

    def validate(self, name: str, value: FieldType) -> None:
        """Validate a field value against its manifest definition using JSON Schema.

        Raises:
            FieldValidationError: If the value is invalid.
        """
        definition = self.get_definition(name)
        schema = build_type_schema(definition)
        try:
            jsonschema.validate(value, schema)
        except jsonschema.ValidationError as e:
            raise FieldValidationError(
                f"Field '{name}' failed validation: {e.message}"
            ) from e

    def get_scope(self, name: str) -> Scope:
        """Get the scope of a declared field."""
        return self.get_definition(name).scope

    def is_user_scoped(self, name: str) -> bool:
        """Check if a field is user-scoped."""
        return self.get_scope(name) in (
            Scope.user_activity,
            Scope.user_course,
            Scope.user_platform,
        )

    def user_field_names(self) -> list[str]:
        """Return names of user-scoped fields."""
        return [name for name in self.field_names if self.is_user_scoped(name)]

    def shared_field_names(self) -> list[str]:
        """Return names of non-user-scoped (shared) fields."""
        return [name for name in self.field_names if not self.is_user_scoped(name)]
