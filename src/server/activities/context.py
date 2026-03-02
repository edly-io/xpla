"""
Host functions for Extism plugins.

These functions are injected into the plugin runtime and can be called
by WebAssembly code. They provide controlled access to server capabilities.
"""

from collections.abc import Callable
import json
import logging
from pathlib import Path
from typing import Annotated, Any
import urllib.error
import urllib.request

from extism import Json

from server.activities.actions import ActionChecker
from server.activities.capabilities import CapabilityChecker, CapabilityError
from server.activities.events import EventChecker
from server.activities.permission import Permission
from server.activities.fields import FieldChecker, FieldType
from server.activities.manifest_types import Scope, XplaActivityManifest
from server.activities import kv
from server.activities.sandbox import SandboxExecutor

logger = logging.getLogger(__file__)


class MissingSandboxError(Exception):
    """Raised when a sandbox function is called but no wasm file exists."""


class AssetAccessError(Exception):
    """Raised when attempting to access an activity asset that does not exist or without the right permissions"""


class ActivityContext:
    # TODO actually set these parameters in a real-life scenario
    DEFAULT_COURSE_ID = "democourse"
    DEFAULT_ACTIVITY_ID = "activityid"
    DEFAULT_PERMISSION = Permission.play
    DEFAULT_USER_ID = "alice"

    def __init__(
        self,
        activity_dir: Path,
        # TODO make these arguments positional, and not optional
        activity_id: str = DEFAULT_ACTIVITY_ID,
        course_id: str = DEFAULT_COURSE_ID,
        user_id: str = DEFAULT_USER_ID,
        permission: Permission = DEFAULT_PERMISSION,
    ) -> None:
        self._activity_dir = activity_dir
        self._user_id: str = user_id
        self._permission: Permission = permission
        self._course_id: str = course_id
        self._activity_id: str = activity_id

        # Key-value store (used internally for field storage)
        self.kv_store = kv.get_default()

        # Events posted by sandbox during execution
        self._pending_events: list[dict[str, str]] = []

        # Manifest capabilities and fields (validated by Pydantic)
        with open(self._activity_dir / "manifest.json", encoding="utf8") as f:
            self.manifest = XplaActivityManifest.model_validate_json(f.read())
        self.capability_checker = CapabilityChecker(self.manifest.capabilities)
        self.field_checker = FieldChecker(self.manifest.fields)
        self.action_checker = ActionChecker(self.manifest.actions)
        self.event_checker = EventChecker(self.manifest.events)

        # Sandboxed code
        self.sandbox: SandboxExecutor | None = None
        server_path = self.manifest.server
        if server_path is not None:
            # Note: we know that this is a safe path thanks to path constraints in the manifests
            wasm_path = self._activity_dir / server_path
            self.sandbox = SandboxExecutor(wasm_path, self.host_functions())

    @property
    def user_id(self) -> str:
        return self._user_id

    @user_id.setter
    def user_id(self, value: str) -> None:
        self._user_id = value

    @property
    def course_id(self) -> str:
        return self._course_id

    @course_id.setter
    def course_id(self, value: str) -> None:
        self._course_id = value

    @property
    def activity_id(self) -> str:
        return self._activity_id

    @activity_id.setter
    def activity_id(self, value: str) -> None:
        self._activity_id = value

    @property
    def permission(self) -> Permission:
        return self._permission

    @permission.setter
    def permission(self, value: Permission) -> None:
        self._permission = value

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def client_path(self) -> str:
        """
        Path to client script, relative to activity directory.

        Note that this is a safe path thanks to schema constraints.
        """
        return self.manifest.client

    def get_asset_path(self, file_path: str) -> Path:
        full_path = self._activity_dir / file_path
        try:
            full_path.resolve().relative_to(self._activity_dir.resolve())
        except ValueError as e:
            raise AssetAccessError("Incorrect path") from e

        # Only serve files declared in manifest
        if file_path not in (self.manifest.client, "manifest.json"):
            if file_path not in [item.root for item in (self.manifest.static or [])]:
                raise AssetAccessError("Undeclared asset")

        if not full_path.exists() or not full_path.is_file():
            raise AssetAccessError("Asset does not exist")

        return full_path

    def on_action(self, action_name: str, action_value: Any) -> None:
        """
        Call the sandbox onAction callback.

        Raise ActionValidationError if action is not valid.
        """
        self.action_checker.validate(action_name, action_value)
        # Call sandbox's onAction if available
        if self.sandbox is not None:
            action_input = {"name": action_name, "value": action_value}
            try:
                self.call_sandbox_function("onAction", action_input)
            except RuntimeError as e:
                # onAction not defined in sandbox - log warning and continue
                # TODO how to capture errors related to sandbox code? Should we raise a 500?
                logger.warning(
                    "Activity '%s' has no onAction handler: %s", self.activity_id, e
                )

    def call_sandbox_function(
        self, function_name: str, input_data: Any = None
    ) -> bytes:
        if self.sandbox is None:
            raise MissingSandboxError()

        # TODO catch errors?
        return self.sandbox.call_function(function_name, input_data)

    def _field_key(
        self, name: str, course_id: str, activity_id: str, user_id: str
    ) -> str:
        """Generate the KV store key for a field."""
        return f"xpla.{self.name}.{course_id}.{activity_id}.{user_id}.{name}"

    def load_field(
        self, course_id: str, activity_id: str, user_id: str, name: str
    ) -> FieldType:
        """Get a declared field.

        Returns the stored value, or the default if not set.

        Raises:
            FieldValidationError: If the field is not declared in manifest.
        """
        # Check that field is declared (raises if not)
        default = self.field_checker.get_default(name)

        key = self._field_key(name, course_id, activity_id, user_id)
        stored = self.kv_store.get(key)
        if stored is None:
            return default
        return stored

    def store_field(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_id: str,
        user_id: str,
        name: str,
        value: FieldType,
    ) -> None:
        """Set a declared field.

        Raises:
            FieldValidationError: If the field is not declared or invalid.
        """
        # Validate against manifest definition
        self.field_checker.validate(name, value)

        key = self._field_key(name, course_id, activity_id, user_id)
        self.kv_store.set(key, value)

    def _scope_key_segments(self, scope: Scope, user_id: str) -> tuple[str, str, str]:
        """Return (course_id, activity_id, user_id) key segments for a scope."""
        scope_map: dict[Scope, tuple[str, str, str]] = {
            Scope.activity: (self._course_id, self._activity_id, ""),
            Scope.user_activity: (self._course_id, self._activity_id, user_id),
            Scope.course: (self._course_id, "", ""),
            Scope.user_course: (self._course_id, "", user_id),
            Scope.platform: ("", "", ""),
            Scope.user_platform: ("", "", user_id),
        }
        return scope_map[scope]

    def get_all_fields(self, user_id: str) -> dict[str, FieldType]:
        """Get all declared fields for a user.

        Args:
            user_id: The user ID for loading user-scoped fields.

        Returns:
            A dict of field names to their current values.
        """
        result: dict[str, FieldType] = {}
        for name in self.field_checker.field_names:
            scope = self.field_checker.get_scope(name)
            course_id, activity_id, uid = self._scope_key_segments(scope, user_id)
            result[name] = self.load_field(course_id, activity_id, uid, name)
        return result

    def get_state(self) -> dict[str, FieldType]:
        """Get the activity state to send to the client.

        If the sandbox exports a getState function, calls it and returns the
        result. Otherwise falls back to returning all fields.
        """
        if self.sandbox is not None:
            try:
                result = self.call_sandbox_function("getState")
                state: dict[str, FieldType] = json.loads(result)
                return state
            except RuntimeError:
                pass
        return self.get_all_fields(self._user_id)

    def clear_pending_events(self) -> list[dict[str, str]]:
        """Return and clear all pending events."""
        events = self._pending_events
        self._pending_events = []
        return events

    def host_functions(self) -> list[Callable[..., Any]]:
        """
        Host functions that will be made available to the sandbox.
        """
        return [
            self.get_permission,
            self.send_event,
            self.get_field,
            self.set_field,
            self.http_request,
            self.submit_grade,
        ]

    def get_permission(self) -> str:
        """
        Return the current permission level.
        """
        return self._permission.value

    def send_event(self, name: str, value: str) -> str:
        """Send an event back to the client.

        Called by sandbox code to send events (e.g., field changes) to the frontend.

        Raises:
            EventValidationError: If the event is not declared in manifest.
        """
        self.event_checker.validate(name, json.loads(value))
        self._pending_events.append({"name": name, "value": value})
        return ""

    def get_field(self, name: str) -> str:
        """Get a field, resolving scope from manifest.

        Returns JSON-encoded value (e.g., "42" for integer, "true" for boolean).
        Returns the default value if not set.
        """
        scope = self.field_checker.get_scope(name)
        course_id, activity_id, user_id = self._scope_key_segments(scope, self._user_id)
        value = self.load_field(course_id, activity_id, user_id, name)
        return json.dumps(value)

    def set_field(self, name: str, value: str) -> bool:
        """Set a field, resolving scope from manifest. Takes JSON-encoded value."""
        scope = self.field_checker.get_scope(name)
        course_id, activity_id, user_id = self._scope_key_segments(scope, self._user_id)
        try:
            decoded = json.loads(value)
        except json.decoder.JSONDecodeError:
            logger.error(
                "Failed to decode name='%s' value='%s'",
                name,
                value,
            )
            raise
        self.store_field(course_id, activity_id, user_id, name, decoded)
        return True

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
            self.capability_checker.check_http_request(url)
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

    def submit_grade(self, score: float) -> bool:
        # TODO actually submit grade
        logger.info("submitted score: %f", score)
        return True
