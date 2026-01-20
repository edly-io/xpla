import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
import urllib.error

import pytest

from server.activities.context import ActivityContext, MissingSandboxError


def create_manifest(
    name: str = "test-activity", capabilities: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Helper to create a manifest dict."""
    return {"name": name, "capabilities": capabilities or {}}


def setup_activity_dir(tmp_path: Path, manifest: dict[str, Any]) -> Path:
    """Set up an activity directory with a manifest."""
    activity_dir = tmp_path / "activity"
    activity_dir.mkdir()
    with open(activity_dir / "manifest.json", "w", encoding="utf8") as f:
        json.dump(manifest, f)
    return activity_dir


class TestActivityContextInit:
    """Tests for ActivityContext initialization."""

    def test_init_creates_kv_store(self, tmp_path: Path) -> None:
        """Should create a KV store at the expected path."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)

        ctx = ActivityContext(activity_dir)

        assert ctx.kv_store is not None

    def test_init_loads_manifest(self, tmp_path: Path) -> None:
        """Should load manifest from activity directory."""
        manifest = create_manifest("my-activity", {"http": {}})
        activity_dir = setup_activity_dir(tmp_path, manifest)

        ctx = ActivityContext(activity_dir)

        assert ctx.manifest["name"] == "my-activity"
        assert "http" in ctx.manifest["capabilities"]

    def test_init_creates_capability_checker(self, tmp_path: Path) -> None:
        """Should create a CapabilityChecker from manifest."""
        manifest = create_manifest(capabilities={"lms": ["get_user"]})
        activity_dir = setup_activity_dir(tmp_path, manifest)

        ctx = ActivityContext(activity_dir)

        assert ctx.checker is not None
        # Should not raise for allowed function
        ctx.checker.check_lms_function("get_user")

    def test_init_without_sandbox(self, tmp_path: Path) -> None:
        """Should set sandbox to None when no wasm file exists."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)

        ctx = ActivityContext(activity_dir)

        assert ctx.sandbox is None

    @patch("server.activities.context.SandboxExecutor")
    def test_init_with_sandbox(
        self, mock_sandbox_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Should create SandboxExecutor when wasm file exists."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        (activity_dir / "sandbox.wasm").write_bytes(b"fake wasm")

        ctx = ActivityContext(activity_dir)

        mock_sandbox_executor.assert_called_once()
        assert ctx.sandbox is not None


class TestActivityContextProperties:
    """Tests for ActivityContext properties."""

    def test_activity_dir_property(self, tmp_path: Path) -> None:
        """Should return the activity directory path."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)

        ctx = ActivityContext(activity_dir)

        assert ctx.activity_dir == activity_dir

    def test_name_property(self, tmp_path: Path) -> None:
        """Should return the activity name from manifest."""
        manifest = create_manifest("quiz-activity")
        activity_dir = setup_activity_dir(tmp_path, manifest)

        ctx = ActivityContext(activity_dir)

        assert ctx.name == "quiz-activity"

    def test_html_property_with_file(self, tmp_path: Path) -> None:
        """Should return HTML content when activity.html exists."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        html_content = "<html><body>Test</body></html>"
        (activity_dir / "activity.html").write_text(html_content, encoding="utf8")

        ctx = ActivityContext(activity_dir)

        assert ctx.html == html_content

    def test_html_property_without_file(self, tmp_path: Path) -> None:
        """Should return empty string when activity.html doesn't exist."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)

        ctx = ActivityContext(activity_dir)

        assert ctx.html == ""

    def test_sandbox_path_property(self, tmp_path: Path) -> None:
        """Should return path to sandbox.wasm."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)

        ctx = ActivityContext(activity_dir)

        assert ctx.sandbox_path == activity_dir / "sandbox.wasm"


class TestCallSandboxFunction:
    """Tests for call_sandbox_function method."""

    def test_raises_when_no_sandbox(self, tmp_path: Path) -> None:
        """Should raise MissingSandboxError when sandbox is None."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        with pytest.raises(MissingSandboxError):
            ctx.call_sandbox_function("test_fn", b"input")

    @patch("server.activities.context.SandboxExecutor")
    def test_calls_sandbox_function(
        self, mock_sandbox_class: MagicMock, tmp_path: Path
    ) -> None:
        """Should delegate to sandbox.call_function."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        (activity_dir / "sandbox.wasm").write_bytes(b"fake wasm")

        mock_sandbox = MagicMock()
        mock_sandbox.call_function.return_value = b"result"
        mock_sandbox_class.return_value = mock_sandbox

        ctx = ActivityContext(activity_dir)
        result = ctx.call_sandbox_function("my_function", b"input_data")

        mock_sandbox.call_function.assert_called_once_with("my_function", b"input_data")
        assert result == b"result"


class TestHostFunctions:
    """Tests for host_functions method."""

    def test_returns_expected_functions(self, tmp_path: Path) -> None:
        """Should return list of host function callables."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        functions = ctx.host_functions()

        assert len(functions) == 3
        function_names = [f.__name__ for f in functions]
        assert "lms_submit_grade" in function_names
        assert "http_request" in function_names
        assert "lms_get_user" in function_names


class TestLmsSubmitGrade:
    """Tests for lms_submit_grade host function."""

    def test_success_when_allowed(self, tmp_path: Path) -> None:
        """Should return success when LMS capability allows submit_grade."""
        manifest = create_manifest(capabilities={"lms": ["submit_grade"]})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.lms_submit_grade({"score": 85, "max_score": 100})

        data = json.loads(result)
        assert data["status"] == "submitted"
        assert data["score"] == 85

    def test_error_when_not_allowed(self, tmp_path: Path) -> None:
        """Should return error when LMS capability doesn't allow submit_grade."""
        manifest = create_manifest(capabilities={"lms": ["get_user"]})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.lms_submit_grade({"score": 85})

        data = json.loads(result)
        assert "error" in data
        assert "not allowed" in data["error"]

    def test_error_when_no_lms_capability(self, tmp_path: Path) -> None:
        """Should return error when no LMS capability declared."""
        manifest = create_manifest(capabilities={})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.lms_submit_grade({"score": 85})

        data = json.loads(result)
        assert "error" in data
        assert "not declared" in data["error"]


class TestLmsGetUser:
    """Tests for lms_get_user host function."""

    def test_success_when_allowed(self, tmp_path: Path) -> None:
        """Should return user info when LMS capability allows get_user."""
        manifest = create_manifest(capabilities={"lms": ["get_user"]})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.lms_get_user("")

        data = json.loads(result)
        assert "id" in data
        assert "name" in data

    def test_error_when_not_allowed(self, tmp_path: Path) -> None:
        """Should return error when LMS capability doesn't allow get_user."""
        manifest = create_manifest(capabilities={"lms": ["submit_grade"]})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.lms_get_user("")

        data = json.loads(result)
        assert "error" in data
        assert "not allowed" in data["error"]

    def test_error_when_no_lms_capability(self, tmp_path: Path) -> None:
        """Should return error when no LMS capability declared."""
        manifest = create_manifest(capabilities={})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.lms_get_user("")

        data = json.loads(result)
        assert "error" in data
        assert "not declared" in data["error"]


class TestHttpRequest:
    """Tests for http_request host function."""

    def test_error_when_no_http_capability(self, tmp_path: Path) -> None:
        """Should return error when no HTTP capability declared."""
        manifest = create_manifest(capabilities={})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.http_request("https://example.com", "GET", b"", ())

        data = json.loads(result)
        assert "error" in data
        assert "not declared" in data["error"]

    def test_error_when_host_not_allowed(self, tmp_path: Path) -> None:
        """Should return error when host not in allowed list."""
        manifest = create_manifest(
            capabilities={"http": {"allowed_hosts": ["api.example.com"]}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.http_request("https://evil.com/hack", "GET", b"", ())

        data = json.loads(result)
        assert "error" in data
        assert "not allowed" in data["error"]

    @patch("server.activities.context.urllib.request.urlopen")
    def test_success_when_allowed(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        """Should make request and return response when allowed."""
        manifest = create_manifest(
            capabilities={"http": {"allowed_hosts": ["api.example.com"]}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"data": "test"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = ctx.http_request(
            "https://api.example.com/data",
            "POST",
            b"body",
            (("Content-Type", "application/json"),),
        )

        assert result == '{"data": "test"}'
        mock_urlopen.assert_called_once()

    @patch("server.activities.context.urllib.request.urlopen")
    def test_handles_http_error(self, mock_urlopen: MagicMock, tmp_path: Path) -> None:
        """Should return error on HTTPError."""
        manifest = create_manifest(capabilities={"http": {}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://example.com", 404, "Not Found", None, None  # type: ignore[arg-type]
        )

        result = ctx.http_request("https://example.com", "GET", b"", ())

        data = json.loads(result)
        assert "error" in data
        assert "404" in data["error"]

    @patch("server.activities.context.urllib.request.urlopen")
    def test_handles_url_error(self, mock_urlopen: MagicMock, tmp_path: Path) -> None:
        """Should return error on URLError."""
        manifest = create_manifest(capabilities={"http": {}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        result = ctx.http_request("https://example.com", "GET", b"", ())

        data = json.loads(result)
        assert "error" in data
        assert "Connection refused" in data["error"]

    @patch("server.activities.context.urllib.request.urlopen")
    def test_permissive_mode_allows_all_hosts(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        """Should allow all hosts when allowed_hosts is empty."""
        manifest = create_manifest(capabilities={"http": {}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        mock_response = MagicMock()
        mock_response.read.return_value = b"ok"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = ctx.http_request("https://any-host.com/api", "GET", b"", ())

        assert result == "ok"
