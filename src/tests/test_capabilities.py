import pytest
from server.activities.capabilities import (
    CapabilityChecker,
    CapabilityError,
    Manifest,
    ValueChecker,
    ValueValidationError,
    parse_capabilities,
    parse_value_definition,
    validate_value,
)


class TestCapabilities:
    """Tests for capability enforcement."""

    def test_capabilities_parsing(self) -> None:
        """Should parse capabilities from manifest."""

        manifest: Manifest = {
            "name": "test",
            "capabilities": {
                "kv": {"namespace": "test", "max_bytes": 1024},
                "http": {"allowed_hosts": ["api.example.com"]},
                "lms": ["get_user"],
            },
        }
        caps = parse_capabilities(manifest)
        assert caps.kv_enabled is True
        assert caps.kv_namespace == "test"
        assert caps.http_enabled is True
        assert "api.example.com" in caps.http_allowed_hosts
        assert caps.lms_enabled is True
        assert "get_user" in caps.lms_allowed_functions

    def test_kv_namespace_enforcement(self) -> None:
        """Should enforce KV namespace prefix."""
        manifest: Manifest = {
            "name": "test",
            "capabilities": {"kv": {"namespace": "test"}},
        }
        checker = CapabilityChecker.load_from_manifest(manifest)

        # Should allow keys with correct namespace
        checker.check_kv_write("test:mykey", "value")

        # Should reject keys without namespace prefix
        with pytest.raises(CapabilityError, match="namespace prefix"):
            checker.check_kv_write("wrongkey", "value")

    def test_http_host_enforcement(self) -> None:
        """Should enforce HTTP allowed hosts."""
        manifest: Manifest = {
            "name": "test",
            "capabilities": {"http": {"allowed_hosts": ["api.example.com"]}},
        }
        checker = CapabilityChecker.load_from_manifest(manifest)

        # Should allow whitelisted host
        checker.check_http_request("https://api.example.com/data")

        # Should reject other hosts
        with pytest.raises(CapabilityError, match="not allowed"):
            checker.check_http_request("https://evil.com/hack")

    def test_lms_function_enforcement(self) -> None:
        """Should enforce LMS allowed functions."""
        manifest: Manifest = {
            "name": "test",
            "capabilities": {"lms": ["get_user"]},
        }
        checker = CapabilityChecker.load_from_manifest(manifest)

        # Should allow whitelisted function
        checker.check_lms_function("get_user")

        # Should reject other functions
        with pytest.raises(CapabilityError, match="not allowed"):
            checker.check_lms_function("submit_grade")

    def test_missing_capability_rejected(self) -> None:
        """Should reject operations when capability not declared."""
        manifest: Manifest = {"name": "test", "capabilities": {}}
        checker = CapabilityChecker.load_from_manifest(manifest)

        with pytest.raises(CapabilityError, match="kv capability not declared"):
            checker.check_kv_access()

        with pytest.raises(CapabilityError, match="http capability not declared"):
            checker.check_http_request("https://example.com")

        with pytest.raises(CapabilityError, match="lms capability not declared"):
            checker.check_lms_function("get_user")


class TestParseValueDefinition:
    """Tests for parse_value_definition function."""

    def test_shorthand_string_type(self) -> None:
        """Should convert string shorthand to full definition."""
        result = parse_value_definition("score", "integer")
        assert result["type"] == "integer"

    def test_full_definition_preserved(self) -> None:
        """Should preserve full definition with all fields."""
        definition = {"type": "integer", "default": 0, "min": 0, "max": 100}
        result = parse_value_definition("score", definition)
        assert result["type"] == "integer"
        assert result["default"] == 0
        assert result["min"] == 0
        assert result["max"] == 100

    def test_invalid_shorthand_type_raises(self) -> None:
        """Should raise for invalid type in shorthand form."""
        with pytest.raises(ValueValidationError, match="Invalid type 'invalid'"):
            parse_value_definition("score", "invalid")

    def test_invalid_full_type_raises(self) -> None:
        """Should raise for invalid type in full definition."""
        with pytest.raises(ValueValidationError, match="Invalid type 'badtype'"):
            parse_value_definition("score", {"type": "badtype"})

    def test_all_valid_types(self) -> None:
        """Should accept all valid type names."""
        for type_name in ("integer", "float", "string", "boolean"):
            result = parse_value_definition("test", type_name)
            assert result["type"] == type_name


