"""Tests for ORM cascade deletes and DB-level ON DELETE CASCADE."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from xpla.notebook.auth import hash_password
from xpla.notebook.field_store import FieldEntry
from xpla.notebook.models import Course, CourseActivity, Page, PageActivity, User


def _make_user(session: Session, email: str = "a@example.com") -> User:
    pw_hash, pw_salt = hash_password("password123")
    user = User(email=email, password_hash=pw_hash, password_salt=pw_salt)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _make_full_course(
    session: Session, user: User
) -> tuple[Course, Page, PageActivity, CourseActivity]:
    course = Course(title="Test", owner_id=user.id)
    session.add(course)
    session.commit()

    page = Page(title="Page", course_id=course.id)
    session.add(page)
    session.commit()

    pa = PageActivity(page_id=page.id, activity_type="markdown")
    session.add(pa)
    session.commit()

    ca = CourseActivity(course_id=course.id, activity_type="@u/quiz")
    session.add(ca)
    session.commit()

    return course, page, pa, ca


def test_delete_course_cascades_to_pages_and_activities(session: Session) -> None:
    user = _make_user(session)
    course, page, pa, ca = _make_full_course(session, user)

    session.delete(course)
    session.commit()

    assert session.get(Course, course.id) is None
    assert session.get(Page, page.id) is None
    assert session.get(PageActivity, pa.id) is None
    assert session.get(CourseActivity, ca.id) is None


def test_delete_page_cascades_to_activities(session: Session) -> None:
    user = _make_user(session)
    course, page, pa, _ca = _make_full_course(session, user)

    session.delete(page)
    session.commit()

    assert session.get(Page, page.id) is None
    assert session.get(PageActivity, pa.id) is None
    # Course and CourseActivity are unaffected
    assert session.get(Course, course.id) is not None


def test_delete_activity_cleans_up_field_store(session: Session) -> None:
    """Deleting a PageActivity should automatically remove its field entries."""
    user = _make_user(session)
    course, _page, pa, _ca = _make_full_course(session, user)

    # Insert a field entry for this activity.
    entry = FieldEntry(
        course_id=course.id,
        activity_name=pa.activity_type,
        activity_id=pa.id,
        user_id=user.id,
        key="score",
        value="42",
    )
    session.add(entry)
    session.commit()
    assert session.exec(select(FieldEntry)).first() is not None

    # Delete the activity — the after_delete event should clean up the field entry.
    session.delete(pa)
    session.commit()

    assert session.exec(select(FieldEntry)).first() is None


def test_fk_enforcement_rejects_orphan_page(session: Session) -> None:
    """Inserting a Page with a nonexistent course_id should raise IntegrityError."""
    page = Page(title="Orphan", course_id="nonexistent-id")
    session.add(page)
    with pytest.raises(IntegrityError):
        session.commit()
