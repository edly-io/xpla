"""
LMS simulation for development and testing.

Provides mock user identity, grade storage, and progress tracking.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class User:
    """Simulated LMS user."""

    id: str
    name: str
    email: str
    roles: list[str] = field(default_factory=lambda: ["student"])


@dataclass
class GradeRecord:
    """A grade submission record."""

    user_id: str
    activity_id: str
    score: float
    max_score: float
    timestamp: datetime
    comment: str = ""

    def to_dict(self) -> dict[str, object]:
        """Convert to JSON-serializable dict."""
        return {
            "user_id": self.user_id,
            "activity_id": self.activity_id,
            "score": self.score,
            "max_score": self.max_score,
            "timestamp": self.timestamp.isoformat(),
            "comment": self.comment,
        }


class LMSSimulator:
    """Mock LMS for development.

    Stores grades to disk in the activity directory.
    """

    def __init__(self, activity_dir: Path, activity_id: str) -> None:
        """Initialize the LMS simulator.

        Args:
            activity_dir: Path to store grade data.
            activity_id: ID of the current activity.
        """
        self._activity_dir = activity_dir
        self._activity_id = activity_id
        self._grades_path = activity_dir / "grades.json"
        self._current_user = User(
            id="user-001",
            name="Test Student",
            email="student@example.com",
        )
        self._grades: list[GradeRecord] = []
        self._load_grades()

    def _load_grades(self) -> None:
        """Load grades from disk."""
        if self._grades_path.exists():
            with self._grades_path.open() as f:
                data = json.load(f)
                for record in data:
                    self._grades.append(
                        GradeRecord(
                            user_id=record["user_id"],
                            activity_id=record["activity_id"],
                            score=record["score"],
                            max_score=record["max_score"],
                            timestamp=datetime.fromisoformat(record["timestamp"]),
                            comment=record.get("comment", ""),
                        )
                    )

    def _save_grades(self) -> None:
        """Save grades to disk."""
        with self._grades_path.open("w") as f:
            json.dump([g.to_dict() for g in self._grades], f, indent=2)

    def get_current_user(self) -> User:
        """Get the current user."""
        return self._current_user

    def set_current_user(self, user: User) -> None:
        """Set the current user (for testing)."""
        self._current_user = user

    def submit_grade(
        self,
        score: float,
        max_score: float = 100.0,
        comment: str = "",
    ) -> GradeRecord:
        """Submit a grade for the current user."""
        record = GradeRecord(
            user_id=self._current_user.id,
            activity_id=self._activity_id,
            score=score,
            max_score=max_score,
            timestamp=datetime.now(),
            comment=comment,
        )
        self._grades.append(record)
        self._save_grades()
        return record

    def get_grades(self, user_id: str | None = None) -> list[GradeRecord]:
        """Get grades, optionally filtered by user."""
        if user_id is None:
            return [g for g in self._grades if g.activity_id == self._activity_id]
        return [
            g
            for g in self._grades
            if g.activity_id == self._activity_id and g.user_id == user_id
        ]

    def get_best_grade(self, user_id: str | None = None) -> GradeRecord | None:
        """Get the best grade for a user."""
        grades = self.get_grades(user_id or self._current_user.id)
        if not grades:
            return None
        return max(grades, key=lambda g: g.score / g.max_score)
