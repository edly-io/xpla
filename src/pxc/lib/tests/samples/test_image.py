"""Tests for the image sample activity."""

import base64

from pxc.lib.permission import Permission
from pxc.lib.tests.samples.conftest import make_runtime


def test_get_state_defaults() -> None:
    rt = make_runtime("image")
    state = rt.get_state()
    assert state["image_filename"] == ""


def test_image_upload() -> None:
    rt = make_runtime("image", permission=Permission.edit)
    # Create a small PNG-like base64 payload
    pixel_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    b64 = base64.b64encode(pixel_data).decode()
    data_url = f"data:image/png;base64,{b64}"

    rt.on_action("image.upload", {"data": data_url})
    state = rt.get_state()
    assert state["image_filename"] != ""

    events = rt.clear_pending_events()
    image_events = [e for e in events if e["name"] == "image.changed"]
    assert len(image_events) == 1
