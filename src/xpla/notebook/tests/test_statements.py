"""Tests for activity report statements persisted in the notebook app."""

import json
from pathlib import Path
from unittest.mock import patch

from sqlmodel import Session, col, select

from xpla.lib.permission import Permission
from xpla.notebook.models import ActivityStatement
from xpla.notebook.runtime import NotebookActivityRuntime
from xpla.notebook.tests.conftest import _make_engine


def _make_notebook_runtime(tmp_path: Path, engine: object) -> NotebookActivityRuntime:
    """Create a NotebookActivityRuntime backed by an in-memory DB."""
    activity_dir = tmp_path / "activity"
    activity_dir.mkdir()
    manifest = {"name": "test-activity", "client": "client.js", "capabilities": {}}
    (activity_dir / "manifest.json").write_text(json.dumps(manifest))

    with patch("xpla.notebook.runtime.engine", engine):
        return NotebookActivityRuntime(
            activity_dir,
            activity_id="a1",
            course_id="c1",
            user_id="u1",
            permission=Permission.play,
        )


class TestActivityStatements:
    def test_report_completed(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.runtime.engine", engine):
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
        with patch("xpla.notebook.runtime.engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine)
            rt.report_passed(0.85)
        with Session(engine) as session:
            rows = session.exec(select(ActivityStatement)).all()
            assert len(rows) == 1
            assert rows[0].verb == "passed"
            assert rows[0].score == 0.85

    def test_report_passed_without_score(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.runtime.engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine)
            rt.report_passed(None)
        with Session(engine) as session:
            rows = session.exec(select(ActivityStatement)).all()
            assert len(rows) == 1
            assert rows[0].verb == "passed"
            assert rows[0].score is None

    def test_report_failed(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.runtime.engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine)
            rt.report_failed(0.3)
        with Session(engine) as session:
            rows = session.exec(select(ActivityStatement)).all()
            assert len(rows) == 1
            assert rows[0].verb == "failed"
            assert rows[0].score == 0.3

    def test_report_progressed(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.runtime.engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine)
            rt.report_progressed(0.5)
        with Session(engine) as session:
            rows = session.exec(select(ActivityStatement)).all()
            assert len(rows) == 1
            assert rows[0].verb == "progressed"
            assert rows[0].score == 0.5

    def test_report_scored(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.runtime.engine", engine):
            rt = _make_notebook_runtime(tmp_path, engine)
            rt.report_scored(0.75)
        with Session(engine) as session:
            rows = session.exec(select(ActivityStatement)).all()
            assert len(rows) == 1
            assert rows[0].verb == "scored"
            assert rows[0].score == 0.75

    def test_multiple_statements(self, tmp_path: Path) -> None:
        engine = _make_engine()
        with patch("xpla.notebook.runtime.engine", engine):
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
