import json
from pathlib import Path
from typing import Any

import pytest

from server.activities.context import ActivityContext
from server.activities.streams import StreamChecker, StreamValidationError
from server.activities.manifest_types import Scope, StreamDefinition, TypeSchema, Type


def create_manifest(
    name: str = "test-activity",
    streams: dict[str, Any] | None = None,
    client: str = "client.js",
) -> dict[str, Any]:
    """Helper to create a manifest dict with streams."""
    manifest: dict[str, Any] = {
        "name": name,
        "client": client,
    }
    if streams is not None:
        manifest["streams"] = streams
    return manifest


def setup_activity_dir(tmp_path: Path, manifest: dict[str, Any]) -> Path:
    """Set up an activity directory with a manifest."""
    activity_dir = tmp_path / "activity"
    activity_dir.mkdir()
    with open(activity_dir / "manifest.json", "w", encoding="utf8") as f:
        json.dump(manifest, f)
    return activity_dir


class TestStreamChecker:
    """Tests for StreamChecker validation."""

    def test_empty_streams(self) -> None:
        """Should accept None or empty dict."""
        checker = StreamChecker(None)
        assert not checker.stream_names

        checker = StreamChecker({})
        assert not checker.stream_names

    def test_stream_names(self) -> None:
        """Should return declared stream names."""
        checker = StreamChecker(
            {
                "messages": StreamDefinition(
                    items=TypeSchema(type=Type.object),
                    scope=Scope.activity,
                ),
                "logs": StreamDefinition(
                    items=TypeSchema(type=Type.string),
                    scope=Scope.activity,
                ),
            }
        )
        assert sorted(checker.stream_names) == ["logs", "messages"]

    def test_get_definition(self) -> None:
        """Should return definition for declared stream."""
        definition = StreamDefinition(
            items=TypeSchema(type=Type.object),
            scope=Scope.activity,
        )
        checker = StreamChecker({"messages": definition})
        assert checker.get_definition("messages") is definition

    def test_get_definition_undeclared(self) -> None:
        """Should raise for undeclared stream."""
        checker = StreamChecker({})
        with pytest.raises(StreamValidationError, match="not declared"):
            checker.get_definition("unknown")

    def test_get_scope(self) -> None:
        """Should return scope for a declared stream."""
        checker = StreamChecker(
            {
                "messages": StreamDefinition(
                    items=TypeSchema(type=Type.object),
                    scope=Scope.user_activity,
                ),
            }
        )
        assert checker.get_scope("messages") == Scope.user_activity

    def test_validate_item_valid(self) -> None:
        """Should accept valid items."""
        checker = StreamChecker(
            {
                "messages": StreamDefinition(
                    items=TypeSchema(
                        type=Type.object,
                        properties={
                            "text": TypeSchema(type=Type.string),
                        },
                    ),
                    scope=Scope.activity,
                ),
            }
        )
        checker.validate_item("messages", {"text": "hello"})

    def test_validate_item_invalid(self) -> None:
        """Should reject invalid items."""
        checker = StreamChecker(
            {
                "messages": StreamDefinition(
                    items=TypeSchema(type=Type.string),
                    scope=Scope.activity,
                ),
            }
        )
        with pytest.raises(StreamValidationError, match="failed validation"):
            checker.validate_item("messages", 42)


