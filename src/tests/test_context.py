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

    def test_sandbox_path_property(self, tmp_path: Path) -> None:
        """Should return path to server.wasm."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)

        ctx = ActivityContext(activity_dir)

        assert ctx.sandbox_path == activity_dir / "server.wasm"


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
        (activity_dir / "server.wasm").write_bytes(b"fake wasm")

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

        assert len(functions) == 6
        function_names = [f.__name__ for f in functions]
        assert "lms_submit_grade" in function_names
        assert "http_request" in function_names
        assert "get_user_id" in function_names
        assert "post_event" in function_names
        assert "get_value" in function_names
        assert "set_value" in function_names


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
    """Tests for get_user_id host function."""

    def test_success_when_allowed(self, tmp_path: Path) -> None:
        """Should return user info when LMS capability allows get_user."""
        manifest = create_manifest(capabilities={"lms": ["get_user"]})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.get_user_id("")

        data = json.loads(result)
        assert "id" in data

    def test_error_when_not_allowed(self, tmp_path: Path) -> None:
        """Should return error when LMS capability doesn't allow get_user."""
        manifest = create_manifest(capabilities={"lms": ["submit_grade"]})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.get_user_id("")

        data = json.loads(result)
        assert "error" in data
        assert "not allowed" in data["error"]

    def test_error_when_no_lms_capability(self, tmp_path: Path) -> None:
        """Should return error when no LMS capability declared."""
        manifest = create_manifest(capabilities={})
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.get_user_id("")

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


