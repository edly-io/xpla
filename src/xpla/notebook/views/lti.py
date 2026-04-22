"""LTI 1.3 integration for the notebook app.

Mounts the reusable LTI core router and adds token-gated activity endpoints
that resolve PageActivity instances from the notebook database.
"""

import json
import logging
import secrets
import time

import jwt
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from xpla.lib.actions import ActionValidationError
from xpla.lib.event_bus import EventBus
from xpla.lib.permission import Permission
from xpla.lib.runtime import AssetAccessError
from xpla.lti.core.keys import load_or_create_key
from xpla.lti.core.launch import LaunchData
from xpla.lti.core.routes import create_lti_router
from xpla.notebook import constants
from xpla.notebook.db import engine
from xpla.notebook.models import CourseActivity, Page, PageActivity
from xpla.notebook.runtime import NotebookActivityRuntime
from xpla.notebook.views.activities import find_activity_dir

# Register LTI models with SQLModel metadata (needed for ORM queries on
# Platform/Nonce/Deployment using the notebook's shared DB engine).
import xpla.lti.core.models  # pylint: disable=wrong-import-position,unused-import

logger = logging.getLogger(__name__)

_INSTRUCTOR_ROLES = {
    "http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor",
    "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Instructor",
    "http://purl.imsglobal.org/vocab/lis/v2/membership#ContentDeveloper",
    "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Administrator",
}

LTI_PREFIX = "/lti"
_session_secret = secrets.token_urlsafe(32)

constants.LTI_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
_key_set = load_or_create_key(constants.LTI_KEY_PATH)

_lti_templates = Jinja2Templates(
    directory=str(constants.CURRENT_DIR.parent / "lti" / "templates")
)

event_bus = EventBus()


# ── Launch handler ───────────────────────────────────────────────────


def _is_instructor(roles: list[str]) -> bool:
    return bool(set(roles) & _INSTRUCTOR_ROLES)


def _resolve_activity(activity_id: str) -> tuple[str, str, bool]:
    """Look up an activity and return (activity_type, course_id, is_course_activity)."""
    with Session(engine) as session:
        pa = session.get(PageActivity, activity_id)
        if pa is not None:
            page = session.get(Page, pa.page_id)
            if page is None:
                raise HTTPException(status_code=404, detail="Page not found")
            return pa.activity_type, page.course_id, False
        ca = session.get(CourseActivity, activity_id)
        if ca is not None:
            return ca.activity_type, ca.course_id, True
        raise HTTPException(status_code=404, detail="Activity not found")


def _make_session_token(
    user_id: str,
    activity_id: str,
    activity_type: str,
    course_id: str,
    permission: Permission,
    is_course_activity: bool,
) -> str:
    now = int(time.time())
    payload: dict[str, object] = {
        "sub": user_id,
        "activity_id": activity_id,
        "activity_type": activity_type,
        "course_id": course_id,
        "permission": permission.value,
        "is_course_activity": is_course_activity,
        "iat": now,
        "exp": now + 7200,
    }
    token: str = jwt.encode(payload, _session_secret, algorithm="HS256")
    return token


def _decode_session_token(token: str) -> dict[str, object]:
    claims: dict[str, object] = jwt.decode(token, _session_secret, algorithms=["HS256"])
    return claims


async def _launch_handler(
    launch_data: LaunchData, request: Request
) -> HTMLResponse | RedirectResponse:
    """Handle an LTI resource link launch by resolving a PageActivity."""
    activity_id = launch_data.custom.get("activity_id", "")
    if not activity_id:
        return _lti_templates.TemplateResponse(
            request=request,
            name="launch_error.html",
            context={"error_message": "No activity_id in custom parameters"},
            status_code=400,
        )

    activity_type, course_id, is_course_activity = _resolve_activity(activity_id)
    find_activity_dir(activity_type)  # validate it exists

    permission = (
        Permission.edit if _is_instructor(launch_data.roles) else Permission.play
    )
    token = _make_session_token(
        launch_data.user_id,
        activity_id,
        activity_type,
        course_id,
        permission,
        is_course_activity,
    )
    return RedirectResponse(
        url=f"{constants.LTI_BASE_URL}/activity/{token}", status_code=303
    )


# ── Token-gated activity endpoints ──────────────────────────────────


def _load_activity_from_token(token: str) -> NotebookActivityRuntime:
    claims = _decode_session_token(token)
    activity_dir = find_activity_dir(str(claims["activity_type"]))
    return NotebookActivityRuntime(
        activity_dir,
        activity_id=str(claims["activity_id"]),
        course_id=str(claims["course_id"]),
        user_id=str(claims["sub"]),
        permission=Permission(str(claims["permission"])),
        is_course_activity=bool(claims.get("is_course_activity", False)),
    )


activity_router = APIRouter()


@activity_router.get("/activity/{token}", response_class=HTMLResponse)
async def lti_activity_page(request: Request, token: str) -> HTMLResponse:
    """Render an activity from a session token."""
    ctx = _load_activity_from_token(token)
    state = ctx.get_state()
    scope = {
        "user_id": ctx.user_id,
        "course_id": ctx.course_id,
        "activity_id": ctx.activity_id,
    }
    host = request.headers.get("host", "localhost:9753")
    ws_scheme = "wss" if request.scope["scheme"] == "https" else "ws"
    ws_url = f"{ws_scheme}://{host}{LTI_PREFIX}/activity/{token}/ws"
    asset_base_url = f"{LTI_PREFIX}/activity/{token}/assets"
    return _lti_templates.TemplateResponse(
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


@activity_router.get("/activity/{token}/client.js", name="activity_client_js")
async def lti_activity_client_js(token: str) -> FileResponse:
    """Serve the client script for an activity."""
    ctx = _load_activity_from_token(token)
    try:
        full_path = ctx.get_client_js_path()
    except AssetAccessError as e:
        raise HTTPException(status_code=404, detail="Access denied") from e
    return FileResponse(full_path)


@activity_router.get("/activity/{token}/assets/{file_path:path}", name="activity_asset")
async def lti_activity_asset(token: str, file_path: str) -> FileResponse:
    """Serve static files from an activity directory."""
    ctx = _load_activity_from_token(token)
    try:
        full_path = ctx.get_asset_path(file_path)
    except AssetAccessError as e:
        raise HTTPException(status_code=404, detail="Access denied") from e
    return FileResponse(full_path)


@activity_router.post("/activity/{token}/actions/{action_name}", name="send_action")
async def lti_send_action(
    token: str, request: Request, action_name: str
) -> JSONResponse:
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


@activity_router.websocket("/activity/{token}/ws")
async def lti_activity_ws(websocket: WebSocket, token: str) -> None:
    """WebSocket for real-time events."""
    await websocket.accept()
    ctx = _load_activity_from_token(token)
    subscriber = event_bus.subscribe(
        ctx.activity_id,
        websocket,
        ctx.user_id,
        ctx.permission,
        ctx.course_id,
        ctx.activity_id,
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


# ── Router assembly ──────────────────────────────────────────────────

_lti_core_router = create_lti_router(
    db_engine=engine,
    key_set=_key_set,
    launch_handler=_launch_handler,
    base_url=constants.LTI_BASE_URL,
    templates=_lti_templates,
    prefix=LTI_PREFIX,
)

router = APIRouter()
router.include_router(_lti_core_router)
router.include_router(activity_router)
