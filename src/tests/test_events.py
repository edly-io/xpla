import pytest
from server.activities.events import EventChecker, EventValidationError
from server.activities.manifest_types import TypeSchema


def type_schema(**kwargs: object) -> TypeSchema:
    """Helper to build a TypeSchema from keyword args."""
    return TypeSchema.model_validate(kwargs)


class TestEventChecker:
    """Tests for EventChecker."""

    def test_raises_for_undeclared_event(self) -> None:
        """Should raise EventValidationError for undeclared event."""
        checker = EventChecker(None)
        with pytest.raises(EventValidationError, match="not declared"):
            checker.validate("unknown", {})

    def test_raises_for_invalid_payload(self) -> None:
        """Should raise EventValidationError for invalid payload."""
        checker = EventChecker({"my.event": type_schema(type="object", properties={})})
        with pytest.raises(EventValidationError, match="failed validation"):
            checker.validate("my.event", "not an object")

    def test_valid_event_passes(self) -> None:
        """Should not raise for valid event with matching payload."""
        checker = EventChecker({"my.event": type_schema(type="object", properties={})})
        checker.validate("my.event", {"key": "value"})

    def test_undeclared_values_change_rejected(self) -> None:
        """Should reject undeclared values.change.* events."""
        checker = EventChecker(None)
        with pytest.raises(EventValidationError, match="not declared"):
            checker.validate("values.change.score", 42)

    def test_declared_values_change_passes(self) -> None:
        """Should pass validation for declared values.change.* events."""
        checker = EventChecker({"values.change.score": type_schema(type="integer")})
        checker.validate("values.change.score", 42)
