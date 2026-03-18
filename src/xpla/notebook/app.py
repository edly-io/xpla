import logging
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session, col, desc, select

from xpla.lib.actions import ActionValidationError
from xpla.lib.manifest_types import XplaActivityManifest
from xpla.lib.runtime import ActivityRuntime, AssetAccessError
from xpla.lib.event_bus import EventBus
from xpla.lib.permission import Permission
from xpla.notebook import constants
from xpla.notebook.db import run_migrations, get_session
from xpla.notebook.field_store import SQLiteFieldStore
from xpla.notebook.models import Course, Page, PageActivity

logger = logging.getLogger(__name__)

app = FastAPI(title="xPLN", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=constants.STATIC_DIR), name="static")

event_bus = EventBus()

USER_ID = "student"

field_store = SQLiteFieldStore()


@app.on_event("startup")
def on_startup() -> None:
    run_migrations()


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
    return ActivityRuntime(
        activity_dir,
        field_store,
        activity_id=activity_id,
        user_id=USER_ID,
        course_id=course_id,
        permission=permission,
    )


def activity_dict(
    pa: PageActivity,
    session: Session,
    permission: Permission = Permission.play,
) -> dict[str, object]:
    page = session.get(Page, pa.page_id)
    course_id = page.course_id if page else ""
    ctx = load_activity(pa.activity_type, pa.id, course_id, permission)
    return {
        "id": pa.id,
        "page_id": pa.page_id,
        "activity_type": pa.activity_type,
        "position": pa.position,
        "client_path": ctx.client_path,
        "state": ctx.get_state(),
        "permission": ctx.permission.name,
        "context": {
            "user_id": USER_ID,
            "course_id": course_id,
            "activity_id": pa.id,
        },
    }


# ---- course API ----


@app.get("/api/courses")
async def list_courses(
    session: Session = Depends(get_session),
) -> JSONResponse:
    courses = session.exec(select(Course).order_by(col(Course.position))).all()
    return JSONResponse(
        [{"id": c.id, "title": c.title, "position": c.position} for c in courses]
    )


