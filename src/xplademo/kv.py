import json
from pathlib import Path
from typing import Any

from xpla.fields import FieldType

# Project root's dist/ directory
DIST_DIR = Path(__file__).parent.parent.parent / "dist"


class KVStore:
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

    def get(self, key: str) -> FieldType | None:
        return self._data.get(key)

    def set(self, key: str, value: FieldType) -> None:
        self._data[key] = value
        self._save()

    def delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            self._save()
            return True
        return False

    def keys(self) -> list[str]:
        return list(self._data.keys())

    # Log field methods

    def _log_data(self, key: str) -> dict[str, Any]:
        stored = self._data.get(key)
        if stored is None:
            return {"next_id": 0, "entries": {}}
        assert isinstance(stored, dict)
        return stored

    def log_get(self, key: str, entry_id: int) -> FieldType | None:
        data = self._log_data(key)
        value: FieldType | None = data["entries"].get(str(entry_id))
        return value

    def log_get_range(self, key: str, from_id: int, to_id: int) -> list[dict[str, Any]]:
        data = self._log_data(key)
        result: list[dict[str, Any]] = []
        for i in range(from_id, to_id):
            k = str(i)
            if k in data["entries"]:
                result.append({"id": i, "value": data["entries"][k]})
        return result

    def log_append(self, key: str, value: FieldType) -> int:
        data = self._log_data(key)
        entry_id: int = data["next_id"]
        data["entries"][str(entry_id)] = value
        data["next_id"] = entry_id + 1
        self._data[key] = data
        self._save()
        return entry_id

    def log_delete(self, key: str, entry_id: int) -> bool:
        data = self._log_data(key)
        k = str(entry_id)
        if k not in data["entries"]:
            return False
        del data["entries"][k]
        self._data[key] = data
        self._save()
        return True

    def log_delete_range(self, key: str, from_id: int, to_id: int) -> int:
        data = self._log_data(key)
        count = 0
        for i in range(from_id, to_id):
            k = str(i)
            if k in data["entries"]:
                del data["entries"][k]
                count += 1
        if count > 0:
            self._data[key] = data
            self._save()
        return count


def get_default() -> KVStore:
    return KVStore(DIST_DIR / "kv.json")
