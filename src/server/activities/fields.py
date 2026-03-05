"""Field validation."""

import copy
from typing import Any

import jsonschema

from server.activities.manifest_types import (
    ArrayField,
    ArrayType,
    BooleanField,
    FieldDefinition,
    IntegerField,
    LogField,
    LogType,
    NumberField,
    ObjectField,
    ObjectType,
    Scope,
    StringField,
)

# Union of all concrete field definition types (the inner type of FieldDefinition)
FieldVariant = (
    IntegerField
    | NumberField
    | StringField
    | BooleanField
    | ArrayField
    | ObjectField
    | LogField
)

__all__ = [
    "FieldChecker",
    "FieldType",
    "FieldValidationError",
]

# Type alias for field data that can be stored
FieldType = int | float | str | bool | list[Any] | dict[str, Any]

# Default values by type name
_TYPE_DEFAULTS: dict[str, FieldType] = {
    "integer": 0,
    "number": 0.0,
    "string": "",
    "boolean": False,
    "array": [],
    "object": {},
}


def build_type_schema(definition: Any) -> dict[str, Any]:
    """Build a JSON Schema fragment from a type definition."""
    if isinstance(definition, (ArrayType, ArrayField)):
        return {"type": "array", "items": build_type_schema(definition.items.root)}
    if isinstance(definition, (ObjectType, ObjectField)):
        return {
            "type": "object",
            "properties": {
                k: build_type_schema(v.root) for k, v in definition.properties.items()
            },
        }
    if isinstance(definition, (LogType, LogField)):
        return build_type_schema(definition.items.root)
    return {"type": definition.type}


class FieldValidationError(Exception):
    """Raised when a field validation fails."""


class FieldChecker:
    """Validates fields against their manifest definitions."""

    def __init__(self, fields: dict[str, FieldDefinition] | None) -> None:
        self._definitions: dict[str, FieldVariant] = {
            k: v.root for k, v in (fields or {}).items()
        }

    @property
    def field_names(self) -> list[str]:
        """Return the list of declared field names."""
        return list(self._definitions.keys())

    def get_definition(self, name: str) -> FieldVariant:
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
            default: FieldType = copy.deepcopy(definition.default)
            return default
        return copy.deepcopy(_TYPE_DEFAULTS[definition.type])

    def validate(self, name: str, value: FieldType) -> None:
        """Validate a field value against its manifest definition using JSON Schema.

        Raises:
            FieldValidationError: If the value is invalid.
        """
        definition = self.get_definition(name)
        schema = build_type_schema(definition)
        try:
            # TODO this validates the schema in addition to the value. For
            # faster validation, we should use
            # jsonschema.protocols.Validator.validate
            jsonschema.validate(value, schema)
        except jsonschema.ValidationError as e:
            raise FieldValidationError(
                f"Field '{name}' failed validation: {e.message}"
            ) from e

    def validate_property(self, name: str, key: str, value: FieldType) -> None:
        """Validate a single property value against its type schema, if declared."""
        definition = self.get_definition(name)
        if isinstance(definition, ObjectField) and key in definition.properties:
            prop_schema = build_type_schema(definition.properties[key].root)
            try:
                jsonschema.validate(value, prop_schema)
            except jsonschema.ValidationError as e:
                raise FieldValidationError(
                    f"Field '{name}', key '{key}' failed validation: {e.message}"
                ) from e

    def require_object_type(self, name: str) -> None:
        """Raise if the field is not of type 'object'."""
        definition = self.get_definition(name)
        if not isinstance(definition, ObjectField):
            raise FieldValidationError(
                f"Field '{name}' is of type '{definition.type}', expected 'object'"
            )

    def require_log_type(self, name: str) -> None:
        """Raise if the field is not of type 'log'."""
        definition = self.get_definition(name)
        if not isinstance(definition, LogField):
            raise FieldValidationError(
                f"Field '{name}' is of type '{definition.type}', expected 'log'"
            )

    def validate_log_item(self, name: str, value: FieldType) -> None:
        """Validate a single item value against the log's items schema.

        Raises:
            FieldValidationError: If the value is invalid.
        """
        definition = self.get_definition(name)
        assert isinstance(definition, LogField)
        schema = build_type_schema(definition)
        try:
            jsonschema.validate(value, schema)
        except jsonschema.ValidationError as e:
            raise FieldValidationError(
                f"Log field '{name}' item failed validation: {e.message}"
            ) from e

    def get_scope(self, name: str) -> Scope:
        """Get the scope of a declared field."""
        return self.get_definition(name).scope

    def is_user_scoped(self, name: str) -> bool:
        """Check if a field is user-scoped."""
        return self.get_scope(name) in (
            Scope.user_activity,
            Scope.user_course,
            Scope.user_global,
        )
