import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from sqlmodel import Session, col, desc, select

from xpla.lib.manifest_types import XplaActivityManifest
from xpla.lib.permission import Permission
from xpla.notebook import constants, llms
from xpla.notebook.db import get_session
from xpla.notebook.models import Page, PageActivity
from xpla.notebook.runtime import NotebookActivityRuntime, delete_activity_by

router = APIRouter()

USER_ID = "student"

ACTIVITY_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class ActivityTypeBody(BaseModel):
    activity_type: str


class MoveActivityBody(BaseModel):
    direction: str
    page_id: str


def find_activity_dir(activity_type: str) -> Path:
    if activity_type.startswith("@"):
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
) -> NotebookActivityRuntime:
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


def activity_dict(
    pa: PageActivity,
    session: Session,
    permission: Permission = Permission.play,
) -> dict[str, object]:
    page = get_page_or_404(session, pa.page_id)
    ctx = load_activity(pa.activity_type, pa.id, page.course_id, permission)
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
            "course_id": page.course_id,
            "activity_id": pa.id,
        },
    }


# ---- page detail + activity API ----


@router.get("/api/pages/{page_id}", summary="Get a page with its activities")
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


@router.post(
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


@router.get(
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


@router.delete(
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


@router.get(
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

    manifest_actions = {}
    if runtime.manifest.actions:
        manifest_actions = {
            name: action.model_dump()
            for name, action in runtime.manifest.actions.items()
        }

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


@router.post(
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


# ---- activity type API ----


@router.get("/api/activity-types", summary="List available activity types")
async def get_activity_types() -> JSONResponse:
    """Return all activity types: built-in samples and current user's uploads."""
    return JSONResponse(list_activity_types(USER_ID))


@router.post(
    "/api/activity-types",
    status_code=201,
    summary="Upload a custom activity type",
)
async def upload_activity_type(
    file: UploadFile,
    name: str = Form(),
) -> JSONResponse:
    """Upload a zip archive as a new activity type for the current user."""
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


@router.delete(
    "/api/activity-types/{name}",
    status_code=204,
    summary="Delete a custom activity type",
)
async def delete_activity_type(
    name: str,
    session: Session = Depends(get_session),
) -> None:
    """Delete a user-uploaded activity type and cascade-remove all instances."""
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
