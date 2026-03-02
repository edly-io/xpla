import json
from pathlib import Path

from server.constants import DIST_DIR
from server.activities.fields import FieldType


class KVStore:
    """Persistent key-value store backed by a JSON file."""

    def __init__(self, storage_path: Path) -> None:
        """Initialize the KV store.

        Args:
            storage_path: Path to the JSON file for persistence.
        """
        self._path = storage_path
        self._data: dict[str, FieldType] = {}
        self._load()

    def _load(self) -> None:
        """Load data from disk."""
        if self._path.exists():
            with self._path.open() as f:
                self._data = json.load(f)

    def _save(self) -> None:
        """Save data to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str) -> FieldType | None:
        """Get a value by key."""
        return self._data.get(key)

    def set(self, key: str, value: FieldType) -> None:
        """Set a key-value pair."""
        self._data[key] = value
        self._save()

    def delete(self, key: str) -> bool:
        """Delete a key. Returns True if key existed."""
        if key in self._data:
            del self._data[key]
            self._save()
            return True
        return False

    def keys(self) -> list[str]:
        """List all keys."""
        return list(self._data.keys())


def get_default() -> KVStore:
    """
    Return the default key-value store from <root>/dist/kv.json.
    """
    return KVStore(DIST_DIR / "kv.json")
