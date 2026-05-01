"""Tests for activity report statements persisted in the notebook app."""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from sqlmodel import Session, col, select

from xpla.lib.permission import Permission
from xpla.notebook.models import ActivityStatement
from xpla.notebook.views.course_activities import (
    find_course_activity_dir,
    list_course_activity_types,
)
from xpla.notebook.runtime import NotebookActivityRuntime
from xpla.notebook.tests.conftest import _make_engine


def _make_notebook_runtime(
    tmp_path: Path,
    engine: object,
    *,
    is_course_activity: bool = False,
    activity_id: str = "a1",
    course_id: str = "c1",
    user_id: str = "u1",
) -> NotebookActivityRuntime:
    """Create a NotebookActivityRuntime backed by an in-memory DB."""
    activity_dir = tmp_path / "activity"
    activity_dir.mkdir(exist_ok=True)
    capabilities: dict[str, object] = {}
    manifest = {"name": "test-activity", "ui": "ui.js", "capabilities": capabilities}
    (activity_dir / "manifest.json").write_text(json.dumps(manifest))

    with patch("xpla.notebook.db._engine", engine):
        return NotebookActivityRuntime(
            activity_dir,
            activity_id=activity_id,
            course_id=course_id,
            user_id=user_id,
            permission=Permission.play,
            is_course_activity=is_course_activity,
        )


class TestActivityStatements:
    def test_report_completed(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine)
            rt.report_completed()
        with Session(engine) as session:
            rows = session.exec(select(ActivityStatement)).all()
            assert len(rows) == 1
            assert rows[0].verb == "completed"
            assert rows[0].score is None
            assert rows[0].user_id == "u1"
            assert rows[0].activity_id == "a1"
            assert rows[0].course_id == "c1"
            assert rows[0].activity_name == "test-activity"

    def test_report_passed_with_score(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine)
            rt.report_passed(0.85)
        with Session(engine) as session:
            rows = session.exec(select(ActivityStatement)).all()
            assert len(rows) == 1
            assert rows[0].verb == "passed"
            assert rows[0].score == 0.85

    def test_report_passed_without_score(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine)
            rt.report_passed(None)
        with Session(engine) as session:
            rows = session.exec(select(ActivityStatement)).all()
            assert len(rows) == 1
            assert rows[0].verb == "passed"
            assert rows[0].score is None

    def test_report_failed(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine)
            rt.report_failed(0.3)
        with Session(engine) as session:
            rows = session.exec(select(ActivityStatement)).all()
            assert len(rows) == 1
            assert rows[0].verb == "failed"
            assert rows[0].score == 0.3

    def test_report_progressed(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine)
            rt.report_progressed(0.5)
        with Session(engine) as session:
            rows = session.exec(select(ActivityStatement)).all()
            assert len(rows) == 1
            assert rows[0].verb == "progressed"
            assert rows[0].score == 0.5

    def test_report_scored(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine)
            rt.report_scored(0.75)
        with Session(engine) as session:
            rows = session.exec(select(ActivityStatement)).all()
            assert len(rows) == 1
            assert rows[0].verb == "scored"
            assert rows[0].score == 0.75

    def test_multiple_statements(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine)
            rt.report_progressed(0.5)
            rt.report_completed()
            rt.report_passed(0.9)
        with Session(engine) as session:
            rows = session.exec(
                select(ActivityStatement).order_by(col(ActivityStatement.id))
            ).all()
            assert len(rows) == 3
            assert [r.verb for r in rows] == ["progressed", "completed", "passed"]


