import pytest
from server.activities.capabilities import (
    CapabilityChecker,
    CapabilityError,
    parse_capabilities,
    Manifest,
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