class TestLoadValue:
    """Tests for load_value method."""

    def test_returns_default_when_not_set(self, tmp_path: Path) -> None:
        """Should return default value when value not yet stored."""
        manifest = create_manifest(
            values={
                "score": {
                    "type": "integer",
                    "scope": "user,unit",
                    "access": "user",
                    "default": 0,
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.load_value(unique_user(tmp_path), "score")

        assert result == 0

    def test_returns_type_default_when_no_explicit_default(
        self, tmp_path: Path
    ) -> None:
        """Should return type-specific default when no explicit default."""
        manifest = create_manifest(
            values={
                "count": {"type": "integer", "scope": "user,unit", "access": "user"},
                "ratio": {"type": "float", "scope": "user,unit", "access": "user"},
                "name": {"type": "string", "scope": "user,unit", "access": "user"},
                "done": {"type": "boolean", "scope": "user,unit", "access": "user"},
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        assert ctx.load_value(user, "count") == 0
        assert ctx.load_value(user, "ratio") == 0.0
        assert ctx.load_value(user, "name") == ""
        assert ctx.load_value(user, "done") is False

    def test_returns_stored_value(self, tmp_path: Path) -> None:
        """Should return stored value when set."""
        manifest = create_manifest(
            values={
                "score": {
                    "type": "integer",
                    "scope": "user,unit",
                    "access": "user",
                    "default": 0,
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value(user, "score", 42)
        result = ctx.load_value(user, "score")

        assert result == 42

    def test_raises_for_undeclared_value(self, tmp_path: Path) -> None:
        """Should raise for value not declared in manifest."""
        manifest = create_manifest(
            values={
                "score": {"type": "integer", "scope": "user,unit", "access": "user"}
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        with pytest.raises(ValueValidationError, match="not declared"):
            ctx.load_value(unique_user(tmp_path), "unknown")

    def test_values_isolated_by_user(self, tmp_path: Path) -> None:
        """Should store separate values for different users."""
        manifest = create_manifest(
            values={
                "score": {
                    "type": "integer",
                    "scope": "user,unit",
                    "access": "user",
                    "default": 0,
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        base_user = unique_user(tmp_path)

        ctx.store_value(f"{base_user}_1", "score", 10)
        ctx.store_value(f"{base_user}_2", "score", 20)

        assert ctx.load_value(f"{base_user}_1", "score") == 10
        assert ctx.load_value(f"{base_user}_2", "score") == 20

    def test_shared_value_uses_empty_user_id(self, tmp_path: Path) -> None:
        """Should use empty string for shared (non-user) values."""
        manifest = create_manifest(
            values={
                "question": {
                    "type": "string",
                    "scope": "unit",
                    "access": "user",
                    "default": "",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.store_value("", "question", "What is 2+2?")
        result = ctx.load_value("", "question")

        assert result == "What is 2+2?"


class TestStoreValue:
    """Tests for store_value method."""

    def test_stores_integer(self, tmp_path: Path) -> None:
        """Should store and retrieve integer value."""
        manifest = create_manifest(
            values={
                "count": {"type": "integer", "scope": "user,unit", "access": "user"}
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value(user, "count", 42)

        assert ctx.load_value(user, "count") == 42

    def test_stores_float(self, tmp_path: Path) -> None:
        """Should store and retrieve float value."""
        manifest = create_manifest(
            values={"ratio": {"type": "float", "scope": "user,unit", "access": "user"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value(user, "ratio", 3.14)

        assert ctx.load_value(user, "ratio") == 3.14

    def test_stores_string(self, tmp_path: Path) -> None:
        """Should store and retrieve string value."""
        manifest = create_manifest(
            values={"name": {"type": "string", "scope": "user,unit", "access": "user"}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value(user, "name", "Alice")

        assert ctx.load_value(user, "name") == "Alice"

    def test_stores_boolean(self, tmp_path: Path) -> None:
        """Should store and retrieve boolean value."""
        manifest = create_manifest(
            values={
                "completed": {"type": "boolean", "scope": "user,unit", "access": "user"}
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value(user, "completed", True)

        assert ctx.load_value(user, "completed") is True

    def test_raises_for_wrong_type(self, tmp_path: Path) -> None:
        """Should raise when value type doesn't match declaration."""
        manifest = create_manifest(
            values={
                "count": {"type": "integer", "scope": "user,unit", "access": "user"}
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        with pytest.raises(ValueValidationError, match="must be integer"):
            ctx.store_value(user, "count", "not an int")

    def test_raises_for_undeclared_value(self, tmp_path: Path) -> None:
        """Should raise for value not declared in manifest."""
        manifest = create_manifest(
            values={
                "score": {"type": "integer", "scope": "user,unit", "access": "user"}
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        with pytest.raises(ValueValidationError, match="not declared"):
            ctx.store_value(user, "unknown", 42)

    def test_overwrites_existing_value(self, tmp_path: Path) -> None:
        """Should overwrite previously stored value."""
        manifest = create_manifest(
            values={
                "count": {"type": "integer", "scope": "user,unit", "access": "user"}
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value(user, "count", 10)
        ctx.store_value(user, "count", 20)

        assert ctx.load_value(user, "count") == 20


class TestGetFilteredValues:
    """Tests for get_filtered_values method."""

    def test_filters_by_access_level(self, tmp_path: Path) -> None:
        """Should exclude values above user's access level."""
        manifest = create_manifest(
            values={
                "public": {"type": "string", "scope": "unit", "access": "user"},
                "secret": {"type": "string", "scope": "unit", "access": "unit"},
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        # User with "user" access should only see public value
        result = ctx.get_filtered_values(unique_user(tmp_path), "user")
        assert "public" in result
        assert "secret" not in result

    def test_higher_access_sees_all(self, tmp_path: Path) -> None:
        """User with higher access should see all values."""
        manifest = create_manifest(
            values={
                "public": {"type": "string", "scope": "unit", "access": "user"},
                "secret": {"type": "string", "scope": "unit", "access": "unit"},
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        # User with "unit" access should see both values
        result = ctx.get_filtered_values(unique_user(tmp_path), "unit")
        assert "public" in result
        assert "secret" in result

    def test_includes_user_scoped_values(self, tmp_path: Path) -> None:
        """Should correctly handle user-scoped values with filtering."""
        manifest = create_manifest(
            values={
                "score": {
                    "type": "integer",
                    "scope": "user,unit",
                    "access": "user",
                    "default": 0,
                },
                "secret_score": {
                    "type": "integer",
                    "scope": "user,unit",
                    "access": "unit",
                    "default": 0,
                },
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        user = unique_user(tmp_path)

        ctx.store_value(user, "score", 42)
        ctx.store_value(user, "secret_score", 100)

        # User access should only see score
        result = ctx.get_filtered_values(user, "user")
        assert result == {"score": 42}

        # Unit access should see both
        result = ctx.get_filtered_values(user, "unit")
        assert result == {"score": 42, "secret_score": 100}

    def test_mcq_scenario(self, tmp_path: Path) -> None:
        """Test realistic MCQ scenario where correct_answers is hidden from students."""
        manifest = create_manifest(
            values={
                "question": {
                    "type": "string",
                    "scope": "unit",
                    "access": "user",
                    "default": "",
                },
                "answers": {
                    "type": "string",
                    "scope": "unit",
                    "access": "user",
                    "default": "[]",
                },
                "correct_answers": {
                    "type": "string",
                    "scope": "unit",
                    "access": "unit",
                    "default": "[]",
                },
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        # Set up MCQ
        ctx.store_value("", "question", "What is 2+2?")
        ctx.store_value("", "answers", '["3", "4", "5"]')
        ctx.store_value("", "correct_answers", "[1]")

        # Student (user access) should NOT see correct_answers
        student_values = ctx.get_filtered_values("student1", "user")
        assert "question" in student_values
        assert "answers" in student_values
        assert "correct_answers" not in student_values

        # Author (unit access) should see correct_answers
        author_values = ctx.get_filtered_values("author1", "unit")
        assert "question" in author_values
        assert "answers" in author_values
        assert "correct_answers" in author_values
        assert author_values["correct_answers"] == "[1]"


class TestPostEvent:
    """Tests for post_event host function."""

    def test_appends_event_to_pending(self, tmp_path: Path) -> None:
        """Should append event to pending events list."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.post_event("test.event", "some value")

        assert ctx.clear_pending_events() == [
            {"name": "test.event", "value": "some value"}
        ]

    def test_appends_multiple_events(self, tmp_path: Path) -> None:
        """Should accumulate multiple events."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.post_event("event1", "value1")
        ctx.post_event("event2", "value2")

        assert ctx.clear_pending_events() == [
            {"name": "event1", "value": "value1"},
            {"name": "event2", "value": "value2"},
        ]

    def test_returns_empty_string(self, tmp_path: Path) -> None:
        """Should return empty string as success indicator."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result = ctx.post_event("test", "value")

        assert result == ""


class TestClearPendingEvents:
    """Tests for clear_pending_events method."""

    def test_returns_and_clears_events(self, tmp_path: Path) -> None:
        """Should return pending events and clear the list."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        ctx.post_event("event1", "value1")
        ctx.post_event("event2", "value2")

        result = ctx.clear_pending_events()

        assert result == [
            {"name": "event1", "value": "value1"},
            {"name": "event2", "value": "value2"},
        ]
        assert not ctx.clear_pending_events()

    def test_returns_empty_when_no_events(self, tmp_path: Path) -> None:
        """Should return empty list when no events pending."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        assert not ctx.clear_pending_events()
