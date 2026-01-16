"""
Host functions for Extism plugins.

These functions are injected into the plugin runtime and can be called
by WebAssembly code. They provide controlled access to server capabilities.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any
import urllib.error
import urllib.request

from extism import Json

from server.activities.capabilities import CapabilityError, CapabilityChecker, Manifest
from server.activities.kv import KVStore
from server.activities.sandbox import Sandbox


class MissingSandboxError(Exception):
    """
    TODO rename/move/delete this class because it's mostly useless
    """


class ActivityContext:
    INSTANCE: "ActivityContext" | None = None

    @classmethod
    def load(cls, activity_dir: Path) -> "ActivityContext":
        """
        TODO this static method is unnecessary, remove it in the future.
        """
        cls.INSTANCE = ActivityContext(activity_dir)
        return cls.INSTANCE

    def __init__(self, activity_dir: Path) -> None:
        self._activity_dir = activity_dir

        # Key-value store
        kv_store_path = self._activity_dir / "kv_store.json"
        self.kv_store = KVStore(kv_store_path)

        # Manifest capabilities checker
        with open(self._activity_dir / "manifest.json", encoding="utf8") as f:
            self.manifest: Manifest = json.load(f)
        self.checker = CapabilityChecker.load_from_manifest(self.manifest)

        # Sandboxed code
        self.sandbox: Sandbox | None = None
        if self.sandbox_plugin_path.exists():
            self.sandbox = Sandbox(self.sandbox_plugin_path, self.host_functions())

    @property
    def name(self) -> str:
        return self.manifest["name"]

    @property
    def sandbox_plugin_path(self) -> Path:
        return self._activity_dir / "plugin.wasm"

    def call_sandbox_function(self, function_name: str, body: bytes) -> bytes:
        if self.sandbox is None:
            raise MissingSandboxError()

        # TODO catch errors?
        return self.sandbox.call_function(function_name, body)

    def host_functions(self) -> list[Callable[..., Any]]:
        """
        Host functions that will be made available to the sandbox.
        """
        # TODO we should associate functions only if they are part of the manifest?
        return [
            self.kv_get,
            self.kv_set,
            self.kv_delete,
            self.kv_keys,
            self.http_request,
            self.lms_get_user,
            self.lms_submit_grade,
        ]

    def lms_submit_grade(self, grade: Annotated[dict[str, object], Json]) -> str:
        """Submit a grade for the current user.

        Expects JSON: {"score": 85, "max_score": 100, "comment": "..."}
        Returns JSON: {"status": "submitted"}
        """
        print(f"Grade submitted for activity '{self.name}'")
        try:
            self.checker.check_lms_function("submit_grade")
        except CapabilityError as e:
            return json.dumps({"error": str(e)})

        # TODO actually submit grade
        return json.dumps({"status": "submitted", "score": grade["score"]})

    def kv_get(self, key: str) -> str:
        """Get a value from the key-value store.

        Returns empty string if key not found.
        """
        try:
            self.checker.check_kv_access()
        except CapabilityError as e:
            return json.dumps({"error": str(e)})

        return self.kv_store.get(key) or ""

    def kv_set(self, input_data: Annotated[dict[str, str], Json]) -> str:
        """Set a key-value pair in the store.

        Expects JSON: {"key": "...", "value": "..."}
        Returns "ok" on success.
        """
        try:
            self.checker.check_kv_write(input_data["key"], input_data["value"])
        except CapabilityError as e:
            return json.dumps({"error": str(e)})

        self.kv_store.set(input_data["key"], input_data["value"])
        return "ok"

    def kv_delete(self, key: str) -> str:
        """Delete a key from the store.

        Returns "deleted" if key existed, "not_found" otherwise.
        """
        try:
            self.checker.check_kv_access()
        except CapabilityError as e:
            return json.dumps({"error": str(e)})

        if self.kv_store.delete(key):
            return "deleted"
        return "not_found"

    def kv_keys(self, _input: str) -> str:
        """List all keys in the store.

        Returns JSON array of keys.
        """
        try:
            self.checker.check_kv_access()
        except CapabilityError as e:
            return json.dumps({"error": str(e)})

        return json.dumps(self.kv_store.keys())

    def http_request(
        self,
        url: str,
        method: str,
        body: bytes,
        headers: Annotated[tuple[tuple[str, str]], Json],
        # Annotated[dict[str, object], Json]
    ) -> str:
        """Make an HTTP request.

        Expects JSON: {
            "method": "GET"|"POST"|...,
            "url": "https://...",
            "headers": {"...": "..."},
            "body": "..."
        }

        Returns response body as string, or error message.
        """
        try:
            self.checker.check_http_request(url)
        except CapabilityError as e:
            return json.dumps({"error": str(e)})

        body_bytes = body or None

        req = urllib.request.Request(
            url,
            data=body_bytes,
            headers=dict(headers),
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                content: str = response.read().decode("utf-8")
                return content
        except urllib.error.HTTPError as e:
            return json.dumps({"error": f"HTTP {e.code}: {e.reason}"})
        except urllib.error.URLError as e:
            return json.dumps({"error": str(e.reason)})

    def lms_get_user(self, _input: str) -> str:
        """Get current LMS user info as JSON.

        Returns JSON: {"id": "...", "name": "..."}
        """
        try:
            self.checker.check_lms_function("get_user")
        except CapabilityError as e:
            return json.dumps({"error": str(e)})

        # TODO return actual user?
        return json.dumps(
            {
                "id": 1,
                "name": "John Doe",
            }
        )
