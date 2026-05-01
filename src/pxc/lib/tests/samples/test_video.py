"""Tests for the video sample activity."""

from pxc.lib.permission import Permission
from pxc.lib.tests.samples.conftest import make_runtime


def test_get_state_defaults() -> None:
    rt = make_runtime("video")
    state = rt.get_state()
    assert state["video_url"] == ""


def test_config_save() -> None:
    rt = make_runtime("video", permission=Permission.edit)
    rt.on_action("config.save", {"video_url": "https://example.com/video.mp4"})
    state = rt.get_state()
    assert state["video_url"] == "https://example.com/video.mp4"


def test_config_save_emits_event() -> None:
    rt = make_runtime("video", permission=Permission.edit)
    rt.on_action("config.save", {"video_url": "https://example.com/v.mp4"})
    events = rt.clear_pending_events()
    names = [e["name"] for e in events]
    assert "fields.change.video_url" in names
