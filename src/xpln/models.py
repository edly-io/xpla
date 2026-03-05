from uuid import uuid4

from sqlmodel import Field, SQLModel


class Course(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
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
