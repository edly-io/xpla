"""SQLite-backed FieldStore implementation for xpln."""

import json
from typing import Any

from sqlmodel import Field, Session, SQLModel, select

from xpla.fields import FieldType
from xpln.db import engine


class FieldEntry(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str  # JSON-encoded


class FieldLogEntry(SQLModel, table=True):
    key: str = Field(primary_key=True)
    entry_id: int = Field(primary_key=True)
    value: str  # JSON-encoded


class FieldLogSeq(SQLModel, table=True):
    key: str = Field(primary_key=True)
    next_id: int = Field(default=0)


class SQLiteFieldStore:
    """FieldStore backed by SQLite via SQLModel."""

    def get(self, key: str) -> FieldType | None:
        with Session(engine) as session:
            entry = session.get(FieldEntry, key)
            if entry is None:
                return None
            result: FieldType = json.loads(entry.value)
            return result

    def set(self, key: str, value: FieldType) -> None:
        with Session(engine) as session:
            entry = session.get(FieldEntry, key)
            encoded = json.dumps(value)
            if entry is None:
                entry = FieldEntry(key=key, value=encoded)
            else:
                entry.value = encoded
            session.add(entry)
            session.commit()

    def delete(self, key: str) -> bool:
        with Session(engine) as session:
            entry = session.get(FieldEntry, key)
            if entry is None:
                return False
            session.delete(entry)
            session.commit()
            return True

    def keys(self) -> list[str]:
        with Session(engine) as session:
            entries = session.exec(select(FieldEntry.key)).all()
            return list(entries)

    def log_get(self, key: str, entry_id: int) -> FieldType | None:
        with Session(engine) as session:
            entry = session.get(FieldLogEntry, (key, entry_id))
            if entry is None:
                return None
            result: FieldType = json.loads(entry.value)
            return result

    def log_get_range(self, key: str, from_id: int, to_id: int) -> list[dict[str, Any]]:
        with Session(engine) as session:
            stmt = (
                select(FieldLogEntry)
                .where(FieldLogEntry.key == key)
                .where(FieldLogEntry.entry_id >= from_id)
                .where(FieldLogEntry.entry_id < to_id)
                .order_by(FieldLogEntry.entry_id)  # type: ignore[arg-type]
            )
            entries = session.exec(stmt).all()
            return [{"id": e.entry_id, "value": json.loads(e.value)} for e in entries]

    def log_append(self, key: str, value: FieldType) -> int:
        with Session(engine) as session:
            seq = session.get(FieldLogSeq, key)
            if seq is None:
                seq = FieldLogSeq(key=key, next_id=0)
            entry_id = seq.next_id
            seq.next_id = entry_id + 1
            session.add(seq)
            log_entry = FieldLogEntry(
                key=key, entry_id=entry_id, value=json.dumps(value)
            )
            session.add(log_entry)
            session.commit()
            return entry_id

    def log_delete(self, key: str, entry_id: int) -> bool:
        with Session(engine) as session:
            entry = session.get(FieldLogEntry, (key, entry_id))
            if entry is None:
                return False
            session.delete(entry)
            session.commit()
            return True

    def log_delete_range(self, key: str, from_id: int, to_id: int) -> int:
        with Session(engine) as session:
            stmt = (
                select(FieldLogEntry)
                .where(FieldLogEntry.key == key)
                .where(FieldLogEntry.entry_id >= from_id)
                .where(FieldLogEntry.entry_id < to_id)
            )
            entries = session.exec(stmt).all()
            count = len(entries)
            for entry in entries:
                session.delete(entry)
            if count > 0:
                session.commit()
            return count
