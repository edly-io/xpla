#!/bin/env python
"""
Unit tests for the learning activity server.
"""

import json
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

import server.app as app_module


@pytest.fixture
def samples_dir(monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    """Create a temporary samples directory and patch SAMPLES_DIR."""
    with tempfile.TemporaryDirectory() as tmpdir:
        samples_path = Path(tmpdir)

        # Create test-activity subdirectory
        activity_path = samples_path / "test-activity"
        activity_path.mkdir()

        # Create manifest
        manifest: dict[str, Any] = {
            "name": "test-activity",
            "capabilities": {},
        }
        (activity_path / "manifest.json").write_text(json.dumps(manifest))

        # Create index.html
        (activity_path / "index.html").write_text("<html><body>Test</body></html>")

        # Patch SAMPLES_DIR
        monkeypatch.setattr(app_module, "SAMPLES_DIR", samples_path)

        yield samples_path


@pytest.fixture
def client(samples_dir: Path) -> TestClient:  # pylint: disable=unused-argument
    """Create a test client for the server."""
    return TestClient(app_module.app)


class TestStaticFiles:
    """Tests for static file serving."""

    def test_serve_index_html(self, client: TestClient) -> None:
        """Should serve index.html."""
        response = client.get("/a/test-activity/index.html")
        assert response.status_code == 200
        assert "Test" in response.text

    def test_serve_library(self, client: TestClient) -> None:
        """Should serve library files."""
        response = client.get("/static/js/learningactivity.js")
        assert response.status_code == 200
        assert (
            "learning-activity" in response.text.lower()
            or "LearningActivity" in response.text
        )

    def test_activity_not_found(self, client: TestClient) -> None:
        """Should return 404 for unknown activity."""
        response = client.get("/a/nonexistent/index.html")
        assert response.status_code == 404


class TestPluginEndpoint:
    """Tests for plugin execution endpoint."""

    def test_no_plugin_returns_404(self, client: TestClient) -> None:
        """Should return 404 when no plugin is loaded."""
        response = client.post(
            "/api/test-activity/plugin/test_function", content="test"
        )
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
