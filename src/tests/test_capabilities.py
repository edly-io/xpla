import pytest
from server.activities.capabilities import (
    CapabilityChecker,
    CapabilityError,
    Manifest,
    ValueChecker,
    ValueDefinition,
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

    def test_valid_definition(self) -> None:
        """Should accept valid definition with type, scope and default."""
        definition: ValueDefinition = {
            "type": "integer",
            "scope": "user,unit",
            "default": 0,
        }
        result = parse_value_definition("score", definition)
        assert result["type"] == "integer"
        assert result["scope"] == "user,unit"
        assert result["default"] == 0

    def test_missing_type_raises(self) -> None:
        """Should raise when type field is missing."""
        with pytest.raises(ValueValidationError, match="missing required 'type' field"):
            parse_value_definition("score", {"scope": "unit", "default": 0})  # type: ignore[typeddict-item]

    def test_missing_scope_raises(self) -> None:
        """Should raise when scope field is missing."""
        with pytest.raises(
            ValueValidationError, match="missing required 'scope' field"
        ):
            parse_value_definition("score", {"type": "integer"})  # type: ignore[typeddict-item]

    def test_invalid_type_raises(self) -> None:
        """Should raise for invalid type."""
        with pytest.raises(ValueValidationError, match="Invalid type 'badtype'"):
            parse_value_definition("score", {"type": "badtype", "scope": "unit"})

    def test_invalid_scope_raises(self) -> None:
        """Should raise for invalid scope."""
        with pytest.raises(ValueValidationError, match="Invalid scope 'global'"):
            parse_value_definition("score", {"type": "integer", "scope": "global"})

    def test_default_type_validated(self) -> None:
        """Should reject default that doesn't match declared type."""
        with pytest.raises(
            ValueValidationError, match="Default for 'score' must be integer"
        ):
            parse_value_definition(
                "score", {"type": "integer", "scope": "unit", "default": "wrong"}
            )

    def test_default_type_accepts_valid(self) -> None:
        """Should accept default that matches declared type."""
        result = parse_value_definition(
            "flag", {"type": "boolean", "scope": "user,unit", "default": True}
        )
        assert result["default"] is True

    def test_all_valid_types(self) -> None:
        """Should accept all valid type names."""
        for type_name in ("integer", "float", "string", "boolean"):
            result = parse_value_definition(
                "test", {"type": type_name, "scope": "unit"}
            )
            assert result["type"] == type_name

    def test_all_valid_scopes(self) -> None:
        """Should accept all valid scope values."""
        for scope in ("unit", "user,unit"):
            result = parse_value_definition("test", {"type": "integer", "scope": scope})
            assert result["scope"] == scope


class TestValidateValue:
    """Tests for validate_value function."""

    def test_integer_accepts_int(self) -> None:
        """Should accept int for integer type."""
        validate_value("count", 42, {"type": "integer", "scope": "unit"})

    def test_integer_rejects_float(self) -> None:
        """Should reject float for integer type."""
        with pytest.raises(ValueValidationError, match="must be integer"):
            validate_value("count", 3.14, {"type": "integer", "scope": "unit"})

    def test_integer_rejects_string(self) -> None:
        """Should reject string for integer type."""
        with pytest.raises(ValueValidationError, match="must be integer"):
            validate_value("count", "42", {"type": "integer", "scope": "unit"})

    def test_float_accepts_float(self) -> None:
        """Should accept float for float type."""
        validate_value("ratio", 3.14, {"type": "float", "scope": "unit"})

    def test_float_accepts_int(self) -> None:
        """Should accept int for float type (int is valid float)."""
        validate_value("ratio", 42, {"type": "float", "scope": "unit"})

    def test_string_accepts_string(self) -> None:
        """Should accept string for string type."""
        validate_value("name", "hello", {"type": "string", "scope": "unit"})

    def test_string_rejects_int(self) -> None:
        """Should reject int for string type."""
        with pytest.raises(ValueValidationError, match="must be string"):
            validate_value("name", 42, {"type": "string", "scope": "unit"})

    def test_boolean_accepts_bool(self) -> None:
        """Should accept bool for boolean type."""
        validate_value("enabled", True, {"type": "boolean", "scope": "unit"})
        validate_value("enabled", False, {"type": "boolean", "scope": "unit"})

    def test_boolean_rejects_int(self) -> None:
        """Should reject int for boolean type (even 0/1)."""
        with pytest.raises(ValueValidationError, match="must be boolean"):
            validate_value("enabled", 1, {"type": "boolean", "scope": "unit"})


class TestValueChecker:
    """Tests for ValueChecker class."""

    def test_load_from_manifest_empty(self) -> None:
        """Should handle manifest with no values."""
        manifest: Manifest = {"name": "test"}
        checker = ValueChecker.load_from_manifest(manifest)
        assert not checker.value_names

    def test_load_from_manifest_with_values(self) -> None:
        """Should parse all value definitions from manifest."""
        manifest: Manifest = {
            "name": "test",
            "values": {
                "score": {"type": "integer", "scope": "user,unit"},
                "attempts": {"type": "integer", "scope": "user,unit", "default": 0},
            },
        }
        checker = ValueChecker.load_from_manifest(manifest)
        assert sorted(checker.value_names) == ["attempts", "score"]

    def test_get_definition_exists(self) -> None:
        """Should return definition for declared value."""
        manifest: Manifest = {
            "name": "test",
            "values": {
                "score": {"type": "integer", "scope": "user,unit", "default": 10}
            },
        }
        checker = ValueChecker.load_from_manifest(manifest)
        definition = checker.get_definition("score")
        assert definition["type"] == "integer"
        assert definition["scope"] == "user,unit"
        assert definition["default"] == 10

    def test_get_definition_not_declared(self) -> None:
        """Should raise for undeclared value."""
        manifest: Manifest = {
            "name": "test",
            "values": {"score": {"type": "integer", "scope": "unit"}},
        }
        checker = ValueChecker.load_from_manifest(manifest)
        with pytest.raises(ValueValidationError, match="not declared"):
            checker.get_definition("unknown")

    def test_get_default_with_default(self) -> None:
        """Should return default value when defined."""
        manifest: Manifest = {
            "name": "test",
            "values": {"score": {"type": "integer", "scope": "unit", "default": 100}},
        }
        checker = ValueChecker.load_from_manifest(manifest)
        assert checker.get_default("score") == 100

    def test_get_default_without_default(self) -> None:
        """Should return type-specific default when no explicit default defined."""
        manifest: Manifest = {
            "name": "test",
            "values": {
                "count": {"type": "integer", "scope": "unit"},
                "ratio": {"type": "float", "scope": "unit"},
                "name": {"type": "string", "scope": "unit"},
                "enabled": {"type": "boolean", "scope": "unit"},
            },
        }
        checker = ValueChecker.load_from_manifest(manifest)
        assert checker.get_default("count") == 0
        assert checker.get_default("ratio") == 0.0
        assert checker.get_default("name") == ""
        assert checker.get_default("enabled") is False

    def test_validate_passes(self) -> None:
        """Should pass validation for valid value."""
        manifest: Manifest = {
            "name": "test",
            "values": {
                "score": {"type": "integer", "scope": "user,unit", "default": 0}
            },
        }
        checker = ValueChecker.load_from_manifest(manifest)
        checker.validate("score", 50)  # Should not raise

    def test_validate_fails_type(self) -> None:
        """Should fail validation for wrong type."""
        manifest: Manifest = {
            "name": "test",
            "values": {"score": {"type": "integer", "scope": "unit"}},
        }
        checker = ValueChecker.load_from_manifest(manifest)
        with pytest.raises(ValueValidationError, match="must be integer"):
            checker.validate("score", "not an int")

    def test_is_user_scoped(self) -> None:
        """Should correctly identify user-scoped values."""
        manifest: Manifest = {
            "name": "test",
            "values": {
                "score": {"type": "integer", "scope": "user,unit"},
                "question": {"type": "string", "scope": "unit"},
            },
        }
        checker = ValueChecker.load_from_manifest(manifest)
        assert checker.is_user_scoped("score") is True
        assert checker.is_user_scoped("question") is False

    def test_user_value_names(self) -> None:
        """Should return only user-scoped value names."""
        manifest: Manifest = {
            "name": "test",
            "values": {
                "score": {"type": "integer", "scope": "user,unit"},
                "attempts": {"type": "integer", "scope": "user,unit"},
                "question": {"type": "string", "scope": "unit"},
            },
        }
        checker = ValueChecker.load_from_manifest(manifest)
        assert sorted(checker.user_value_names()) == ["attempts", "score"]

    def test_shared_value_names(self) -> None:
        """Should return only shared (non-user-scoped) value names."""
        manifest: Manifest = {
            "name": "test",
            "values": {
                "score": {"type": "integer", "scope": "user,unit"},
                "question": {"type": "string", "scope": "unit"},
                "answers": {"type": "string", "scope": "unit"},
            },
        }
        checker = ValueChecker.load_from_manifest(manifest)
        assert sorted(checker.shared_value_names()) == ["answers", "question"]
