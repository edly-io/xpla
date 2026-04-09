from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session, col, desc, select

from xpla.notebook.db import get_session
from xpla.notebook.models import Course, CourseActivity, Page, PageActivity
from xpla.notebook.runtime import delete_activity_by

router = APIRouter()


class TitleBody(BaseModel):
    title: str


class ReorderCoursesBody(BaseModel):
    course_ids: list[str]


class ReorderPagesBody(BaseModel):
    page_ids: list[str]


def get_course_or_404(session: Session, course_id: str) -> Course:
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def get_page_or_404(session: Session, page_id: str) -> Page:
    page = session.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


# ---- course API ----


@router.get("/api/courses", summary="List all courses")
async def list_courses(
    session: Session = Depends(get_session),
) -> JSONResponse:
    """Return all courses ordered by position."""
    courses = session.exec(select(Course).order_by(col(Course.position))).all()
    return JSONResponse(
        [{"id": c.id, "title": c.title, "position": c.position} for c in courses]
    )


@router.post("/api/courses", status_code=201, summary="Create a course")
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


@router.patch("/api/courses/{course_id}", summary="Rename a course")
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


@router.delete("/api/courses/{course_id}", status_code=204, summary="Delete a course")
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
    course_activities = session.exec(
        select(CourseActivity).where(CourseActivity.course_id == course_id)
    ).all()
    for ca in course_activities:
        delete_activity_by(activity_id=ca.id, course_id=course_id)
        session.delete(ca)
    session.delete(course)
    session.commit()


@router.post("/api/courses/reorder", summary="Reorder courses")
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


@router.get("/api/courses/{course_id}", summary="Get a course with its pages")
async def get_course(
    course_id: str,
    session: Session = Depends(get_session),
) -> JSONResponse:
    """Return course details including the ordered list of pages."""
    course = get_course_or_404(session, course_id)
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


@router.post(
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


@router.patch("/api/pages/{page_id}", summary="Rename a page")
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


@router.delete("/api/pages/{page_id}", status_code=204, summary="Delete a page")
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


@router.post("/api/pages/reorder", summary="Reorder pages")
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
