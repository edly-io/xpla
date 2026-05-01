"""SQLite-backed FieldStore implementation for xpln."""

import json
from typing import Any

from sqlalchemy import delete as sa_delete
from sqlalchemy import event
from sqlmodel import Field, SQLModel, UniqueConstraint, col, select

from xpla.lib.field_store import FieldStore
from xpla.lib.fields import FieldType
from xpla.notebook import db


class FieldEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    course_id: str = Field(index=True)
    activity_name: str = Field(index=True)
    activity_id: str = Field(index=True)
    user_id: str = Field(index=True)
    key: str = Field(index=True)
    value: str  # JSON-encoded

    __table_args__ = (
        UniqueConstraint("course_id", "activity_name", "activity_id", "user_id", "key"),
    )


class FieldLogEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    course_id: str = Field(index=True)
    activity_name: str = Field(index=True)
    activity_id: str = Field(index=True)
    user_id: str = Field(index=True)
    key: str = Field(index=True)
    entry_id: int
    value: str  # JSON-encoded

    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "activity_name",
            "activity_id",
            "user_id",
            "key",
            "entry_id",
        ),
    )


class FieldLogSeq(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    course_id: str = Field(index=True)
    activity_name: str = Field(index=True)
    activity_id: str = Field(index=True)
    user_id: str = Field(index=True)
    key: str = Field(index=True)
    next_id: int = Field(default=0)

    __table_args__ = (
        UniqueConstraint("course_id", "activity_name", "activity_id", "user_id", "key"),
    )


def _key_filter(
    stmt: Any,
    model: type[FieldEntry] | type[FieldLogEntry] | type[FieldLogSeq],
    course_id: str,
    activity_name: str,
    activity_id: str,
    user_id: str,
    key: str,
) -> Any:
    """Apply the 5-column key filter to a statement."""
    return (
        stmt.where(col(model.course_id) == course_id)
        .where(col(model.activity_name) == activity_name)
        .where(col(model.activity_id) == activity_id)
        .where(col(model.user_id) == user_id)
        .where(col(model.key) == key)
    )


class SQLiteFieldStore(FieldStore):
    """FieldStore backed by SQLite via SQLModel."""

    def get(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
    ) -> FieldType | None:
        with db.session_scope() as session:
            stmt = _key_filter(
                select(FieldEntry),
                FieldEntry,
                course_id,
                activity_name,
                activity_id,
                user_id,
                key,
            )
            entry = session.exec(stmt).first()
            if entry is None:
                return None
            result: FieldType = json.loads(entry.value)
            return result

    def set(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        value: FieldType,
    ) -> None:
        with db.session_scope() as session:
            stmt = _key_filter(
                select(FieldEntry),
                FieldEntry,
                course_id,
                activity_name,
                activity_id,
                user_id,
                key,
            )
            entry = session.exec(stmt).first()
            encoded = json.dumps(value)
            if entry is None:
                entry = FieldEntry(
                    course_id=course_id,
                    activity_name=activity_name,
                    activity_id=activity_id,
                    user_id=user_id,
                    key=key,
                    value=encoded,
                )
            else:
                entry.value = encoded
            session.add(entry)
            session.commit()

    def delete(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
    ) -> bool:
        with db.session_scope() as session:
            stmt = _key_filter(
                select(FieldEntry),
                FieldEntry,
                course_id,
                activity_name,
                activity_id,
                user_id,
                key,
            )
            entry = session.exec(stmt).first()
            if entry is None:
                return False
            session.delete(entry)
            session.commit()
            return True

    def keys(self) -> list[str]:
        with db.session_scope() as session:
            entries = session.exec(select(FieldEntry.key)).all()
            return list(entries)

    def log_get(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        entry_id: int,
    ) -> FieldType | None:
        with db.session_scope() as session:
            stmt = _key_filter(
                select(FieldLogEntry),
                FieldLogEntry,
                course_id,
                activity_name,
                activity_id,
                user_id,
                key,
            ).where(col(FieldLogEntry.entry_id) == entry_id)
            entry = session.exec(stmt).first()
            if entry is None:
                return None
            result: FieldType = json.loads(entry.value)
            return result

    def log_get_range(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        from_id: int,
        to_id: int,
    ) -> list[dict[str, Any]]:
        with db.session_scope() as session:
            stmt = (
                _key_filter(
                    select(FieldLogEntry),
                    FieldLogEntry,
                    course_id,
                    activity_name,
                    activity_id,
                    user_id,
                    key,
                )
                .where(
                    col(FieldLogEntry.entry_id) >= from_id,
                    col(FieldLogEntry.entry_id) < to_id,
                )
                .order_by(col(FieldLogEntry.entry_id))
            )
            entries = session.exec(stmt).all()
            return [{"id": e.entry_id, "value": json.loads(e.value)} for e in entries]

    def log_append(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        value: FieldType,
    ) -> int:
        with db.session_scope() as session:
            stmt = _key_filter(
                select(FieldLogSeq),
                FieldLogSeq,
                course_id,
                activity_name,
                activity_id,
                user_id,
                key,
            )
            seq = session.exec(stmt).first()
            if seq is None:
                seq = FieldLogSeq(
                    course_id=course_id,
                    activity_name=activity_name,
                    activity_id=activity_id,
                    user_id=user_id,
                    key=key,
                    next_id=0,
                )
            entry_id: int = seq.next_id
            seq.next_id = entry_id + 1
            session.add(seq)
            log_entry = FieldLogEntry(
                course_id=course_id,
                activity_name=activity_name,
                activity_id=activity_id,
                user_id=user_id,
                key=key,
                entry_id=entry_id,
                value=json.dumps(value),
            )
            session.add(log_entry)
            session.commit()
            return entry_id

    def log_delete(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        entry_id: int,
    ) -> bool:
        with db.session_scope() as session:
            stmt = _key_filter(
                select(FieldLogEntry),
                FieldLogEntry,
                course_id,
                activity_name,
                activity_id,
                user_id,
                key,
            ).where(col(FieldLogEntry.entry_id) == entry_id)
            entry = session.exec(stmt).first()
            if entry is None:
                return False
            session.delete(entry)
            session.commit()
            return True

    def log_delete_range(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        from_id: int,
        to_id: int,
    ) -> int:
        with db.session_scope() as session:
            stmt = _key_filter(
                select(FieldLogEntry),
                FieldLogEntry,
                course_id,
                activity_name,
                activity_id,
                user_id,
                key,
            ).where(
                col(FieldLogEntry.entry_id) >= from_id,
                col(FieldLogEntry.entry_id) < to_id,
            )
            entries = session.exec(stmt).all()
            count = len(entries)
            for entry in entries:
                session.delete(entry)
            if count > 0:
                session.commit()
            return count


def delete_fields_by(
    activity_id: str | None = None,
    activity_name: str | None = None,
    course_id: str | None = None,
) -> None:
    """Delete all field data for a given course/activity type/id."""
    with db.session_scope() as session:
        for model in (FieldEntry, FieldLogEntry, FieldLogSeq):
            select_filter = select(model)
            if course_id:
                select_filter = select_filter.where(col(model.course_id) == course_id)
            if activity_name:
                select_filter = select_filter.where(
                    col(model.activity_name) == activity_name
                )
            if activity_id:
                select_filter = select_filter.where(
                    col(model.activity_id) == activity_id
                )
            entries = session.exec(select_filter).all()
            for entry in entries:
                session.delete(entry)
        session.commit()


# ---------------------------------------------------------------------------
# Automatic field cleanup when activities are deleted via the ORM
# ---------------------------------------------------------------------------
# pylint: disable=wrong-import-position
from xpla.notebook.models import CourseActivity, PageActivity


def _on_activity_delete(_mapper: Any, connection: Any, target: Any) -> None:
    """Remove field store entries when an activity row is deleted."""
    for model in (FieldEntry, FieldLogEntry, FieldLogSeq):
        connection.execute(sa_delete(model).where(col(model.activity_id) == target.id))


event.listen(PageActivity, "after_delete", _on_activity_delete)
event.listen(CourseActivity, "after_delete", _on_activity_delete)
