"""
FastAPI application for the xPLA server.
"""

import json
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from server.activities.context import ActivityContext, MissingSandboxError
from server.activities.actions import ActionValidationError
from server.activities.manifest_types import XplaActivityManifest
from server.activities.permission import Permission
from server import constants

SIMULATED_USERS = ["alice", "bob", "charlie"]
DEFAULT_USER = SIMULATED_USERS[0]
DEFAULT_PERMISSION = Permission.view


def get_simulation_params(request: Request) -> tuple[str, Permission]:
    """Read simulated user/permission from cookies, with validation and fallback."""
    # TODO cookie names should be defined as variables to be shared with the frontend
    user_id = request.cookies.get("xpla_user", DEFAULT_USER)
    if user_id not in SIMULATED_USERS:
        user_id = DEFAULT_USER

    permission_str = request.cookies.get("xpla_permission", DEFAULT_PERMISSION.value)
    try:
        permission = Permission(permission_str)
    except ValueError:
        permission = DEFAULT_PERMISSION

    return user_id, permission


class ActivityNotFound(Exception):
    """Raised when an activity cannot be found."""


def load_activity(activity_id: str) -> ActivityContext:
    """Load an activity by ID from the samples directory."""
    if activity_id not in list_activities():
        raise ActivityNotFound(f"Activity '{activity_id}' not found")

    activity_dir = constants.SAMPLES_DIR / activity_id
    manifest_path = activity_dir / "manifest.json"
    if not manifest_path.exists():
        raise ActivityNotFound(f"Activity '{activity_id}' has no manifest.json")

    return ActivityContext(activity_dir)


def list_activities() -> list[str]:
    return sorted(d.name for d in constants.SAMPLES_DIR.iterdir() if d.is_dir())


app = FastAPI(
    title="xPLA Server",
    description="LMS simulation for xPLA development",
    version="0.3.0",
)

app.mount("/static", StaticFiles(directory=constants.STATIC_DIR), name="static")
templates = Jinja2Templates(directory=constants.TEMPLATES_DIR)


@app.get("/")
async def home(request: Request) -> HTMLResponse:
    """List all available activities."""
    return templates.TemplateResponse(
        request=request, name="home.html", context={"activities": list_activities()}
    )


@app.get("/a/{activity_id}")
async def activity(request: Request, activity_id: str) -> HTMLResponse:
    """Serve an activity"""
    try:
        activity_context = load_activity(activity_id)
    except ActivityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    user_id, permission = get_simulation_params(request)
    activity_context.user_id = user_id
    activity_context.permission = permission
    activity_state = activity_context.get_state()

    return templates.TemplateResponse(
        request=request,
        name="activity.html",
        context={
            "activity_context": activity_context,
            "state_json": json.dumps(activity_state),
            "simulated_users": SIMULATED_USERS,
            "current_user": user_id,
            "permission_levels": [p.value for p in Permission],
            "current_permission": permission.value,
        },
    )


@app.get("/a/{activity_id}/embed")
async def activity_embed(request: Request, activity_id: str) -> HTMLResponse:
    """Serve an activity in a standalone page for iframe embedding."""
    try:
        activity_context = load_activity(activity_id)
    except ActivityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    user_id, permission = get_simulation_params(request)
    activity_context.user_id = user_id
    activity_context.permission = permission
    activity_state = activity_context.get_state()

    return templates.TemplateResponse(
        request=request,
        name="activity_embed.html",
        context={
            "activity_context": activity_context,
            "state_json": json.dumps(activity_state),
            "current_permission": permission.value,
        },
    )


def _is_allowed_asset(manifest: XplaActivityManifest, file_path: str) -> bool:
    """Check whether a file path is allowed to be served as a static asset."""
    if file_path in (manifest.client, "manifest.json"):
        return True
    return file_path in [item.root for item in (manifest.static or [])]


@app.get("/a/{activity_id}/{file_path:path}")
async def activity_asset(activity_id: str, file_path: str) -> FileResponse:
    """Serve static files from an activity directory."""
    try:
        activity_context = load_activity(activity_id)
    except ActivityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Security: ensure path doesn't escape activity directory
    full_path = activity_context.activity_dir / file_path
    try:
        full_path.resolve().relative_to(activity_context.activity_dir.resolve())
    except ValueError as e:
        raise HTTPException(status_code=403, detail="Access denied") from e

    # Only serve files declared in manifest
    if not _is_allowed_asset(activity_context.manifest, file_path):
        raise HTTPException(status_code=403, detail="Access denied")

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    return FileResponse(full_path)


@app.post("/api/{activity_id}/plugin/{function_name}")
async def call_plugin(
    activity_id: str, function_name: str, request: Request
) -> JSONResponse:
    """Execute a function in the activity plugin."""
    try:
        context = load_activity(activity_id)
    except ActivityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    user_id, permission = get_simulation_params(request)
    context.user_id = user_id
    context.permission = permission

    body = await request.body()
    try:
        result = context.call_sandbox_function(function_name, body)
    except MissingSandboxError as e:
        raise HTTPException(
            status_code=404, detail="Activity has no WASM runtime"
        ) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return JSONResponse(content={"result": result.decode("utf-8")})


logger = logging.getLogger(__name__)


@app.post("/api/activity/{activity_id}/actions/{action_name}")
async def send_action(
    activity_id: str, action_name: str, request: Request
) -> JSONResponse:
    """Send an action to the activity sandbox and receive response events."""
    try:
        context = load_activity(activity_id)
    except ActivityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    user_id, permission = get_simulation_params(request)
    context.user_id = user_id
    context.permission = permission

    # Parse action payload from request body
    action_value = await request.json()

    # Validate action against manifest
    try:
        context.action_checker.validate(action_name, action_value)
    except ActionValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Call sandbox's onAction if available
    if context.sandbox is not None:
        action_input = json.dumps({"name": action_name, "value": action_value})
        try:
            context.call_sandbox_function("onAction", action_input.encode("utf-8"))
        except RuntimeError as e:
            # onAction not defined in sandbox - log warning and continue
            logger.warning("Activity '%s' has no onAction handler: %s", activity_id, e)

    # Return events posted by sandbox
    events = context.clear_pending_events()
    return JSONResponse(content={"events": events})
