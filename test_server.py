#!/usr/bin/env -S uv run --with pytest --with httpx
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pytest>=8.0.0",
#     "httpx>=0.27.0",
#     "fastapi>=0.115.0",
#     "uvicorn[standard]>=0.32.0",
#     "extism>=1.0.0",
# ]
# ///
"""
Unit tests for the learning activity server.

Run with: ./test_server.py or pytest test_server.py
"""

import json
import tempfile
from pathlib import Path

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
    """Return the library directory (project root)."""
    return Path(__file__).parent


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
        assert "learning-activity" in response.text.lower() or "LearningActivity" in response.text


class TestPluginEndpoint:
    """Tests for plugin execution endpoint."""

    def test_no_plugin_returns_404(self, client: TestClient) -> None:
        """Should return 404 when no plugin is loaded."""
        response = client.post("/api/plugin/test_function", content="test")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
