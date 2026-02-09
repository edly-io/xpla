import pytest
from server.activities.capabilities import (
    Access,
    CapabilityChecker,
    CapabilityError,
    ValueChecker,
    ValueValidationError,
)
from server.activities.manifest_types import (
    Capabilities,
    Http,
    Scope,
    Type,
    TypeSchema,
    ValueDefinition,
)


class TestCapabilityChecker:
    """Tests for CapabilityChecker."""

    def test_http_host_enforcement(self) -> None:
        """Should enforce HTTP allowed hosts."""
        caps = Capabilities(http=Http(allowed_hosts=["api.example.com"]))
        checker = CapabilityChecker(caps)

        # Should allow whitelisted host
        checker.check_http_request("https://api.example.com/data")

        # Should reject other hosts
        with pytest.raises(CapabilityError, match="not allowed"):
            checker.check_http_request("https://evil.com/hack")

    def test_missing_capability_rejected(self) -> None:
        """Should reject operations when capability not declared."""
        checker = CapabilityChecker(None)

        with pytest.raises(CapabilityError, match="http capability not declared"):
            checker.check_http_request("https://example.com")

    def test_empty_capabilities_rejected(self) -> None:
        """Should reject operations when capabilities object has no relevant field."""
        caps = Capabilities()
        checker = CapabilityChecker(caps)

        with pytest.raises(CapabilityError, match="http capability not declared"):
            checker.check_http_request("https://example.com")


