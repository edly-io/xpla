import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
import urllib.error

import pytest

from server.activities.context import ActivityContext, MissingSandboxError
from server.activities.events import EventValidationError
from server.activities.permission import Permission
from server.activities.values import ValueValidationError


def create_manifest(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    name: str = "test-activity",
    capabilities: dict[str, Any] | None = None,
    values: dict[str, Any] | None = None,
    actions: dict[str, Any] | None = None,
    events: dict[str, Any] | None = None,
    client: str = "client.js",
    server: str | None = None,
) -> dict[str, Any]:
    """Helper to create a manifest dict."""
    manifest: dict[str, Any] = {
        "name": name,
        "client": client,
        "capabilities": capabilities or {},
    }
    if server is not None:
        manifest["server"] = server
    if values is not None:
        manifest["values"] = values
    if actions is not None:
        manifest["actions"] = actions
    if events is not None:
        manifest["events"] = events
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

        assert ctx.manifest.name == "my-activity"
        assert ctx.manifest.capabilities is not None
        assert ctx.manifest.capabilities.http is not None

    def test_init_creates_capability_checker(self, tmp_path: Path) -> None:
        """Should create a CapabilityChecker from manifest."""
        manifest = create_manifest(capabilities={"http": {}})
        activity_dir = setup_activity_dir(tmp_path, manifest)

        ctx = ActivityContext(activity_dir)

        assert ctx.checker is not None
        # Should not raise for http capability
        ctx.checker.check_http_request("https://example.com")

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
        """Should create SandboxExecutor when server is declared in manifest."""
        manifest = create_manifest(server="server.wasm")
        activity_dir = setup_activity_dir(tmp_path, manifest)
        (activity_dir / "server.wasm").write_bytes(b"fake wasm")

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

    def test_client_path_property(self, tmp_path: Path) -> None:
        """Should return client path from manifest."""
        manifest = create_manifest(client="src/my-client.js")
        activity_dir = setup_activity_dir(tmp_path, manifest)

        ctx = ActivityContext(activity_dir)

        assert ctx.client_path == "src/my-client.js"


class TestCallSandboxFunction:
    """Tests for call_sandbox_function method."""

    def test_raises_when_no_sandbox(self, tmp_path: Path) -> None:
        """Should raise MissingSandboxError when sandbox is None."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        with pytest.raises(MissingSandboxError):
            ctx.call_sandbox_function("test_fn", "input")

    @patch("server.activities.context.SandboxExecutor")
    def test_calls_sandbox_function(
        self, mock_sandbox_class: MagicMock, tmp_path: Path
    ) -> None:
        """Should delegate to sandbox.call_function."""
        manifest = create_manifest(server="server.wasm")
        activity_dir = setup_activity_dir(tmp_path, manifest)
        (activity_dir / "server.wasm").write_bytes(b"fake wasm")

        mock_sandbox = MagicMock()
        mock_sandbox.call_function.return_value = b"result"
        mock_sandbox_class.return_value = mock_sandbox

        ctx = ActivityContext(activity_dir)
        result = ctx.call_sandbox_function("my_function", "input_data")

        mock_sandbox.call_function.assert_called_once_with("my_function", "input_data")
        assert result == b"result"


class TestHostFunctions:
    """Tests for host_functions method."""

    def test_returns_expected_functions(self, tmp_path: Path) -> None:
        """Should return list of host function callables."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        functions = ctx.host_functions()

        function_names = [f.__name__ for f in functions]
        assert "http_request" in function_names
        assert "send_event" in function_names
        assert "get_value" in function_names
        assert "set_value" in function_names
        assert "get_user_value" in function_names
        assert "set_user_value" in function_names
        assert "get_course_value" in function_names
        assert "set_course_value" in function_names
        assert "get_course_user_value" in function_names
        assert "set_course_user_value" in function_names
        assert "get_platform_value" in function_names
        assert "set_platform_value" in function_names
        assert "get_platform_user_value" in function_names
        assert "set_platform_user_value" in function_names


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


