from collections.abc import Generator
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from server.activities.kv import KVStore


@pytest.fixture(autouse=True)
def _isolated_kv() -> Generator[None]:
    """Ensure each test gets a fresh, isolated KV store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = KVStore(Path(tmpdir) / "kv.json")
        with patch("server.activities.kv.get_default", return_value=store):
            yield
