"""Tests for file storage — LocalFileStorage, MemoryFileStorage, and capability enforcement."""

import json
import tempfile
from pathlib import Path

import pytest

from xpla.lib.capabilities import CapabilityChecker, CapabilityError
from xpla.lib.file_storage import (
    FileStorageError,
    LocalFileStorage,
    MemoryFileStorage,
)
from xpla.lib.manifest_types import Capabilities
from xpla.lib.runtime import ActivityRuntime
from xpla.lib.field_store import MemoryKVStore
from xpla.lib.permission import Permission

# ── helpers ─────────────────────────────────────────────────────────────


def _make_runtime(
    capabilities: dict[str, object] | None = None,
    file_storage: MemoryFileStorage | None = None,
) -> ActivityRuntime:
    """Create an ActivityRuntime with a manifest containing the given capabilities."""
    activity_dir = Path(tempfile.mkdtemp())
    manifest = {
        "name": "test-activity",
        "client": "client.js",
        "capabilities": capabilities or {},
    }
    (activity_dir / "manifest.json").write_text(json.dumps(manifest))
    storage = file_storage or MemoryFileStorage()
    return ActivityRuntime(
        activity_dir,
        MemoryKVStore(),
        storage,
        "activity-1",
        "course-1",
        "user-1",
        Permission.play,
    )


# ── LocalFileStorage direct API tests ──────────────────────────────────