class TestStreamOperations:
    """Tests for stream operations on ActivityContext."""

    def test_append_returns_id(self, tmp_path: Path) -> None:
        """Append should return sequential integer IDs."""
        manifest = create_manifest(
            streams={
                "messages": {
                    "items": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                    },
                    "scope": "activity",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        result1 = json.loads(
            ctx.stream_query(
                "messages", json.dumps({"op": "append", "value": {"text": "hello"}})
            )
        )
        result2 = json.loads(
            ctx.stream_query(
                "messages", json.dumps({"op": "append", "value": {"text": "world"}})
            )
        )

        assert result1 == 1
        assert result2 == 2

    def test_range_after_limit(self, tmp_path: Path) -> None:
        """Range with after and limit should return matching entries."""
        manifest = create_manifest(
            streams={
                "log": {
                    "items": {
                        "type": "object",
                        "properties": {"msg": {"type": "string"}},
                    },
                    "scope": "activity",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        for i in range(5):
            ctx.stream_query(
                "log", json.dumps({"op": "append", "value": {"msg": f"entry{i}"}})
            )

        result = json.loads(
            ctx.stream_query("log", json.dumps({"op": "range", "after": 2, "limit": 2}))
        )

        assert len(result) == 2
        assert result[0]["id"] == 3
        assert result[1]["id"] == 4

    def test_range_from_start(self, tmp_path: Path) -> None:
        """Range with after=0 should return from the beginning."""
        manifest = create_manifest(
            streams={
                "log": {
                    "items": {"type": "string"},
                    "scope": "activity",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.stream_query("log", json.dumps({"op": "append", "value": "a"}))
        ctx.stream_query("log", json.dumps({"op": "append", "value": "b"}))

        result = json.loads(
            ctx.stream_query(
                "log", json.dumps({"op": "range", "after": 0, "limit": 20})
            )
        )
        assert len(result) == 2

    def test_range_last(self, tmp_path: Path) -> None:
        """Range with last should return the last N entries."""
        manifest = create_manifest(
            streams={
                "log": {
                    "items": {
                        "type": "object",
                        "properties": {"msg": {"type": "string"}},
                    },
                    "scope": "activity",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        for i in range(5):
            ctx.stream_query(
                "log", json.dumps({"op": "append", "value": {"msg": f"e{i}"}})
            )

        result = json.loads(
            ctx.stream_query("log", json.dumps({"op": "range", "last": 2}))
        )

        assert len(result) == 2
        assert result[0]["id"] == 4
        assert result[1]["id"] == 5

    def test_length(self, tmp_path: Path) -> None:
        """Length should return the number of entries."""
        manifest = create_manifest(
            streams={
                "log": {
                    "items": {"type": "string"},
                    "scope": "activity",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        assert json.loads(ctx.stream_query("log", json.dumps({"op": "length"}))) == 0
        ctx.stream_query("log", json.dumps({"op": "append", "value": "a"}))
        ctx.stream_query("log", json.dumps({"op": "append", "value": "b"}))
        assert json.loads(ctx.stream_query("log", json.dumps({"op": "length"}))) == 2

    def test_delete(self, tmp_path: Path) -> None:
        """Delete should remove entry by ID and return true."""
        manifest = create_manifest(
            streams={
                "log": {
                    "items": {"type": "string"},
                    "scope": "activity",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.stream_query("log", json.dumps({"op": "append", "value": "a"}))
        ctx.stream_query("log", json.dumps({"op": "append", "value": "b"}))
        ctx.stream_query("log", json.dumps({"op": "append", "value": "c"}))

        deleted = json.loads(
            ctx.stream_query("log", json.dumps({"op": "delete", "id": 2}))
        )
        assert deleted is True

        length = json.loads(ctx.stream_query("log", json.dumps({"op": "length"})))
        assert length == 2

        entries = json.loads(
            ctx.stream_query(
                "log", json.dumps({"op": "range", "after": 0, "limit": 10})
            )
        )
        ids = [e["id"] for e in entries]
        assert ids == [1, 3]

    def test_delete_nonexistent(self, tmp_path: Path) -> None:
        """Delete of nonexistent ID should return false."""
        manifest = create_manifest(
            streams={
                "log": {
                    "items": {"type": "string"},
                    "scope": "activity",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        deleted = json.loads(
            ctx.stream_query("log", json.dumps({"op": "delete", "id": 999}))
        )
        assert deleted is False

    def test_undeclared_stream_error(self, tmp_path: Path) -> None:
        """Operations on undeclared streams should return error."""
        manifest = create_manifest()
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        with pytest.raises(StreamValidationError, match="not declared in manifest"):
            ctx.stream_query("unknown", json.dumps({"op": "length"}))

    def test_item_validation(self, tmp_path: Path) -> None:
        """Append with invalid item should return error."""
        manifest = create_manifest(
            streams={
                "log": {
                    "items": {"type": "string"},
                    "scope": "activity",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        with pytest.raises(StreamValidationError, match="item failed validation"):
            ctx.stream_query("log", json.dumps({"op": "append", "value": 42}))

    def test_scope_isolation(self, tmp_path: Path) -> None:
        """User-scoped streams should be isolated between users."""
        manifest = create_manifest(
            streams={
                "notes": {
                    "items": {"type": "string"},
                    "scope": "user,activity",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.user_id = "alice"
        ctx.stream_query("notes", json.dumps({"op": "append", "value": "alice-note"}))

        ctx.user_id = "bob"
        ctx.stream_query("notes", json.dumps({"op": "append", "value": "bob-note"}))

        # Bob should only see his own note
        bob_entries = json.loads(
            ctx.stream_query(
                "notes", json.dumps({"op": "range", "after": 0, "limit": 10})
            )
        )
        assert len(bob_entries) == 1
        assert bob_entries[0]["value"] == "bob-note"

        # Alice should only see her own note
        ctx.user_id = "alice"
        alice_entries = json.loads(
            ctx.stream_query(
                "notes", json.dumps({"op": "range", "after": 0, "limit": 10})
            )
        )
        assert len(alice_entries) == 1
        assert alice_entries[0]["value"] == "alice-note"

    def test_unknown_op(self, tmp_path: Path) -> None:
        """Unknown operation should return error."""
        manifest = create_manifest(
            streams={
                "log": {
                    "items": {"type": "string"},
                    "scope": "activity",
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        with pytest.raises(StreamValidationError, match="Unknown stream operation"):
            ctx.stream_query("log", json.dumps({"op": "bogus"}))
