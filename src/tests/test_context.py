import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
import urllib.error

import pytest

from server.activities.context import ActivityContext, MissingSandboxError
from server.activities.capabilities import ValueValidationError


def create_manifest(
    name: str = "test-activity",
    capabilities: dict[str, Any] | None = None,
    values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Helper to create a manifest dict."""
    manifest: dict[str, Any] = {"name": name, "capabilities": capabilities or {}}
    if values is not None:
        manifest["values"] = values
    return manifest


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


def unique_user(tmp_path: Path) -> str:
    """Generate a unique user ID based on tmp_path to avoid KV store collisions."""
    return f"user_{tmp_path.name}"


class TestGetValue:
    """Tests for get_value method."""

    def test_returns_default_when_not_set(self, tmp_path: Path) -> None:
        """Should return default value when value not yet stored."""
        manifest = create_manifest(values={"score": {"type": "integer", "default": 0}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.get_value("score", unique_user(tmp_path))

        assert result == 0

    def test_returns_type_default_when_no_explicit_default(
        self, tmp_path: Path
    ) -> None:
        """Should return type-specific default when no explicit default."""
        manifest = create_manifest(
            values={
                "count": {"type": "integer"},
                "ratio": {"type": "float"},
                "name": {"type": "string"},
                "done": {"type": "boolean"},
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        assert ctx.get_value("count", user) == 0
        assert ctx.get_value("ratio", user) == 0.0
        assert ctx.get_value("name", user) == ""
        assert ctx.get_value("done", user) is False

    def test_returns_stored_value(self, tmp_path: Path) -> None:
        """Should return stored value when set."""
        manifest = create_manifest(values={"score": {"type": "integer", "default": 0}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.set_value("score", user, 42)
        result = ctx.get_value("score", user)

        assert result == 42

    def test_raises_for_undeclared_value(self, tmp_path: Path) -> None:
        """Should raise for value not declared in manifest."""
        manifest = create_manifest(values={"score": {"type": "integer"}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        with pytest.raises(ValueValidationError, match="not declared"):
            ctx.get_value("unknown", unique_user(tmp_path))

    def test_values_isolated_by_user(self, tmp_path: Path) -> None:
        """Should store separate values for different users."""
        manifest = create_manifest(values={"score": {"type": "integer", "default": 0}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        base_user = unique_user(tmp_path)

        ctx.set_value("score", f"{base_user}_1", 10)
        ctx.set_value("score", f"{base_user}_2", 20)

        assert ctx.get_value("score", f"{base_user}_1") == 10
        assert ctx.get_value("score", f"{base_user}_2") == 20


class TestSetValue:
    """Tests for set_value method."""

    def test_stores_integer(self, tmp_path: Path) -> None:
        """Should store and retrieve integer value."""
        manifest = create_manifest(values={"count": {"type": "integer"}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.set_value("count", user, 42)

        assert ctx.get_value("count", user) == 42

    def test_stores_float(self, tmp_path: Path) -> None:
        """Should store and retrieve float value."""
        manifest = create_manifest(values={"ratio": {"type": "float"}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.set_value("ratio", user, 3.14)

        assert ctx.get_value("ratio", user) == 3.14

    def test_stores_string(self, tmp_path: Path) -> None:
        """Should store and retrieve string value."""
        manifest = create_manifest(values={"name": {"type": "string"}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.set_value("name", user, "Alice")

        assert ctx.get_value("name", user) == "Alice"

    def test_stores_boolean(self, tmp_path: Path) -> None:
        """Should store and retrieve boolean value."""
        manifest = create_manifest(values={"completed": {"type": "boolean"}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.set_value("completed", user, True)

        assert ctx.get_value("completed", user) is True

    def test_raises_for_wrong_type(self, tmp_path: Path) -> None:
        """Should raise when value type doesn't match declaration."""
        manifest = create_manifest(values={"count": {"type": "integer"}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        with pytest.raises(ValueValidationError, match="must be integer"):
            ctx.set_value("count", user, "not an int")

    def test_raises_for_undeclared_value(self, tmp_path: Path) -> None:
        """Should raise for value not declared in manifest."""
        manifest = create_manifest(values={"score": {"type": "integer"}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        with pytest.raises(ValueValidationError, match="not declared"):
            ctx.set_value("unknown", user, 42)

    def test_overwrites_existing_value(self, tmp_path: Path) -> None:
        """Should overwrite previously stored value."""
        manifest = create_manifest(values={"count": {"type": "integer"}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.set_value("count", user, 10)
        ctx.set_value("count", user, 20)

        assert ctx.get_value("count", user) == 20


class TestGetAllValues:
    """Tests for get_all_values method."""

    def test_returns_empty_dict_when_no_values_declared(self, tmp_path: Path) -> None:
        """Should return empty dict when manifest has no values."""
        manifest = create_manifest(values={})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        result = ctx.get_all_values(user)

        assert result == {}

    def test_returns_defaults_when_not_set(self, tmp_path: Path) -> None:
        """Should return default values when none have been set."""
        manifest = create_manifest(
            values={
                "score": {"type": "integer", "default": 100},
                "name": {"type": "string"},
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        result = ctx.get_all_values(user)

        assert result == {"score": 100, "name": ""}

    def test_returns_stored_values(self, tmp_path: Path) -> None:
        """Should return stored values mixed with defaults."""
        manifest = create_manifest(
            values={
                "correct": {"type": "integer", "default": 0},
                "wrong": {"type": "integer", "default": 0},
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)
        ctx.set_value("correct", user, 5)

        result = ctx.get_all_values(user)

        assert result == {"correct": 5, "wrong": 0}
