from pathlib import Path

from xpla.lib.file_storage import LocalFileStorage
from xpla.lib.permission import Permission
from xpla.lib.manifest_types import Scope
from xpla.lib.runtime import ActivityRuntime
from xpla.notebook import constants
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

    def delete_storage(self) -> None:
        """Delete all file storage scoped to this activity instance."""
        if not self.manifest.capabilities or not self.manifest.capabilities.storage:
            return
        for storage_name, storage_def in self.manifest.capabilities.storage.items():
            if storage_def.scope in (Scope.activity, Scope.user_activity):
                self._file_storage.delete(
                    f"{self.manifest.name}/{storage_name}"
                    f"/{self._course_id}/{self._activity_id}"
                )


def delete_type_storage(activity_name: str) -> None:
    """Delete all file storage for an activity type."""
    FILE_STORAGE.delete(activity_name)
