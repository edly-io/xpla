"""Shared fixtures for sample activity tests."""

from pathlib import Path

from xpla.lib.field_store import MemoryKVStore
from xpla.lib.permission import Permission
from xpla.lib.runtime import ActivityRuntime

SAMPLES_DIR = Path(__file__).resolve().parents[5] / "samples"


def make_runtime(
    sample_name: str,
    permission: Permission = Permission.play,
    activity_id: str = "a1",
    course_id: str = "c1",
    user_id: str = "u1",
    storage_dir: Path | None = None,
) -> ActivityRuntime:
    """Create an ActivityRuntime pointing at a real sample directory."""
    activity_dir = SAMPLES_DIR / sample_name
    field_store = MemoryKVStore()
    return ActivityRuntime(
        activity_dir=activity_dir,
        field_store=field_store,
        activity_id=activity_id,
        course_id=course_id,
        user_id=user_id,
        permission=permission,
        storage_dir=storage_dir,
    )
