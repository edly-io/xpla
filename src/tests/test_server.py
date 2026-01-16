#!/bin/env python
"""
Unit tests for the learning activity server.
"""

import json
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

from server import create_app


@pytest.fixture
def activity_dir() -> Generator[Path, None, None]:
    """Create a temporary activity directory with required files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        activity_path = Path(tmpdir)

        # Create manifest
        manifest = {
            "name": "test-activity",
            "version": "1.0.0",
            "title": "Test Activity",
            "capabilities": {},
        }
        (activity_path / "manifest.json").write_text(json.dumps(manifest))

        # Create index.html
        (activity_path / "index.html").write_text("<html><body>Test</body></html>")

        yield activity_path


@pytest.fixture
def lib_dir() -> Path:
    """Return the library directory."""
    return Path(__file__).parent.parent / "lib"


@pytest.fixture
def client(activity_dir: Path, lib_dir: Path) -> TestClient:
    """Create a test client for the server."""
    app = create_app(activity_dir, lib_dir)
    return TestClient(app)


class TestStaticFiles:
    """Tests for static file serving."""

    def test_serve_index_html(self, client: TestClient) -> None:
        """Should serve index.html."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Test" in response.text

    def test_serve_library(self, client: TestClient) -> None:
        """Should serve library files."""
        response = client.get("/lib/learningactivity.js")
        assert response.status_code == 200
        assert (
            "learning-activity" in response.text.lower()
            or "LearningActivity" in response.text
        )


class TestPluginEndpoint:
    """Tests for plugin execution endpoint."""

    def test_no_plugin_returns_404(self, client: TestClient) -> None:
        """Should return 404 when no plugin is loaded."""
        response = client.post("/api/plugin/test_function", content="test")
        assert response.status_code == 404


class TestCapabilities:
    """Tests for capability enforcement."""

    def test_capabilities_parsing(self) -> None:
        """Should parse capabilities from manifest."""
        from server.activities.capabilities import Manifest, parse_capabilities

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
        from server.activities.capabilities import (
            CapabilityChecker,
            CapabilityError,
            Manifest,
            parse_capabilities,
        )

        manifest: Manifest = {
            "name": "test",
            "capabilities": {"kv": {"namespace": "test"}},
        }
        caps = parse_capabilities(manifest)
        checker = CapabilityChecker(caps)

        # Should allow keys with correct namespace
        checker.check_kv_write("test:mykey", "value")

        # Should reject keys without namespace prefix
        with pytest.raises(CapabilityError, match="namespace prefix"):
            checker.check_kv_write("wrongkey", "value")

    def test_http_host_enforcement(self) -> None:
        """Should enforce HTTP allowed hosts."""
        from server.activities.capabilities import (
            CapabilityChecker,
            CapabilityError,
            Manifest,
            parse_capabilities,
        )

        manifest: Manifest = {
            "name": "test",
            "capabilities": {"http": {"allowed_hosts": ["api.example.com"]}},
        }
        caps = parse_capabilities(manifest)
        checker = CapabilityChecker(caps)

        # Should allow whitelisted host
        checker.check_http_request("https://api.example.com/data")

        # Should reject other hosts
        with pytest.raises(CapabilityError, match="not allowed"):
            checker.check_http_request("https://evil.com/hack")

    def test_lms_function_enforcement(self) -> None:
        """Should enforce LMS allowed functions."""
        from server.activities.capabilities import (
            CapabilityChecker,
            CapabilityError,
            Manifest,
            parse_capabilities,
        )

        manifest: Manifest = {
            "name": "test",
            "capabilities": {"lms": ["get_user"]},
        }
        caps = parse_capabilities(manifest)
        checker = CapabilityChecker(caps)

        # Should allow whitelisted function
        checker.check_lms_function("get_user")

        # Should reject other functions
        with pytest.raises(CapabilityError, match="not allowed"):
            checker.check_lms_function("submit_grade")

    def test_missing_capability_rejected(self) -> None:
        """Should reject operations when capability not declared."""
        from server.activities.capabilities import (
            CapabilityChecker,
            CapabilityError,
            Manifest,
            parse_capabilities,
        )

        manifest: Manifest = {"name": "test", "capabilities": {}}
        caps = parse_capabilities(manifest)
        checker = CapabilityChecker(caps)

        with pytest.raises(CapabilityError, match="kv capability not declared"):
            checker.check_kv_access()

        with pytest.raises(CapabilityError, match="http capability not declared"):
            checker.check_http_request("https://example.com")

        with pytest.raises(CapabilityError, match="lms capability not declared"):
            checker.check_lms_function("get_user")
