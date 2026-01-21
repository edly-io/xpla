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

from server.activities.capabilities import (
    CapabilityError,
    CapabilityChecker,
    Manifest,
    ValueChecker,
    ValueType,
)
from server.activities import kv
from server.activities.sandbox import SandboxExecutor


class MissingSandboxError(Exception):
    """Raised when a sandbox function is called but no wasm file exists."""


class ActivityContext:
    def __init__(self, activity_dir: Path) -> None:
        self._activity_dir = activity_dir

        # Key-value store
        self.kv_store = kv.get_default()

        # Events posted by sandbox during execution
        self._pending_events: list[dict[str, str]] = []

        # Manifest capabilities and values
        # TODO check manifest validity
        with open(self._activity_dir / "manifest.json", encoding="utf8") as f:
            self.manifest: Manifest = json.load(f)
        self.checker = CapabilityChecker.load_from_manifest(self.manifest)
        self.value_checker = ValueChecker.load_from_manifest(self.manifest)

        # Sandboxed code
        self.sandbox: SandboxExecutor | None = None
        if self.sandbox_path.exists():
            self.sandbox = SandboxExecutor(self.sandbox_path, self.host_functions())

    @property
    def activity_dir(self) -> Path:
        return self._activity_dir

    @property
    def name(self) -> str:
        return self.manifest["name"]

    @property
    def html(self) -> str:
        html_path = self.activity_dir / "activity.html"
        if html_path.exists():
            return open(html_path, encoding="utf8").read()
        return ""

    @property
    def sandbox_path(self) -> Path:
        return self._activity_dir / "sandbox.wasm"

    def call_sandbox_function(self, function_name: str, body: bytes) -> bytes:
        if self.sandbox is None:
            raise MissingSandboxError()

        # TODO catch errors?
        return self.sandbox.call_function(function_name, body)

    def _value_key(self, name: str, user_id: str) -> str:
        """Generate the KV store key for a value."""
        return f"learningactivity.{self.name}.{user_id}.{name}"

    def get_value(self, name: str, user_id: str) -> ValueType:
        """Get a declared value for a user.

        Returns the stored value, or the default if not set.

        Raises:
            ValueValidationError: If the value is not declared in manifest.
        """
        # Check that value is declared (raises if not)
        default = self.value_checker.get_default(name)

        key = self._value_key(name, user_id)
        stored = self.kv_store.get(key)
        if stored is None:
            return default

        # Deserialize from JSON
        result: ValueType = json.loads(stored)
        return result

    def set_value(self, name: str, user_id: str, value: ValueType) -> None:
        """Set a declared value for a user.

        Raises:
            ValueValidationError: If the value is not declared or invalid.
        """
        # Validate against manifest definition
        self.value_checker.validate(name, value)

        key = self._value_key(name, user_id)
        self.kv_store.set(key, json.dumps(value))

    def get_all_values(self, user_id: str) -> dict[str, ValueType]:
        """Get all declared values for a user.

        Returns a dict mapping value names to their current values (or defaults).
        """
        return {
            name: self.get_value(name, user_id)
            for name in self.value_checker.value_names
        }

    def clear_pending_events(self) -> list[dict[str, str]]:
        """Return and clear all pending events."""
        events = self._pending_events
        self._pending_events = []
        return events

    def post_event(self, name: str, value: str) -> str:
        """Post an event to be sent back to the client.

        Called by sandbox code to send events (e.g., value changes) to the frontend.
        """
        self._pending_events.append({"name": name, "value": value})
        return ""

    # TODO value_get and value_set should really be get_value and set_value, but
    # then these would conflict with the other methods. Either give a different
    # name via host_fn or move methods to a different class.
    def value_get(self, user_id: str, name: str) -> str:
        """Get a declared activity value for a user.

        Returns JSON-encoded value (e.g., "42" for integer, "true" for boolean).
        Returns the default value if not set.
        """
        value = self.get_value(name, user_id)
        return json.dumps(value)

    def value_set(self, user_id: str, name: str, value: str) -> bool:
        """Set a declared activity value for a user.

        Takes JSON-encoded value. Validates against manifest.
        Returns True if set successfully, False on validation error.
        """
        try:
            decoded = json.loads(value)
            self.set_value(name, user_id, decoded)
            return True
        except (json.JSONDecodeError, ValueError):
            return False

    def host_functions(self) -> list[Callable[..., Any]]:
        """
        Host functions that will be made available to the sandbox.
        """
        # TODO we should associate functions only if they are part of the manifest?
        return [
            self.lms_submit_grade,
            self.value_get,
            self.value_set,
            # self.kv_get,
            # self.kv_set,
            # self.kv_delete,
            # self.kv_keys,
            self.http_request,
            self.lms_get_user,
            self.post_event,
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

        key = f"learningactivity.{self.name}.{key}"
        return self.kv_store.get(key) or ""

    def kv_set(self, key: str, value: str) -> bool:
        """Set a key-value pair in the store.

        Returns True if the value was set, False if capability check failed.
        """
        try:
            self.checker.check_kv_write(key, value)
        except CapabilityError:
            return False

        key = f"learningactivity.{self.name}.{key}"
        self.kv_store.set(key, value)
        return True

    # def kv_delete(self, key: str) -> str:
    #     """Delete a key from the store.

    #     Returns "deleted" if key existed, "not_found" otherwise.
    #     """
    #     try:
    #         self.checker.check_kv_access()
    #     except CapabilityError as e:
    #         return json.dumps({"error": str(e)})

    #     if self.kv_store.delete(key):
    #         return "deleted"
    #     return "not_found"

    # def kv_keys(self, _input: str) -> str:
    #     """List all keys in the store.

    #     Returns JSON array of keys.
    #     """
    #     try:
    #         self.checker.check_kv_access()
    #     except CapabilityError as e:
    #         return json.dumps({"error": str(e)})

    #     return json.dumps(self.kv_store.keys())

    def http_request(
        self,
        url: str,
        method: str,
        body: bytes,
        headers: Annotated[tuple[tuple[str, str], ...], Json],
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

        # TODO return actual user. (and replace instances of 'anonymous' elsewhere.)
        return json.dumps({"id": "anonymous"})
