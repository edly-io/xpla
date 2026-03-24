"""FileStorage — abstract base class, local, and in-memory implementations."""

import shutil
from abc import ABC, abstractmethod
from pathlib import Path


class FileStorageError(Exception):
    """Raised on file storage access errors (path traversal, missing files, etc.)."""


class FileStorage(ABC):
    """Abstract base class for file persistence.

    Every method takes a relative ``path``.  The caller is responsible for
    including any scoping prefix (e.g. activity ID) in the path.
    """

    @abstractmethod
    def read(self, path: str) -> bytes:
        """Read content from a single file"""

    @abstractmethod
    def write(self, path: str, content: bytes) -> None:
        """Write content to a single file"""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check whether a file exists"""

    @abstractmethod
    def list(self, path: str) -> tuple[list[str], list[str]]:
        """Return ``(files, directories)`` — sorted lists of entry names."""

    @abstractmethod
    def delete(self, path: str) -> bool:
        """Delete a single file.  Returns ``True`` if it existed."""

    @abstractmethod
    def delete_all(self, path: str) -> None:
        """Recursively delete everything under *path*."""


class LocalFileStorage(FileStorage):
    """File storage backed by the local filesystem.

    Files are stored at ``<base_dir>/<path>``.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def _resolve(self, path: str) -> Path:
        root = self._base_dir.resolve()
        full = (self._base_dir / path).resolve()
        try:
            full.relative_to(root)
        except ValueError as e:
            raise FileStorageError(f"Path escapes storage root: {path!r}") from e
        return full

    def read(self, path: str) -> bytes:
        full = self._resolve(path)
        if not full.is_file():
            raise FileStorageError(f"File not found: {path!r}")
        return full.read_bytes()

    def write(self, path: str, content: bytes) -> None:
        full = self._resolve(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(content)

    def exists(self, path: str) -> bool:
        return self._resolve(path).exists()

    def list(self, path: str) -> tuple[list[str], list[str]]:
        full = self._resolve(path)
        if not full.is_dir():
            raise FileStorageError(f"Directory not found: {path!r}")
        files: list[str] = []
        directories: list[str] = []
        for entry in sorted(full.iterdir()):
            if entry.is_file():
                files.append(entry.name)
            elif entry.is_dir():
                directories.append(entry.name)
        return files, directories

    def delete(self, path: str) -> bool:
        full = self._resolve(path)
        if full.is_file():
            full.unlink()
            return True
        return False

    def delete_all(self, path: str) -> None:
        full = self._resolve(path)
        if full.is_dir():
            shutil.rmtree(full)


class MemoryFileStorage(FileStorage):
    """In-memory file storage for testing."""

    def __init__(self) -> None:
        self._files: dict[str, bytes] = {}

    def read(self, path: str) -> bytes:
        path = path.strip("/")
        if path not in self._files:
            raise FileStorageError(f"File not found: {path!r}")
        return self._files[path]

    def write(self, path: str, content: bytes) -> None:
        path = path.strip("/")
        self._files[path] = content

    def exists(self, path: str) -> bool:
        path = path.strip("/")
        if path in self._files:
            return True
        prefix = path + "/"
        return any(k.startswith(prefix) for k in self._files)

    def list(self, path: str) -> tuple[list[str], list[str]]:
        path = path.strip("/")
        prefix = path + "/" if path else ""
        files: set[str] = set()
        directories: set[str] = set()
        for key in self._files:
            if not key.startswith(prefix):
                continue
            rest = key[len(prefix) :]
            if "/" in rest:
                directories.add(rest.split("/")[0])
            else:
                files.add(rest)
        if not files and not directories:
            raise FileStorageError(f"Directory not found: {path!r}")
        return sorted(files), sorted(directories)

    def delete(self, path: str) -> bool:
        path = path.strip("/")
        if path in self._files:
            del self._files[path]
            return True
        return False

    def delete_all(self, path: str) -> None:
        path = path.strip("/")
        prefix = path + "/"
        to_delete = [k for k in self._files if k == path or k.startswith(prefix)]
        for k in to_delete:
            del self._files[k]
