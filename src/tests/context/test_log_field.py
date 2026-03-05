from pathlib import Path

import pytest

from server.activities.context import ActivityContext
from server.activities.fields import FieldValidationError
from .utils import create_manifest, setup_activity_dir


def make_ctx(tmp_path: Path) -> ActivityContext:
    manifest = create_manifest(
        fields={
            "messages": {
                "type": "log",
                "items": {
                    "type": "object",
                    "properties": {
                        "user": {"type": "string"},
                        "text": {"type": "string"},
                    },
                },
                "scope": "activity",
            }
        }
    )
    activity_dir = setup_activity_dir(tmp_path, manifest)
    return ActivityContext(activity_dir)


class TestLogFieldFunctions:
    """Tests for log_* host functions."""

    def test_log_append_returns_id(self, tmp_path: Path) -> None:
        ctx = make_ctx(tmp_path)
        id0 = ctx.log_append("messages", {"user": "alice", "text": "hi"}, {})
        id1 = ctx.log_append("messages", {"user": "bob", "text": "hello"}, {})
        assert id0 == 0
        assert id1 == 1

    def test_log_get_retrieves_by_id(self, tmp_path: Path) -> None:
        ctx = make_ctx(tmp_path)
        ctx.log_append("messages", {"user": "alice", "text": "hi"}, {})
        ctx.log_append("messages", {"user": "bob", "text": "hello"}, {})
        assert ctx.log_get("messages", 0, {}) == {"user": "alice", "text": "hi"}
        assert ctx.log_get("messages", 1, {}) == {"user": "bob", "text": "hello"}

    def test_log_get_missing_returns_none(self, tmp_path: Path) -> None:
        ctx = make_ctx(tmp_path)
        assert ctx.log_get("messages", 99, {}) is None

    def test_log_get_range(self, tmp_path: Path) -> None:
        ctx = make_ctx(tmp_path)
        ctx.log_append("messages", {"user": "a", "text": "1"}, {})
        ctx.log_append("messages", {"user": "b", "text": "2"}, {})
        ctx.log_append("messages", {"user": "c", "text": "3"}, {})
        result = ctx.log_get_range("messages", 0, 3, {})
        assert len(result) == 3
        assert result[0] == {"id": 0, "value": {"user": "a", "text": "1"}}
        assert result[2] == {"id": 2, "value": {"user": "c", "text": "3"}}

    def test_log_get_range_partial(self, tmp_path: Path) -> None:
        ctx = make_ctx(tmp_path)
        ctx.log_append("messages", {"user": "a", "text": "1"}, {})
        ctx.log_append("messages", {"user": "b", "text": "2"}, {})
        result = ctx.log_get_range("messages", 1, 2, {})
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_log_delete(self, tmp_path: Path) -> None:
        ctx = make_ctx(tmp_path)
        ctx.log_append("messages", {"user": "a", "text": "1"}, {})
        assert ctx.log_delete("messages", 0, {}) is True
        assert ctx.log_get("messages", 0, {}) is None

    def test_log_delete_missing(self, tmp_path: Path) -> None:
        ctx = make_ctx(tmp_path)
        assert ctx.log_delete("messages", 99, {}) is False

    def test_log_delete_range(self, tmp_path: Path) -> None:
        ctx = make_ctx(tmp_path)
        ctx.log_append("messages", {"user": "a", "text": "1"}, {})
        ctx.log_append("messages", {"user": "b", "text": "2"}, {})
        ctx.log_append("messages", {"user": "c", "text": "3"}, {})
        count = ctx.log_delete_range("messages", 0, 2, {})
        assert count == 2
        assert ctx.log_get("messages", 0, {}) is None
        assert ctx.log_get("messages", 1, {}) is None
        assert ctx.log_get("messages", 2, {}) == {"user": "c", "text": "3"}

    def test_get_field_raises_on_log(self, tmp_path: Path) -> None:
        ctx = make_ctx(tmp_path)
        with pytest.raises(FieldValidationError, match="type 'log'"):
            ctx.get_field("messages", {})

    def test_set_field_raises_on_log(self, tmp_path: Path) -> None:
        ctx = make_ctx(tmp_path)
        with pytest.raises(FieldValidationError, match="type 'log'"):
            ctx.set_field("messages", [], {})

    def test_scope_override(self, tmp_path: Path) -> None:
        manifest = create_manifest(
            fields={
                "messages": {
                    "type": "log",
                    "items": {"type": "string"},
                    "scope": "user,activity",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        ctx.user_id = "alice"

        ctx.log_append("messages", "alice msg", {})
        ctx.log_append("messages", "bob msg", {"user_id": "bob"})

        assert ctx.log_get("messages", 0, {}) == "alice msg"
        assert ctx.log_get("messages", 0, {"user_id": "bob"}) == "bob msg"

    def test_item_validation_rejects_wrong_type(self, tmp_path: Path) -> None:
        ctx = make_ctx(tmp_path)
        with pytest.raises(FieldValidationError, match="item failed validation"):
            ctx.log_append("messages", "not an object", {})

    def test_get_all_fields_skips_log(self, tmp_path: Path) -> None:
        manifest = create_manifest(
            fields={
                "messages": {
                    "type": "log",
                    "items": {"type": "string"},
                    "scope": "activity",
                },
                "count": {"type": "integer", "scope": "activity"},
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        result = ctx.get_all_fields()
        assert "count" in result
        assert "messages" not in result
