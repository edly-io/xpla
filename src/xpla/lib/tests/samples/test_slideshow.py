"""Tests for the slideshow sample activity."""

from xpla.lib.permission import Permission
from xpla.lib.tests.samples.conftest import make_runtime


def test_get_state_defaults() -> None:
    rt = make_runtime("slideshow")
    state = rt.get_state()
    assert state["slides_html"] == ""


def test_config_save() -> None:
    rt = make_runtime("slideshow", permission=Permission.edit)
    html = "<section><h1>Slide 1</h1></section>"
    rt.on_action("config.save", {"slides_html": html})
    state = rt.get_state()
    assert state["slides_html"] == html


def test_config_save_emits_event() -> None:
    rt = make_runtime("slideshow", permission=Permission.edit)
    rt.on_action("config.save", {"slides_html": "<section>Hi</section>"})
    events = rt.clear_pending_events()
    names = [e["name"] for e in events]
    assert "fields.change.slides_html" in names
