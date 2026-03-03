import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
import urllib.error

import pytest

from server.activities.context import ActivityContext, MissingSandboxError
from server.activities.events import EventValidationError
from server.activities.permission import Permission
from server.activities.fields import FieldValidationError


def create_manifest(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    name: str = "test-activity",
    capabilities: dict[str, Any] | None = None,
    fields: dict[str, Any] | None = None,
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
    if fields is not None:
        manifest["fields"] = fields
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

        assert ctx.capability_checker is not None
        # Should not raise for http capability
        ctx.capability_checker.check_http_request("https://example.com")

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

    def test_name_property(self, tmp_path: Path) -> None:
        """Should return the activity name from manifest."""
        manifest = create_manifest("quiz-activity")
        activity_dir = setup_activity_dir(tmp_path, manifest)

        ctx = ActivityContext(activity_dir)

        assert ctx.name == "quiz-activity"

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
        assert function_names == [
            "get_permission",
            "send_event",
            "get_field",
            "set_field",
            "http_request",
            "submit_grade",
        ]


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


class TestLoadField:
    """Tests for load_field method."""

    def test_returns_default_when_not_set(self, tmp_path: Path) -> None:
        """Should return default value when field not yet stored."""
        manifest = create_manifest(
            fields={
                "score": {
                    "type": "integer",
                    "scope": "user,activity",
                    "default": 0,
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.load_field("c", "a", "alice", "score")

        assert result == 0

    def test_returns_type_default_when_no_explicit_default(
        self, tmp_path: Path
    ) -> None:
        """Should return type-specific default when no explicit default."""
        manifest = create_manifest(
            fields={
                "count": {"type": "integer", "scope": "user,activity"},
                "ratio": {"type": "number", "scope": "user,activity"},
                "name": {"type": "string", "scope": "user,activity"},
                "done": {"type": "boolean", "scope": "user,activity"},
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = "alice"

        assert ctx.load_field("c", "a", user, "count") == 0
        assert ctx.load_field("c", "a", user, "ratio") == 0.0
        assert ctx.load_field("c", "a", user, "name") == ""
        assert ctx.load_field("c", "a", user, "done") is False

    def test_returns_stored_value(self, tmp_path: Path) -> None:
        """Should return stored value when set."""
        manifest = create_manifest(
            fields={
                "score": {
                    "type": "integer",
                    "scope": "user,activity",
                    "default": 0,
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = "alice"

        ctx.store_field("c", "a", user, "score", 42)
        result = ctx.load_field("c", "a", user, "score")

        assert result == 42

    def test_raises_for_undeclared_field(self, tmp_path: Path) -> None:
        """Should raise for field not declared in manifest."""
        manifest = create_manifest(
            fields={"score": {"type": "integer", "scope": "user,activity"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        with pytest.raises(FieldValidationError, match="not declared"):
            ctx.load_field("c", "a", "alice", "unknown")

    def test_fields_isolated_by_user(self, tmp_path: Path) -> None:
        """Should store separate values for different users."""
        manifest = create_manifest(
            fields={
                "score": {
                    "type": "integer",
                    "scope": "user,activity",
                    "default": 0,
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        base_user = "alice"

        ctx.store_field("c", "a", f"{base_user}_1", "score", 10)
        ctx.store_field("c", "a", f"{base_user}_2", "score", 20)

        assert ctx.load_field("c", "a", f"{base_user}_1", "score") == 10
        assert ctx.load_field("c", "a", f"{base_user}_2", "score") == 20

    def test_shared_field_uses_empty_user_id(self, tmp_path: Path) -> None:
        """Should use empty string for shared (non-user) fields."""
        manifest = create_manifest(
            fields={
                "question": {
                    "type": "string",
                    "scope": "activity",
                    "default": "",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.store_field("c", "a", "", "question", "What is 2+2?")
        result = ctx.load_field("c", "a", "", "question")

        assert result == "What is 2+2?"


class TestStoreField:
    """Tests for store_field method."""

    def test_stores_integer(self, tmp_path: Path) -> None:
        """Should store and retrieve integer value."""
        manifest = create_manifest(
            fields={"count": {"type": "integer", "scope": "user,activity"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = "alice"

        ctx.store_field("c", "a", user, "count", 42)

        assert ctx.load_field("c", "a", user, "count") == 42

    def test_stores_float(self, tmp_path: Path) -> None:
        """Should store and retrieve float value."""
        manifest = create_manifest(
            fields={"ratio": {"type": "number", "scope": "user,activity"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = "alice"

        ctx.store_field("c", "a", user, "ratio", 3.14)

        assert ctx.load_field("c", "a", user, "ratio") == 3.14

    def test_stores_string(self, tmp_path: Path) -> None:
        """Should store and retrieve string value."""
        manifest = create_manifest(
            fields={"name": {"type": "string", "scope": "user,activity"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = "alice"

        ctx.store_field("c", "a", user, "name", "Alice")

        assert ctx.load_field("c", "a", user, "name") == "Alice"

    def test_stores_boolean(self, tmp_path: Path) -> None:
        """Should store and retrieve boolean value."""
        manifest = create_manifest(
            fields={"completed": {"type": "boolean", "scope": "user,activity"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = "alice"

        ctx.store_field("c", "a", user, "completed", True)

        assert ctx.load_field("c", "a", user, "completed") is True

    def test_stores_array(self, tmp_path: Path) -> None:
        """Should store and retrieve array value."""
        manifest = create_manifest(
            fields={
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "scope": "user,activity",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = "alice"

        ctx.store_field("c", "a", user, "tags", ["a", "b", "c"])

        assert ctx.load_field("c", "a", user, "tags") == ["a", "b", "c"]

    def test_raises_for_wrong_type(self, tmp_path: Path) -> None:
        """Should raise when value type doesn't match declaration."""
        manifest = create_manifest(
            fields={"count": {"type": "integer", "scope": "user,activity"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = "alice"

        with pytest.raises(FieldValidationError, match="failed validation"):
            ctx.store_field("c", "a", user, "count", "not an int")

    def test_raises_for_undeclared_field(self, tmp_path: Path) -> None:
        """Should raise for field not declared in manifest."""
        manifest = create_manifest(
            fields={"score": {"type": "integer", "scope": "user,activity"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = "alice"

        with pytest.raises(FieldValidationError, match="not declared"):
            ctx.store_field("c", "a", user, "unknown", 42)

    def test_overwrites_existing_value(self, tmp_path: Path) -> None:
        """Should overwrite previously stored value."""
        manifest = create_manifest(
            fields={"count": {"type": "integer", "scope": "user,activity"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = "alice"

        ctx.store_field("c", "a", user, "count", 10)
        ctx.store_field("c", "a", user, "count", 20)

        assert ctx.load_field("c", "a", user, "count") == 20


class TestGetAllFields:
    """Tests for get_all_fields method."""

    def test_returns_all_fields(self, tmp_path: Path) -> None:
        """Should return all declared fields."""
        manifest = create_manifest(
            fields={
                "public": {"type": "string", "scope": "activity"},
                "secret": {"type": "string", "scope": "activity"},
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.get_all_fields()
        assert "public" in result
        assert "secret" in result

    def test_includes_user_scoped_fields(self, tmp_path: Path) -> None:
        """Should include user-scoped fields loaded for the given user."""
        manifest = create_manifest(
            fields={
                "score": {
                    "type": "integer",
                    "scope": "user,activity",
                    "default": 0,
                },
                "question": {
                    "type": "string",
                    "scope": "activity",
                    "default": "",
                },
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.store_field(ctx.course_id, ctx.activity_id, ctx.user_id, "score", 42)
        ctx.store_field(ctx.course_id, ctx.activity_id, "", "question", "What is 2+2?")

        result = ctx.get_all_fields()
        assert result == {"score": 42, "question": "What is 2+2?"}

    def test_includes_course_scoped_fields(self, tmp_path: Path) -> None:
        """Should include course-scoped and user,course-scoped fields."""
        manifest = create_manifest(
            fields={
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

        ctx.store_field(ctx.course_id, "", "", "course_total", 100)
        ctx.store_field(ctx.course_id, "", ctx.user_id, "course_score", 85)

        result = ctx.get_all_fields()
        assert result == {"course_total": 100, "course_score": 85}

    def test_includes_global_scoped_fields(self, tmp_path: Path) -> None:
        """Should include global-scoped and user,global-scoped fields."""
        manifest = create_manifest(
            fields={
                "global_setting": {
                    "type": "string",
                    "scope": "global",
                    "default": "",
                },
                "global_pref": {
                    "type": "string",
                    "scope": "user,global",
                    "default": "",
                },
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.store_field("", "", "", "global_setting", "on")
        ctx.store_field("", "", ctx.user_id, "global_pref", "dark")

        result = ctx.get_all_fields()
        assert result == {"global_setting": "on", "global_pref": "dark"}


class TestGetPermission:
    """Tests for get_permission host function."""

    def test_default_permission(self, tmp_path: Path) -> None:
        """Should default to 'play' permission."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        assert ctx.get_permission() == "play"

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


class TestScopeAwareGetSetField:
    """Tests for scope-aware get_field/set_field host functions."""

    def test_activity_scope(self, tmp_path: Path) -> None:
        """Should get/set activity-scoped fields."""
        manifest = create_manifest(
            fields={"question": {"type": "string", "scope": "activity", "default": ""}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        assert json.loads(ctx.get_field("question", "{}")) == ""
        ctx.set_field("question", '"What is 2+2?"', "{}")
        assert json.loads(ctx.get_field("question", "{}")) == "What is 2+2?"

    def test_user_activity_scope(self, tmp_path: Path) -> None:
        """Should get/set user,activity-scoped fields."""
        manifest = create_manifest(
            fields={
                "score": {"type": "integer", "scope": "user,activity", "default": 0}
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        ctx.user_id = "alice"

        assert json.loads(ctx.get_field("score", "{}")) == 0
        ctx.set_field("score", "42", "{}")
        assert json.loads(ctx.get_field("score", "{}")) == 42

    def test_course_scope(self, tmp_path: Path) -> None:
        """Should get/set course-scoped fields."""
        manifest = create_manifest(
            fields={"total": {"type": "integer", "scope": "course", "default": 0}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        assert json.loads(ctx.get_field("total", "{}")) == 0
        ctx.set_field("total", "99", "{}")
        assert json.loads(ctx.get_field("total", "{}")) == 99

    def test_user_course_scope(self, tmp_path: Path) -> None:
        """Should get/set user,course-scoped fields."""
        manifest = create_manifest(
            fields={"grade": {"type": "integer", "scope": "user,course", "default": 0}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        ctx.user_id = "alice"

        assert json.loads(ctx.get_field("grade", "{}")) == 0
        ctx.set_field("grade", "85", "{}")
        assert json.loads(ctx.get_field("grade", "{}")) == 85

    def test_global_scope(self, tmp_path: Path) -> None:
        """Should get/set global-scoped fields."""
        manifest = create_manifest(
            fields={"setting": {"type": "string", "scope": "global", "default": ""}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        assert json.loads(ctx.get_field("setting", "{}")) == ""
        ctx.set_field("setting", '"dark"', "{}")
        assert json.loads(ctx.get_field("setting", "{}")) == "dark"

    def test_user_global_scope(self, tmp_path: Path) -> None:
        """Should get/set user,global-scoped fields."""
        manifest = create_manifest(
            fields={"pref": {"type": "string", "scope": "user,global", "default": ""}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        ctx.user_id = "alice"

        assert json.loads(ctx.get_field("pref", "{}")) == ""
        ctx.set_field("pref", '"en"', "{}")
        assert json.loads(ctx.get_field("pref", "{}")) == "en"

    def test_different_scopes_isolated(self, tmp_path: Path) -> None:
        """Fields with different scopes should not collide."""
        manifest = create_manifest(
            fields={
                "count_activity": {
                    "type": "integer",
                    "scope": "activity",
                    "default": 0,
                },
                "count_course": {"type": "integer", "scope": "course", "default": 0},
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.set_field("count_activity", "10", "{}")
        ctx.set_field("count_course", "20", "{}")

        assert json.loads(ctx.get_field("count_activity", "{}")) == 10
        assert json.loads(ctx.get_field("count_course", "{}")) == 20


class TestGetState:
    """Tests for get_state method."""

    def test_fallback_without_sandbox(self, tmp_path: Path) -> None:
        """Should fall back to get_all_fields when no sandbox exists."""
        manifest = create_manifest(
            fields={
                "score": {
                    "type": "integer",
                    "scope": "user,activity",
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
        """Should fall back to get_all_fields when getState raises RuntimeError."""
        manifest = create_manifest(
            server="server.wasm",
            fields={
                "score": {
                    "type": "integer",
                    "scope": "user,activity",
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

    def test_allows_declared_fields_change_events(self, tmp_path: Path) -> None:
        """Should allow fields.change.* events when declared in manifest."""
        manifest = create_manifest(events={"fields.change.score": {"type": "integer"}})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.send_event("fields.change.score", "42")

        assert ctx.clear_pending_events() == [
            {"name": "fields.change.score", "value": "42"}
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


class TestFieldScopeOverrides:
    """Tests for get_field/set_field with scope overrides."""

    def test_get_field_with_user_override(self, tmp_path: Path) -> None:
        """Should read another user's user,activity field via scope override."""
        manifest = create_manifest(
            fields={
                "score": {"type": "integer", "scope": "user,activity", "default": 0}
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        ctx.user_id = "alice"

        # Set a field for bob via scope override
        ctx.set_field("score", "42", '{"user_id": "bob"}')

        # Read bob's field via scope override
        assert json.loads(ctx.get_field("score", '{"user_id": "bob"}')) == 42
        # Alice's own field is still the default
        assert json.loads(ctx.get_field("score", "{}")) == 0

    def test_set_field_with_user_override(self, tmp_path: Path) -> None:
        """Should write another user's user,activity field via scope override."""
        manifest = create_manifest(
            fields={
                "score": {"type": "integer", "scope": "user,activity", "default": 0}
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        ctx.user_id = "alice"

        ctx.set_field("score", "99", '{"user_id": "bob"}')

        assert json.loads(ctx.get_field("score", '{"user_id": "bob"}')) == 99
        # Alice's field unchanged
        assert json.loads(ctx.get_field("score", "{}")) == 0

    def test_scope_override_invalid_key_raises(self, tmp_path: Path) -> None:
        """Should raise FieldValidationError for invalid override key on course-scoped field."""
        manifest = create_manifest(
            fields={"total": {"type": "integer", "scope": "course", "default": 0}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        with pytest.raises(FieldValidationError, match="Invalid scope override"):
            ctx.get_field("total", '{"instance_id": "other"}')

    def test_scope_override_user_id_on_non_user_scoped_raises(
        self, tmp_path: Path
    ) -> None:
        """Should raise FieldValidationError when passing user_id on activity-scoped field."""
        manifest = create_manifest(
            fields={"question": {"type": "string", "scope": "activity", "default": ""}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        with pytest.raises(FieldValidationError, match="Invalid scope override"):
            ctx.get_field("question", '{"user_id": "bob"}')