@app.post("/api/courses", status_code=201)
async def create_course(
    body: TitleBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
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


@app.patch("/api/courses/{course_id}")
async def update_course(
    course_id: str,
    body: TitleBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Not found")
    course.title = body.title
    session.add(course)
    session.commit()
    session.refresh(course)
    return JSONResponse(
        {"id": course.id, "title": course.title, "position": course.position}
    )


@app.delete("/api/courses/{course_id}", status_code=204)
async def delete_course(
    course_id: str,
    session: Session = Depends(get_session),
) -> None:
    course = session.get(Course, course_id)
    if course:
        pages = session.exec(select(Page).where(Page.course_id == course_id)).all()
        for page in pages:
            activities = session.exec(
                select(PageActivity).where(PageActivity.page_id == page.id)
            ).all()
            for act in activities:
                session.delete(act)
            session.delete(page)
        session.delete(course)
        session.commit()


@app.post("/api/courses/reorder")
async def reorder_courses(
    body: ReorderCoursesBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
    for i, course_id in enumerate(body.course_ids):
        course = session.get(Course, course_id)
        if course:
            course.position = i
            session.add(course)
    session.commit()
    return JSONResponse(content={})


# ---- course detail + page API ----


@app.get("/api/courses/{course_id}")
async def get_course(
    course_id: str,
    session: Session = Depends(get_session),
) -> JSONResponse:
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Not found")
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


@app.post("/api/courses/{course_id}/pages", status_code=201)
async def create_page(
    course_id: str,
    body: TitleBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
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


@app.patch("/api/pages/{page_id}")
async def update_page(
    page_id: str,
    body: TitleBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
    page = session.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Not found")
    page.title = body.title
    session.add(page)
    session.commit()
    session.refresh(page)
    return JSONResponse({"id": page.id, "title": page.title, "position": page.position})


@app.delete("/api/pages/{page_id}", status_code=204)
async def delete_page(
    page_id: str,
    session: Session = Depends(get_session),
) -> None:
    page = session.get(Page, page_id)
    if page:
        activities = session.exec(
            select(PageActivity).where(PageActivity.page_id == page_id)
        ).all()
        for act in activities:
            session.delete(act)
        session.delete(page)
        session.commit()


@app.post("/api/pages/reorder")
async def reorder_pages(
    body: ReorderPagesBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
    for i, page_id in enumerate(body.page_ids):
        page = session.get(Page, page_id)
        if page:
            page.position = i
            session.add(page)
    session.commit()
    return JSONResponse(content={})


# ---- page detail + activity API ----


@app.get("/api/pages/{page_id}")
async def get_page(
    page_id: str,
    session: Session = Depends(get_session),
) -> JSONResponse:
    page = session.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Not found")
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


@app.post("/api/pages/{page_id}/activities", status_code=201)
async def create_activity(
    page_id: str,
    body: ActivityTypeBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
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


@app.get("/api/activities/{activity_id}/{permission}")
async def get_activity(
    activity_id: str,
    permission: str,
    session: Session = Depends(get_session),
) -> JSONResponse:
    pa = session.get(PageActivity, activity_id)
    if not pa:
        raise HTTPException(status_code=404, detail="Not found")
    return JSONResponse(activity_dict(pa, session, Permission(permission)))


@app.delete("/api/activities/{activity_id}", status_code=204)
async def delete_activity(
    activity_id: str,
    session: Session = Depends(get_session),
) -> None:
    pa = session.get(PageActivity, activity_id)
    if pa:
        session.delete(pa)
        session.commit()


@app.post("/api/activities/{activity_id}/move")
async def move_activity(
    activity_id: str,
    body: MoveActivityBody,
    session: Session = Depends(get_session),
) -> JSONResponse:
    pa = session.get(PageActivity, activity_id)
    if not pa:
        raise HTTPException(status_code=404, detail="Not found")

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


@app.get("/api/activity-types")
async def get_activity_types() -> JSONResponse:
    return JSONResponse(list_activity_types(USER_ID))


ACTIVITY_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


# ---- user activity upload API ----


@app.get("/api/my-activities")
async def list_my_activities() -> JSONResponse:
    user_dir = constants.ACTIVITIES_DIR / USER_ID
    if not user_dir.is_dir():
        return JSONResponse([])
    return JSONResponse(sorted(d.name for d in user_dir.iterdir() if d.is_dir()))


@app.post("/api/my-activities", status_code=201)
async def upload_activity(
    name: str,
    file: UploadFile,
) -> JSONResponse:
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

        for static_item in manifest.static or []:
            static_path = static_item.root
            if not (extract_dir / static_path).exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"Static file '{static_path}' not found in zip",
                )

        target_dir = constants.ACTIVITIES_DIR / USER_ID / name
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(extract_dir), str(target_dir))

    return JSONResponse({"name": name}, status_code=201)


@app.delete("/api/my-activities/{name}", status_code=204)
async def delete_my_activity(
    name: str,
    session: Session = Depends(get_session),
) -> None:
    activity_type_str = f"@{USER_ID}/{name}"
    activities = session.exec(
        select(PageActivity).where(PageActivity.activity_type == activity_type_str)
    ).all()
    for pa in activities:
        field_store.delete_by_activity(pa.id)
        session.delete(pa)
    session.commit()

    target_dir = constants.ACTIVITIES_DIR / USER_ID / name
    if target_dir.exists():
        shutil.rmtree(target_dir)


# ---- activity runtime routes ----


@app.get("/a/{activity_id}/{file_path:path}")
async def activity_asset(
    activity_id: str, file_path: str, session: Session = Depends(get_session)
) -> FileResponse:
    pa = session.get(PageActivity, activity_id)
    if pa is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    page = session.get(Page, pa.page_id)
    course_id = page.course_id if page else ""
    ctx = load_activity(pa.activity_type, activity_id, course_id, Permission.play)
    try:
        full_path = ctx.get_asset_path(file_path)
    except AssetAccessError as e:
        raise HTTPException(status_code=404, detail="Access denied") from e
    return FileResponse(full_path)


@app.websocket("/api/activity/{activity_id}/{permission}/ws")
async def activity_ws(
    websocket: WebSocket,
    activity_id: str,
    permission: str,
    session: Session = Depends(get_session),
) -> None:

    # Check arguments
    # https://websocket.org/reference/close-codes/
    policy_violation_code = 1008
    pa = session.get(PageActivity, activity_id)
    if not pa:
        await websocket.close(code=policy_violation_code)
        return
    try:
        activity_permission = Permission(permission)
    except ValueError:
        await websocket.close(code=policy_violation_code)
        return
    page = session.get(Page, pa.page_id)
    if not page:
        await websocket.close(code=policy_violation_code)
        return

    await websocket.accept()

    subscriber = event_bus.subscribe(
        pa.activity_type,
        websocket,
        USER_ID,
        activity_permission,
        page.course_id,
        activity_id,
    )

    while True:
        try:
            data = await websocket.receive_json()
        except WebSocketDisconnect:
            event_bus.unsubscribe(pa.activity_type, subscriber)
            return
        action_name = data.get("action", "")
        action_value = data.get("value", "")

        ctx = load_activity(
            pa.activity_type, activity_id, page.course_id, activity_permission
        )
        try:
            ctx.on_action(action_name, action_value)
        except ActionValidationError as e:
            logger.warning("WS action validation error: %s", e)
            continue

        events = ctx.clear_pending_events()
        await event_bus.publish(pa.activity_type, events)