class TestReportQuery:
    def _setup(self, tmp_path: Path, engine: object) -> NotebookActivityRuntime:
        """Create a course-activity runtime and seed some statements."""
        rt = _make_notebook_runtime(tmp_path, engine, is_course_activity=True)
        rt.report_completed()
        rt.report_passed(0.8)
        rt.report_failed(0.3)
        return rt

    def test_empty_result(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine, is_course_activity=True)
            results = json.loads(rt.report_query("{}"))
        assert results == []

    def test_returns_all_course_statements(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = self._setup(tmp_path, engine)
            results = json.loads(rt.report_query("{}"))
        assert len(results) == 3
        assert [r["verb"] for r in results] == ["completed", "passed", "failed"]

    def test_filter_by_verb(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = self._setup(tmp_path, engine)
            results = json.loads(rt.report_query('{"verb": "passed"}'))
        assert len(results) == 1
        assert results[0]["verb"] == "passed"
        assert results[0]["score"] == 0.8

    def test_filter_by_user_id(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = self._setup(tmp_path, engine)
            results = json.loads(rt.report_query('{"user_id": "u1"}'))
            assert len(results) == 3
            results = json.loads(rt.report_query('{"user_id": "other"}'))
            assert len(results) == 0

    def test_filter_by_activity_id(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = self._setup(tmp_path, engine)
            results = json.loads(rt.report_query('{"activity_id": "a1"}'))
            assert len(results) == 3
            results = json.loads(rt.report_query('{"activity_id": "other"}'))
            assert len(results) == 0

    def test_filter_by_activity_name(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = self._setup(tmp_path, engine)
            results = json.loads(rt.report_query('{"activity_name": "test-activity"}'))
            assert len(results) == 3
            results = json.loads(rt.report_query('{"activity_name": "other"}'))
            assert len(results) == 0

    def test_course_scoping(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt_c1 = _make_notebook_runtime(
                tmp_path, engine, is_course_activity=True, course_id="c1"
            )
            rt_c1.report_completed()
            rt_c2 = _make_notebook_runtime(
                tmp_path, engine, is_course_activity=True, course_id="c2"
            )
            rt_c2.report_passed(0.9)
            # c1 should only see its own statement
            results = json.loads(rt_c1.report_query("{}"))
            assert len(results) == 1
            assert results[0]["verb"] == "completed"
            # c2 should only see its own statement
            results = json.loads(rt_c2.report_query("{}"))
            assert len(results) == 1
            assert results[0]["verb"] == "passed"

    def test_pagination_after_id(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = self._setup(tmp_path, engine)
            all_results = json.loads(rt.report_query("{}"))
            first_id = all_results[0]["id"]
            results = json.loads(rt.report_query(json.dumps({"after_id": first_id})))
            assert len(results) == 2
            assert all(r["id"] > first_id for r in results)

    def test_pagination_limit(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = self._setup(tmp_path, engine)
            results = json.loads(rt.report_query('{"limit": 2}'))
            assert len(results) == 2

    def test_not_registered_for_page_activity(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine, is_course_activity=False)
            assert "analytics" not in rt.host_functions()

    def test_registered_for_course_activity(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine, is_course_activity=True)
            assert "report-query" in rt.host_functions()["analytics"]

    def test_filter_before_date(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine, is_course_activity=True)
            rt.report_completed()
        # Set the created_at to a known time for testing
        with Session(engine) as session:
            row = session.exec(select(ActivityStatement)).one()
            row.created_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
            session.add(row)
            session.commit()
        with patch("xpla.notebook.db._engine", engine):
            # before_date excludes the row
            results = json.loads(
                rt.report_query('{"before_date": "2026-01-01T00:00:00+00:00"}')
            )
            assert len(results) == 0
            # before_date includes the row
            results = json.loads(
                rt.report_query('{"before_date": "2026-02-01T00:00:00+00:00"}')
            )
            assert len(results) == 1

    def test_filter_after_date(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.db._engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine, is_course_activity=True)
            rt.report_completed()
        with Session(engine) as session:
            row = session.exec(select(ActivityStatement)).one()
            row.created_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
            session.add(row)
            session.commit()
        with patch("xpla.notebook.db._engine", engine):
            # after_date excludes the row
            results = json.loads(
                rt.report_query('{"after_date": "2026-02-01T00:00:00+00:00"}')
            )
            assert len(results) == 0
            # after_date includes the row
            results = json.loads(
                rt.report_query('{"after_date": "2026-01-01T00:00:00+00:00"}')
            )
            assert len(results) == 1


class TestCourseActivityDiscovery:
    def test_list_includes_builtin_samples(self) -> None:
        types = list_course_activity_types("nonexistent-user")
        assert "reports" in types

    def test_find_builtin_course_activity(self) -> None:
        activity_dir = find_course_activity_dir("reports")
        assert (activity_dir / "manifest.json").exists()
