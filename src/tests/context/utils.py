import json
import tempfile
from pathlib import Path
from typing import Any

from xpla.context import ActivityContext
from xplademo.kv import KVStore


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


def make_kv_store() -> KVStore:
    """Create a temporary KVStore for tests."""
    tmpdir = tempfile.mkdtemp()
    return KVStore(Path(tmpdir) / "kv.json")


def make_activity_context(tmp_path: Path, manifest: dict[str, Any]) -> ActivityContext:
    """Create an ActivityContext with a dummy key-value store and activity directory for tests"""
    activity_dir = setup_activity_dir(tmp_path, manifest)
    return ActivityContext(activity_dir, make_kv_store())
