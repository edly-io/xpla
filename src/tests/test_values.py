import pytest
from server.activities.values import ValueChecker, ValueValidationError
from server.activities.manifest_types import (
    Scope,
    Type,
    TypeSchema,
    ValueDefinition,
)


class TestValueChecker:
    """Tests for ValueChecker class."""

    def test_empty_values(self) -> None:
        """Should handle None values."""
        checker = ValueChecker(None)
        assert not checker.value_names

    def test_with_values(self) -> None:
        """Should parse all value definitions."""
        values = {
            "score": ValueDefinition(type=Type.integer, scope=Scope.user_unit),
            "attempts": ValueDefinition(
                type=Type.integer, scope=Scope.user_unit, default=0
            ),
        }
        checker = ValueChecker(values)
        assert sorted(checker.value_names) == ["attempts", "score"]

    def test_get_definition_exists(self) -> None:
        """Should return definition for declared value."""
        values = {
            "score": ValueDefinition(
                type=Type.integer,
                scope=Scope.user_unit,
                default=10,
            )
        }
        checker = ValueChecker(values)
        definition = checker.get_definition("score")
        assert definition.type == Type.integer
        assert definition.scope == Scope.user_unit
        assert definition.default == 10

    def test_get_definition_not_declared(self) -> None:
        """Should raise for undeclared value."""
        values = {"score": ValueDefinition(type=Type.integer, scope=Scope.unit)}
        checker = ValueChecker(values)
        with pytest.raises(ValueValidationError, match="not declared"):
            checker.get_definition("unknown")

    def test_get_default_with_default(self) -> None:
        """Should return default value when defined."""
        values = {
            "score": ValueDefinition(type=Type.integer, scope=Scope.unit, default=100)
        }
        checker = ValueChecker(values)
        assert checker.get_default("score") == 100

    def test_get_default_without_default(self) -> None:
        """Should return type-specific default when no explicit default defined."""
        values = {
            "count": ValueDefinition(type=Type.integer, scope=Scope.unit),
            "ratio": ValueDefinition(type=Type.number, scope=Scope.unit),
            "name": ValueDefinition(type=Type.string, scope=Scope.unit),
            "enabled": ValueDefinition(type=Type.boolean, scope=Scope.unit),
        }
        checker = ValueChecker(values)
        assert checker.get_default("count") == 0
        assert checker.get_default("ratio") == 0.0
        assert checker.get_default("name") == ""
        assert checker.get_default("enabled") is False

    def test_validate_passes(self) -> None:
        """Should pass validation for valid value."""
        values = {
            "score": ValueDefinition(
                type=Type.integer,
                scope=Scope.user_unit,
                default=0,
            )
        }
        checker = ValueChecker(values)
        checker.validate("score", 50)  # Should not raise

    def test_validate_fails_type(self) -> None:
        """Should fail validation for wrong type."""
        values = {"score": ValueDefinition(type=Type.integer, scope=Scope.unit)}
        checker = ValueChecker(values)
        with pytest.raises(ValueValidationError, match="failed validation"):
            checker.validate("score", "not an int")

    def test_is_user_scoped(self) -> None:
        """Should correctly identify user-scoped values."""
        values = {
            "score": ValueDefinition(type=Type.integer, scope=Scope.user_unit),
            "question": ValueDefinition(type=Type.string, scope=Scope.unit),
            "course_score": ValueDefinition(type=Type.integer, scope=Scope.user_course),
            "course_data": ValueDefinition(type=Type.string, scope=Scope.course),
            "global_score": ValueDefinition(
                type=Type.integer, scope=Scope.user_platform
            ),
            "global_data": ValueDefinition(type=Type.string, scope=Scope.platform),
        }
        checker = ValueChecker(values)
        assert checker.is_user_scoped("score") is True
        assert checker.is_user_scoped("question") is False
        assert checker.is_user_scoped("course_score") is True
        assert checker.is_user_scoped("course_data") is False
        assert checker.is_user_scoped("global_score") is True
        assert checker.is_user_scoped("global_data") is False

    def test_get_scope(self) -> None:
        """Should return the scope of a declared value."""
        values = {
            "a": ValueDefinition(type=Type.integer, scope=Scope.unit),
            "b": ValueDefinition(type=Type.integer, scope=Scope.user_unit),
            "c": ValueDefinition(type=Type.integer, scope=Scope.course),
            "d": ValueDefinition(type=Type.integer, scope=Scope.user_course),
            "e": ValueDefinition(type=Type.integer, scope=Scope.platform),
            "f": ValueDefinition(type=Type.integer, scope=Scope.user_platform),
        }
        checker = ValueChecker(values)
        assert checker.get_scope("a") == Scope.unit
        assert checker.get_scope("b") == Scope.user_unit
        assert checker.get_scope("c") == Scope.course
        assert checker.get_scope("d") == Scope.user_course
        assert checker.get_scope("e") == Scope.platform
        assert checker.get_scope("f") == Scope.user_platform

    def test_user_value_names(self) -> None:
        """Should return only user-scoped value names."""
        values = {
            "score": ValueDefinition(type=Type.integer, scope=Scope.user_unit),
            "attempts": ValueDefinition(type=Type.integer, scope=Scope.user_unit),
            "question": ValueDefinition(type=Type.string, scope=Scope.unit),
        }
        checker = ValueChecker(values)
        assert sorted(checker.user_value_names()) == ["attempts", "score"]

    def test_shared_value_names(self) -> None:
        """Should return only shared (non-user-scoped) value names."""
        values = {
            "score": ValueDefinition(type=Type.integer, scope=Scope.user_unit),
            "question": ValueDefinition(type=Type.string, scope=Scope.unit),
            "answers": ValueDefinition(type=Type.string, scope=Scope.unit),
        }
        checker = ValueChecker(values)
        assert sorted(checker.shared_value_names()) == ["answers", "question"]

    def test_get_default_array(self) -> None:
        """Should return empty list as default for array type."""
        values = {
            "items": ValueDefinition(
                type=Type.array,
                items=TypeSchema(type=Type.string),
                scope=Scope.unit,
            )
        }
        checker = ValueChecker(values)
        assert checker.get_default("items") == []

    def test_get_default_object(self) -> None:
        """Should return empty dict as default for object type."""
        values = {"data": ValueDefinition(type=Type.object, scope=Scope.unit)}
        checker = ValueChecker(values)
        assert checker.get_default("data") == {}

    def test_validate_array(self) -> None:
        """Should validate array values."""
        values = {
            "tags": ValueDefinition(
                type=Type.array,
                items=TypeSchema(type=Type.string),
                scope=Scope.unit,
            )
        }
        checker = ValueChecker(values)
        checker.validate("tags", ["a", "b", "c"])  # Should not raise

    def test_validate_array_rejects_wrong_items(self) -> None:
        """Should reject array with wrong item types."""
        values = {
            "tags": ValueDefinition(
                type=Type.array,
                items=TypeSchema(type=Type.string),
                scope=Scope.unit,
            )
        }
        checker = ValueChecker(values)
        with pytest.raises(ValueValidationError, match="failed validation"):
            checker.validate("tags", [1, 2, 3])

    def test_validate_array_rejects_non_array(self) -> None:
        """Should reject non-array value for array type."""
        values = {
            "tags": ValueDefinition(
                type=Type.array,
                items=TypeSchema(type=Type.string),
                scope=Scope.unit,
            )
        }
        checker = ValueChecker(values)
        with pytest.raises(ValueValidationError, match="failed validation"):
            checker.validate("tags", "not an array")

    def test_validate_object(self) -> None:
        """Should validate object values."""
        values = {
            "config": ValueDefinition(
                type=Type.object,
                properties={"name": TypeSchema(type=Type.string)},
                scope=Scope.unit,
            )
        }
        checker = ValueChecker(values)
        checker.validate("config", {"name": "test"})  # Should not raise
