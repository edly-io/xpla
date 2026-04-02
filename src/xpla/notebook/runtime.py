from pathlib import Path

from xpla.lib.file_storage import LocalFileStorage
from xpla.lib.permission import Permission
from xpla.lib.runtime import ActivityRuntime
from xpla.notebook import constants, field_store
from xpla.notebook.field_store import SQLiteFieldStore

FILE_STORAGE = LocalFileStorage(constants.DIST_DIR / "xpln" / "storage")
FIELD_STORE = SQLiteFieldStore()


class NotebookActivityRuntime(ActivityRuntime):
    def __init__(
        self,
        activity_dir: Path,
        activity_id: str,
        course_id: str,
        user_id: str,
        permission: Permission,
    ) -> None:
        super().__init__(
            activity_dir,
            FIELD_STORE,
            FILE_STORAGE,
            activity_id,
            course_id,
            user_id,
            permission,
        )


def delete_activity_by(
    activity_id: str | None = None,
    activity_name: str | None = None,
    course_id: str | None = None,
) -> None:
    """Delete all data (fields and storage) for matching activities."""
    field_store.delete_fields_by(
        activity_id=activity_id, activity_name=activity_name, course_id=course_id
    )
    if activity_name:
        FILE_STORAGE.delete(activity_name)
