import pytest
from pxc.lib.capabilities import CapabilityChecker, CapabilityError, InterfaceName
from pxc.lib.manifest_types import (
    Capabilities,
    Http,
    StorageDefinition,
    Scope,
)


class TestInterfaceRequested:
    """Tests for CapabilityChecker.is_interface_requested."""

    def test_state_always_requested(self) -> None:
        assert CapabilityChecker(None).is_interface_requested(InterfaceName.state)
        assert CapabilityChecker(Capabilities()).is_interface_requested(
            InterfaceName.state
        )

    def test_http_requires_allowlist(self) -> None:
        assert not CapabilityChecker(Capabilities()).is_interface_requested(
            InterfaceName.http
        )
        caps = Capabilities(http=Http(allowed_hosts=["api.example.com"]))
        assert CapabilityChecker(caps).is_interface_requested(InterfaceName.http)

    def test_storage_requires_buckets(self) -> None:
        assert not CapabilityChecker(Capabilities()).is_interface_requested(
            InterfaceName.storage
        )
        caps = Capabilities(storage={"media": StorageDefinition(scope=Scope.activity)})
        assert CapabilityChecker(caps).is_interface_requested(InterfaceName.storage)

    def test_grading_opt_in(self) -> None:
        assert not CapabilityChecker(Capabilities()).is_interface_requested(
            InterfaceName.grading
        )
        caps = Capabilities(grading={})
        assert CapabilityChecker(caps).is_interface_requested(InterfaceName.grading)


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

        with pytest.raises(
            CapabilityError,
            match=r"HTTP requests to example\.com not allowed. Allowed hosts: \[\]",
        ):
            checker.check_http_request("https://example.com")

    def test_empty_capabilities_rejected(self) -> None:
        """Should reject operations when capabilities object has no relevant field."""
        caps = Capabilities()
        checker = CapabilityChecker(caps)

        with pytest.raises(
            CapabilityError,
            match=r"HTTP requests to example\.com not allowed. Allowed hosts: \[\]",
        ):
            checker.check_http_request("https://example.com")
