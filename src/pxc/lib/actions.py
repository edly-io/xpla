"""Action validation against manifest declarations."""

from typing import Any

import jsonschema

from pxc.lib.fields import build_type_schema
from pxc.lib.manifest_types import TypeSchema

__all__ = [
    "ActionChecker",
    "ActionValidationError",
]


class ActionValidationError(Exception):
    """Raised when an action validation fails."""


class ActionChecker:
    """Validates actions against their manifest declarations."""

    def __init__(self, actions: dict[str, TypeSchema] | None) -> None:
        self._definitions = actions or {}

    def validate(self, name: str, payload: Any) -> None:
        """Validate an action name and payload against the manifest.

        Raises:
            ActionValidationError: If the action is not declared or payload is invalid.
        """
        if name not in self._definitions:
            raise ActionValidationError(
                f"Action '{name}' not declared in manifest. "
                f"Declared: {sorted(self._definitions.keys())}"
            )
        schema = build_type_schema(self._definitions[name].root)
        try:
            jsonschema.validate(payload, schema)
        except jsonschema.ValidationError as e:
            raise ActionValidationError(
                f"Action '{name}' payload failed validation: {e.message}"
            ) from e
