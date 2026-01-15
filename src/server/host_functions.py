"""
Host functions for Extism plugins.

These functions are injected into the plugin runtime and can be called
by WebAssembly code. They provide controlled access to server capabilities.
"""

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Annotated

from extism import host_fn, Json


class KVStore:
    """Persistent key-value store backed by a JSON file."""

    def __init__(self, storage_path: Path) -> None:
        """Initialize the KV store.

        Args:
            storage_path: Path to the JSON file for persistence.
        """
        self._path = storage_path
        self._data: dict[str, str] = {}
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

    def get(self, key: str) -> str | None:
        """Get a value by key."""
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
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


# Module-level instances (set by create_host_functions)
_kv_store: KVStore | None = None
_lms: "LMSSimulator | None" = None  # type: ignore[name-defined]
_checker: "CapabilityChecker | None" = None  # type: ignore[name-defined]


def create_host_functions(
    activity_dir: Path,
    activity_id: str = "unknown",
    manifest: dict[str, object] | None = None,
) -> list:
    """Create host functions configured for an activity.

    Args:
        activity_dir: Path to the activity directory for storage.
        activity_id: ID of the activity (from manifest).
        manifest: Optional manifest dict for capability enforcement.

    Returns:
        List of host functions to register with the plugin.
    """
    global _kv_store, _lms, _checker

    # Lazy imports to avoid circular dependencies
    from server.capabilities import CapabilityChecker, parse_capabilities
    from server.lms import LMSSimulator

    storage_path = activity_dir / "kv_store.json"
    _kv_store = KVStore(storage_path)
    _lms = LMSSimulator(activity_dir, activity_id)

    # Set up capability checker if manifest provided
    if manifest is not None:
        capabilities = parse_capabilities(manifest)
        _checker = CapabilityChecker(capabilities)
    else:
        _checker = None

    return [
        kv_get,
        kv_set,
        kv_delete,
        kv_keys,
        http_request,
        lms_get_user,
        lms_submit_grade,
    ]


@host_fn()
def kv_get(key: str) -> str:
    """Get a value from the key-value store.

    Returns empty string if key not found.
    """
    if _checker is not None:
        try:
            _checker.check_kv_access()
        except Exception as e:
            return json.dumps({"error": str(e)})

    if _kv_store is None:
        return ""
    return _kv_store.get(key) or ""


@host_fn()
def kv_set(input_data: Annotated[dict[str, str], Json]) -> str:
    """Set a key-value pair in the store.

    Expects JSON: {"key": "...", "value": "..."}
    Returns "ok" on success.
    """
    if _checker is not None:
        try:
            _checker.check_kv_write(input_data["key"], input_data["value"])
        except Exception as e:
            return json.dumps({"error": str(e)})

    if _kv_store is None:
        return "error: store not initialized"
    _kv_store.set(input_data["key"], input_data["value"])
    return "ok"


@host_fn()
def kv_delete(key: str) -> str:
    """Delete a key from the store.

    Returns "deleted" if key existed, "not_found" otherwise.
    """
    if _checker is not None:
        try:
            _checker.check_kv_access()
        except Exception as e:
            return json.dumps({"error": str(e)})

    if _kv_store is None:
        return "error: store not initialized"
    if _kv_store.delete(key):
        return "deleted"
    return "not_found"


@host_fn()
def kv_keys(_input: str) -> str:
    """List all keys in the store.

    Returns JSON array of keys.
    """
    if _checker is not None:
        try:
            _checker.check_kv_access()
        except Exception as e:
            return json.dumps({"error": str(e)})

    if _kv_store is None:
        return "[]"
    return json.dumps(_kv_store.keys())


@host_fn()
def http_request(request_data: Annotated[dict[str, object], Json]) -> str:
    """Make an HTTP request.

    Expects JSON: {
        "method": "GET"|"POST"|...,
        "url": "https://...",
        "headers": {"...": "..."},
        "body": "..."
    }

    Returns response body as string, or error message.
    """
    url = str(request_data["url"])

    if _checker is not None:
        try:
            _checker.check_http_request(url)
        except Exception as e:
            return json.dumps({"error": str(e)})

    method = str(request_data.get("method", "GET"))
    headers = {str(k): str(v) for k, v in dict(request_data.get("headers", {})).items()}
    body = request_data.get("body")

    body_bytes = str(body).encode("utf-8") if body else None

    req = urllib.request.Request(
        url,
        data=body_bytes,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as e:
        return json.dumps({"error": str(e.reason)})
    except urllib.error.HTTPError as e:
        return json.dumps({"error": f"HTTP {e.code}: {e.reason}"})


@host_fn()
def lms_get_user(_input: str) -> str:
    """Get current LMS user info as JSON.

    Returns JSON: {"id": "...", "name": "...", "email": "...", "roles": [...]}
    """
    if _checker is not None:
        try:
            _checker.check_lms_function("get_user")
        except Exception as e:
            return json.dumps({"error": str(e)})

    if _lms is None:
        return json.dumps({"error": "LMS not initialized"})

    user = _lms.get_current_user()
    return json.dumps(
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "roles": user.roles,
        }
    )


@host_fn()
def lms_submit_grade(grade_data: Annotated[dict[str, object], Json]) -> str:
    """Submit a grade for the current user.

    Expects JSON: {"score": 85, "max_score": 100, "comment": "..."}
    Returns JSON: {"status": "submitted", "timestamp": "..."}
    """
    if _checker is not None:
        try:
            _checker.check_lms_function("submit_grade")
        except Exception as e:
            return json.dumps({"error": str(e)})

    if _lms is None:
        return json.dumps({"error": "LMS not initialized"})

    record = _lms.submit_grade(
        score=float(grade_data["score"]),
        max_score=float(grade_data.get("max_score", 100)),
        comment=str(grade_data.get("comment", "")),
    )
    return json.dumps(
        {
            "status": "submitted",
            "timestamp": record.timestamp.isoformat(),
        }
    )
