import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sqlmodel import Session, col, select

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

MAX_REPORT_QUERY_LIMIT = 1000
DEFAULT_REPORT_QUERY_LIMIT = 100


class NotebookActivityRuntime(ActivityRuntime):
    def __init__(
        self,
        activity_dir: Path,
        activity_id: str,
        course_id: str,
        user_id: str,
        permission: Permission,
        *,
        is_course_activity: bool = False,
    ) -> None:
        self._is_course_activity = is_course_activity
        super().__init__(
            activity_dir,
            FIELD_STORE,
            FILE_STORAGE,
            activity_id,
            course_id,
            user_id,
            permission,
        )

    def host_functions(self) -> dict[str, Callable[..., Any]]:
        funcs = super().host_functions()
        if self._is_course_activity:
            funcs["report-query"] = self.report_query
        return funcs

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

    def report_query(self, filters: str) -> str:
        parsed: dict[str, Any] = json.loads(filters)
        query = select(ActivityStatement).where(
            ActivityStatement.course_id == self._course_id
        )
        if "activity_id" in parsed:
            query = query.where(ActivityStatement.activity_id == parsed["activity_id"])
        if "activity_name" in parsed:
            query = query.where(
                ActivityStatement.activity_name == parsed["activity_name"]
            )
        if "user_id" in parsed:
            query = query.where(ActivityStatement.user_id == parsed["user_id"])
        if "verb" in parsed:
            query = query.where(ActivityStatement.verb == parsed["verb"])
        if "after_id" in parsed:
            query = query.where(col(ActivityStatement.id) > int(parsed["after_id"]))
        limit = min(
            int(parsed.get("limit", DEFAULT_REPORT_QUERY_LIMIT)),
            MAX_REPORT_QUERY_LIMIT,
        )
        query = query.order_by(col(ActivityStatement.id)).limit(limit)
        with Session(engine) as session:
            rows = session.exec(query).all()
        return json.dumps(
            [
                {
                    "id": row.id,
                    "activity_id": row.activity_id,
                    "activity_name": row.activity_name,
                    "user_id": row.user_id,
                    "verb": row.verb,
                    "score": row.score,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
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
