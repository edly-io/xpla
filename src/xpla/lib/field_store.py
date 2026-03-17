"""FieldStore — abstract base class for field persistence."""

from abc import ABC, abstractmethod
from typing import Any

from xpla.lib.fields import FieldType


class FieldStore(ABC):
    """Abstract base class for storing scalar and log field data."""

    # Scalar fields
    @abstractmethod
    def get(
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
    ) -> FieldType | None: ...

    @abstractmethod
    def set(
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        value: FieldType,
    ) -> None: ...

    @abstractmethod
    def delete(
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
    ) -> bool: ...

    @abstractmethod
    def keys(self) -> list[str]: ...

    # Log fields
    @abstractmethod
    def log_get(
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        entry_id: int,
    ) -> FieldType | None: ...

    @abstractmethod
    def log_get_range(
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        from_id: int,
        to_id: int,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    def log_append(
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        value: FieldType,
    ) -> int: ...

    @abstractmethod
    def log_delete(
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        entry_id: int,
    ) -> bool: ...

    @abstractmethod
    def log_delete_range(
        self,
        course_id: str,
        activity_name: str,
        activity_id: str,
        user_id: str,
        key: str,
        from_id: int,
        to_id: int,
    ) -> int: ...
