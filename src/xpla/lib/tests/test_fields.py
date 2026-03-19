import pytest
from pydantic import ValidationError

from xpla.lib.fields import FieldChecker, FieldValidationError
from xpla.lib.manifest_types import (
    Scope,
    FieldDefinition,
)


def field(**kwargs: object) -> FieldDefinition:
    """Helper to build a FieldDefinition from keyword args."""
    return FieldDefinition.model_validate(kwargs)


class TestFieldChecker:
    """Tests for FieldChecker class."""

    def test_empty_fields(self) -> None:
        """Should handle None fields."""
        checker = FieldChecker(None)
        assert not checker.field_names

    def test_with_fields(self) -> None:
        """Should parse all field definitions."""
        fields = {
            "score": field(type="integer", scope=Scope.user_activity),
            "attempts": field(type="integer", scope=Scope.user_activity, default=0),
        }
        checker = FieldChecker(fields)
        assert sorted(checker.field_names) == ["attempts", "score"]

    def test_get_definition_exists(self) -> None:
        """Should return definition for declared field."""
        fields = {"score": field(type="integer", scope=Scope.user_activity, default=10)}
        checker = FieldChecker(fields)
        definition = checker.get_definition("score")
        assert definition.type == "integer"
        assert definition.scope == Scope.user_activity
        assert definition.default == 10

    def test_get_definition_not_declared(self) -> None:
        """Should raise for undeclared field."""
        fields = {"score": field(type="integer", scope=Scope.activity)}
        checker = FieldChecker(fields)
        with pytest.raises(FieldValidationError, match="not declared"):
            checker.get_definition("unknown")

    def test_get_default_with_default(self) -> None:
        """Should return default value when defined."""
        fields = {"score": field(type="integer", scope=Scope.activity, default=100)}
        checker = FieldChecker(fields)
        assert checker.get_default("score") == 100

    def test_get_default_without_default(self) -> None:
        """Should return type-specific default when no explicit default defined."""
        fields = {
            "count": field(type="integer", scope=Scope.activity),
            "ratio": field(type="number", scope=Scope.activity),
            "name": field(type="string", scope=Scope.activity),
            "enabled": field(type="boolean", scope=Scope.activity),
        }
        checker = FieldChecker(fields)
        assert checker.get_default("count") == 0
        assert checker.get_default("ratio") == 0.0
        assert checker.get_default("name") == ""
        assert checker.get_default("enabled") is False

    def test_validate_passes(self) -> None:
        """Should pass validation for valid value."""
        fields = {"score": field(type="integer", scope=Scope.user_activity, default=0)}
        checker = FieldChecker(fields)
        checker.validate("score", 50)  # Should not raise

    def test_validate_fails_type(self) -> None:
        """Should fail validation for wrong type."""
        fields = {"score": field(type="integer", scope=Scope.activity)}
        checker = FieldChecker(fields)
        with pytest.raises(FieldValidationError, match="failed validation"):
            checker.validate("score", "not an int")

    def test_is_user_scoped(self) -> None:
        """Should correctly identify user-scoped fields."""
        fields = {
            "score": field(type="integer", scope=Scope.user_activity),
            "question": field(type="string", scope=Scope.activity),
            "course_score": field(type="integer", scope=Scope.user_course),
            "course_data": field(type="string", scope=Scope.course),
            "global_score": field(type="integer", scope=Scope.user_global),
            "global_data": field(type="string", scope=Scope.global_),
        }
        checker = FieldChecker(fields)
        assert checker.is_user_scoped("score") is True
        assert checker.is_user_scoped("question") is False
        assert checker.is_user_scoped("course_score") is True
        assert checker.is_user_scoped("course_data") is False
        assert checker.is_user_scoped("global_score") is True
        assert checker.is_user_scoped("global_data") is False

    def test_get_scope(self) -> None:
        """Should return the scope of a declared field."""
        fields = {
            "a": field(type="integer", scope=Scope.activity),
            "b": field(type="integer", scope=Scope.user_activity),
            "c": field(type="integer", scope=Scope.course),
            "d": field(type="integer", scope=Scope.user_course),
            "e": field(type="integer", scope=Scope.global_),
            "f": field(type="integer", scope=Scope.user_global),
        }
        checker = FieldChecker(fields)
        assert checker.get_scope("a") == Scope.activity
        assert checker.get_scope("b") == Scope.user_activity
        assert checker.get_scope("c") == Scope.course
        assert checker.get_scope("d") == Scope.user_course
        assert checker.get_scope("e") == Scope.global_
        assert checker.get_scope("f") == Scope.user_global

    def test_get_default_array(self) -> None:
        """Should return empty list as default for array type."""
        fields = {
            "items": field(type="array", items={"type": "string"}, scope=Scope.activity)
        }
        checker = FieldChecker(fields)
        assert checker.get_default("items") == []

    def test_get_default_object(self) -> None:
        """Should return empty dict as default for object type."""
        fields = {
            "data": field(
                type="object",
                properties={"x": {"type": "integer"}},
                scope=Scope.activity,
            )
        }
        checker = FieldChecker(fields)
        assert checker.get_default("data") == {}

    def test_validate_array(self) -> None:
        """Should validate array values."""
        fields = {
            "tags": field(type="array", items={"type": "string"}, scope=Scope.activity)
        }
        checker = FieldChecker(fields)
        checker.validate("tags", ["a", "b", "c"])  # Should not raise

    def test_validate_array_rejects_wrong_items(self) -> None:
        """Should reject array with wrong item types."""
        fields = {
            "tags": field(type="array", items={"type": "string"}, scope=Scope.activity)
        }
        checker = FieldChecker(fields)
        with pytest.raises(FieldValidationError, match="failed validation"):
            checker.validate("tags", [1, 2, 3])

    def test_validate_array_rejects_non_array(self) -> None:
        """Should reject non-array value for array type."""
        fields = {
            "tags": field(type="array", items={"type": "string"}, scope=Scope.activity)
        }
        checker = FieldChecker(fields)
        with pytest.raises(FieldValidationError, match="failed validation"):
            checker.validate("tags", "not an array")

    def test_require_object_type_passes_for_object(self) -> None:
        """Should not raise for object-typed fields."""
        fields = {
            "data": field(
                type="object",
                properties={"x": {"type": "integer"}},
                scope=Scope.activity,
            )
        }
        checker = FieldChecker(fields)
        checker.require_object_type("data")  # Should not raise

    def test_require_object_type_raises_for_non_object(self) -> None:
        """Should raise FieldValidationError for non-object fields."""
        fields = {"count": field(type="integer", scope=Scope.activity)}
        checker = FieldChecker(fields)
        with pytest.raises(FieldValidationError, match="expected 'object'"):
            checker.require_object_type("count")

    def test_validate_property_passes_for_valid_value(self) -> None:
        """Should pass when value matches the property's type schema."""
        fields = {
            "config": field(
                type="object",
                properties={"name": {"type": "string"}},
                scope=Scope.activity,
            )
        }
        checker = FieldChecker(fields)
        checker.validate_property("config", "name", "hello")  # Should not raise

    def test_validate_property_raises_for_invalid_value(self) -> None:
        """Should raise when value does not match the property's type schema."""
        fields = {
            "config": field(
                type="object",
                properties={"name": {"type": "string"}},
                scope=Scope.activity,
            )
        }
        checker = FieldChecker(fields)
        with pytest.raises(FieldValidationError, match="key 'name' failed validation"):
            checker.validate_property("config", "name", 123)

    def test_validate_property_skips_undeclared_key(self) -> None:
        """Should not raise when key is not in declared properties."""
        fields = {
            "config": field(
                type="object",
                properties={"name": {"type": "string"}},
                scope=Scope.activity,
            )
        }
        checker = FieldChecker(fields)
        checker.validate_property("config", "unknown", 123)  # Should not raise

    def test_validate_object(self) -> None:
        """Should validate object values."""
        fields = {
            "config": field(
                type="object",
                properties={"name": {"type": "string"}},
                scope=Scope.activity,
            )
        }
        checker = FieldChecker(fields)
        checker.validate("config", {"name": "test"})  # Should not raise

    def test_array_field_rejects_properties(self) -> None:
        """Should reject an array field that has 'properties' (object-only attribute)."""
        with pytest.raises(ValidationError):
            field(
                type="array",
                scope="activity",
                items={"type": "integer"},
                properties={"x": {"type": "integer"}},
            )

    def test_log_field_accepted(self) -> None:
        """Should accept a log field definition."""
        fields = {
            "messages": field(
                type="log",
                items={"type": "string"},
                scope=Scope.activity,
            )
        }
        checker = FieldChecker(fields)
        assert "messages" in checker.field_names

    def test_require_log_type_passes_for_log(self) -> None:
        """Should not raise for log-typed fields."""
        fields = {
            "messages": field(
                type="log",
                items={"type": "string"},
                scope=Scope.activity,
            )
        }
        checker = FieldChecker(fields)
        checker.require_log_type("messages")  # Should not raise

    def test_require_log_type_raises_for_non_log(self) -> None:
        """Should raise FieldValidationError for non-log fields."""
        fields = {"count": field(type="integer", scope=Scope.activity)}
        checker = FieldChecker(fields)
        with pytest.raises(FieldValidationError, match="expected 'log'"):
            checker.require_log_type("count")

    def test_validate_log_item_passes(self) -> None:
        """Should pass for valid log item."""
        fields = {
            "messages": field(
                type="log",
                items={"type": "string"},
                scope=Scope.activity,
            )
        }
        checker = FieldChecker(fields)
        checker.validate_log_item("messages", "hello")  # Should not raise

    def test_validate_log_item_fails(self) -> None:
        """Should raise for invalid log item."""
        fields = {
            "messages": field(
                type="log",
                items={"type": "string"},
                scope=Scope.activity,
            )
        }
        checker = FieldChecker(fields)
        with pytest.raises(FieldValidationError, match="item failed validation"):
            checker.validate_log_item("messages", 123)

    def test_log_field_rejects_properties(self) -> None:
        """Should reject a log field that has 'properties' (object-only attribute)."""
        with pytest.raises(ValidationError):
            field(
                type="log",
                scope="activity",
                items={"type": "string"},
                properties={"x": {"type": "integer"}},
            )