class TestValidateValue:
    """Tests for validate_value function."""

    def test_integer_accepts_int(self) -> None:
        """Should accept int for integer type."""
        validate_value("count", 42, {"type": "integer"})

    def test_integer_rejects_float(self) -> None:
        """Should reject float for integer type."""
        with pytest.raises(ValueValidationError, match="must be integer"):
            validate_value("count", 3.14, {"type": "integer"})

    def test_integer_rejects_string(self) -> None:
        """Should reject string for integer type."""
        with pytest.raises(ValueValidationError, match="must be integer"):
            validate_value("count", "42", {"type": "integer"})

    def test_float_accepts_float(self) -> None:
        """Should accept float for float type."""
        validate_value("ratio", 3.14, {"type": "float"})

    def test_float_accepts_int(self) -> None:
        """Should accept int for float type (int is valid float)."""
        validate_value("ratio", 42, {"type": "float"})

    def test_string_accepts_string(self) -> None:
        """Should accept string for string type."""
        validate_value("name", "hello", {"type": "string"})

    def test_string_rejects_int(self) -> None:
        """Should reject int for string type."""
        with pytest.raises(ValueValidationError, match="must be string"):
            validate_value("name", 42, {"type": "string"})

    def test_boolean_accepts_bool(self) -> None:
        """Should accept bool for boolean type."""
        validate_value("enabled", True, {"type": "boolean"})
        validate_value("enabled", False, {"type": "boolean"})

    def test_boolean_rejects_int(self) -> None:
        """Should reject int for boolean type (even 0/1)."""
        with pytest.raises(ValueValidationError, match="must be boolean"):
            validate_value("enabled", 1, {"type": "boolean"})

    def test_min_constraint_passes(self) -> None:
        """Should accept value at or above min."""
        validate_value("score", 0, {"type": "integer", "min": 0})
        validate_value("score", 10, {"type": "integer", "min": 0})

    def test_min_constraint_fails(self) -> None:
        """Should reject value below min."""
        with pytest.raises(ValueValidationError, match="must be >= 0"):
            validate_value("score", -1, {"type": "integer", "min": 0})

    def test_max_constraint_passes(self) -> None:
        """Should accept value at or below max."""
        validate_value("score", 100, {"type": "integer", "max": 100})
        validate_value("score", 50, {"type": "integer", "max": 100})

    def test_max_constraint_fails(self) -> None:
        """Should reject value above max."""
        with pytest.raises(ValueValidationError, match="must be <= 100"):
            validate_value("score", 101, {"type": "integer", "max": 100})

    def test_min_max_combined(self) -> None:
        """Should enforce both min and max constraints."""
        definition = {"type": "integer", "min": 0, "max": 100}
        validate_value("score", 50, definition)
        with pytest.raises(ValueValidationError):
            validate_value("score", -1, definition)
        with pytest.raises(ValueValidationError):
            validate_value("score", 101, definition)


class TestValueChecker:
    """Tests for ValueChecker class."""

    def test_load_from_manifest_empty(self) -> None:
        """Should handle manifest with no values."""
        manifest: Manifest = {"name": "test"}
        checker = ValueChecker.load_from_manifest(manifest)
        assert checker.value_names == []

    def test_load_from_manifest_with_values(self) -> None:
        """Should parse all value definitions from manifest."""
        manifest: Manifest = {
            "name": "test",
            "values": {
                "score": "integer",
                "attempts": {"type": "integer", "default": 0},
            },
        }
        checker = ValueChecker.load_from_manifest(manifest)
        assert sorted(checker.value_names) == ["attempts", "score"]

    def test_get_definition_exists(self) -> None:
        """Should return definition for declared value."""
        manifest: Manifest = {
            "name": "test",
            "values": {"score": {"type": "integer", "min": 0}},
        }
        checker = ValueChecker.load_from_manifest(manifest)
        definition = checker.get_definition("score")
        assert definition["type"] == "integer"
        assert definition["min"] == 0

    def test_get_definition_not_declared(self) -> None:
        """Should raise for undeclared value."""
        manifest: Manifest = {"name": "test", "values": {"score": "integer"}}
        checker = ValueChecker.load_from_manifest(manifest)
        with pytest.raises(ValueValidationError, match="not declared"):
            checker.get_definition("unknown")

    def test_get_default_with_default(self) -> None:
        """Should return default value when defined."""
        manifest: Manifest = {
            "name": "test",
            "values": {"score": {"type": "integer", "default": 100}},
        }
        checker = ValueChecker.load_from_manifest(manifest)
        assert checker.get_default("score") == 100

    def test_get_default_without_default(self) -> None:
        """Should return None when no default defined."""
        manifest: Manifest = {"name": "test", "values": {"score": "integer"}}
        checker = ValueChecker.load_from_manifest(manifest)
        assert checker.get_default("score") is None

    def test_validate_passes(self) -> None:
        """Should pass validation for valid value."""
        manifest: Manifest = {
            "name": "test",
            "values": {"score": {"type": "integer", "min": 0, "max": 100}},
        }
        checker = ValueChecker.load_from_manifest(manifest)
        checker.validate("score", 50)  # Should not raise

    def test_validate_fails_type(self) -> None:
        """Should fail validation for wrong type."""
        manifest: Manifest = {"name": "test", "values": {"score": "integer"}}
        checker = ValueChecker.load_from_manifest(manifest)
        with pytest.raises(ValueValidationError, match="must be integer"):
            checker.validate("score", "not an int")

    def test_validate_fails_constraint(self) -> None:
        """Should fail validation for constraint violation."""
        manifest: Manifest = {
            "name": "test",
            "values": {"score": {"type": "integer", "min": 0}},
        }
        checker = ValueChecker.load_from_manifest(manifest)
        with pytest.raises(ValueValidationError, match="must be >= 0"):
            checker.validate("score", -5)
