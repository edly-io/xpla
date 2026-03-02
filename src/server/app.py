"""
FastAPI application for the xPLA server.
"""

import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from server.activities.context import ActivityContext
from server.activities.actions import ActionValidationError
from server.activities.manifest_types import XplaActivityManifest
from server.activities.permission import Permission
from server import constants

SIMULATED_USERS = ["alice", "bob", "charlie"]
DEFAULT_USER = SIMULATED_USERS[0]
DEFAULT_PERMISSION = Permission.view
USER_ID_COOKIE = "xpla_user"

logger = logging.getLogger(__name__)


app = FastAPI(
    title="xPLA Server",
    description="LMS simulation for xPLA development",
    version="0.3.0",
)

app.mount("/static", StaticFiles(directory=constants.STATIC_DIR), name="static")
templates = Jinja2Templates(
    directory=constants.TEMPLATES_DIR,
    context_processors=[
        lambda _request: {
            "USER_ID_COOKIE": USER_ID_COOKIE,
        }
    ],
)


def get_simulation_params(request: Request) -> tuple[str, Permission]:
    """Read simulated user/permission from cookies, with validation and fallback."""
    user_id = request.cookies.get(USER_ID_COOKIE, DEFAULT_USER)
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


def load_activity(request: Request, activity_type: str) -> ActivityContext:
    """Load an activity by ID from the samples directory."""
    try:
        activity_dir = find_activity_dir(activity_type)
    except ActivityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    activity_context = ActivityContext(activity_dir)
    user_id, permission = get_simulation_params(request)
    activity_context.user_id = user_id
    activity_context.course_id = "democourse"
    activity_context.activity_id = "activityid"
    activity_context.permission = permission
    return activity_context


def find_activity_dir(activity_type: str) -> Path:
    """
    Find the directory of a sample activity.
    """
    if activity_type not in list_activities():
        raise ActivityNotFound(f"Activity '{activity_type}' not found")

    activity_dir = constants.SAMPLES_DIR / activity_type
    manifest_path = activity_dir / "manifest.json"
    if not manifest_path.exists():
        raise ActivityNotFound(f"Activity '{activity_type}' has no manifest.json")
    return activity_dir


def list_activities() -> list[str]:
    return sorted(d.name for d in constants.SAMPLES_DIR.iterdir() if d.is_dir())


@app.get("/")
async def home(request: Request) -> HTMLResponse:
    """List all available activities."""
    return templates.TemplateResponse(
        request=request, name="home.html", context={"activities": list_activities()}
    )


@app.get("/a/{activity_type}")
async def activity(request: Request, activity_type: str) -> HTMLResponse:
    """Serve an activity"""
    activity_context = load_activity(request, activity_type)
    activity_state = activity_context.get_state()

    return templates.TemplateResponse(
        request=request,
        name="activity.html",
        context={
            "activity_context": activity_context,
            "state_json": json.dumps(activity_state),
            "simulated_users": SIMULATED_USERS,
            "current_user": activity_context.user_id,
            "permission_levels": [p.value for p in Permission],
            "current_permission": activity_context.permission.value,
        },
    )


@app.get("/a/{activity_type}/embed")
async def activity_embed(request: Request, activity_type: str) -> HTMLResponse:
    """Serve an activity in a standalone page for iframe embedding."""
    activity_context = load_activity(request, activity_type)
    activity_state = activity_context.get_state()

    return templates.TemplateResponse(
        request=request,
        name="activity_embed.html",
        context={
            "activity_context": activity_context,
            "state_json": json.dumps(activity_state),
            "current_permission": activity_context.permission.value,
        },
    )


def _is_allowed_asset(manifest: XplaActivityManifest, file_path: str) -> bool:
    """Check whether a file path is allowed to be served as a static asset."""
    if file_path in (manifest.client, "manifest.json"):
        return True
    return file_path in [item.root for item in (manifest.static or [])]


@app.get("/a/{activity_type}/{file_path:path}")
async def activity_asset(
    request: Request, activity_type: str, file_path: str
) -> FileResponse:
    """Serve static files from an activity directory."""
    activity_context = load_activity(request, activity_type)

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


@app.post("/api/activity/{activity_type}/actions/{action_name}")
async def send_action(
    request: Request, activity_type: str, action_name: str
) -> JSONResponse:
    """Send an action to the activity sandbox and receive response events."""
    context = load_activity(request, activity_type)
    action_value = await request.json()

    try:
        context.on_action(action_name, action_value)
    except ActionValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Return events posted by sandbox
    events = context.clear_pending_events()
    return JSONResponse(content={"events": events})
