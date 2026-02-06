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
    Access,
    CapabilityError,
    CapabilityChecker,
    ValueChecker,
    ValueType,
)
from server.activities.manifest_types import GulpsActivityManifest
from server.activities import kv
from server.activities.sandbox import SandboxExecutor


class MissingSandboxError(Exception):
    """Raised when a sandbox function is called but no wasm file exists."""


class ActivityContext:
    def __init__(self, activity_dir: Path) -> None:
        self._activity_dir = activity_dir

        # Key-value store (used internally for value storage)
        self.kv_store = kv.get_default()

        # Events posted by sandbox during execution
        self._pending_events: list[dict[str, str]] = []

        # Manifest capabilities and values (validated by Pydantic)
        with open(self._activity_dir / "manifest.json", encoding="utf8") as f:
            self.manifest = GulpsActivityManifest.model_validate_json(f.read())
        self.checker = CapabilityChecker(self.manifest.capabilities)
        self.value_checker = ValueChecker(self.manifest.values)

        # Sandboxed code
        self.sandbox: SandboxExecutor | None = None
        # TODO we need to make sure that the server field does not point to a parent directory
        server_path = self.manifest.server
        if server_path is not None:
            wasm_path = self._activity_dir / server_path
            self.sandbox = SandboxExecutor(wasm_path, self.host_functions())

    @property
    def activity_dir(self) -> Path:
        return self._activity_dir

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def html(self) -> str:
        html_path = self.activity_dir / "activity.html"
        if html_path.exists():
            return open(html_path, encoding="utf8").read()
        return ""

    @property
    def client_path(self) -> str:
        """Path to client script, relative to activity directory."""
        return self.manifest.client

    def call_sandbox_function(self, function_name: str, body: bytes) -> bytes:
        if self.sandbox is None:
            raise MissingSandboxError()

        # TODO catch errors?
        return self.sandbox.call_function(function_name, body)

    def _value_key(self, name: str, user_id: str) -> str:
        """Generate the KV store key for a value."""
        return f"gulps.{self.name}.{user_id}.{name}"

    def load_value(self, user_id: str, name: str) -> ValueType:
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

    def store_value(self, user_id: str, name: str, value: ValueType) -> None:
        """Set a declared value for a user.

        Raises:
            ValueValidationError: If the value is not declared or invalid.
        """
        # Validate against manifest definition
        self.value_checker.validate(name, value)

        key = self._value_key(name, user_id)
        self.kv_store.set(key, json.dumps(value))

    def get_filtered_values(
        self, user_id: str, user_access_level: Access
    ) -> dict[str, ValueType]:
        """Get all declared values that the user is allowed to see.

        Filters values based on user's access level. Values with higher access
        requirements than the user's level are excluded.

        Args:
            user_id: The user ID for loading user-scoped values.
            user_access_level: The user's access level.

        Returns:
            A dict of value names to their current values, filtered by access.
        """
        result: dict[str, ValueType] = {}
        for name in self.value_checker.value_names:
            if not self.value_checker.can_access(name, user_access_level):
                continue
            if self.value_checker.is_user_scoped(name):
                result[name] = self.load_value(user_id, name)
            else:
                result[name] = self.load_value("", name)
        return result

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

    def get_value(self, user_id: str, name: str) -> str:
        """Get a declared GULPS value for a user.

        Returns JSON-encoded value (e.g., "42" for integer, "true" for boolean).
        Returns the default value if not set.
        """
        value = self.load_value(user_id, name)
        return json.dumps(value)

    def set_value(self, user_id: str, name: str, value: str) -> bool:
        """Set a declared GULPS value for a user (host function).

        Takes JSON-encoded value. Validates against manifest.
        Returns True if set successfully, False on validation error.
        """
        try:
            decoded = json.loads(value)
            self.store_value(user_id, name, decoded)
            return True
        except (json.JSONDecodeError, ValueError):
            return False

    def host_functions(self) -> list[Callable[..., Any]]:
        """
        Host functions that will be made available to the sandbox.
        """
        return [
            self.get_value,
            self.set_value,
            self.http_request,
            self.post_event,
        ]

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
