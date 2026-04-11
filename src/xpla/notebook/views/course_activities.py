import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session, col, desc, select

from xpla.lib.manifest_types import XplaActivityManifest
from xpla.lib.permission import Permission
from xpla.notebook import constants
from xpla.notebook.auth import get_current_user
from xpla.notebook.db import get_session
from xpla.notebook.models import Course, CourseActivity, User
from xpla.notebook.runtime import NotebookActivityRuntime, delete_type_storage

router = APIRouter()

ACTIVITY_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class ActivityTypeBody(BaseModel):
    activity_type: str


class MoveCourseActivityBody(BaseModel):
    direction: str
    course_id: str


def get_course_or_404(session: Session, course_id: str, user: User) -> Course:
    course = session.get(Course, course_id)
    if not course or course.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def find_course_activity_dir(activity_type: str) -> Path:
    if activity_type.startswith("@"):
        parts = activity_type[1:].split("/", 1)
        if len(parts) != 2:
            raise HTTPException(
                status_code=404,
                detail=f"Course activity '{activity_type}' not found",
            )
        user_id, name = parts
        activity_dir = constants.COURSE_ACTIVITIES_DIR / user_id / name
    else:
        activity_dir = constants.COURSE_ACTIVITY_SAMPLES_DIR / activity_type
    if not (activity_dir / "manifest.json").exists():
        raise HTTPException(
            status_code=404,
            detail=f"Course activity '{activity_type}' not found",
        )
    return activity_dir


def list_course_activity_types(user_id: str) -> list[str]:
    builtins: list[str] = []
    samples_dir = constants.COURSE_ACTIVITY_SAMPLES_DIR
    if samples_dir.is_dir():
        builtins = sorted(
            d.name
            for d in samples_dir.iterdir()
            if d.is_dir() and (d / "manifest.json").exists()
        )
    user_uploads: list[str] = []
    user_dir = constants.COURSE_ACTIVITIES_DIR / user_id
    if user_dir.is_dir():
        user_uploads = sorted(
            f"@{user_id}/{d.name}" for d in user_dir.iterdir() if d.is_dir()
        )
    return builtins + user_uploads


def load_course_activity(
    activity_type: str,
    activity_id: str,
    course_id: str,
    user_id: str,
    permission: Permission,
) -> NotebookActivityRuntime:
    activity_dir = find_course_activity_dir(activity_type)
    return NotebookActivityRuntime(
        activity_dir,
        activity_id,
        course_id,
        user_id,
        permission,
        is_course_activity=True,
    )


def get_course_activity_or_404(
    session: Session, activity_id: str, user: User
) -> tuple[CourseActivity, Course]:
    ca = session.get(CourseActivity, activity_id)
    if not ca or ca.course.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Course activity not found")
    return ca, ca.course


def course_activity_dict(
    ca: CourseActivity,
    user_id: str,
    permission: Permission = Permission.play,
) -> dict[str, object]:
    ctx = load_course_activity(
        ca.activity_type, ca.id, ca.course_id, user_id, permission
    )
    return {
        "id": ca.id,
        "course_id": ca.course_id,
        "activity_type": ca.activity_type,
        "position": ca.position,
        "client_path": ctx.client_path,
        "state": ctx.get_state(),
        "permission": ctx.permission.name,
        "context": {
            "user_id": user_id,
            "course_id": ca.course_id,
            "activity_id": ca.id,
        },
    }


# ---- course activity type API ----


@router.get("/api/course-activity-types", summary="List course activity types")
async def get_course_activity_types(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Return all course activity types uploaded by the current user."""
    return JSONResponse(list_course_activity_types(current_user.id))


@router.post(
    "/api/course-activity-types",
    status_code=201,
    summary="Upload a course activity type",
)
async def upload_course_activity_type(
    file: UploadFile,
    name: str = Form(),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Upload a zip archive as a new course activity type."""
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

        for asset in manifest.assets or []:
            asset_path = asset.root
            if not (extract_dir / asset_path).exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"Static file '{asset_path}' not found in zip",
                )

        target_dir = constants.COURSE_ACTIVITIES_DIR / current_user.id / name
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(extract_dir), str(target_dir))

    return JSONResponse({"name": name}, status_code=201)


