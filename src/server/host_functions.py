"""
Host functions for Extism plugins.

These functions are injected into the plugin runtime and can be called
by WebAssembly code. They provide controlled access to server capabilities.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

from extism import host_fn, Json

from server.capabilities import (
    Capabilities,
    CapabilityError,
    CapabilityChecker,
    Manifest,
    parse_capabilities,
)


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
_checker = CapabilityChecker(Capabilities())


def create_host_functions(
    activity_dir: Path,
    manifest: Manifest,
) -> list[Callable[..., Any]]:
    """Create host functions configured for an activity.

    Args:
        activity_dir: Path to the activity directory for storage.
        manifest: Activity manifest for capability enforcement.

    Returns:
        List of host functions to register with the plugin.
    """
    # TODO get rid of globals
    global _kv_store, _checker

    storage_path = activity_dir / "kv_store.json"
    _kv_store = KVStore(storage_path)

    capabilities = parse_capabilities(manifest)
    _checker = CapabilityChecker(capabilities)

    # TODO for now we pass the activity name as user data, but in the future we
    # should pass the activity, with all the corresponding API: KVStore, manifest, etc.
    # TODO add activity to context data
    context_data = manifest["name"]

    def _lms_submit_grade(grade: Annotated[dict[str, object], Json]) -> str:
        return lms_submit_grade(grade, context_data)

    # TODO we should associate functions only if they are part of the manifest?
    return [
        host_fn(name=func.__name__)(_func)
        for (func, _func) in [
            # (kv_get, _kv_get),
            # (kv_set, _kv_set),
            # (kv_delete, _kv_delete),
            # (kv_keys, _kv_keys),
            # (http_request, _http_request),
            # (lms_get_user, _lms_get_user),
            (lms_submit_grade, _lms_submit_grade),
        ]
    ]


def lms_submit_grade(
    grade: Annotated[dict[str, object], Json], context_data: str
) -> str:
    """Submit a grade for the current user.

    Expects JSON: {"score": 85, "max_score": 100, "comment": "..."}
    Returns JSON: {"status": "submitted"}
    """
    print(f"Grade submitted for activity '{context_data}'")
    try:
        _checker.check_lms_function("submit_grade")
    except CapabilityError as e:
        return json.dumps({"error": str(e)})

    # TODO actually submit grade
    return json.dumps({"status": "submitted", "score": grade["score"]})


# def kv_get(key: str, user_data: bytes) -> str:
#     """Get a value from the key-value store.

#     Returns empty string if key not found.
#     """
#     try:
#         _checker.check_kv_access()
#     except CapabilityError as e:
#         return json.dumps({"error": str(e)})

#     if _kv_store is None:
#         return ""
#     return _kv_store.get(key) or ""


# def kv_set(input_data: Annotated[dict[str, str], Json], context_data: bytes) -> str:
#     """Set a key-value pair in the store.

#     Expects JSON: {"key": "...", "value": "..."}
#     Returns "ok" on success.
#     """
#     try:
#         _checker.check_kv_write(input_data["key"], input_data["value"])
#     except CapabilityError as e:
#         return json.dumps({"error": str(e)})

#     if _kv_store is None:
#         return "error: store not initialized"
#     _kv_store.set(input_data["key"], input_data["value"])
#     return "ok"


# def kv_delete(key: str, context_data: bytes) -> str:
#     """Delete a key from the store.

#     Returns "deleted" if key existed, "not_found" otherwise.
#     """
#     try:
#         _checker.check_kv_access()
#     except CapabilityError as e:
#         return json.dumps({"error": str(e)})

#     if _kv_store is None:
#         return "error: store not initialized"
#     if _kv_store.delete(key):
#         return "deleted"
#     return "not_found"


# def kv_keys(_input: str, context_data: bytes) -> str:
#     """List all keys in the store.

#     Returns JSON array of keys.
#     """
#     try:
#         _checker.check_kv_access()
#     except CapabilityError as e:
#         return json.dumps({"error": str(e)})

#     if _kv_store is None:
#         return "[]"
#     return json.dumps(_kv_store.keys())


# def http_request(request_data: Annotated[dict[str, object], Json], context_data: bytes) -> str:
#     """Make an HTTP request.

#     Expects JSON: {
#         "method": "GET"|"POST"|...,
#         "url": "https://...",
#         "headers": {"...": "..."},
#         "body": "..."
#     }

#     Returns response body as string, or error message.
#     """
#     url = str(request_data["url"])

#     try:
#         _checker.check_http_request(url)
#     except CapabilityError as e:
#         return json.dumps({"error": str(e)})

#     method = str(request_data.get("method", "GET"))
#     headers = {str(k): str(v) for k, v in dict(request_data.get("headers", {})).items()}
#     body = request_data.get("body")

#     body_bytes = str(body).encode("utf-8") if body else None

#     req = urllib.request.Request(
#         url,
#         data=body_bytes,
#         headers=headers,
#         method=method,
#     )

#     try:
#         with urllib.request.urlopen(req, timeout=10) as response:
#             content: str = response.read().decode("utf-8")
#             return content
#     except urllib.error.HTTPError as e:
#         return json.dumps({"error": f"HTTP {e.code}: {e.reason}"})
#     except urllib.error.URLError as e:
#         return json.dumps({"error": str(e.reason)})


# def lms_get_user(_input: str, context_data: bytes) -> str:
#     """Get current LMS user info as JSON.

#     Returns JSON: {"id": "...", "name": "..."}
#     """
#     try:
#         _checker.check_lms_function("get_user")
#     except CapabilityError as e:
#         return json.dumps({"error": str(e)})

#     # TODO return actual user?
#     return json.dumps(
#         {
#             "id": 1,
#             "name": "John Doe",
#         }
#     )