class TestValueChecker:
    """Tests for ValueChecker class."""

    def test_empty_values(self) -> None:
        """Should handle None values."""
        checker = ValueChecker(None)
        assert not checker.value_names

    def test_with_values(self) -> None:
        """Should parse all value definitions."""
        values = {
            "score": ValueDefinition(
                type=Type.integer, scope=Scope.user_unit, access=Access.user
            ),
            "attempts": ValueDefinition(
                type=Type.integer, scope=Scope.user_unit, access=Access.user, default=0
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
                access=Access.user,
                default=10,
            )
        }
        checker = ValueChecker(values)
        definition = checker.get_definition("score")
        assert definition.type == Type.integer
        assert definition.scope == Scope.user_unit
        assert definition.access == Access.user
        assert definition.default == 10

    def test_get_definition_not_declared(self) -> None:
        """Should raise for undeclared value."""
        values = {
            "score": ValueDefinition(
                type=Type.integer, scope=Scope.unit, access=Access.user
            )
        }
        checker = ValueChecker(values)
        with pytest.raises(ValueValidationError, match="not declared"):
            checker.get_definition("unknown")

    def test_get_default_with_default(self) -> None:
        """Should return default value when defined."""
        values = {
            "score": ValueDefinition(
                type=Type.integer, scope=Scope.unit, access=Access.user, default=100
            )
        }
        checker = ValueChecker(values)
        assert checker.get_default("score") == 100

    def test_get_default_without_default(self) -> None:
        """Should return type-specific default when no explicit default defined."""
        values = {
            "count": ValueDefinition(
                type=Type.integer, scope=Scope.unit, access=Access.user
            ),
            "ratio": ValueDefinition(
                type=Type.number, scope=Scope.unit, access=Access.user
            ),
            "name": ValueDefinition(
                type=Type.string, scope=Scope.unit, access=Access.user
            ),
            "enabled": ValueDefinition(
                type=Type.boolean, scope=Scope.unit, access=Access.user
            ),
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
                access=Access.user,
                default=0,
            )
        }
        checker = ValueChecker(values)
        checker.validate("score", 50)  # Should not raise

    def test_validate_fails_type(self) -> None:
        """Should fail validation for wrong type."""
        values = {
            "score": ValueDefinition(
                type=Type.integer, scope=Scope.unit, access=Access.user
            )
        }
        checker = ValueChecker(values)
        with pytest.raises(ValueValidationError, match="failed validation"):
            checker.validate("score", "not an int")

    def test_is_user_scoped(self) -> None:
        """Should correctly identify user-scoped values."""
        values = {
            "score": ValueDefinition(
                type=Type.integer, scope=Scope.user_unit, access=Access.user
            ),
            "question": ValueDefinition(
                type=Type.string, scope=Scope.unit, access=Access.user
            ),
        }
        checker = ValueChecker(values)
        assert checker.is_user_scoped("score") is True
        assert checker.is_user_scoped("question") is False

    def test_user_value_names(self) -> None:
        """Should return only user-scoped value names."""
        values = {
            "score": ValueDefinition(
                type=Type.integer, scope=Scope.user_unit, access=Access.user
            ),
            "attempts": ValueDefinition(
                type=Type.integer, scope=Scope.user_unit, access=Access.user
            ),
            "question": ValueDefinition(
                type=Type.string, scope=Scope.unit, access=Access.user
            ),
        }
        checker = ValueChecker(values)
        assert sorted(checker.user_value_names()) == ["attempts", "score"]

    def test_shared_value_names(self) -> None:
        """Should return only shared (non-user-scoped) value names."""
        values = {
            "score": ValueDefinition(
                type=Type.integer, scope=Scope.user_unit, access=Access.user
            ),
            "question": ValueDefinition(
                type=Type.string, scope=Scope.unit, access=Access.user
            ),
            "answers": ValueDefinition(
                type=Type.string, scope=Scope.unit, access=Access.user
            ),
        }
        checker = ValueChecker(values)
        assert sorted(checker.shared_value_names()) == ["answers", "question"]

    def test_get_access_level(self) -> None:
        """Should return the access level for a value."""
        values = {
            "public": ValueDefinition(
                type=Type.string, scope=Scope.unit, access=Access.user
            ),
            "secret": ValueDefinition(
                type=Type.string, scope=Scope.unit, access=Access.unit
            ),
        }
        checker = ValueChecker(values)
        assert checker.get_access_level("public") == Access.user
        assert checker.get_access_level("secret") == Access.unit

    def test_can_access_same_level(self) -> None:
        """User can access values at their own level."""
        values = {
            "val": ValueDefinition(
                type=Type.string, scope=Scope.unit, access=Access.unit
            )
        }
        checker = ValueChecker(values)
        assert checker.can_access("val", Access.unit) is True

    def test_can_access_higher_level(self) -> None:
        """User with higher access can see lower-level values."""
        values = {
            "val": ValueDefinition(
                type=Type.string, scope=Scope.unit, access=Access.user
            )
        }
        checker = ValueChecker(values)
        assert checker.can_access("val", Access.unit) is True
        assert checker.can_access("val", Access.course) is True
        assert checker.can_access("val", Access.platform) is True

    def test_cannot_access_lower_level(self) -> None:
        """User with lower access cannot see higher-level values."""
        values = {
            "val": ValueDefinition(
                type=Type.string, scope=Scope.unit, access=Access.unit
            )
        }
        checker = ValueChecker(values)
        assert checker.can_access("val", Access.user) is False

    def test_access_hierarchy(self) -> None:
        """Test the full access hierarchy."""
        values = {
            "user_val": ValueDefinition(
                type=Type.string, scope=Scope.unit, access=Access.user
            ),
            "unit_val": ValueDefinition(
                type=Type.string, scope=Scope.unit, access=Access.unit
            ),
            "course_val": ValueDefinition(
                type=Type.string, scope=Scope.unit, access=Access.course
            ),
            "platform_val": ValueDefinition(
                type=Type.string, scope=Scope.unit, access=Access.platform
            ),
        }
        checker = ValueChecker(values)

        # User can only access user-level
        assert checker.can_access("user_val", Access.user) is True
        assert checker.can_access("unit_val", Access.user) is False
        assert checker.can_access("course_val", Access.user) is False
        assert checker.can_access("platform_val", Access.user) is False

        # Unit can access user and unit level
        assert checker.can_access("user_val", Access.unit) is True
        assert checker.can_access("unit_val", Access.unit) is True
        assert checker.can_access("course_val", Access.unit) is False
        assert checker.can_access("platform_val", Access.unit) is False

        # Platform can access all levels
        assert checker.can_access("user_val", Access.platform) is True
        assert checker.can_access("unit_val", Access.platform) is True
        assert checker.can_access("course_val", Access.platform) is True
        assert checker.can_access("platform_val", Access.platform) is True

    def test_get_default_array(self) -> None:
        """Should return empty list as default for array type."""
        values = {
            "items": ValueDefinition(
                type=Type.array,
                items=TypeSchema(type=Type.string),
                scope=Scope.unit,
                access=Access.user,
            )
        }
        checker = ValueChecker(values)
        assert checker.get_default("items") == []

    def test_get_default_object(self) -> None:
        """Should return empty dict as default for object type."""
        values = {
            "data": ValueDefinition(
                type=Type.object, scope=Scope.unit, access=Access.user
            )
        }
        checker = ValueChecker(values)
        assert checker.get_default("data") == {}

    def test_validate_array(self) -> None:
        """Should validate array values."""
        values = {
            "tags": ValueDefinition(
                type=Type.array,
                items=TypeSchema(type=Type.string),
                scope=Scope.unit,
                access=Access.user,
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
                access=Access.user,
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
                access=Access.user,
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
                access=Access.user,
            )
        }
        checker = ValueChecker(values)
        checker.validate("config", {"name": "test"})  # Should not raise
