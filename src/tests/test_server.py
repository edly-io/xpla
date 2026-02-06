#!/bin/env python
"""
Unit tests for the GULPS server.
"""

import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from server.app import app
from server import constants


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
        }
        (activity_path / "manifest.json").write_text(json.dumps(manifest))

        # Create index.html
        (activity_path / "index.html").write_text("<html><body>Test</body></html>")

        # Patch SAMPLES_DIR
        monkeypatch.setattr(constants, "SAMPLES_DIR", samples_path)

        yield samples_path


@pytest.fixture(name="client")
def fixtures_client(samples_dir: Path) -> TestClient:  # pylint: disable=unused-argument
    """Create a test client for the server."""
    return TestClient(app)


class TestStaticFiles:
    """Tests for static file serving."""

    def test_serve_index_html(self, client: TestClient) -> None:
        """Should serve index.html."""
        response = client.get("/a/test-activity/index.html")
        assert response.status_code == 200
        assert "Test" in response.text

    def test_serve_library(self, client: TestClient) -> None:
        """Should serve library files."""
        response = client.get("/static/js/gulps.js")
        assert response.status_code == 200
        assert "gulps" in response.text.lower() or "Gulps" in response.text

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
