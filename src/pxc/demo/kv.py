import json
from pathlib import Path

from pxc.lib.field_store import MemoryKVStore
from pxc.lib.fields import FieldType

# Project root's dist/ directory
DIST_DIR = Path(__file__).parent.parent.parent.parent / "dist"


class KVStore(MemoryKVStore):
    """Persistent key-value store backed by a JSON file."""

    def __init__(self, storage_path: Path) -> None:
        super().__init__()
        self._path = storage_path
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            with self._path.open() as f:
                self._data = json.load(f)

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w") as f:
            json.dump(self._data, f, indent=2)

    def set(
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        value: FieldType,
    ) -> None:
        super().set(course_id, activity_name, activity_id, user_id, key, value)
        self._save()

    def delete(
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
    ) -> bool:
        deleted = super().delete(course_id, activity_name, activity_id, user_id, key)
        if deleted:
            self._save()
        return deleted

    def log_append(
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        value: FieldType,
    ) -> int:
        entry_id = super().log_append(
            course_id, activity_name, activity_id, user_id, key, value
        )
        self._save()
        return entry_id

    def log_delete(
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        entry_id: int,
    ) -> bool:
        deleted = super().log_delete(
            course_id, activity_name, activity_id, user_id, key, entry_id
        )
        if deleted:
            self._save()
        return deleted

    def log_delete_range(
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        from_id: int,
        to_id: int,
    ) -> int:
        count = super().log_delete_range(
            course_id, activity_name, activity_id, user_id, key, from_id, to_id
        )
        if count > 0:
            self._save()
        return count


def load_field_store() -> KVStore:
    return KVStore(DIST_DIR / "kv.json")
