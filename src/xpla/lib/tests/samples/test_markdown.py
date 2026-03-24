"""Tests for the markdown sample activity.

Skipped if server.component.wasm is not built.
"""

import pytest

from xpla.lib.permission import Permission
from xpla.lib.tests.samples.conftest import SAMPLES_DIR, make_runtime

WASM_MISSING = not (SAMPLES_DIR / "markdown" / "server.component.wasm").exists()
skip_if_no_wasm = pytest.mark.skipif(WASM_MISSING, reason="WASM not built")


@skip_if_no_wasm
def test_get_state_defaults() -> None:
    rt = make_runtime("markdown")
    state = rt.get_state()
    assert state["markdown_content"] == ""
    assert state["rendered_html"] == ""


@skip_if_no_wasm
def test_config_save() -> None:
    rt = make_runtime("markdown", permission=Permission.edit)
    rt.on_action("config.save", {"markdown_content": "# Hello"})
    state = rt.get_state()
    assert state["markdown_content"] == "# Hello"


@skip_if_no_wasm
def test_config_save_renders_html() -> None:
    rt = make_runtime("markdown", permission=Permission.edit)
    rt.on_action("config.save", {"markdown_content": "# Title"})
    state = rt.get_state()
    rendered: str = state["rendered_html"]  # type: ignore[assignment]
    assert "<h" in rendered
