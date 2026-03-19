#!/usr/bin/env python
"""
Unit tests for the xPLA server.
"""

import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from xpla.demo.app import app
from xpla.demo import constants


@pytest.fixture(name="samples_dir")
def fixtures_samples_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Path, None, None]:
    """Create a temporary samples directory and patch SAMPLES_DIR."""
    with tempfile.TemporaryDirectory() as tmpdir:
        samples_path = Path(tmpdir)

        # Create test-activity subdirectory
        activity_path = samples_path / "test-activity"
        activity_path.mkdir()

        # Create manifest
        manifest: dict[str, Any] = {
            "name": "test-activity",
            "client": "client.js",
            "capabilities": {},
            "static": ["index.html"],
        }
        (activity_path / "manifest.json").write_text(json.dumps(manifest))

        # Create index.html
        (activity_path / "index.html").write_text("<html><body>Test</body></html>")

        # Create a file not declared in static
        (activity_path / "secret.txt").write_text("secret")

        # Patch SAMPLES_DIR
        monkeypatch.setattr(constants, "SAMPLES_DIR", samples_path)

        yield samples_path


@pytest.fixture(name="client")
def fixtures_client(samples_dir: Path) -> TestClient:  # pylint: disable=unused-argument
    """Create a test client for the server."""
    return TestClient(app)


class TestPages:
    """Load app pages."""

    def test_home(self, client: TestClient) -> None:
        """GET / should return 200."""
        response = client.get("/")
        assert response.status_code == 200
        assert "test-activity" in response.text


class TestStaticFiles:
    """Tests for static file serving."""

    def test_serve_index_html(self, client: TestClient) -> None:
        """Should serve index.html."""
        response = client.get("/a/test-activity/index.html")
        assert response.status_code == 200
        assert "Test" in response.text

    def test_serve_library(self, client: TestClient) -> None:
        """Should serve library files."""
        response = client.get("/static/js/xpla.js")
        assert response.status_code == 200
        assert "xpla" in response.text.lower() or "xPLA" in response.text

    def test_undeclared_asset_returns_404(self, client: TestClient) -> None:
        """Should return 404 for files not declared in static."""
        response = client.get("/a/test-activity/secret.txt")
        assert response.status_code == 404

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


class TestActionEndpoint:
    """Tests for action endpoint."""

    def test_returns_422_for_undeclared_action(
        self, samples_dir: Path, client: TestClient
    ) -> None:
        """Should return 422 when action is not declared in manifest."""
        # Update manifest to include actions
        activity_path = samples_dir / "test-activity"
        manifest: dict[str, Any] = {
            "name": "test-activity",
            "client": "client.js",
            "capabilities": {},
            "actions": {
                "known.action": {"type": "object", "properties": {}},
            },
        }
        (activity_path / "manifest.json").write_text(json.dumps(manifest))

        response = client.post(
            "/api/activity/test-activity/actions/unknown.action",
            json={"data": "test"},
        )
        assert response.status_code == 422

    def test_returns_422_for_invalid_payload(
        self, samples_dir: Path, client: TestClient
    ) -> None:
        """Should return 422 when action payload doesn't match schema."""
        activity_path = samples_dir / "test-activity"
        manifest: dict[str, Any] = {
            "name": "test-activity",
            "client": "client.js",
            "capabilities": {},
            "actions": {
                "typed.action": {"type": "integer"},
            },
        }
        (activity_path / "manifest.json").write_text(json.dumps(manifest))

        response = client.post(
            "/api/activity/test-activity/actions/typed.action",
            json="not an integer",
        )
        assert response.status_code == 422
