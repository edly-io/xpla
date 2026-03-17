from collections.abc import Generator
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from xpla.demo.kv import KVStore


@pytest.fixture(autouse=True)
def _isolated_kv() -> Generator[KVStore]:
    """Ensure each test gets a fresh, isolated KV store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = KVStore(Path(tmpdir) / "kv.json")
        with patch("xpla.demo.kv.get_default", return_value=store):
            with patch("xpla.demo.app.kv_store", store):
                yield store
