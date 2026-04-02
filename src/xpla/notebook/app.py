from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import json
import logging
import mimetypes
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session, col, desc, select

from xpla.lib.actions import ActionValidationError
from xpla.lib.capabilities import CapabilityError
from xpla.lib.file_storage import FileStorageError
from xpla.lib.manifest_types import XplaActivityManifest
from xpla.lib.runtime import ActivityRuntime, AssetAccessError, SandboxContext
from xpla.lib.event_bus import EventBus
from xpla.lib.permission import Permission
from xpla.notebook import constants
from xpla.notebook.db import run_migrations, get_session
from xpla.notebook.runtime import (
    NotebookActivityRuntime,
    delete_activity_by
)
from xpla.notebook.models import Course, Page, PageActivity
from xpla.notebook import llms

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Startup
    run_migrations()
    yield
    # shutdown: noop


app = FastAPI(title="xPLN", version="0.1.0", lifespan=app_lifespan)

app.mount("/static", StaticFiles(directory=constants.STATIC_DIR), name="static")

if constants.FRONTEND_DIR.is_dir():
    app.mount(
        "/_next",
        StaticFiles(directory=constants.FRONTEND_DIR / "_next"),
        name="next-assets",
    )

event_bus = EventBus()

USER_ID = "student"

# ---- request bodies ----


class TitleBody(BaseModel):
    title: str


class ReorderCoursesBody(BaseModel):
    course_ids: list[str]


class ReorderPagesBody(BaseModel):
    page_ids: list[str]


class ActivityTypeBody(BaseModel):
    activity_type: str


class MoveActivityBody(BaseModel):
    direction: str
    page_id: str


class ActivityAction(BaseModel):
    name: str
    value: object


# ---- helpers ----


def find_activity_dir(activity_type: str) -> Path:
    if activity_type.startswith("@"):
        # Format: @<user_id>/<name>
        parts = activity_type[1:].split("/", 1)
        if len(parts) != 2:
            raise HTTPException(
                status_code=404, detail=f"Activity '{activity_type}' not found"
            )
        user_id, name = parts
        activity_dir = constants.ACTIVITIES_DIR / user_id / name
    else:
        activity_dir = constants.SAMPLES_DIR / activity_type
    if not (activity_dir / "manifest.json").exists():
        raise HTTPException(
            status_code=404, detail=f"Activity '{activity_type}' not found"
        )
    return activity_dir


def list_activity_types(user_id: str) -> list[str]:
    samples = sorted(d.name for d in constants.SAMPLES_DIR.iterdir() if d.is_dir())
    user_dir = constants.ACTIVITIES_DIR / user_id
    user_uploads: list[str] = []
    if user_dir.is_dir():
        user_uploads = sorted(
            f"@{user_id}/{d.name}" for d in user_dir.iterdir() if d.is_dir()
        )
    return samples + user_uploads


def load_activity(
    activity_type: str,
    activity_id: str,
    course_id: str,
    permission: Permission,
) -> ActivityRuntime:
    activity_dir = find_activity_dir(activity_type)
    return NotebookActivityRuntime(
        activity_dir,
        activity_id,
        course_id,
        USER_ID,
        permission,
    )


def get_activity_or_404(session: Session, activity_id: str) -> PageActivity:
    page_activity = session.get(PageActivity, activity_id)
    if not page_activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return page_activity


def get_page_or_404(session: Session, page_id: str) -> Page:
    page = session.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


def get_course_or_404(session: Session, course_id: str) -> Course:
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def activity_dict(
    pa: PageActivity,
    session: Session,
    permission: Permission = Permission.play,
) -> dict[str, object]:
    page = get_page_or_404(session, pa.page_id)
    course = get_course_or_404(session, page.course_id)
    ctx = load_activity(pa.activity_type, pa.id, course.id, permission)
    return {
        "id": pa.id,
        "page_id": page.id,
        "activity_type": pa.activity_type,
        "position": pa.position,
        "client_path": ctx.client_path,
        "state": ctx.get_state(),
        "permission": ctx.permission.name,
        "context": {
            "user_id": USER_ID,
            "course_id": course.id,
            "activity_id": pa.id,
        },
    }


# ---- course API ----


