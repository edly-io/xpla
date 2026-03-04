from pathlib import Path

import pytest

from server.activities.context import ActivityContext
from server.activities.fields import FieldValidationError
from .utils import create_manifest, setup_activity_dir


class TestObjectFieldFunctions:
    """Tests for get_object_field/set_object_field host functions."""

    def test_get_object_field_key(self, tmp_path: Path) -> None:
        """Should get individual keys from an object field."""
        manifest = create_manifest(
            fields={
                "config": {
                    "type": "object",
                    "scope": "activity",
                    "properties": {
                        "color": {"type": "string"},
                        "size": {"type": "integer"},
                    },
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.set_field("config", {"color": "red", "size": 10}, {})

        assert ctx.get_object_field("config", "color", None, {}) == "red"
        assert ctx.get_object_field("config", "size", None, {}) == 10

    def test_set_object_field_key(self, tmp_path: Path) -> None:
        """Should set individual keys, verifiable via get_field."""
        manifest = create_manifest(
            fields={
                "config": {
                    "type": "object",
                    "scope": "activity",
                    "properties": {
                        "color": {"type": "string"},
                        "size": {"type": "integer"},
                    },
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        ctx.set_object_field("config", "color", "blue", {})
        ctx.set_object_field("config", "size", 42, {})

        assert ctx.get_field("config", {}) == {"color": "blue", "size": 42}

    def test_get_object_field_missing_key_returns_default(self, tmp_path: Path) -> None:
        """Should return the default value when key is not in object."""
        manifest = create_manifest(
            fields={"data": {"type": "object", "scope": "activity", "properties": {}}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        assert ctx.get_object_field("data", "missing", "fallback", {}) == "fallback"
        assert ctx.get_object_field("data", "missing", None, {}) is None

    def test_get_object_field_non_object_raises(self, tmp_path: Path) -> None:
        """Should raise FieldValidationError on non-object field."""
        manifest = create_manifest(
            fields={"count": {"type": "integer", "scope": "activity", "default": 0}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        with pytest.raises(FieldValidationError, match="expected 'object'"):
            ctx.get_object_field("count", "key", None, {})

    def test_set_object_field_non_object_raises(self, tmp_path: Path) -> None:
        """Should raise FieldValidationError on non-object field."""
        manifest = create_manifest(
            fields={"count": {"type": "integer", "scope": "activity", "default": 0}}
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        with pytest.raises(FieldValidationError, match="expected 'object'"):
            ctx.set_object_field("count", "key", 42, {})

    def test_set_object_field_validates_schema(self, tmp_path: Path) -> None:
        """Should raise when value violates the object's property schema."""
        manifest = create_manifest(
            fields={
                "config": {
                    "type": "object",
                    "scope": "activity",
                    "properties": {"name": {"type": "string"}},
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)

        with pytest.raises(FieldValidationError, match="failed validation"):
            ctx.set_object_field("config", "name", 123, {})

    def test_object_field_with_scope_override(self, tmp_path: Path) -> None:
        """Should respect scope overrides for object field access."""
        manifest = create_manifest(
            fields={
                "prefs": {
                    "type": "object",
                    "scope": "user,activity",
                    "properties": {},
                }
            }
        )
        activity_dir = setup_activity_dir(tmp_path, manifest)
        ctx = ActivityContext(activity_dir)
        ctx.user_id = "alice"

        ctx.set_object_field("prefs", "theme", "dark", {"user_id": "bob"})

        assert (
            ctx.get_object_field("prefs", "theme", None, {"user_id": "bob"}) == "dark"
        )
        assert ctx.get_object_field("prefs", "theme", None, {}) is None
