import pytest
from pxc.lib.actions import ActionChecker, ActionValidationError
from pxc.lib.manifest_types import TypeSchema


def type_schema(**kwargs: object) -> TypeSchema:
    """Helper to build a TypeSchema from keyword args."""
    return TypeSchema.model_validate(kwargs)


class TestActionChecker:
    """Tests for ActionChecker."""

    def test_raises_for_undeclared_action(self) -> None:
        """Should raise ActionValidationError for undeclared action."""
        checker = ActionChecker(None)
        with pytest.raises(ActionValidationError, match="not declared"):
            checker.validate("unknown", {})

    def test_raises_for_invalid_payload(self) -> None:
        """Should raise ActionValidationError for invalid payload."""
        checker = ActionChecker(
            {"my.action": type_schema(type="object", properties={})}
        )
        with pytest.raises(ActionValidationError, match="failed validation"):
            checker.validate("my.action", "not an object")

    def test_valid_action_passes(self) -> None:
        """Should not raise for valid action with matching payload."""
        checker = ActionChecker(
            {
                "my.action": type_schema(
                    type="object", properties={"key": {"type": "string"}}
                )
            }
        )
        checker.validate("my.action", {"key": "value"})
