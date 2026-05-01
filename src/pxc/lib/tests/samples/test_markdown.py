"""Tests for the markdown sample activity."""

from pxc.lib.permission import Permission
from pxc.lib.tests.samples.conftest import make_runtime


def test_get_state_defaults() -> None:
    rt = make_runtime("markdown")
    state = rt.get_state()
    assert "markdown_content" not in state
    assert state["rendered_html"] == ""


def test_config_save() -> None:
    rt = make_runtime("markdown", permission=Permission.edit)
    rt.on_action("config.save", {"markdown_content": "# Hello"})
    state = rt.get_state()
    assert state["markdown_content"] == "# Hello"


def test_config_save_renders_html() -> None:
    rt = make_runtime("markdown", permission=Permission.edit)
    rt.on_action("config.save", {"markdown_content": "# Title"})
    state = rt.get_state()
    rendered: str = state["rendered_html"]  # type: ignore[assignment]
    assert "<h" in rendered