@router.delete(
    "/api/course-activity-types/{name}",
    status_code=204,
    summary="Delete a course activity type",
)
async def delete_course_activity_type(
    name: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a course activity type and cascade-remove all instances."""
    activity_type_str = f"@{current_user.id}/{name}"
    activities = session.exec(
        select(CourseActivity).where(CourseActivity.activity_type == activity_type_str)
    ).all()
    delete_type_storage(activity_type_str)
    for ca in activities:
        session.delete(ca)
    session.commit()

    target_dir = constants.COURSE_ACTIVITIES_DIR / current_user.id / name
    if target_dir.exists():
        shutil.rmtree(target_dir)


# ---- course dashboard API ----


@router.get(
    "/api/courses/{course_id}/dashboard",
    summary="Get course dashboard with activities",
)
async def get_course_dashboard(
    course_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Return course details, dashboard activities, and available types."""
    course = get_course_or_404(session, course_id, current_user)
    cas = session.exec(
        select(CourseActivity)
        .where(CourseActivity.course_id == course_id)
        .order_by(col(CourseActivity.position))
    ).all()
    activities = [course_activity_dict(ca, current_user.id) for ca in cas]
    return JSONResponse(
        {
            "id": course.id,
            "title": course.title,
            "activities": activities,
            "activity_types": list_course_activity_types(current_user.id),
        }
    )


@router.post(
    "/api/courses/{course_id}/dashboard/activities",
    status_code=201,
    summary="Add a course activity",
)
async def create_course_activity(
    course_id: str,
    body: ActivityTypeBody,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Create a new course activity instance on the dashboard."""
    get_course_or_404(session, course_id, current_user)
    find_course_activity_dir(body.activity_type)
    max_pos = session.exec(
        select(CourseActivity.position)
        .where(CourseActivity.course_id == course_id)
        .order_by(desc(col(CourseActivity.position)))
    ).first()
    ca = CourseActivity(
        course_id=course_id,
        activity_type=body.activity_type,
        position=(max_pos or 0) + 1,
    )
    session.add(ca)
    session.commit()
    session.refresh(ca)
    return JSONResponse(course_activity_dict(ca, current_user.id), status_code=201)


@router.get(
    "/api/course-activities/{activity_id}/{permission}",
    summary="Get a course activity instance",
)
async def get_course_activity(
    activity_id: str,
    permission: Permission,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Return course activity state and metadata."""
    ca, _course = get_course_activity_or_404(session, activity_id, current_user)
    return JSONResponse(course_activity_dict(ca, current_user.id, permission))


@router.delete(
    "/api/course-activities/{activity_id}",
    status_code=204,
    summary="Delete a course activity instance",
)
async def delete_course_activity_instance(
    activity_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a course activity instance."""
    ca, _course = get_course_activity_or_404(session, activity_id, current_user)
    ctx = load_course_activity(
        ca.activity_type, ca.id, ca.course_id, current_user.id, Permission.edit
    )
    ctx.delete_storage()
    session.delete(ca)
    session.commit()


@router.post(
    "/api/course-activities/{activity_id}/move",
    summary="Move a course activity up or down",
)
async def move_course_activity(
    activity_id: str,
    body: MoveCourseActivityBody,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Swap the course activity with its neighbor."""
    get_course_activity_or_404(session, activity_id, current_user)
    get_course_or_404(session, body.course_id, current_user)

    items = list(
        session.exec(
            select(CourseActivity)
            .where(CourseActivity.course_id == body.course_id)
            .order_by(col(CourseActivity.position))
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
            select(CourseActivity)
            .where(CourseActivity.course_id == body.course_id)
            .order_by(col(CourseActivity.position))
        ).all()
    )
    return JSONResponse(
        {"activities": [course_activity_dict(r, current_user.id) for r in refreshed]}
    )
