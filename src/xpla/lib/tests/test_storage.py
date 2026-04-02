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
from xpla.lib.fields import FieldValidationError
from xpla.lib.manifest_types import Capabilities, Scope, StorageDefinition
from xpla.lib.runtime import SandboxContext
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

    def test_delete_directory_removes_files(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fs = LocalFileStorage(Path(d))
            fs.write("a1/f1.txt", b"1")
            fs.write("a1/sub/f2.txt", b"2")
            assert fs.delete("a1") is True
            assert not Path(d, "a1").exists()

    def test_delete_nonexistent_directory_returns_false(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fs = LocalFileStorage(Path(d))
            assert fs.delete("nonexistent") is False

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

    def test_delete_directory(self) -> None:
        fs = MemoryFileStorage()
        fs.write("a1/f1.txt", b"1")
        fs.write("a1/sub/f2.txt", b"2")
        fs.write("a2/other.txt", b"3")
        assert fs.delete("a1") is True
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
        caps = Capabilities(storage={"media": StorageDefinition(scope=Scope.activity)})
        checker = CapabilityChecker(caps)
        with pytest.raises(CapabilityError, match="not declared"):
            checker.check_storage("private")

    def test_declared_name_passes(self) -> None:
        caps = Capabilities(storage={"media": StorageDefinition(scope=Scope.activity)})
        checker = CapabilityChecker(caps)
        checker.check_storage("media")  # should not raise

    def test_get_storage_scope(self) -> None:
        caps = Capabilities(
            storage={"media": StorageDefinition(scope=Scope.user_activity)}
        )
        checker = CapabilityChecker(caps)
        assert checker.get_storage_scope("media") == Scope.user_activity

    def test_get_storage_scope_undeclared_raises(self) -> None:
        caps = Capabilities(storage={"media": StorageDefinition(scope=Scope.activity)})
        checker = CapabilityChecker(caps)
        with pytest.raises(CapabilityError, match="not declared"):
            checker.get_storage_scope("private")


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
        rt = _make_runtime(capabilities={"storage": {"media": {"scope": "activity"}}})
        with pytest.raises(
            CapabilityError,
            match=r"Storage 'private' not declared\. Declared: \['media'\]",
        ):
            rt.storage_read("private", "secret.txt")

    def test_storage_write_and_read(self) -> None:
        rt = _make_runtime(capabilities={"storage": {"media": {"scope": "activity"}}})
        rt.storage_write("media", "img.png", b"png-data")
        assert rt.storage_read("media", "img.png") == b"png-data"

    def test_storage_exists(self) -> None:
        rt = _make_runtime(capabilities={"storage": {"media": {"scope": "activity"}}})
        assert not rt.storage_exists("media", "nope.txt")
        rt.storage_write("media", "nope.txt", b"data")
        assert rt.storage_exists("media", "nope.txt")

    def test_storage_delete(self) -> None:
        rt = _make_runtime(capabilities={"storage": {"media": {"scope": "activity"}}})
        rt.storage_write("media", "f.txt", b"data")
        assert rt.storage_delete("media", "f.txt") is True
        assert not rt.storage_exists("media", "f.txt")

    def test_storage_list(self) -> None:
        rt = _make_runtime(capabilities={"storage": {"media": {"scope": "activity"}}})
        rt.storage_write("media", "a.txt", b"a")
        rt.storage_write("media", "sub/b.txt", b"b")
        directories, files = rt.storage_list("media", "")
        assert directories == ["sub"]
        assert files == ["a.txt"]

    def test_storage_url_returns_correct_path(self) -> None:
        rt = _make_runtime(capabilities={"storage": {"media": {"scope": "activity"}}})
        url = rt.storage_url("media", "img.png")
        assert url == "/activity/activity-1/storage/media/img.png"

    def test_storage_url_with_context_override(self) -> None:
        rt = _make_runtime(
            capabilities={"storage": {"uploads": {"scope": "user,activity"}}}
        )
        ctx: SandboxContext = {
            "activity-id": None,
            "course-id": None,
            "user-id": "other-user",
        }
        url = rt.storage_url("uploads", "file.txt", ctx)
        assert url == (
            "/activity/activity-1/storage/uploads/file.txt?user_id=other-user"
        )

    def test_storage_url_undeclared_name_rejected(self) -> None:
        rt = _make_runtime(capabilities={"storage": {"media": {"scope": "activity"}}})
        with pytest.raises(CapabilityError, match="not declared"):
            rt.storage_url("private", "img.png")


# ── Storage scope tests ──────────────────────────────────────────────


class TestStorageScopePaths:
    """Tests for scoped storage path resolution."""

    def test_activity_scope_path(self) -> None:
        rt = _make_runtime(capabilities={"storage": {"media": {"scope": "activity"}}})
        rt.storage_write("media", "img.png", b"data")
        assert rt.storage_read("media", "img.png") == b"data"

    def test_course_scope_path(self) -> None:
        """Course-scoped storage is shared across activities in the same course."""
        storage = MemoryFileStorage()
        rt1 = _make_runtime(
            capabilities={"storage": {"shared": {"scope": "course"}}},
            file_storage=storage,
        )
        rt1.storage_write("shared", "file.txt", b"course-data")

        # A different activity in the same course should see the same file
        rt2 = _make_runtime(
            capabilities={"storage": {"shared": {"scope": "course"}}},
            file_storage=storage,
        )
        # rt2 has the same course_id ("course-1") so it should read the same file
        assert rt2.storage_read("shared", "file.txt") == b"course-data"

    def test_global_scope_path(self) -> None:
        """Global-scoped storage is shared across all activities."""
        storage = MemoryFileStorage()
        rt = _make_runtime(
            capabilities={"storage": {"global_data": {"scope": "global"}}},
            file_storage=storage,
        )
        rt.storage_write("global_data", "config.json", b"{}")
        # Path: {activity_name}/{storage_name}/{path}
        assert storage.exists("test-activity/global_data/config.json")

    def test_user_activity_scope_path(self) -> None:
        """User+activity-scoped storage isolates per user."""
        storage = MemoryFileStorage()
        rt = _make_runtime(
            capabilities={"storage": {"uploads": {"scope": "user,activity"}}},
            file_storage=storage,
        )
        rt.storage_write("uploads", "file.txt", b"user-data")
        assert rt.storage_read("uploads", "file.txt") == b"user-data"
        # Path: {activity_name}/{storage_name}/{course_id}/{activity_id}/{user_id}/{path}
        assert storage.exists(
            "test-activity/uploads/course-1/activity-1/user-1/file.txt"
        )

    def test_user_course_scope_path(self) -> None:
        storage = MemoryFileStorage()
        rt = _make_runtime(
            capabilities={"storage": {"notes": {"scope": "user,course"}}},
            file_storage=storage,
        )
        rt.storage_write("notes", "note.txt", b"my-note")
        assert storage.exists("test-activity/notes/course-1/user-1/note.txt")

    def test_user_global_scope_path(self) -> None:
        storage = MemoryFileStorage()
        rt = _make_runtime(
            capabilities={"storage": {"profile": {"scope": "user,global"}}},
            file_storage=storage,
        )
        rt.storage_write("profile", "avatar.png", b"img")
        assert storage.exists("test-activity/profile/user-1/avatar.png")

    def test_context_override_user_id(self) -> None:
        """Passing a context with a different user_id accesses that user's storage."""
        storage = MemoryFileStorage()
        rt = _make_runtime(
            capabilities={"storage": {"uploads": {"scope": "user,activity"}}},
            file_storage=storage,
        )
        rt.storage_write("uploads", "file.txt", b"user1-data")

        # Read with a different user context
        other_context: SandboxContext = {
            "activity-id": None,
            "course-id": None,
            "user-id": "user-2",
        }
        # user-2 hasn't written anything, so should not exist
        assert not rt.storage_exists("uploads", "file.txt", other_context)

    def test_context_override_invalid_key_rejected(self) -> None:
        """Passing user_id context on activity-scoped storage should raise."""
        rt = _make_runtime(
            capabilities={"storage": {"media": {"scope": "activity"}}},
        )
        with pytest.raises(FieldValidationError, match="Invalid scope override"):
            rt.storage_write(
                "media",
                "file.txt",
                b"data",
                {"activity-id": None, "course-id": None, "user-id": "bob"},
            )
