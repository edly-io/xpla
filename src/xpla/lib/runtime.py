"""
Host functions for Extism plugins.

These functions are injected into the plugin runtime and can be called
by WebAssembly code. They provide controlled access to server capabilities.
"""

from collections.abc import Callable
import json
import logging
from pathlib import Path
from typing import Annotated, Any, TypedDict
import urllib.error
import urllib.request

import extism

from xpla.lib.actions import ActionChecker
from xpla.lib.capabilities import CapabilityChecker, CapabilityError
from xpla.lib.events import EventChecker
from xpla.lib.field_store import FieldStore
from xpla.lib.permission import Permission
from xpla.lib.fields import FieldChecker, FieldType, FieldValidationError
from xpla.lib.manifest_types import LogField, Scope, XplaActivityManifest
from xpla.lib.sandbox import SandboxExecutor, SandboxRuntimeError, get_sandbox_executor

logger = logging.getLogger(__file__)


class PendingEvent(TypedDict):
    name: str
    value: str
    context: dict[str, str]
    permission: str


class AssetAccessError(Exception):
    """Raised when attempting to access an activity asset that does not exist or without the right permissions"""


class ActivityRuntime:

    def __init__(
        self,
        activity_dir: Path,
        field_store: FieldStore,
        activity_id: str,
        course_id: str,
        user_id: str,
        permission: Permission,
    ) -> None:
        self._activity_dir = activity_dir
        self._user_id: str = user_id
        self._permission: Permission = permission
        self._course_id: str = course_id
        self._activity_id: str = activity_id

        # Field storage backend
        self.field_store: FieldStore = field_store

        # Events posted by sandbox during execution
        self._pending_events: list[PendingEvent] = []

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
            self.sandbox = get_sandbox_executor(wasm_path, self.host_functions())

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

        The sandbox receives the action name, the action value, a context dict
        with the current identifiers (user_id, course_id, activity_id),
        and the current permission level.

        Raise ActionValidationError if action is not valid.
        """
        self.action_checker.validate(action_name, action_value)
        # Call sandbox's onAction if available
        if self.sandbox is not None:
            action_input = {
                "name": action_name,
                "value": action_value,
                "context": {
                    "user_id": self._user_id,
                    "course_id": self._course_id,
                    "activity_id": self._activity_id,
                },
                "permission": self._permission.value,
            }
            try:
                self.sandbox.call_function("onAction", action_input)
            except SandboxRuntimeError as e:
                # TODO It's OK to ignore onAction errors, but we should report errors to the frontend
                logger.exception(e)

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

        stored = self.field_store.get(course_id, self.name, activity_id, user_id, name)
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

        self.field_store.set(course_id, self.name, activity_id, user_id, name, value)

    # Valid override keys for each scope
    _VALID_SCOPE_KEYS: dict[Scope, set[str]] = {
        Scope.activity: {"course_id", "instance_id"},
        Scope.user_activity: {"course_id", "instance_id", "user_id"},
        Scope.course: {"course_id"},
        Scope.user_course: {"course_id", "user_id"},
        Scope.global_: set(),
        Scope.user_global: {"user_id"},
    }

    def _scope_key_segments(
        self, scope: Scope, overrides: dict[str, str] | None = None
    ) -> tuple[str, str, str]:
        """Return (course_id, activity_id, user_id) key segments for a scope.

        Args:
            scope: The field scope.
            overrides: Optional dict of dimension overrides (e.g. {"user_id": "bob"}).

        Raises:
            FieldValidationError: If an override key is not valid for the scope.
        """
        if overrides:
            valid_keys = self._VALID_SCOPE_KEYS[scope]
            invalid = set(overrides.keys()) - valid_keys
            if invalid:
                raise FieldValidationError(
                    f"Invalid scope override keys {invalid} for scope '{scope.value}'. "
                    f"Valid keys: {valid_keys}"
                )

        overrides = overrides or {}
        scope_map: dict[Scope, tuple[str, str, str]] = {
            Scope.activity: (
                overrides.get("course_id", self._course_id),
                overrides.get("instance_id", self._activity_id),
                "",
            ),
            Scope.user_activity: (
                overrides.get("course_id", self._course_id),
                overrides.get("instance_id", self._activity_id),
                overrides.get("user_id", self._user_id),
            ),
            Scope.course: (
                overrides.get("course_id", self._course_id),
                "",
                "",
            ),
            Scope.user_course: (
                overrides.get("course_id", self._course_id),
                "",
                overrides.get("user_id", self._user_id),
            ),
            Scope.global_: ("", "", ""),
            Scope.user_global: (
                "",
                "",
                overrides.get("user_id", self._user_id),
            ),
        }
        return scope_map[scope]

    def get_all_fields(self) -> dict[str, FieldType]:
        """Get all declared fields for a user.

        Returns:
            A dict of field names to their current values.
        """
        result: dict[str, FieldType] = {}
        for name in self.field_checker.field_names:
            if isinstance(self.field_checker.get_definition(name), LogField):
                continue
            scope = self.field_checker.get_scope(name)
            course_id, activity_id, uid = self._scope_key_segments(scope)
            result[name] = self.load_field(course_id, activity_id, uid, name)
        return result

    def get_state(self) -> dict[str, FieldType]:
        """Get the activity state to send to the client.

        If the sandbox exports a getState function, calls it with a
        ``{context, permission}`` input dict and returns the result.
        Otherwise falls back to returning all fields.
        """
        if self.sandbox is None:
            return self.get_all_fields()
        state_input = {
            "context": {
                "user_id": self._user_id,
                "course_id": self._course_id,
                "activity_id": self._activity_id,
            },
            "permission": self._permission.value,
        }
        try:
            result = self.sandbox.call_function("getState", state_input)
        except SandboxRuntimeError as e:
            # TODO we should prevent displaying the activity in the frontend
            logger.exception(e)
            raise
        state: dict[str, FieldType] = json.loads(result)
        return state

    def clear_pending_events(self) -> list[PendingEvent]:
        """Return and clear all pending events."""
        events = self._pending_events
        self._pending_events = []
        return events

    def host_functions(self) -> list[Callable[..., Any]]:
        """
        Host functions that will be made available to the sandbox.
        """
        return [
            self.send_event,
            self.get_field,
            self.set_field,
            self.log_get,
            self.log_get_range,
            self.log_append,
            self.log_delete,
            self.log_delete_range,
            self.http_request,
            self.submit_grade,
        ]

    def send_event(self, name: str, value: str, context: str, permission: str) -> str:
        """Send an event back to the client.

        Called by sandbox code to send events (e.g., field changes) to the frontend.

        Args:
            name: Event name.
            value: JSON-encoded event value.
            context: JSON-encoded context dict (e.g. '{"activity_id": "..."}').
                     Empty dict {} means use current context.
            permission: Minimum permission to receive the event ("view", "play", or "edit").

        Raises:
            EventValidationError: If the event is not declared in manifest.
        """
        self.event_checker.validate(name, json.loads(value))
        parsed_context = json.loads(context)
        # Fill in defaults for empty context
        if not parsed_context:
            parsed_context = {
                "activity_id": self._activity_id,
                "course_id": self._course_id,
            }
        self._pending_events.append(
            {
                "name": name,
                "value": value,
                "context": parsed_context,
                "permission": permission,
            }
        )
        return ""

    def get_field(
        self, name: str, context: Annotated[dict[str, str], extism.Json]
    ) -> Annotated[FieldType, extism.Json]:
        """Get a field, resolving scope from manifest.

        Args:
            name: Field name.
            context: JSON-encoded dict of context overrides (e.g. '{"user_id": "bob"}').

        Returns JSON-encoded value (e.g., "42" for integer, "true" for boolean).
        Returns the default value if not set.
        """
        if isinstance(self.field_checker.get_definition(name), LogField):
            raise FieldValidationError(
                f"Field '{name}' is of type 'log'; use log_get/log_get_range instead"
            )
        field_scope = self.field_checker.get_scope(name)
        course_id, activity_id, user_id = self._scope_key_segments(field_scope, context)
        value = self.load_field(course_id, activity_id, user_id, name)
        return value

    def set_field(
        self,
        name: str,
        value: Annotated[FieldType, extism.Json],
        context: Annotated[dict[str, str], extism.Json],
    ) -> bool:
        """Set a field, resolving scope from manifest. Takes JSON-encoded value.

        Args:
            name: Field name.
            value: JSON-encoded value.
            context: JSON-encoded dict of context overrides.
        """
        if isinstance(self.field_checker.get_definition(name), LogField):
            raise FieldValidationError(
                f"Field '{name}' is of type 'log'; use log_append instead"
            )
        field_scope = self.field_checker.get_scope(name)
        course_id, activity_id, user_id = self._scope_key_segments(field_scope, context)
        self.store_field(course_id, activity_id, user_id, name, value)
        return True

    def _log_scope_segments(
        self, name: str, context: dict[str, str] | None = None
    ) -> tuple[str, str, str]:
        """Validate log field and return scope key segments."""
        self.field_checker.require_log_type(name)
        field_scope = self.field_checker.get_scope(name)
        return self._scope_key_segments(field_scope, context)

    def log_get(
        self,
        name: str,
        entry_id: int,
        context: Annotated[dict[str, str], extism.Json],
    ) -> Annotated[FieldType | None, extism.Json]:
        """Get a single log entry by id.

        Returns the value if found, None otherwise.
        """
        course_id, activity_id, user_id = self._log_scope_segments(name, context)
        return self.field_store.log_get(
            course_id, self.name, activity_id, user_id, name, entry_id
        )

    def log_get_range(
        self,
        name: str,
        from_id: int,
        to_id: int,
        context: Annotated[dict[str, str], extism.Json],
    ) -> Annotated[list[dict[str, Any]], extism.Json]:
        """Get log entries in range [from_id, to_id).

        Returns a list of {id, value} dicts.
        """
        course_id, activity_id, user_id = self._log_scope_segments(name, context)
        return self.field_store.log_get_range(
            course_id, self.name, activity_id, user_id, name, from_id, to_id
        )

    def log_append(
        self,
        name: str,
        value: Annotated[FieldType, extism.Json],
        context: Annotated[dict[str, str], extism.Json],
    ) -> int:
        """Append a value to a log field. Returns the assigned id."""
        course_id, activity_id, user_id = self._log_scope_segments(name, context)
        self.field_checker.validate_log_item(name, value)
        return self.field_store.log_append(
            course_id, self.name, activity_id, user_id, name, value
        )

    def log_delete(
        self,
        name: str,
        entry_id: int,
        context: Annotated[dict[str, str], extism.Json],
    ) -> bool:
        """Delete a single log entry by id. Returns True if the entry existed."""
        course_id, activity_id, user_id = self._log_scope_segments(name, context)
        return self.field_store.log_delete(
            course_id, self.name, activity_id, user_id, name, entry_id
        )

    def log_delete_range(
        self,
        name: str,
        from_id: int,
        to_id: int,
        context: Annotated[dict[str, str], extism.Json],
    ) -> int:
        """Delete log entries in range [from_id, to_id). Returns count deleted."""
        course_id, activity_id, user_id = self._log_scope_segments(name, context)
        return self.field_store.log_delete_range(
            course_id, self.name, activity_id, user_id, name, from_id, to_id
        )

    def http_request(
        self,
        url: str,
        method: str,
        body: bytes,
        headers: Annotated[tuple[tuple[str, str], ...], extism.Json],
    ) -> str:
        """Make an HTTP request.

        Returns a JSON string: {"status": int, "headers": [[k,v],...], "body": str}

        - 2xx: returns status, headers, body
        - 4xx/5xx: returns status, headers, error body (no exception)
        - Connection error: returns status=0, empty headers, error message
        - Capability error: returns status=0, empty headers, error message
        """
        try:
            self.capability_checker.check_http_request(url)
        except CapabilityError as e:
            return json.dumps({"status": 0, "headers": [], "body": str(e)})

        body_bytes = body or None

        req = urllib.request.Request(
            url,
            data=body_bytes,
            headers=dict(headers),
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                resp_headers = list(response.getheaders())
                resp_body: str = response.read().decode("utf-8")
                return json.dumps(
                    {
                        "status": response.status,
                        "headers": resp_headers,
                        "body": resp_body,
                    }
                )
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            err_headers = list(e.headers.items()) if e.headers else []
            logger.warning(
                "HTTP request error: code=%d reason=%s body=%s",
                e.code,
                e.reason,
                err_body,
            )
            return json.dumps(
                {
                    "status": e.code,
                    "headers": err_headers,
                    "body": err_body,
                }
            )
        except urllib.error.URLError as e:
            logger.warning("HTTP URL error: reason=%s", e.reason)
            return json.dumps(
                {
                    "status": 0,
                    "headers": [],
                    "body": str(e.reason),
                }
            )

    def submit_grade(self, score: float) -> bool:
        # TODO actually submit grade
        logger.info("submitted score: %f", score)
        return True
