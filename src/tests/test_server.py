#!/bin/env python
"""
Unit tests for the learning activity server.
"""

import json
import sys
import tempfile
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

from server import create_app


@pytest.fixture
def activity_dir() -> Path:
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


class TestManifestEndpoint:
    """Tests for /api/manifest endpoint."""

    def test_get_manifest(self, client: TestClient) -> None:
        """Should return the activity manifest."""
        response = client.get("/api/manifest")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-activity"
        assert data["version"] == "1.0.0"


class TestKVEndpoints:
    """Tests for KV store endpoints."""

    def test_kv_set_and_get(self, client: TestClient) -> None:
        """Should set and retrieve a value."""
        # Set a value
        response = client.put("/api/kv/mykey", content="myvalue")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # Get the value
        response = client.get("/api/kv/mykey")
        assert response.status_code == 200
        assert response.json()["value"] == "myvalue"

    def test_kv_get_nonexistent(self, client: TestClient) -> None:
        """Should return 404 for nonexistent key."""
        response = client.get("/api/kv/nonexistent")
        assert response.status_code == 404

    def test_kv_delete(self, client: TestClient) -> None:
        """Should delete a key."""
        # Set a value first
        client.put("/api/kv/todelete", content="value")

        # Delete it
        response = client.delete("/api/kv/todelete")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        # Verify it's gone
        response = client.get("/api/kv/todelete")
        assert response.status_code == 404

    def test_kv_list_keys(self, client: TestClient) -> None:
        """Should list all keys."""
        # Set some values
        client.put("/api/kv/key1", content="value1")
        client.put("/api/kv/key2", content="value2")

        # List keys
        response = client.get("/api/kv")
        assert response.status_code == 200
        keys = response.json()["keys"]
        assert "key1" in keys
        assert "key2" in keys


class TestLMSEndpoints:
    """Tests for LMS simulation endpoints."""

    def test_get_user(self, client: TestClient) -> None:
        """Should return current user info."""
        response = client.get("/api/lms/user")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "email" in data
        assert "roles" in data

    def test_submit_grade(self, client: TestClient) -> None:
        """Should submit a grade."""
        response = client.post(
            "/api/lms/grade",
            json={"score": 85, "max_score": 100, "comment": "Good work!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"
        assert data["score"] == 85
        assert data["max_score"] == 100

    def test_get_grades(self, client: TestClient) -> None:
        """Should return submitted grades."""
        # Submit a grade first
        client.post("/api/lms/grade", json={"score": 90})

        # Get grades
        response = client.get("/api/lms/grades")
        assert response.status_code == 200
        data = response.json()
        assert "grades" in data
        assert len(data["grades"]) >= 1

    def test_get_best_grade(self, client: TestClient) -> None:
        """Should return the best grade."""
        # Submit multiple grades
        client.post("/api/lms/grade", json={"score": 70})
        client.post("/api/lms/grade", json={"score": 95})
        client.post("/api/lms/grade", json={"score": 80})

        # Get best grade
        response = client.get("/api/lms/grades/best")
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 95


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
        from server.capabilities import parse_capabilities

        manifest = {
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
        from server.capabilities import (
            CapabilityChecker,
            CapabilityError,
            parse_capabilities,
        )

        manifest = {
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
        from server.capabilities import (
            CapabilityChecker,
            CapabilityError,
            parse_capabilities,
        )

        manifest = {
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
        from server.capabilities import (
            CapabilityChecker,
            CapabilityError,
            parse_capabilities,
        )

        manifest = {
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
        from server.capabilities import (
            CapabilityChecker,
            CapabilityError,
            parse_capabilities,
        )

        manifest = {"name": "test", "capabilities": {}}
        caps = parse_capabilities(manifest)
        checker = CapabilityChecker(caps)

        with pytest.raises(CapabilityError, match="kv capability not declared"):
            checker.check_kv_access()

        with pytest.raises(CapabilityError, match="http capability not declared"):
            checker.check_http_request("https://example.com")

        with pytest.raises(CapabilityError, match="lms capability not declared"):
            checker.check_lms_function("get_user")
