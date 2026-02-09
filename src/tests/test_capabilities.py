import pytest
from server.activities.capabilities import CapabilityChecker, CapabilityError
from server.activities.manifest_types import (
    Capabilities,
    Http,
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
