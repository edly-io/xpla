from pathlib import Path

from sqlmodel import Session

from xpla.lib.file_storage import LocalFileStorage
from xpla.lib.permission import Permission
from xpla.lib.manifest_types import Scope
from xpla.lib.runtime import ActivityRuntime
from xpla.notebook import constants
from xpla.notebook.db import engine
from xpla.notebook.field_store import SQLiteFieldStore
from xpla.notebook.models import ActivityStatement

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

    def report_completed(self) -> bool:
        self._record_statement("completed", None)
        return True

    def report_passed(self, score: float | None) -> bool:
        self._record_statement("passed", score)
        return True

    def report_failed(self, score: float | None) -> bool:
        self._record_statement("failed", score)
        return True

    def report_progressed(self, progress: float) -> bool:
        self._record_statement("progressed", progress)
        return True

    def report_scored(self, score: float) -> bool:
        self._record_statement("scored", score)
        return True

    def _record_statement(self, verb: str, score: float | None) -> None:
        with Session(engine) as session:
            session.add(
                ActivityStatement(
                    course_id=self._course_id,
                    activity_id=self._activity_id,
                    activity_name=self.manifest.name,
                    user_id=self._user_id,
                    verb=verb,
                    score=score,
                )
            )
            session.commit()

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