class TestLocalFileStorage:
    """Tests for LocalFileStorage methods."""

    def test_write_and_read(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fs = LocalFileStorage(Path(d))
            fs.write("a1/hello.txt", b"hello world")
            assert fs.read("a1/hello.txt") == b"hello world"

    def test_write_creates_subdirectories(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fs = LocalFileStorage(Path(d))
            fs.write("a1/sub/dir/file.bin", b"\x00\x01")
            assert fs.read("a1/sub/dir/file.bin") == b"\x00\x01"

    def test_exists_false_initially(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fs = LocalFileStorage(Path(d))
            assert not fs.exists("a1/nope.txt")

    def test_exists_true_after_write(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fs = LocalFileStorage(Path(d))
            fs.write("a1/f.txt", b"data")
            assert fs.exists("a1/f.txt")

    def test_read_missing_raises(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fs = LocalFileStorage(Path(d))
            with pytest.raises(FileStorageError, match="File not found"):
                fs.read("a1/missing.txt")

    def test_list_files_and_directories(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fs = LocalFileStorage(Path(d))
            fs.write("a1/a.txt", b"a")
            fs.write("a1/b.txt", b"b")
            fs.write("a1/sub/c.txt", b"c")
            files, dirs = fs.list("a1")
            assert files == ["a.txt", "b.txt"]
            assert dirs == ["sub"]

    def test_list_missing_directory_raises(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fs = LocalFileStorage(Path(d))
            with pytest.raises(FileStorageError, match="Directory not found"):
                fs.list("a1/nonexistent")

    def test_delete_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fs = LocalFileStorage(Path(d))
            fs.write("a1/f.txt", b"data")
            assert fs.delete("a1/f.txt") is True
            assert not fs.exists("a1/f.txt")

    def test_delete_nonexistent_returns_false(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fs = LocalFileStorage(Path(d))
            assert fs.delete("a1/nope.txt") is False

    def test_delete_all_removes_files(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fs = LocalFileStorage(Path(d))
            fs.write("a1/f1.txt", b"1")
            fs.write("a1/sub/f2.txt", b"2")
            fs.delete_all("a1")
            assert not Path(d, "a1").exists()

    def test_delete_all_noop_when_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fs = LocalFileStorage(Path(d))
            fs.delete_all("nonexistent")  # should not raise

    def test_path_traversal_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fs = LocalFileStorage(Path(d))
            with pytest.raises(FileStorageError, match="escapes storage root"):
                fs.read("../../etc/passwd")

    def test_path_traversal_rejected_on_write(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fs = LocalFileStorage(Path(d))
            with pytest.raises(FileStorageError, match="escapes storage root"):
                fs.write("../escape.txt", b"evil")


# ── MemoryFileStorage tests ────────────────────────────────────────────


class TestMemoryFileStorage:
    """Tests for MemoryFileStorage methods."""

    def test_write_and_read(self) -> None:
        fs = MemoryFileStorage()
        fs.write("a1/hello.txt", b"hello")
        assert fs.read("a1/hello.txt") == b"hello"

    def test_exists(self) -> None:
        fs = MemoryFileStorage()
        assert not fs.exists("a1/nope.txt")
        fs.write("a1/nope.txt", b"data")
        assert fs.exists("a1/nope.txt")

    def test_exists_directory(self) -> None:
        fs = MemoryFileStorage()
        fs.write("a1/sub/file.txt", b"data")
        assert fs.exists("a1/sub")

    def test_read_missing_raises(self) -> None:
        fs = MemoryFileStorage()
        with pytest.raises(FileStorageError, match="File not found"):
            fs.read("a1/missing.txt")

    def test_list(self) -> None:
        fs = MemoryFileStorage()
        fs.write("a1/a.txt", b"a")
        fs.write("a1/b.txt", b"b")
        fs.write("a1/sub/c.txt", b"c")
        files, dirs = fs.list("a1")
        assert files == ["a.txt", "b.txt"]
        assert dirs == ["sub"]

    def test_list_missing_raises(self) -> None:
        fs = MemoryFileStorage()
        with pytest.raises(FileStorageError, match="Directory not found"):
            fs.list("a1/nonexistent")

    def test_delete(self) -> None:
        fs = MemoryFileStorage()
        fs.write("a1/f.txt", b"data")
        assert fs.delete("a1/f.txt") is True
        assert not fs.exists("a1/f.txt")

    def test_delete_nonexistent(self) -> None:
        fs = MemoryFileStorage()
        assert fs.delete("a1/nope.txt") is False

    def test_delete_all(self) -> None:
        fs = MemoryFileStorage()
        fs.write("a1/f1.txt", b"1")
        fs.write("a1/sub/f2.txt", b"2")
        fs.write("a2/other.txt", b"3")
        fs.delete_all("a1")
        assert not fs.exists("a1/f1.txt")
        assert not fs.exists("a1/sub/f2.txt")
        assert fs.exists("a2/other.txt")


# ── CapabilityChecker storage tests ────────────────────────────────────


class TestStorageCapabilityChecker:
    """Tests for CapabilityChecker.check_storage."""

    def test_no_capability_rejects(self) -> None:
        checker = CapabilityChecker(None)
        with pytest.raises(
            CapabilityError, match=r"Storage 'media' not declared\. Declared: \[\]"
        ):
            checker.check_storage("media")

    def test_empty_capabilities_rejects(self) -> None:
        checker = CapabilityChecker(Capabilities())
        with pytest.raises(
            CapabilityError, match=r"Storage 'media' not declared\. Declared: \[\]"
        ):
            checker.check_storage("media")

    def test_undeclared_name_rejects(self) -> None:
        caps = Capabilities(storage=["media"])
        checker = CapabilityChecker(caps)
        with pytest.raises(CapabilityError, match="not declared"):
            checker.check_storage("private")

    def test_declared_name_passes(self) -> None:
        caps = Capabilities(storage=["media"])
        checker = CapabilityChecker(caps)
        checker.check_storage("media")  # should not raise


# ── ActivityRuntime storage integration tests ──────────────────────────


class TestStorageRuntimeIntegration:
    """Tests for storage host functions on ActivityRuntime."""

    def test_storage_rejected_without_capability(self) -> None:
        rt = _make_runtime(capabilities={})
        with pytest.raises(
            CapabilityError, match=r"Storage 'media' not declared\. Declared: \[\]"
        ):
            rt.storage_read("media", "test.txt")

    def test_storage_read_rejected_for_undeclared_name(self) -> None:
        rt = _make_runtime(capabilities={"storage": ["media"]})
        with pytest.raises(
            CapabilityError,
            match=r"Storage 'private' not declared\. Declared: \['media'\]",
        ):
            rt.storage_read("private", "secret.txt")

    def test_storage_write_and_read(self) -> None:
        rt = _make_runtime(capabilities={"storage": ["media"]})
        rt.storage_write("media", "img.png", b"png-data")
        assert rt.storage_read("media", "img.png") == b"png-data"

    def test_storage_exists(self) -> None:
        rt = _make_runtime(capabilities={"storage": ["media"]})
        assert not rt.storage_exists("media", "nope.txt")
        rt.storage_write("media", "nope.txt", b"data")
        assert rt.storage_exists("media", "nope.txt")

    def test_storage_delete(self) -> None:
        rt = _make_runtime(capabilities={"storage": ["media"]})
        rt.storage_write("media", "f.txt", b"data")
        assert rt.storage_delete("media", "f.txt") is True
        assert not rt.storage_exists("media", "f.txt")

    def test_storage_list(self) -> None:
        rt = _make_runtime(capabilities={"storage": ["media"]})
        rt.storage_write("media", "a.txt", b"a")
        rt.storage_write("media", "sub/b.txt", b"b")
        directories, files = rt.storage_list("media", "")
        assert directories == ["sub"]
        assert files == ["a.txt"]

    def test_storage_url_returns_correct_path(self) -> None:
        rt = _make_runtime(capabilities={"storage": ["media"]})
        url = rt.storage_url("media", "img.png")
        assert url == "/activity/activity-1/storage/media/img.png"

    def test_storage_url_undeclared_name_rejected(self) -> None:
        rt = _make_runtime(capabilities={"storage": ["media"]})
        with pytest.raises(CapabilityError, match="not declared"):
            rt.storage_url("private", "img.png")
