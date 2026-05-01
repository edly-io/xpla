"""Shared fixtures for sample activity tests."""

from pathlib import Path

from pxc.lib.field_store import MemoryKVStore
from pxc.lib.file_storage import MemoryFileStorage
from pxc.lib.permission import Permission
from pxc.lib.runtime import ActivityRuntime

SAMPLES_DIR = Path(__file__).resolve().parents[5] / "samples"


def make_runtime(
    sample_name: str,
    permission: Permission = Permission.play,
    activity_id: str = "a1",
    course_id: str = "c1",
    user_id: str = "u1",
) -> ActivityRuntime:
    """Create an ActivityRuntime pointing at a real sample directory."""
    activity_dir = SAMPLES_DIR / sample_name
    field_store = MemoryKVStore()
    storage = MemoryFileStorage()
    return ActivityRuntime(
        activity_dir,
        field_store,
        storage,
        activity_id,
        course_id,
        user_id,
        permission,
    )
