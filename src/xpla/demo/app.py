"""
FastAPI application for the xPLA server.
"""

import json
import logging
import mimetypes
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from xpla.lib.runtime import ActivityRuntime, AssetAccessError
from xpla.lib.actions import ActionValidationError
from xpla.lib.capabilities import CapabilityError
from xpla.lib.event_bus import EventBus
from xpla.lib.field_store import FieldStore
from xpla.lib.file_storage import FileStorageError, LocalFileStorage
from xpla.lib.permission import Permission
from xpla.demo import constants
from xpla.demo.kv import load_field_store

USER_ID_COOKIE = "xpla_user"
SIMULATED_USERS = ["alice", "bob", "charlie"]

field_store: FieldStore = load_field_store()
file_storage = LocalFileStorage(constants.DIST_DIR / "demo" / "storage")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

event_bus = EventBus()


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


class ActivityNotFound(Exception):
    """Raised when an activity cannot be found."""


def load_activity(cookies: dict[str, str], activity_type: str) -> ActivityRuntime:
    """Load an activity by ID from the samples directory."""
    try:
        activity_dir = find_activity_dir(activity_type)
    except ActivityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    user_id, permission = get_simulation_params(cookies)
    activity_context = ActivityRuntime(
        activity_dir,
        field_store,
        file_storage,
        activity_id=activity_type,
        course_id="democourse",
        user_id=user_id,
        permission=permission,
    )
    return activity_context


def find_activity_dir(activity_type: str) -> Path:
    """
    Find the directory of a sample activity.
    """
    activity_dir = constants.SAMPLES_DIR / activity_type
    manifest_path = activity_dir / "manifest.json"
    if not manifest_path.exists():
        raise ActivityNotFound(f"Activity '{activity_type}' has no manifest.json")
    return activity_dir


def list_activities() -> list[str]:
    return sorted(d.name for d in constants.SAMPLES_DIR.iterdir() if d.is_dir())


def get_simulation_params(cookies: dict[str, str]) -> tuple[str, Permission]:
    """Read simulated user/permission from cookies, with validation and fallback."""
    user_id = cookies.get(USER_ID_COOKIE)
    if user_id not in SIMULATED_USERS:
        user_id = SIMULATED_USERS[0]

    permission_str = cookies.get("xpla_permission")
    permission = Permission(permission_str) if permission_str else Permission.play

    return user_id, permission


@app.get("/")
async def home(request: Request) -> HTMLResponse:
    """List all available activities."""
    return templates.TemplateResponse(
        request=request, name="home.html", context={"activities": list_activities()}
    )


@app.get("/a/{activity_type}")
async def activity(request: Request, activity_type: str) -> HTMLResponse:
    """Serve an activity"""
    activity_context = load_activity(request.cookies, activity_type)
    activity_state = activity_context.get_state()

    context = {
        "user_id": activity_context.user_id,
        "course_id": activity_context.course_id,
        "activity_id": activity_context.activity_id,
    }

    return templates.TemplateResponse(
        request=request,
        name="activity.html",
        context={
            "activity_context": activity_context,
            "state_json": json.dumps(activity_state),
            "context_json": json.dumps(context),
            "simulated_users": SIMULATED_USERS,
            "current_user": activity_context.user_id,
            "permission_levels": [p.value for p in Permission],
            "current_permission": activity_context.permission.value,
        },
    )


@app.get("/a/{activity_type}/embed")
async def activity_embed(request: Request, activity_type: str) -> HTMLResponse:
    """Serve an activity in a standalone page for iframe embedding."""
    activity_context = load_activity(request.cookies, activity_type)
    activity_state = activity_context.get_state()

    context = {
        "user_id": activity_context.user_id,
        "course_id": activity_context.course_id,
        "activity_id": activity_context.activity_id,
    }

    return templates.TemplateResponse(
        request=request,
        name="activity_embed.html",
        context={
            "activity_context": activity_context,
            "state_json": json.dumps(activity_state),
            "context_json": json.dumps(context),
            "current_permission": activity_context.permission.value,
        },
    )


@app.get("/a/{activity_type}/{file_path:path}")
async def activity_asset(
    request: Request, activity_type: str, file_path: str
) -> FileResponse:
    """Serve static files from an activity directory."""
    activity_context = load_activity(request.cookies, activity_type)

    # Security: ensure path doesn't escape activity directory
    try:
        full_path = activity_context.get_asset_path(file_path)
    except AssetAccessError as e:
        raise HTTPException(status_code=404, detail="Access denied") from e

    return FileResponse(full_path)


@app.get("/activity/{activity_type}/storage/{storage_name}/{file_path:path}")
async def storage_file(
    request: Request, activity_type: str, storage_name: str, file_path: str
) -> Response:
    """Serve a file from activity storage."""
    activity_context = load_activity(request.cookies, activity_type)
    try:
        activity_context.capability_checker.check_storage(storage_name)
    except CapabilityError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    storage_path = f"{activity_type}/{storage_name}/{file_path}"
    try:
        content = file_storage.read(storage_path)
    except FileStorageError as e:
        raise HTTPException(status_code=404, detail="File not found") from e
    media_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    return Response(content=content, media_type=media_type)


@app.post("/api/activity/{activity_type}/actions/{action_name}")
async def send_action(
    request: Request, activity_type: str, action_name: str
) -> JSONResponse:
    """Send an action to the activity sandbox. Events are broadcast via WebSocket."""
    context = load_activity(request.cookies, activity_type)
    action_value = await request.json()

    try:
        context.on_action(action_name, action_value)
    except ActionValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Publish events via the event bus (no longer returned in response)
    events = context.clear_pending_events()
    await event_bus.publish(activity_type, events)
    return JSONResponse(content={})


@app.websocket("/api/activity/{activity_type}/ws")
async def activity_ws(websocket: WebSocket, activity_type: str) -> None:
    """WebSocket endpoint for real-time event broadcasting."""
    await websocket.accept()

    # Read user/permission from cookies (same as HTTP endpoints)
    context = load_activity(websocket.cookies, activity_type)

    subscriber = event_bus.subscribe(
        activity_type,
        websocket,
        context.user_id,
        context.permission,
        course_id=context.course_id,
        activity_id=context.activity_id,
    )

    while True:
        try:
            data = await websocket.receive_json()
        except WebSocketDisconnect:
            event_bus.unsubscribe(activity_type, subscriber)
            return
        action_name = data.get("action", "")
        action_value = data.get("value", "")

        try:
            context.on_action(action_name, action_value)
        except ActionValidationError as e:
            logger.warning("WS action validation error: %s", e)
            continue

        events = context.clear_pending_events()
        await event_bus.publish(activity_type, events)
