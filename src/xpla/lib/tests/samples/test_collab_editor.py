"""Tests for the collab-editor sample activity."""

from xpla.lib.permission import Permission
from xpla.lib.tests.samples.conftest import make_runtime


def test_get_state_defaults() -> None:
    rt = make_runtime("collab-editor")
    state = rt.get_state()
    assert state["content"] == ""
    assert state["render_markdown"] == 0


def test_config_save() -> None:
    rt = make_runtime("collab-editor", permission=Permission.edit)
    rt.on_action("config.save", {"render_markdown": 1})
    state = rt.get_state()
    assert state["render_markdown"] == 1


def test_config_save_emits_event() -> None:
    rt = make_runtime("collab-editor", permission=Permission.edit)
    rt.on_action("config.save", {"render_markdown": 1})
    events = rt.clear_pending_events()
    names = [e["name"] for e in events]
    assert "fields.change.render_markdown" in names
