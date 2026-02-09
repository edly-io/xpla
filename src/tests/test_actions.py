import pytest
from server.activities.actions import ActionChecker, ActionValidationError
from server.activities.manifest_types import Type, TypeSchema


class TestActionChecker:
    """Tests for ActionChecker."""

    def test_raises_for_undeclared_action(self) -> None:
        """Should raise ActionValidationError for undeclared action."""
        checker = ActionChecker(None)
        with pytest.raises(ActionValidationError, match="not declared"):
            checker.validate("unknown", {})

    def test_raises_for_invalid_payload(self) -> None:
        """Should raise ActionValidationError for invalid payload."""
        checker = ActionChecker({"my.action": TypeSchema(type=Type.object)})
        with pytest.raises(ActionValidationError, match="failed validation"):
            checker.validate("my.action", "not an object")

    def test_valid_action_passes(self) -> None:
        """Should not raise for valid action with matching payload."""
        checker = ActionChecker({"my.action": TypeSchema(type=Type.object)})
        checker.validate("my.action", {"key": "value"})
