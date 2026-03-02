"""Stream validation."""

from typing import Any

import jsonschema

from server.activities.fields import build_type_schema
from server.activities.manifest_types import Scope, StreamDefinition

__all__ = [
    "StreamChecker",
    "StreamValidationError",
]


class StreamValidationError(Exception):
    """Raised when a stream validation fails."""


class StreamChecker:
    """Validates streams against their manifest definitions."""

    def __init__(self, streams: dict[str, StreamDefinition] | None) -> None:
        self._definitions = streams or {}

    @property
    def stream_names(self) -> list[str]:
        """Return the list of declared stream names."""
        return list(self._definitions.keys())

    def get_definition(self, name: str) -> StreamDefinition:
        """Get the definition for a stream.

        Raises:
            StreamValidationError: If the stream is not declared.
        """
        if name not in self._definitions:
            raise StreamValidationError(
                f"Stream '{name}' not declared in manifest. "
                f"Declared: {self.stream_names}"
            )
        return self._definitions[name]

    def get_scope(self, name: str) -> Scope:
        """Get the scope of a declared stream."""
        return self.get_definition(name).scope

    def validate_item(self, name: str, value: Any) -> None:
        """Validate a stream item against its declared schema.

        Raises:
            StreamValidationError: If the value is invalid.
        """
        definition = self.get_definition(name)
        schema = build_type_schema(definition.items)
        try:
            jsonschema.validate(value, schema)
        except jsonschema.ValidationError as e:
            raise StreamValidationError(
                f"Stream '{name}' item failed validation: {e.message}"
            ) from e
