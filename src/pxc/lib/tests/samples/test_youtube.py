"""Tests for the youtube sample activity."""

from pxc.lib.permission import Permission
from pxc.lib.tests.samples.conftest import make_runtime


def test_get_state_defaults() -> None:
    rt = make_runtime("youtube")
    state = rt.get_state()
    assert state["video_id"] == ""


def test_get_state_edit_mode() -> None:
    rt = make_runtime("youtube", permission=Permission.edit)
    state = rt.get_state()
    assert "video_id" in state


def test_config_save() -> None:
    rt = make_runtime("youtube", permission=Permission.edit)
    rt.on_action("config.save", {"video_id": "dQw4w9WgXcQ"})
    state = rt.get_state()
    assert state["video_id"] == "dQw4w9WgXcQ"


def test_config_save_emits_event() -> None:
    rt = make_runtime("youtube", permission=Permission.edit)
    rt.on_action("config.save", {"video_id": "abc123"})
    events = rt.clear_pending_events()
    names = [e["name"] for e in events]
    assert "fields.change.video_id" in names
