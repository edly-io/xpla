import json
from pathlib import Path
from typing import Any

from xpla.lib.runtime import ActivityRuntime
from xpla.lib.permission import Permission
from xpla.lib.field_store import FieldStore, MemoryKVStore


def create_manifest(
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


def make_field_store() -> FieldStore:
    """Create a temporary field store for tests."""
    return MemoryKVStore()


def make_activity_runtime(tmp_path: Path, manifest: dict[str, Any]) -> ActivityRuntime:
    """Create an ActivityRuntime with a dummy key-value store and activity directory for tests"""
    activity_dir = setup_activity_dir(tmp_path, manifest)
    return ActivityRuntime(
        activity_dir,
        make_field_store(),
        "activityid",
        "courseid",
        "userid",
        Permission.play,
    )
