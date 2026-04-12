"""FastAPI application for the xPLA LTI 1.3 tool provider."""

import json
import logging
import secrets

from fastapi import (
    FastAPI,
    HTTPException,
    Form,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from xpla.lib.runtime import ActivityRuntime, AssetAccessError
from xpla.lib.actions import ActionValidationError
from xpla.lib.event_bus import EventBus
from xpla.lib.file_storage import LocalFileStorage
from xpla.lib.permission import Permission
from xpla.lti import config
from xpla.lti.core.db import create_db
from xpla.lti.core.keys import load_or_create_key
from xpla.lti.core.routes import create_lti_router
from xpla.lti.integration import LaunchHandler
from xpla.demo.kv import load_field_store

logger = logging.getLogger(__name__)

# Ensure data directory exists
config.DATA_DIR.mkdir(parents=True, exist_ok=True)

db_engine = create_db(str(config.DB_PATH))
key_set = load_or_create_key(config.KEY_PATH)
field_store = load_field_store()
file_storage = LocalFileStorage(config.DATA_DIR / "storage")
event_bus = EventBus()

# Session signing secret (generated once per process)
_session_secret = secrets.token_urlsafe(32)

templates = Jinja2Templates(directory=config.TEMPLATES_DIR)

launch_handler = LaunchHandler(templates, key_set, config.BASE_URL, _session_secret)

app = FastAPI(
    title="xPLA LTI Tool Provider",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

lti_router = create_lti_router(
    db_engine=db_engine,
    key_set=key_set,
    launch_handler=launch_handler,
    base_url=config.BASE_URL,
    templates=templates,
)
app.include_router(lti_router)


# ── Activity endpoints (token-gated) ─────────────────────────────────


def _load_activity_from_token(token: str) -> ActivityRuntime:
    """Decode session token and build ActivityContext."""
    claims = launch_handler.decode_session_token(token)
    activity_type = claims["activity_type"]
    activity_dir = config.SAMPLES_DIR / activity_type
    if not (activity_dir / "manifest.json").exists():
        raise HTTPException(status_code=404, detail="Activity not found")

    return ActivityRuntime(
        activity_dir,
        field_store,
        file_storage,
        activity_id=activity_type,
        course_id=claims["course_id"],
        user_id=claims["sub"],
        permission=Permission(claims["permission"]),
    )


@app.get("/activity/{token}", response_class=HTMLResponse)
async def activity_page(request: Request, token: str) -> HTMLResponse:
    """Render an activity from a session token."""
    ctx = _load_activity_from_token(token)
    state = ctx.get_state()
    scope = {
        "user_id": ctx.user_id,
        "course_id": ctx.course_id,
        "activity_id": ctx.activity_id,
    }
    host = request.headers.get("host", "localhost:9754")
    ws_scheme = "wss" if request.scope["scheme"] == "https" else "ws"
    ws_url = f"{ws_scheme}://{host}/activity/{token}/ws"
    asset_base_url = f"/activity/{token}/assets"
    return templates.TemplateResponse(
        request=request,
        name="activity_render.html",
        context={
            "activity_context": ctx,
            "state_json": json.dumps(state),
            "scope_json": json.dumps(scope),
            "permission": ctx.permission.value,
            "token": token,
            "ws_url": ws_url,
            "asset_base_url": asset_base_url,
        },
    )


@app.get("/activity/{token}/assets/{file_path:path}")
async def activity_asset(token: str, file_path: str) -> FileResponse:
    """Serve static files from an activity directory."""
    ctx = _load_activity_from_token(token)
    try:
        full_path = ctx.get_asset_path(file_path)
    except AssetAccessError as e:
        raise HTTPException(status_code=404, detail="Access denied") from e
    return FileResponse(full_path)


@app.post("/activity/{token}/actions/{action_name}")
async def send_action(token: str, request: Request, action_name: str) -> JSONResponse:
    """Send an action to an activity."""
    ctx = _load_activity_from_token(token)
    action_value = await request.json()
    try:
        ctx.on_action(action_name, action_value)
    except ActionValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    events = ctx.clear_pending_events()
    await event_bus.publish(ctx.activity_id, events)
    return JSONResponse(content={})


@app.websocket("/activity/{token}/ws")
async def activity_ws(websocket: WebSocket, token: str) -> None:
    """WebSocket for real-time events."""
    await websocket.accept()
    ctx = _load_activity_from_token(token)
    subscriber = event_bus.subscribe(
        ctx.activity_id,
        websocket,
        ctx.user_id,
        ctx.permission,
        course_id=ctx.course_id,
        activity_id=ctx.activity_id,
    )
    while True:
        try:
            data = await websocket.receive_json()
        except WebSocketDisconnect:
            event_bus.unsubscribe(ctx.activity_id, subscriber)
            return
        action_name = data.get("action", "")
        action_value = data.get("value", "")
        try:
            ctx.on_action(action_name, action_value)
        except ActionValidationError as e:
            logger.warning("WS action validation error: %s", e)
            continue
        events = ctx.clear_pending_events()
        await event_bus.publish(ctx.activity_id, events)


# ── Deep Linking Response ─────────────────────────────────────────────


@app.post("/deep-link/respond", response_class=HTMLResponse)
async def deep_link_respond(
    activity_type: str = Form(...),
    client_id: str = Form(...),
    deployment_id: str = Form(...),
    return_url: str = Form(...),
) -> HTMLResponse:
    """Build deep linking response JWT and auto-submit to platform."""
    jwt_token = launch_handler.build_deep_link_jwt(
        activity_type,
        client_id=client_id,
        deployment_id=deployment_id,
    )
    return HTMLResponse(
        f'<html><body><form id="f" method="post" action="{return_url}">'
        f'<input type="hidden" name="JWT" value="{jwt_token}">'
        f"</form><script>document.getElementById('f').submit();</script></body></html>"
    )
