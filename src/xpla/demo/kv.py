import json
from pathlib import Path
from typing import Any

from xpla.lib.field_store import FieldStore
from xpla.lib.fields import FieldType

# Project root's dist/ directory
DIST_DIR = Path(__file__).parent.parent.parent.parent / "dist"


class KVStore(FieldStore):
    """Persistent key-value store backed by a JSON file."""

    def __init__(self, storage_path: Path) -> None:
        self._path = storage_path
        self._data: dict[str, FieldType] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            with self._path.open() as f:
                self._data = json.load(f)

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w") as f:
            json.dump(self._data, f, indent=2)

    @staticmethod
    def _composite_key(
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
    ) -> str:
        return f"xpla.{activity_name}.{course_id}.{activity_id}.{user_id}.{key}"

    def get(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
    ) -> FieldType | None:
        return self._data.get(
            self._composite_key(course_id, activity_name, activity_id, user_id, key)
        )

    def set(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        value: FieldType,
    ) -> None:
        self._data[
            self._composite_key(course_id, activity_name, activity_id, user_id, key)
        ] = value
        self._save()

    def delete(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
    ) -> bool:
        ck = self._composite_key(course_id, activity_name, activity_id, user_id, key)
        if ck in self._data:
            del self._data[ck]
            self._save()
            return True
        return False

    def keys(self) -> list[str]:
        return list(self._data.keys())

    # Log field methods

    def _log_key(
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
    ) -> str:
        return self._composite_key(
            course_id, activity_name, activity_id, user_id, f"__log__.{key}"
        )

    def _log_data(self, log_key: str) -> dict[str, Any]:
        stored = self._data.get(log_key)
        if stored is None:
            return {"next_id": 0, "entries": {}}
        assert isinstance(stored, dict)
        return stored

    def log_get(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        entry_id: int,
    ) -> FieldType | None:
        data = self._log_data(
            self._log_key(course_id, activity_name, activity_id, user_id, key)
        )
        value: FieldType | None = data["entries"].get(str(entry_id))
        return value

    def log_get_range(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        from_id: int,
        to_id: int,
    ) -> list[dict[str, Any]]:
        data = self._log_data(
            self._log_key(course_id, activity_name, activity_id, user_id, key)
        )
        result: list[dict[str, Any]] = []
        for i in range(from_id, to_id):
            k = str(i)
            if k in data["entries"]:
                result.append({"id": i, "value": data["entries"][k]})
        return result

    def log_append(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        value: FieldType,
    ) -> int:
        lk = self._log_key(course_id, activity_name, activity_id, user_id, key)
        data = self._log_data(lk)
        entry_id: int = data["next_id"]
        data["entries"][str(entry_id)] = value
        data["next_id"] = entry_id + 1
        self._data[lk] = data
        self._save()
        return entry_id

    def log_delete(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        entry_id: int,
    ) -> bool:
        lk = self._log_key(course_id, activity_name, activity_id, user_id, key)
        data = self._log_data(lk)
        k = str(entry_id)
        if k not in data["entries"]:
            return False
        del data["entries"][k]
        self._data[lk] = data
        self._save()
        return True

    def log_delete_range(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        from_id: int,
        to_id: int,
    ) -> int:
        lk = self._log_key(course_id, activity_name, activity_id, user_id, key)
        data = self._log_data(lk)
        count = 0
        for i in range(from_id, to_id):
            k = str(i)
            if k in data["entries"]:
                del data["entries"][k]
                count += 1
        if count > 0:
            self._data[lk] = data
            self._save()
        return count


def get_default() -> KVStore:
    return KVStore(DIST_DIR / "kv.json")