class TestLoadValue:
    """Tests for load_value method."""

    def test_returns_default_when_not_set(self, tmp_path: Path) -> None:
        """Should return default value when value not yet stored."""
        manifest = create_manifest(
            values={
                "score": {
                    "type": "integer",
                    "scope": "user,unit",
                    "default": 0,
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.load_value("c", "a", unique_user(tmp_path), "score")

        assert result == 0

    def test_returns_type_default_when_no_explicit_default(
        self, tmp_path: Path
    ) -> None:
        """Should return type-specific default when no explicit default."""
        manifest = create_manifest(
            values={
                "count": {"type": "integer", "scope": "user,unit"},
                "ratio": {"type": "number", "scope": "user,unit"},
                "name": {"type": "string", "scope": "user,unit"},
                "done": {"type": "boolean", "scope": "user,unit"},
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        assert ctx.load_value("c", "a", user, "count") == 0
        assert ctx.load_value("c", "a", user, "ratio") == 0.0
        assert ctx.load_value("c", "a", user, "name") == ""
        assert ctx.load_value("c", "a", user, "done") is False

    def test_returns_stored_value(self, tmp_path: Path) -> None:
        """Should return stored value when set."""
        manifest = create_manifest(
            values={
                "score": {
                    "type": "integer",
                    "scope": "user,unit",
                    "default": 0,
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value("c", "a", user, "score", 42)
        result = ctx.load_value("c", "a", user, "score")

        assert result == 42

    def test_raises_for_undeclared_value(self, tmp_path: Path) -> None:
        """Should raise for value not declared in manifest."""
        manifest = create_manifest(
            values={"score": {"type": "integer", "scope": "user,unit"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        with pytest.raises(ValueValidationError, match="not declared"):
            ctx.load_value("c", "a", unique_user(tmp_path), "unknown")

    def test_values_isolated_by_user(self, tmp_path: Path) -> None:
        """Should store separate values for different users."""
        manifest = create_manifest(
            values={
                "score": {
                    "type": "integer",
                    "scope": "user,unit",
                    "default": 0,
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        base_user = unique_user(tmp_path)

        ctx.store_value("c", "a", f"{base_user}_1", "score", 10)
        ctx.store_value("c", "a", f"{base_user}_2", "score", 20)

        assert ctx.load_value("c", "a", f"{base_user}_1", "score") == 10
        assert ctx.load_value("c", "a", f"{base_user}_2", "score") == 20

    def test_shared_value_uses_empty_user_id(self, tmp_path: Path) -> None:
        """Should use empty string for shared (non-user) values."""
        manifest = create_manifest(
            values={
                "question": {
                    "type": "string",
                    "scope": "unit",
                    "default": "",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.store_value("c", "a", "", "question", "What is 2+2?")
        result = ctx.load_value("c", "a", "", "question")

        assert result == "What is 2+2?"


class TestStoreValue:
    """Tests for store_value method."""

    def test_stores_integer(self, tmp_path: Path) -> None:
        """Should store and retrieve integer value."""
        manifest = create_manifest(
            values={"count": {"type": "integer", "scope": "user,unit"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value("c", "a", user, "count", 42)

        assert ctx.load_value("c", "a", user, "count") == 42

    def test_stores_float(self, tmp_path: Path) -> None:
        """Should store and retrieve float value."""
        manifest = create_manifest(
            values={"ratio": {"type": "number", "scope": "user,unit"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value("c", "a", user, "ratio", 3.14)

        assert ctx.load_value("c", "a", user, "ratio") == 3.14

    def test_stores_string(self, tmp_path: Path) -> None:
        """Should store and retrieve string value."""
        manifest = create_manifest(
            values={"name": {"type": "string", "scope": "user,unit"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value("c", "a", user, "name", "Alice")

        assert ctx.load_value("c", "a", user, "name") == "Alice"

    def test_stores_boolean(self, tmp_path: Path) -> None:
        """Should store and retrieve boolean value."""
        manifest = create_manifest(
            values={"completed": {"type": "boolean", "scope": "user,unit"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value("c", "a", user, "completed", True)

        assert ctx.load_value("c", "a", user, "completed") is True

    def test_stores_array(self, tmp_path: Path) -> None:
        """Should store and retrieve array value."""
        manifest = create_manifest(
            values={
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "scope": "user,unit",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value("c", "a", user, "tags", ["a", "b", "c"])

        assert ctx.load_value("c", "a", user, "tags") == ["a", "b", "c"]

    def test_raises_for_wrong_type(self, tmp_path: Path) -> None:
        """Should raise when value type doesn't match declaration."""
        manifest = create_manifest(
            values={"count": {"type": "integer", "scope": "user,unit"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        with pytest.raises(ValueValidationError, match="failed validation"):
            ctx.store_value("c", "a", user, "count", "not an int")

    def test_raises_for_undeclared_value(self, tmp_path: Path) -> None:
        """Should raise for value not declared in manifest."""
        manifest = create_manifest(
            values={"score": {"type": "integer", "scope": "user,unit"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        with pytest.raises(ValueValidationError, match="not declared"):
            ctx.store_value("c", "a", user, "unknown", 42)

    def test_overwrites_existing_value(self, tmp_path: Path) -> None:
        """Should overwrite previously stored value."""
        manifest = create_manifest(
            values={"count": {"type": "integer", "scope": "user,unit"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value("c", "a", user, "count", 10)
        ctx.store_value("c", "a", user, "count", 20)

        assert ctx.load_value("c", "a", user, "count") == 20


class TestGetAllValues:
    """Tests for get_all_values method."""

    def test_returns_all_values(self, tmp_path: Path) -> None:
        """Should return all declared values."""
        manifest = create_manifest(
            values={
                "public": {"type": "string", "scope": "unit"},
                "secret": {"type": "string", "scope": "unit"},
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.get_all_values(unique_user(tmp_path))
        assert "public" in result
        assert "secret" in result

    def test_includes_user_scoped_values(self, tmp_path: Path) -> None:
        """Should include user-scoped values loaded for the given user."""
        manifest = create_manifest(
            values={
                "score": {
                    "type": "integer",
                    "scope": "user,unit",
                    "default": 0,
                },
                "question": {
                    "type": "string",
                    "scope": "unit",
                    "default": "",
                },
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value(ctx.course_id, ctx.activity_id, user, "score", 42)
        ctx.store_value(ctx.course_id, ctx.activity_id, "", "question", "What is 2+2?")

        result = ctx.get_all_values(user)
        assert result == {"score": 42, "question": "What is 2+2?"}

    def test_includes_course_scoped_values(self, tmp_path: Path) -> None:
        """Should include course-scoped and user,course-scoped values."""
        manifest = create_manifest(
            values={
                "course_total": {
                    "type": "integer",
                    "scope": "course",
                    "default": 0,
                },
                "course_score": {
                    "type": "integer",
                    "scope": "user,course",
                    "default": 0,
                },
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value(ctx.course_id, "", "", "course_total", 100)
        ctx.store_value(ctx.course_id, "", user, "course_score", 85)

        result = ctx.get_all_values(user)
        assert result == {"course_total": 100, "course_score": 85}

    def test_includes_platform_scoped_values(self, tmp_path: Path) -> None:
        """Should include platform-scoped and user,platform-scoped values."""
        manifest = create_manifest(
            values={
                "global_setting": {
                    "type": "string",
                    "scope": "platform",
                    "default": "",
                },
                "global_pref": {
                    "type": "string",
                    "scope": "user,platform",
                    "default": "",
                },
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value("", "", "", "global_setting", "on")
        ctx.store_value("", "", user, "global_pref", "dark")

        result = ctx.get_all_values(user)
        assert result == {"global_setting": "on", "global_pref": "dark"}


class TestGetPermission:
    """Tests for get_permission host function."""

    def test_default_permission(self, tmp_path: Path) -> None:
        """Should default to 'view' permission."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        assert ctx.get_permission() == "view"

    def test_set_permission(self, tmp_path: Path) -> None:
        """Should return the permission that was set."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.permission = Permission.edit
        assert ctx.get_permission() == "edit"

        ctx.permission = Permission.play
        assert ctx.get_permission() == "play"

    def test_in_host_functions(self, tmp_path: Path) -> None:
        """get_permission should be in the host functions list."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        function_names = [f.__name__ for f in ctx.host_functions()]
        assert "get_permission" in function_names


class TestCourseAndPlatformHostFunctions:
    """Tests for course and platform scope host functions."""

    def test_course_value_get_set(self, tmp_path: Path) -> None:
        """Should get/set course-scoped values."""
        manifest = create_manifest(
            values={"total": {"type": "integer", "scope": "course", "default": 0}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        assert json.loads(ctx.get_course_value("total")) == 0
        ctx.set_course_value("total", "99")
        assert json.loads(ctx.get_course_value("total")) == 99

    def test_course_user_value_get_set(self, tmp_path: Path) -> None:
        """Should get/set user,course-scoped values."""
        manifest = create_manifest(
            values={"grade": {"type": "integer", "scope": "user,course", "default": 0}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        ctx.user_id = "alice"

        assert json.loads(ctx.get_course_user_value("grade")) == 0
        ctx.set_course_user_value("grade", "85")
        assert json.loads(ctx.get_course_user_value("grade")) == 85

    def test_platform_value_get_set(self, tmp_path: Path) -> None:
        """Should get/set platform-scoped values."""
        manifest = create_manifest(
            values={"setting": {"type": "string", "scope": "platform", "default": ""}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        assert json.loads(ctx.get_platform_value("setting")) == ""
        ctx.set_platform_value("setting", '"dark"')
        assert json.loads(ctx.get_platform_value("setting")) == "dark"

    def test_platform_user_value_get_set(self, tmp_path: Path) -> None:
        """Should get/set user,platform-scoped values."""
        manifest = create_manifest(
            values={"pref": {"type": "string", "scope": "user,platform", "default": ""}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        ctx.user_id = "alice"

        assert json.loads(ctx.get_platform_user_value("pref")) == ""
        ctx.set_platform_user_value("pref", '"en"')
        assert json.loads(ctx.get_platform_user_value("pref")) == "en"

    def test_course_values_isolated_from_unit(self, tmp_path: Path) -> None:
        """Course-scoped values should not collide with unit-scoped values."""
        manifest = create_manifest(
            values={
                "count_unit": {"type": "integer", "scope": "unit", "default": 0},
                "count_course": {"type": "integer", "scope": "course", "default": 0},
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.set_value("count_unit", "10")
        ctx.set_course_value("count_course", "20")

        assert json.loads(ctx.get_value("count_unit")) == 10
        assert json.loads(ctx.get_course_value("count_course")) == 20


class TestGetState:
    """Tests for get_state method."""

    def test_fallback_without_sandbox(self, tmp_path: Path) -> None:
        """Should fall back to get_all_values when no sandbox exists."""
        manifest = create_manifest(
            values={
                "score": {
                    "type": "integer",
                    "scope": "user,unit",
                    "default": 0,
                },
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        ctx.user_id = "alice"

        result = ctx.get_state()
        assert result == {"score": 0}

    @patch("server.activities.context.SandboxExecutor")
    def test_calls_sandbox_getState(
        self, mock_sandbox_class: MagicMock, tmp_path: Path
    ) -> None:
        """Should call sandbox getState when available."""
        manifest = create_manifest(server="server.wasm")
        activity_dir = setup_activity_dir(tmp_path, manifest)
        (activity_dir / "server.wasm").write_bytes(b"fake wasm")

        mock_sandbox = MagicMock()
        mock_sandbox.call_function.return_value = b'{"question": "test"}'
        mock_sandbox_class.return_value = mock_sandbox

        ctx = ActivityContext(activity_dir)
        result = ctx.get_state()

        mock_sandbox.call_function.assert_called_once_with("getState", None)
        assert result == {"question": "test"}

    @patch("server.activities.context.SandboxExecutor")
    def test_fallback_on_runtime_error(
        self, mock_sandbox_class: MagicMock, tmp_path: Path
    ) -> None:
        """Should fall back to get_all_values when getState raises RuntimeError."""
        manifest = create_manifest(
            server="server.wasm",
            values={
                "score": {
                    "type": "integer",
                    "scope": "user,unit",
                    "default": 0,
                },
            },
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        (activity_dir / "server.wasm").write_bytes(b"fake wasm")

        mock_sandbox = MagicMock()
        mock_sandbox.call_function.side_effect = RuntimeError("getState not found")
        mock_sandbox_class.return_value = mock_sandbox

        ctx = ActivityContext(activity_dir)
        ctx.user_id = "alice"
        result = ctx.get_state()

        assert result == {"score": 0}


class TestSendEvent:
    """Tests for send_event host function."""

    def test_appends_event_to_pending(self, tmp_path: Path) -> None:
        """Should append event to pending events list."""
        manifest = create_manifest(events={"test.event": {"type": "string"}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.send_event("test.event", '"some value"')

        assert ctx.clear_pending_events() == [
            {"name": "test.event", "value": '"some value"'}
        ]

    def test_appends_multiple_events(self, tmp_path: Path) -> None:
        """Should accumulate multiple events."""
        manifest = create_manifest(
            events={"event1": {"type": "string"}, "event2": {"type": "string"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.send_event("event1", '"value1"')
        ctx.send_event("event2", '"value2"')

        assert ctx.clear_pending_events() == [
            {"name": "event1", "value": '"value1"'},
            {"name": "event2", "value": '"value2"'},
        ]

    def test_returns_empty_string(self, tmp_path: Path) -> None:
        """Should return empty string as success indicator."""
        manifest = create_manifest(events={"test": {"type": "string"}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.send_event("test", '"value"')

        assert result == ""

    def test_allows_declared_values_change_events(self, tmp_path: Path) -> None:
        """Should allow values.change.* events when declared in manifest."""
        manifest = create_manifest(events={"values.change.score": {"type": "integer"}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.send_event("values.change.score", "42")

        assert ctx.clear_pending_events() == [
            {"name": "values.change.score", "value": "42"}
        ]

    def test_raises_for_undeclared_event(self, tmp_path: Path) -> None:
        """Should raise EventValidationError for undeclared event."""
        manifest = create_manifest(events={"declared.event": {"type": "string"}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        with pytest.raises(EventValidationError, match="not declared"):
            ctx.send_event("unknown.event", '"value"')


class TestClearPendingEvents:
    """Tests for clear_pending_events method."""

    def test_returns_and_clears_events(self, tmp_path: Path) -> None:
        """Should return pending events and clear the list."""
        manifest = create_manifest(
            events={"event1": {"type": "string"}, "event2": {"type": "string"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        ctx.send_event("event1", '"value1"')
        ctx.send_event("event2", '"value2"')

        result = ctx.clear_pending_events()

        assert result == [
            {"name": "event1", "value": '"value1"'},
            {"name": "event2", "value": '"value2"'},
        ]
        assert not ctx.clear_pending_events()

    def test_returns_empty_when_no_events(self, tmp_path: Path) -> None:
        """Should return empty list when no events pending."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        assert not ctx.clear_pending_events()