@app.get("/api/courses", summary="List all courses")
async def list_courses(
    session: Session = Depends(get_session),
) -> JSONResponse:
    """Return all courses ordered by position."""
    courses = session.exec(select(Course).order_by(col(Course.position))).all()
    return JSONResponse(
        [{"id": c.id, "title": c.title, "position": c.position} for c in courses]
    )


@app.post("/api/courses", status_code=201, summary="Create a course")
async def create_course(
    body: TitleBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
    """Create a new course. It is appended at the end of the list."""
    max_pos = session.exec(
        select(Course.position).order_by(desc(col(Course.position)))
    ).first()
    course = Course(title=body.title, position=(max_pos or 0) + 1)
    session.add(course)
    session.commit()
    session.refresh(course)
    return JSONResponse(
        {"id": course.id, "title": course.title, "position": course.position},
        status_code=201,
    )


@app.patch("/api/courses/{course_id}", summary="Rename a course")
async def update_course(
    course_id: str,
    body: TitleBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
    """Update the title of an existing course."""
    course = get_course_or_404(session, course_id)
    course.title = body.title
    session.add(course)
    session.commit()
    session.refresh(course)
    return JSONResponse(
        {"id": course.id, "title": course.title, "position": course.position}
    )


@app.delete("/api/courses/{course_id}", status_code=204, summary="Delete a course")
async def delete_course(
    course_id: str,
    session: Session = Depends(get_session),
) -> None:
    """Delete a course and all its pages and activity instances."""
    course = get_course_or_404(session, course_id)
    pages = session.exec(select(Page).where(Page.course_id == course_id)).all()
    for page in pages:
        activities = session.exec(
            select(PageActivity).where(PageActivity.page_id == page.id)
        ).all()
        for act in activities:
            delete_activity_by(activity_id=act.id, course_id=course_id)
            session.delete(act)
        session.delete(page)
    session.delete(course)
    session.commit()


@app.post("/api/courses/reorder", summary="Reorder courses")
async def reorder_courses(
    body: ReorderCoursesBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
    """Set course positions from the given ordered list of IDs."""
    for i, course_id in enumerate(body.course_ids):
        course = get_course_or_404(session, course_id)
        course.position = i
        session.add(course)
    session.commit()
    return JSONResponse(content={})


# ---- course detail + page API ----


@app.get("/api/courses/{course_id}", summary="Get a course with its pages")
async def get_course(
    course_id: str,
    session: Session = Depends(get_session),
) -> JSONResponse:
    """Return course details including the ordered list of pages."""
    course = course = get_course_or_404(session, course_id)
    pages = session.exec(
        select(Page).where(Page.course_id == course_id).order_by(col(Page.position))
    ).all()
    return JSONResponse(
        {
            "id": course.id,
            "title": course.title,
            "pages": [
                {"id": p.id, "title": p.title, "position": p.position} for p in pages
            ],
        }
    )


@app.post(
    "/api/courses/{course_id}/pages",
    status_code=201,
    summary="Create a page in a course",
)
async def create_page(
    course_id: str,
    body: TitleBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
    """Create a new page appended at the end of the course."""
    max_pos = session.exec(
        select(Page.position)
        .where(Page.course_id == course_id)
        .order_by(desc(col(Page.position)))
    ).first()
    page = Page(title=body.title, course_id=course_id, position=(max_pos or 0) + 1)
    session.add(page)
    session.commit()
    session.refresh(page)
    return JSONResponse(
        {"id": page.id, "title": page.title, "position": page.position},
        status_code=201,
    )


@app.patch("/api/pages/{page_id}", summary="Rename a page")
async def update_page(
    page_id: str,
    body: TitleBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
    """Update the title of an existing page."""
    page = get_page_or_404(session, page_id)
    page.title = body.title
    session.add(page)
    session.commit()
    session.refresh(page)
    return JSONResponse({"id": page.id, "title": page.title, "position": page.position})


@app.delete("/api/pages/{page_id}", status_code=204, summary="Delete a page")
async def delete_page(
    page_id: str,
    session: Session = Depends(get_session),
) -> None:
    """Delete a page and all its activity instances."""
    page = get_page_or_404(session, page_id)
    activities = session.exec(
        select(PageActivity).where(PageActivity.page_id == page_id)
    ).all()
    for act in activities:
        delete_activity_by(activity_id=act.id, course_id=page.course_id)
        session.delete(act)
    session.delete(page)
    session.commit()


@app.post("/api/pages/reorder", summary="Reorder pages")
async def reorder_pages(
    body: ReorderPagesBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
    """Set page positions from the given ordered list of IDs."""
    for i, page_id in enumerate(body.page_ids):
        page = get_page_or_404(session, page_id)
        page.position = i
        session.add(page)
    session.commit()
    return JSONResponse(content={})


# ---- page detail + activity API ----


@app.get("/api/pages/{page_id}", summary="Get a page with its activities")
async def get_page(
    page_id: str,
    session: Session = Depends(get_session),
) -> JSONResponse:
    """Return page details, its activity instances, and available activity types."""
    page = get_page_or_404(session, page_id)
    page_activities = session.exec(
        select(PageActivity)
        .where(PageActivity.page_id == page_id)
        .order_by(col(PageActivity.position))
    ).all()
    activities = [activity_dict(pa, session) for pa in page_activities]
    return JSONResponse(
        {
            "id": page.id,
            "title": page.title,
            "course_id": page.course_id,
            "activities": activities,
            "activity_types": list_activity_types(USER_ID),
        }
    )


@app.post(
    "/api/pages/{page_id}/activities",
    status_code=201,
    summary="Add an activity to a page",
)
async def create_activity(
    page_id: str,
    body: ActivityTypeBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
    """Create a new activity instance of the given type on the page."""
    find_activity_dir(body.activity_type)
    max_pos = session.exec(
        select(PageActivity.position)
        .where(PageActivity.page_id == page_id)
        .order_by(desc(col(PageActivity.position)))
    ).first()
    pa = PageActivity(
        page_id=page_id,
        activity_type=body.activity_type,
        position=(max_pos or 0) + 1,
    )
    session.add(pa)
    session.commit()
    session.refresh(pa)
    return JSONResponse(activity_dict(pa, session), status_code=201)


@app.get(
    "/api/activities/{activity_id}/{permission}",
    summary="Get an activity instance",
)
async def get_activity(
    activity_id: str,
    permission: Permission,
    session: Session = Depends(get_session),
) -> JSONResponse:
    """Return activity state and metadata for the given permission level."""
    pa = get_activity_or_404(session, activity_id)
    return JSONResponse(activity_dict(pa, session, permission))


@app.delete(
    "/api/activities/{activity_id}",
    status_code=204,
    summary="Delete an activity instance",
)
async def delete_activity(
    activity_id: str,
    session: Session = Depends(get_session),
) -> None:
    """Remove an activity instance from its page."""
    pa = get_activity_or_404(session, activity_id)
    page = get_page_or_404(session, pa.page_id)
    delete_activity_by(activity_id=pa.id, course_id=page.course_id)
    session.delete(pa)
    session.commit()


@app.get(
    "/api/activities/{activity_id}/{permission}/llms.txt",
    summary="Activity info for AI agents",
)
async def activity_llms_txt(
    activity_id: str,
    permission: Permission,
    request: Request,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    activity = get_activity_or_404(session, activity_id)
    page = get_page_or_404(session, activity.page_id)

    runtime = load_activity(
        activity.activity_type, activity_id, page.course_id, permission
    )
    base_url = str(request.base_url).rstrip("/")

    # Parse activity actions
    manifest_actions = {}
    if runtime.manifest.actions:
        manifest_actions = {
            name: action.model_dump()
            for name, action in runtime.manifest.actions.items()
        }

    # Get current state
    state = runtime.get_state()

    information = llms.get_activity_information().format(
        base_url=base_url,
        course_id=page.course_id,
        permission=permission.value,
        manifest_actions=json.dumps(manifest_actions, indent=2),
        activity_id=activity_id,
        activity_state=json.dumps(state, indent=2),
        activity_type=activity.activity_type,
        page_id=activity.page_id,
    )
    return PlainTextResponse(information)


@app.post(
    "/api/activities/{activity_id}/move",
    summary="Move an activity up or down",
)
async def move_activity(
    activity_id: str,
    body: MoveActivityBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
    """Swap the activity with its neighbor in the given direction."""
    _pa = get_activity_or_404(session, activity_id)

    items = list(
        session.exec(
            select(PageActivity)
            .where(PageActivity.page_id == body.page_id)
            .order_by(col(PageActivity.position))
        ).all()
    )
    idx = next((i for i, a in enumerate(items) if a.id == activity_id), -1)

    if body.direction == "up" and idx > 0:
        items[idx], items[idx - 1] = items[idx - 1], items[idx]
    elif body.direction == "down" and idx < len(items) - 1:
        items[idx], items[idx + 1] = items[idx + 1], items[idx]

    for i, a in enumerate(items):
        a.position = i
        session.add(a)
    session.commit()

    refreshed = list(
        session.exec(
            select(PageActivity)
            .where(PageActivity.page_id == body.page_id)
            .order_by(col(PageActivity.position))
        ).all()
    )
    return JSONResponse({"activities": [activity_dict(r, session) for r in refreshed]})


ACTIVITY_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


# ---- activity type API ----


@app.get("/api/activity-types", summary="List available activity types")
async def get_activity_types() -> JSONResponse:
    """Return all activity types: built-in samples and current user's uploads.

    Built-in samples are returned as simple names (e.g. ``quiz``).
    User uploads are prefixed with ``@<user_id>/`` (e.g. ``@student/my-quiz``).
    """
    return JSONResponse(list_activity_types(USER_ID))


@app.post(
    "/api/activity-types",
    status_code=201,
    summary="Upload a custom activity type",
)
async def upload_activity_type(
    file: UploadFile,
    name: str = Form(),
) -> JSONResponse:
    """Upload a zip archive as a new activity type for the current user.

    The zip must contain a valid ``manifest.json`` at its root, along with
    the client file (and optionally server/static files) declared in the
    manifest.  The resulting activity type will be available as
    ``@<user_id>/<name>``.  Re-uploading the same name overwrites the
    previous version.
    """
    if not ACTIVITY_NAME_RE.match(name):
        raise HTTPException(
            status_code=400,
            detail="Name must match ^[a-z0-9][a-z0-9_-]*$",
        )

    content = await file.read()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        zip_path = tmp_path / "upload.zip"
        zip_path.write_bytes(content)

        if not zipfile.is_zipfile(zip_path):
            raise HTTPException(
                status_code=400, detail="Uploaded file is not a valid zip"
            )
        extract_dir = tmp_path / "extracted"
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

        manifest_path = extract_dir / "manifest.json"
        if not manifest_path.exists():
            raise HTTPException(
                status_code=400, detail="manifest.json not found in zip"
            )

        try:
            # TODO those many checks should not be performed in the view
            manifest = XplaActivityManifest.model_validate_json(
                manifest_path.read_text()
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid manifest: {e}") from e

        if not (extract_dir / manifest.client).exists():
            raise HTTPException(
                status_code=400,
                detail=f"Client file '{manifest.client}' not found in zip",
            )

        if manifest.server and not (extract_dir / manifest.server).exists():
            raise HTTPException(
                status_code=400,
                detail=f"Server file '{manifest.server}' not found in zip",
            )

        for asset in manifest.assets or []:
            asset_path = asset.root
            if not (extract_dir / asset_path).exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"Static file '{asset_path}' not found in zip",
                )

        target_dir = constants.ACTIVITIES_DIR / USER_ID / name
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(extract_dir), str(target_dir))

    return JSONResponse({"name": name}, status_code=201)


@app.delete(
    "/api/activity-types/{name}",
    status_code=204,
    summary="Delete a custom activity type",
)
async def delete_activity_type(
    name: str,
    session: Session = Depends(get_session),
) -> None:
    """Delete a user-uploaded activity type and cascade-remove all activity
    instances and field data that reference it.
    """
    activity_type_str = f"@{USER_ID}/{name}"
    activities = session.exec(
        select(PageActivity).where(PageActivity.activity_type == activity_type_str)
    ).all()
    delete_activity_by(activity_name=activity_type_str)
    for pa in activities:
        session.delete(pa)
    session.commit()

    target_dir = constants.ACTIVITIES_DIR / USER_ID / name
    if target_dir.exists():
        shutil.rmtree(target_dir)


# ---- activity runtime routes ----


@app.get(
    "/a/{activity_id}/{file_path:path}",
    summary="Serve an activity static asset",
)
async def activity_asset(
    activity_id: str, file_path: str, session: Session = Depends(get_session)
) -> FileResponse:
    pa = get_activity_or_404(session, activity_id)
    page = get_page_or_404(session, pa.page_id)
    course = get_course_or_404(session, page.course_id)
    ctx = load_activity(pa.activity_type, activity_id, course.id, Permission.play)
    try:
        full_path = ctx.get_asset_path(file_path)
    except AssetAccessError as e:
        raise HTTPException(status_code=404, detail="Access denied") from e
    return FileResponse(full_path)


@app.get(
    "/activity/{activity_id}/storage/{storage_name}/{file_path:path}",
    summary="Serve a file from activity storage",
)
async def storage_file(
    activity_id: str,
    storage_name: str,
    file_path: str,
    session: Session = Depends(get_session),
    activity_id_override: str | None = Query(None, alias="activity_id"),
    course_id_override: str | None = Query(None, alias="course_id"),
    user_id_override: str | None = Query(None, alias="user_id"),
) -> Response:
    pa = get_activity_or_404(session, activity_id)
    page = get_page_or_404(session, pa.page_id)
    ctx = load_activity(pa.activity_type, activity_id, page.course_id, Permission.play)
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


@app.post(
    "/api/activity/{activity_id}/{permission}/actions",
    summary="Trigger an action",
)
async def activity_actions(
    activity_id: str,
    permission: Permission,
    action: ActivityAction,
    session: Session = Depends(get_session),
) -> None:
    """
    Trigger an activity action

    This will mimic the behaviour of users interacting with a learning activity from the
    frontend. Actions that are sent via this endpoint *must* match the format that is
    documented in the activity manifest.
    """
    activity = get_activity_or_404(session, activity_id)
    page = get_page_or_404(session, activity.page_id)

    ctx = load_activity(activity.activity_type, activity_id, page.course_id, permission)
    try:
        ctx.on_action(action.name, action.value)
    except ActionValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid action: {e}") from e

    events = ctx.clear_pending_events()
    await event_bus.publish(activity.activity_type, events)


@app.websocket("/api/activity/{activity_id}/{permission}/ws")
async def activity_ws(
    websocket: WebSocket,
    activity_id: str,
    permission: Permission,
    session: Session = Depends(get_session),
) -> None:

    # Check arguments
    # https://websocket.org/reference/close-codes/
    policy_violation_code = 1008
    try:
        pa = get_activity_or_404(session, activity_id)
        page = get_page_or_404(session, pa.page_id)
    except HTTPException:
        await websocket.close(code=policy_violation_code)
        return
    await websocket.accept()

    subscriber = event_bus.subscribe(
        pa.activity_type,
        websocket,
        USER_ID,
        permission,
        page.course_id,
        activity_id,
    )

    while True:
        try:
            data = await websocket.receive_json()
        except WebSocketDisconnect:
            event_bus.unsubscribe(pa.activity_type, subscriber)
            return

        try:
            action_name = data["action"]
            action_value = data["value"]
        except KeyError:
            # TODO raise error?
            continue

        ctx = load_activity(pa.activity_type, activity_id, page.course_id, permission)
        try:
            ctx.on_action(action_name, action_value)
        except ActionValidationError as e:
            # TODO should we return an error to the frontend?
            logger.warning("WS action validation error: %s", e)
            continue

        events = ctx.clear_pending_events()
        await event_bus.publish(pa.activity_type, events)


# ---- SPA fallback ----


@app.get("/{path:path}", include_in_schema=False)
async def spa_fallback(path: str) -> HTMLResponse:  # pylint: disable=unused-argument
    """Serve the frontend index.html for any unmatched GET request (SPA fallback)."""
    index = constants.FRONTEND_DIR / "index.html"
    if not index.is_file():
        return HTMLResponse(
            "<h1>Frontend not built</h1><p>Run <code>make notebook-frontend-build</code></p>",
            status_code=503,
        )
    return HTMLResponse(index.read_text())
