"""Event validation against manifest declarations."""

from typing import Any

import jsonschema

from server.activities.fields import build_type_schema
from server.activities.manifest_types import TypeSchema

__all__ = [
    "EventChecker",
    "EventValidationError",
]


class EventValidationError(Exception):
    """Raised when an event validation fails."""


class EventChecker:
    """Validates events against their manifest declarations."""

    def __init__(self, events: dict[str, TypeSchema] | None) -> None:
        self._definitions = events or {}

    def validate(self, name: str, payload: Any) -> None:
        """Validate an event name and payload against the manifest.

        Raises:
            EventValidationError: If the event is not declared or payload is invalid.
        """
        if name not in self._definitions:
            raise EventValidationError(
                f"Event '{name}' not declared in manifest. "
                f"Declared: {sorted(self._definitions.keys())}"
            )
        schema = build_type_schema(self._definitions[name])
        try:
            jsonschema.validate(payload, schema)
        except jsonschema.ValidationError as e:
            raise EventValidationError(
                f"Event '{name}' payload failed validation: {e.message}"
            ) from e
