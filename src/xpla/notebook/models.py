from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    password_salt: str
    created_at: datetime = Field(default_factory=_utcnow)


class UserSession(SQLModel, table=True):
    token: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime


class Course(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    owner_id: str = Field(foreign_key="user.id", index=True)
    title: str
    position: int = 0


class Page(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    course_id: str = Field(foreign_key="course.id")
    title: str
    position: int = 0


class PageActivity(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    page_id: str = Field(foreign_key="page.id")
    activity_type: str
    position: int = 0


class CourseActivity(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    course_id: str = Field(foreign_key="course.id")
    activity_type: str
    position: int = 0
