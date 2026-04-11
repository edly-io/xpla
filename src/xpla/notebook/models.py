from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Field, Relationship, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    password_salt: str
    created_at: datetime = Field(default_factory=_utcnow)

    sessions: list["UserSession"] = Relationship(
        back_populates="user", cascade_delete=True
    )
    # No cascade_delete — user deletion is not a supported operation; DB-level
    # CASCADE acts as a safety net only.
    courses: list["Course"] = Relationship(back_populates="owner")


class UserSession(SQLModel, table=True):
    token: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime

    user: User = Relationship(back_populates="sessions")


class Course(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    owner_id: str = Field(foreign_key="user.id", index=True)
    title: str
    position: int = 0

    owner: User = Relationship(back_populates="courses")
    pages: list["Page"] = Relationship(back_populates="course", cascade_delete=True)
    course_activities: list["CourseActivity"] = Relationship(
        back_populates="course", cascade_delete=True
    )


class Page(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    course_id: str = Field(foreign_key="course.id")
    title: str
    position: int = 0

    course: Course = Relationship(back_populates="pages")
    activities: list["PageActivity"] = Relationship(
        back_populates="page", cascade_delete=True
    )


class PageActivity(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    page_id: str = Field(foreign_key="page.id")
    activity_type: str
    position: int = 0

    page: Page = Relationship(back_populates="activities")


class CourseActivity(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    course_id: str = Field(foreign_key="course.id")
    activity_type: str
    position: int = 0

    course: Course = Relationship(back_populates="course_activities")


class ActivityStatement(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    course_id: str = Field(index=True)
    activity_id: str = Field(index=True)
    activity_name: str = Field(index=True)
    user_id: str = Field(index=True)
    verb: str
    score: float | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
