import logging
import mimetypes
from typing import NamedTuple

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlmodel import Session

from xpla.lib.actions import ActionValidationError
from xpla.lib.capabilities import CapabilityError
from xpla.lib.event_bus import EventBus
from xpla.lib.file_storage import FileStorageError
from xpla.lib.permission import Permission
from xpla.lib.runtime import ActivityRuntime, AssetAccessError, SandboxContext
from xpla.notebook.auth import SESSION_COOKIE, get_current_user, lookup_user
from xpla.notebook.db import get_session
from xpla.notebook.models import CourseActivity, PageActivity, User
from xpla.notebook.views.activities import load_activity
from xpla.notebook.views.course_activities import load_course_activity

logger = logging.getLogger(__name__)

router = APIRouter()

event_bus = EventBus()


class ActivityAction(BaseModel):
    name: str
    value: object


class ActivityInfo(NamedTuple):
    id: str
    activity_type: str
    course_id: str
    is_course_activity: bool


def resolve_activity(session: Session, activity_id: str, user: User) -> ActivityInfo:
    """Look up an activity in both PageActivity and CourseActivity tables and
    ensure the authenticated user owns the parent course."""
    pa = session.get(PageActivity, activity_id)
    if pa:
        course = pa.page.course
        if course.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        return ActivityInfo(pa.id, pa.activity_type, course.id, False)
    ca = session.get(CourseActivity, activity_id)
    if ca:
        if ca.course.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        return ActivityInfo(ca.id, ca.activity_type, ca.course_id, True)
    raise HTTPException(status_code=404, detail="Activity not found")


def load_any_activity(
    info: ActivityInfo, user_id: str, permission: Permission
) -> ActivityRuntime:
    """Load the runtime for either a page or course activity."""
    if info.is_course_activity:
        return load_course_activity(
            info.activity_type, info.id, info.course_id, user_id, permission
        )
    return load_activity(
        info.activity_type, info.id, info.course_id, user_id, permission
    )


@router.get(
    "/a/{activity_id}/ui.js",
    summary="Serve the activity UI script",
)
async def activity_ui(
    activity_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    info = resolve_activity(session, activity_id, current_user)
    ctx = load_any_activity(info, current_user.id, Permission.play)
    try:
        full_path = ctx.get_ui_path()
    except AssetAccessError as e:
        raise HTTPException(status_code=404, detail="Access denied") from e
    return FileResponse(full_path)


@router.get(
    "/a/{activity_id}/{file_path:path}",
    summary="Serve an activity static asset",
)
async def activity_asset(
    activity_id: str,
    file_path: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    info = resolve_activity(session, activity_id, current_user)
    ctx = load_any_activity(info, current_user.id, Permission.play)
    try:
        full_path = ctx.get_asset_path(file_path)
    except AssetAccessError as e:
        raise HTTPException(status_code=404, detail="Access denied") from e
    return FileResponse(full_path)


@router.get(
    "/activity/{activity_id}/storage/{storage_name}/{file_path:path}",
    summary="Serve a file from activity storage",
)
async def storage_file(
    activity_id: str,
    storage_name: str,
    file_path: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    activity_id_override: str | None = Query(None, alias="activity_id"),
    course_id_override: str | None = Query(None, alias="course_id"),
    user_id_override: str | None = Query(None, alias="user_id"),
) -> Response:
    info = resolve_activity(session, activity_id, current_user)
    ctx = load_any_activity(info, current_user.id, Permission.play)
    context: SandboxContext | None = None
    if activity_id_override or course_id_override or user_id_override:
        context = {
            "activity-id": activity_id_override,
            "course-id": course_id_override,
            "user-id": user_id_override,
        }
    try:
        content = ctx.storage_read(storage_name, file_path, context)
    except CapabilityError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except FileStorageError as e:
        raise HTTPException(status_code=404, detail="File not found") from e
    media_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    return Response(content=content, media_type=media_type)


@router.post(
    "/api/activity/{activity_id}/{permission}/actions",
    summary="Trigger an action",
)
async def activity_actions(
    activity_id: str,
    permission: Permission,
    action: ActivityAction,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Trigger an activity action."""
    info = resolve_activity(session, activity_id, current_user)

    ctx = load_any_activity(info, current_user.id, permission)
    try:
        ctx.on_action(action.name, action.value)
    except ActionValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid action: {e}") from e

    events = ctx.clear_pending_events()
    await event_bus.publish(info.activity_type, events)


@router.websocket("/api/activity/{activity_id}/{permission}/ws")
async def activity_ws(
    websocket: WebSocket,
    activity_id: str,
    permission: Permission,
    session: Session = Depends(get_session),
) -> None:
    policy_violation_code = 1008

    token = websocket.cookies.get(SESSION_COOKIE)
    current_user = lookup_user(session, token)
    if not current_user:
        await websocket.close(code=policy_violation_code)
        return

    try:
        info = resolve_activity(session, activity_id, current_user)
    except HTTPException:
        await websocket.close(code=policy_violation_code)
        return
    await websocket.accept()

    subscriber = event_bus.subscribe(
        info.activity_type,
        websocket,
        current_user.id,
        permission,
        info.course_id,
        activity_id,
    )

    while True:
        try:
            data = await websocket.receive_json()
        except WebSocketDisconnect:
            event_bus.unsubscribe(info.activity_type, subscriber)
            return

        try:
            action_name = data["action"]
            action_value = data["value"]
        except KeyError:
            # TODO raise error?
            continue

        ctx = load_any_activity(info, current_user.id, permission)
        try:
            ctx.on_action(action_name, action_value)
        except ActionValidationError as e:
            # TODO should we return an error to the frontend?
            logger.warning("WS action validation error: %s", e)
            continue

        events = ctx.clear_pending_events()
        await event_bus.publish(info.activity_type, events)
