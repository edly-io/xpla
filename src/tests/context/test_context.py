import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.error

import pytest

from xpla.lib.context import ActivityContext, MissingSandboxError
from xpla.lib.events import EventValidationError
from xpla.lib.fields import FieldValidationError

from .utils import (
    create_manifest,
    make_kv_store,
    setup_activity_dir,
    make_activity_context,
)


class TestActivityContextInit:
    """Tests for ActivityContext initialization."""

    def test_init_creates_kv_store(self, tmp_path: Path) -> None:
        """Should create a KV store at the expected path."""
        manifest = create_manifest()
        ctx = make_activity_context(tmp_path, manifest)

        assert ctx.kv_store is not None

    def test_init_loads_manifest(self, tmp_path: Path) -> None:
        """Should load manifest from activity directory."""
        manifest = create_manifest("my-activity", {"http": {}})
        ctx = make_activity_context(tmp_path, manifest)

        assert ctx.manifest.name == "my-activity"
        assert ctx.manifest.capabilities is not None
        assert ctx.manifest.capabilities.http is not None

    def test_init_creates_capability_checker(self, tmp_path: Path) -> None:
        """Should create a CapabilityChecker from manifest."""
        manifest = create_manifest(capabilities={"http": {}})
        ctx = make_activity_context(tmp_path, manifest)

        assert ctx.capability_checker is not None
        # Should not raise for http capability
        ctx.capability_checker.check_http_request("https://example.com")

    def test_init_without_sandbox(self, tmp_path: Path) -> None:
        """Should set sandbox to None when no wasm file exists."""
        manifest = create_manifest()
        ctx = make_activity_context(tmp_path, manifest)

        assert ctx.sandbox is None

    @patch("xpla.lib.context.SandboxExecutor")
    def test_init_with_sandbox(
        self, mock_sandbox_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Should create SandboxExecutor when server is declared in manifest."""
        manifest = create_manifest(server="server.wasm")
        activity_dir = setup_activity_dir(tmp_path, manifest)
        (activity_dir / "server.wasm").write_bytes(b"fake wasm")

        ctx = ActivityContext(activity_dir, make_kv_store())

        mock_sandbox_executor.assert_called_once()
        assert ctx.sandbox is not None


class TestActivityContextProperties:
    """Tests for ActivityContext properties."""

    def test_name_property(self, tmp_path: Path) -> None:
        """Should return the activity name from manifest."""
        manifest = create_manifest("quiz-activity")
        ctx = make_activity_context(tmp_path, manifest)

        assert ctx.name == "quiz-activity"

    def test_client_path_property(self, tmp_path: Path) -> None:
        """Should return client path from manifest."""
        manifest = create_manifest(client="src/my-client.js")
        ctx = make_activity_context(tmp_path, manifest)

        assert ctx.client_path == "src/my-client.js"


class TestCallSandboxFunction:
    """Tests for call_sandbox_function method."""

    def test_raises_when_no_sandbox(self, tmp_path: Path) -> None:
        """Should raise MissingSandboxError when sandbox is None."""
        manifest = create_manifest()
        ctx = make_activity_context(tmp_path, manifest)

        with pytest.raises(MissingSandboxError):
            ctx.call_sandbox_function("test_fn", "input")

    @patch("xpla.lib.context.SandboxExecutor")
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

        ctx = ActivityContext(activity_dir, make_kv_store())
        result = ctx.call_sandbox_function("my_function", "input_data")

        mock_sandbox.call_function.assert_called_once_with("my_function", "input_data")
        assert result == b"result"


class TestHostFunctions:
    """Tests for host_functions method."""

    def test_returns_expected_functions(self, tmp_path: Path) -> None:
        """Should return list of host function callables."""
        manifest = create_manifest()
        ctx = make_activity_context(tmp_path, manifest)

        functions = ctx.host_functions()

        function_names = [f.__name__ for f in functions]
        assert function_names == [
            "send_event",
            "get_field",
            "set_field",
            "log_get",
            "log_get_range",
            "log_append",
            "log_delete",
            "log_delete_range",
            "http_request",
            "submit_grade",
        ]


class TestHttpRequest:
    """Tests for http_request host function."""

    def test_error_when_no_http_capability(self, tmp_path: Path) -> None:
        """Should return status=0 when no HTTP capability declared."""
        manifest = create_manifest(capabilities={})
        ctx = make_activity_context(tmp_path, manifest)

        result = ctx.http_request("https://example.com", "GET", b"", ())

        data = json.loads(result)
        assert data["status"] == 0
        assert data["headers"] == []
        assert "not declared" in data["body"]

    def test_error_when_host_not_allowed(self, tmp_path: Path) -> None:
        """Should return status=0 when host not in allowed list."""
        manifest = create_manifest(
            capabilities={"http": {"allowed_hosts": ["api.example.com"]}}
        )
        ctx = make_activity_context(tmp_path, manifest)

        result = ctx.http_request("https://evil.com/hack", "GET", b"", ())

        data = json.loads(result)
        assert data["status"] == 0
        assert "not allowed" in data["body"]

    @patch("xpla.lib.context.urllib.request.urlopen")
    def test_success_when_allowed(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        """Should return structured response with status, headers, body."""
        manifest = create_manifest(
            capabilities={"http": {"allowed_hosts": ["api.example.com"]}}
        )
        ctx = make_activity_context(tmp_path, manifest)

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"data": "test"}'
        mock_response.status = 200
        mock_response.getheaders.return_value = [
            ("Content-Type", "application/json"),
        ]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = ctx.http_request(
            "https://api.example.com/data",
            "POST",
            b"body",
            (("Content-Type", "application/json"),),
        )

        data = json.loads(result)
        assert data["status"] == 200
        assert data["body"] == '{"data": "test"}'
        assert ["Content-Type", "application/json"] in data["headers"]
        mock_urlopen.assert_called_once()

    @patch("xpla.lib.context.urllib.request.urlopen")
    def test_handles_http_error(self, mock_urlopen: MagicMock, tmp_path: Path) -> None:
        """Should return structured response on HTTPError."""
        manifest = create_manifest(capabilities={"http": {}})
        ctx = make_activity_context(tmp_path, manifest)

        error = urllib.error.HTTPError(
            "https://example.com", 404, "Not Found", {}, None  # type: ignore[arg-type]
        )
        error.read = MagicMock(return_value=b"not found")  # type: ignore[method-assign]
        mock_urlopen.side_effect = error

        result = ctx.http_request("https://example.com", "GET", b"", ())

        data = json.loads(result)
        assert data["status"] == 404
        assert data["body"] == "not found"

    @patch("xpla.lib.context.urllib.request.urlopen")
    def test_handles_url_error(self, mock_urlopen: MagicMock, tmp_path: Path) -> None:
        """Should return status=0 on URLError."""
        manifest = create_manifest(capabilities={"http": {}})
        ctx = make_activity_context(tmp_path, manifest)

        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        result = ctx.http_request("https://example.com", "GET", b"", ())

        data = json.loads(result)
        assert data["status"] == 0
        assert "Connection refused" in data["body"]

    @patch("xpla.lib.context.urllib.request.urlopen")
    def test_permissive_mode_allows_all_hosts(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        """Should allow all hosts when allowed_hosts is empty."""
        manifest = create_manifest(capabilities={"http": {}})
        ctx = make_activity_context(tmp_path, manifest)

        mock_response = MagicMock()
        mock_response.read.return_value = b"ok"
        mock_response.status = 200
        mock_response.getheaders.return_value = []
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = ctx.http_request("https://any-host.com/api", "GET", b"", ())

        data = json.loads(result)
        assert data["status"] == 200
        assert data["body"] == "ok"


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
        ctx = make_activity_context(tmp_path, manifest)

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
        ctx = make_activity_context(tmp_path, manifest)
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
        ctx = make_activity_context(tmp_path, manifest)
        user = "alice"

        ctx.store_field("c", "a", user, "score", 42)
        result = ctx.load_field("c", "a", user, "score")

        assert result == 42

    def test_raises_for_undeclared_field(self, tmp_path: Path) -> None:
        """Should raise for field not declared in manifest."""
        manifest = create_manifest(
            fields={"score": {"type": "integer", "scope": "user,activity"}}
        )
        ctx = make_activity_context(tmp_path, manifest)

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
        ctx = make_activity_context(tmp_path, manifest)
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
        ctx = make_activity_context(tmp_path, manifest)

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
        ctx = make_activity_context(tmp_path, manifest)
        user = "alice"

        ctx.store_field("c", "a", user, "count", 42)

        assert ctx.load_field("c", "a", user, "count") == 42

    def test_stores_float(self, tmp_path: Path) -> None:
        """Should store and retrieve float value."""
        manifest = create_manifest(
            fields={"ratio": {"type": "number", "scope": "user,activity"}}
        )
        ctx = make_activity_context(tmp_path, manifest)
        user = "alice"

        ctx.store_field("c", "a", user, "ratio", 3.14)

        assert ctx.load_field("c", "a", user, "ratio") == 3.14

    def test_stores_string(self, tmp_path: Path) -> None:
        """Should store and retrieve string value."""
        manifest = create_manifest(
            fields={"name": {"type": "string", "scope": "user,activity"}}
        )
        ctx = make_activity_context(tmp_path, manifest)
        user = "alice"

        ctx.store_field("c", "a", user, "name", "Alice")

        assert ctx.load_field("c", "a", user, "name") == "Alice"

    def test_stores_boolean(self, tmp_path: Path) -> None:
        """Should store and retrieve boolean value."""
        manifest = create_manifest(
            fields={"completed": {"type": "boolean", "scope": "user,activity"}}
        )
        ctx = make_activity_context(tmp_path, manifest)
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
        ctx = make_activity_context(tmp_path, manifest)
        user = "alice"

        ctx.store_field("c", "a", user, "tags", ["a", "b", "c"])

        assert ctx.load_field("c", "a", user, "tags") == ["a", "b", "c"]

    def test_raises_for_wrong_type(self, tmp_path: Path) -> None:
        """Should raise when value type doesn't match declaration."""
        manifest = create_manifest(
            fields={"count": {"type": "integer", "scope": "user,activity"}}
        )
        ctx = make_activity_context(tmp_path, manifest)
        user = "alice"

        with pytest.raises(FieldValidationError, match="failed validation"):
            ctx.store_field("c", "a", user, "count", "not an int")

    def test_raises_for_undeclared_field(self, tmp_path: Path) -> None:
        """Should raise for field not declared in manifest."""
        manifest = create_manifest(
            fields={"score": {"type": "integer", "scope": "user,activity"}}
        )
        ctx = make_activity_context(tmp_path, manifest)
        user = "alice"

        with pytest.raises(FieldValidationError, match="not declared"):
            ctx.store_field("c", "a", user, "unknown", 42)

    def test_overwrites_existing_value(self, tmp_path: Path) -> None:
        """Should overwrite previously stored value."""
        manifest = create_manifest(
            fields={"count": {"type": "integer", "scope": "user,activity"}}
        )
        ctx = make_activity_context(tmp_path, manifest)
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
        ctx = make_activity_context(tmp_path, manifest)

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
        ctx = make_activity_context(tmp_path, manifest)

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
        ctx = make_activity_context(tmp_path, manifest)

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
        ctx = make_activity_context(tmp_path, manifest)

        ctx.store_field("", "", "", "global_setting", "on")
        ctx.store_field("", "", ctx.user_id, "global_pref", "dark")

        result = ctx.get_all_fields()
        assert result == {"global_setting": "on", "global_pref": "dark"}


class TestScopeAwareGetSetField:
    """Tests for scope-aware get_field/set_field host functions."""

    def test_activity_scope(self, tmp_path: Path) -> None:
        """Should get/set activity-scoped fields."""
        manifest = create_manifest(
            fields={"question": {"type": "string", "scope": "activity", "default": ""}}
        )
        ctx = make_activity_context(tmp_path, manifest)

        assert ctx.get_field("question", {}) == ""
        ctx.set_field("question", "What is 2+2?", {})
        assert ctx.get_field("question", {}) == "What is 2+2?"

    def test_user_activity_scope(self, tmp_path: Path) -> None:
        """Should get/set user,activity-scoped fields."""
        manifest = create_manifest(
            fields={
                "score": {"type": "integer", "scope": "user,activity", "default": 0}
            }
        )
        ctx = make_activity_context(tmp_path, manifest)
        ctx.user_id = "alice"

        assert ctx.get_field("score", {}) == 0
        ctx.set_field("score", 42, {})
        assert ctx.get_field("score", {}) == 42

    def test_course_scope(self, tmp_path: Path) -> None:
        """Should get/set course-scoped fields."""
        manifest = create_manifest(
            fields={"total": {"type": "integer", "scope": "course", "default": 0}}
        )
        ctx = make_activity_context(tmp_path, manifest)

        assert ctx.get_field("total", {}) == 0
        ctx.set_field("total", 99, {})
        assert ctx.get_field("total", {}) == 99

    def test_user_course_scope(self, tmp_path: Path) -> None:
        """Should get/set user,course-scoped fields."""
        manifest = create_manifest(
            fields={"grade": {"type": "integer", "scope": "user,course", "default": 0}}
        )
        ctx = make_activity_context(tmp_path, manifest)
        ctx.user_id = "alice"

        assert ctx.get_field("grade", {}) == 0
        ctx.set_field("grade", 85, {})
        assert ctx.get_field("grade", {}) == 85

    def test_global_scope(self, tmp_path: Path) -> None:
        """Should get/set global-scoped fields."""
        manifest = create_manifest(
            fields={"setting": {"type": "string", "scope": "global", "default": ""}}
        )
        ctx = make_activity_context(tmp_path, manifest)

        assert ctx.get_field("setting", {}) == ""
        ctx.set_field("setting", "dark", {})
        assert ctx.get_field("setting", {}) == "dark"

    def test_user_global_scope(self, tmp_path: Path) -> None:
        """Should get/set user,global-scoped fields."""
        manifest = create_manifest(
            fields={"pref": {"type": "string", "scope": "user,global", "default": ""}}
        )
        ctx = make_activity_context(tmp_path, manifest)
        ctx.user_id = "alice"

        assert ctx.get_field("pref", {}) == ""
        ctx.set_field("pref", "en", {})
        assert ctx.get_field("pref", {}) == "en"

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
        ctx = make_activity_context(tmp_path, manifest)

        ctx.set_field("count_activity", 10, {})
        ctx.set_field("count_course", 20, {})

        assert ctx.get_field("count_activity", {}) == 10
        assert ctx.get_field("count_course", {}) == 20


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
        ctx = make_activity_context(tmp_path, manifest)
        ctx.user_id = "alice"

        result = ctx.get_state()
        assert result == {"score": 0}

    @patch("xpla.lib.context.SandboxExecutor")
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

        ctx = ActivityContext(activity_dir, make_kv_store())
        result = ctx.get_state()

        expected_input = {
            "scope": {
                "user_id": ActivityContext.DEFAULT_USER_ID,
                "course_id": ActivityContext.DEFAULT_COURSE_ID,
                "activity_id": ActivityContext.DEFAULT_ACTIVITY_ID,
            },
            "permission": ActivityContext.DEFAULT_PERMISSION.value,
        }
        mock_sandbox.call_function.assert_called_once_with("getState", expected_input)
        assert result == {"question": "test"}

    @patch("xpla.lib.context.SandboxExecutor")
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

        ctx = ActivityContext(activity_dir, make_kv_store())
        ctx.user_id = "alice"
        result = ctx.get_state()

        assert result == {"score": 0}


class TestSendEvent:
    """Tests for send_event host function."""

    def test_appends_event_to_pending(self, tmp_path: Path) -> None:
        """Should append event to pending events list with scope and permission."""
        manifest = create_manifest(events={"test.event": {"type": "string"}})
        ctx = make_activity_context(tmp_path, manifest)

        ctx.send_event("test.event", '"some value"', "{}", "play")

        events = ctx.clear_pending_events()
        assert len(events) == 1
        assert events[0]["name"] == "test.event"
        assert events[0]["value"] == '"some value"'
        assert events[0]["permission"] == "play"
        # Empty scope should be filled with defaults
        scope = events[0]["scope"]
        assert isinstance(scope, dict)
        assert scope["activity_id"] == ctx.activity_id
        assert scope["course_id"] == ctx.course_id

    def test_appends_multiple_events(self, tmp_path: Path) -> None:
        """Should accumulate multiple events."""
        manifest = create_manifest(
            events={"event1": {"type": "string"}, "event2": {"type": "string"}}
        )
        ctx = make_activity_context(tmp_path, manifest)

        ctx.send_event("event1", '"value1"', "{}", "play")
        ctx.send_event("event2", '"value2"', "{}", "edit")

        events = ctx.clear_pending_events()
        assert len(events) == 2
        assert events[0]["name"] == "event1"
        assert events[0]["permission"] == "play"
        assert events[1]["name"] == "event2"
        assert events[1]["permission"] == "edit"

    def test_returns_empty_string(self, tmp_path: Path) -> None:
        """Should return empty string as success indicator."""
        manifest = create_manifest(events={"test": {"type": "string"}})
        ctx = make_activity_context(tmp_path, manifest)

        result = ctx.send_event("test", '"value"', "{}", "play")

        assert result == ""

    def test_allows_declared_fields_change_events(self, tmp_path: Path) -> None:
        """Should allow fields.change.* events when declared in manifest."""
        manifest = create_manifest(events={"fields.change.score": {"type": "integer"}})
        ctx = make_activity_context(tmp_path, manifest)

        ctx.send_event("fields.change.score", "42", "{}", "play")

        events = ctx.clear_pending_events()
        assert len(events) == 1
        assert events[0]["name"] == "fields.change.score"
        assert events[0]["value"] == "42"

    def test_raises_for_undeclared_event(self, tmp_path: Path) -> None:
        """Should raise EventValidationError for undeclared event."""
        manifest = create_manifest(events={"declared.event": {"type": "string"}})
        ctx = make_activity_context(tmp_path, manifest)

        with pytest.raises(EventValidationError, match="not declared"):
            ctx.send_event("unknown.event", '"value"', "{}", "play")

    def test_explicit_scope_preserved(self, tmp_path: Path) -> None:
        """Should preserve explicit scope without filling defaults."""
        manifest = create_manifest(events={"test": {"type": "string"}})
        ctx = make_activity_context(tmp_path, manifest)

        ctx.send_event("test", '"val"', '{"user_id": "bob"}', "view")

        events = ctx.clear_pending_events()
        assert events[0]["scope"] == {"user_id": "bob"}
        assert events[0]["permission"] == "view"


class TestClearPendingEvents:
    """Tests for clear_pending_events method."""

    def test_returns_and_clears_events(self, tmp_path: Path) -> None:
        """Should return pending events and clear the list."""
        manifest = create_manifest(
            events={"event1": {"type": "string"}, "event2": {"type": "string"}}
        )
        ctx = make_activity_context(tmp_path, manifest)
        ctx.send_event("event1", '"value1"', "{}", "play")
        ctx.send_event("event2", '"value2"', "{}", "play")

        result = ctx.clear_pending_events()

        assert len(result) == 2
        assert result[0]["name"] == "event1"
        assert result[1]["name"] == "event2"
        assert not ctx.clear_pending_events()

    def test_returns_empty_when_no_events(self, tmp_path: Path) -> None:
        """Should return empty list when no events pending."""
        manifest = create_manifest()
        ctx = make_activity_context(tmp_path, manifest)
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
        ctx = make_activity_context(tmp_path, manifest)
        ctx.user_id = "alice"

        # Set a field for bob via scope override
        ctx.set_field("score", 42, {"user_id": "bob"})

        # Read bob's field via scope override
        assert ctx.get_field("score", {"user_id": "bob"}) == 42
        # Alice's own field is still the default
        assert ctx.get_field("score", {}) == 0

    def test_set_field_with_user_override(self, tmp_path: Path) -> None:
        """Should write another user's user,activity field via scope override."""
        manifest = create_manifest(
            fields={
                "score": {"type": "integer", "scope": "user,activity", "default": 0}
            }
        )
        ctx = make_activity_context(tmp_path, manifest)
        ctx.user_id = "alice"

        ctx.set_field("score", 99, {"user_id": "bob"})

        assert ctx.get_field("score", {"user_id": "bob"}) == 99
        # Alice's field unchanged
        assert ctx.get_field("score", {}) == 0

    def test_scope_override_invalid_key_raises(self, tmp_path: Path) -> None:
        """Should raise FieldValidationError for invalid override key on course-scoped field."""
        manifest = create_manifest(
            fields={"total": {"type": "integer", "scope": "course", "default": 0}}
        )
        ctx = make_activity_context(tmp_path, manifest)

        with pytest.raises(FieldValidationError, match="Invalid scope override"):
            ctx.get_field("total", {"instance_id": "other"})

    def test_scope_override_user_id_on_non_user_scoped_raises(
        self, tmp_path: Path
    ) -> None:
        """Should raise FieldValidationError when passing user_id on activity-scoped field."""
        manifest = create_manifest(
            fields={"question": {"type": "string", "scope": "activity", "default": ""}}
        )
        ctx = make_activity_context(tmp_path, manifest)

        with pytest.raises(FieldValidationError, match="Invalid scope override"):
            ctx.get_field("question", {"user_id": "bob"})
