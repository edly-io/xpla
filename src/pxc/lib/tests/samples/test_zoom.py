"""Tests for the zoom sample activity."""

from pxc.lib.permission import Permission
from pxc.lib.tests.samples.conftest import make_runtime


def test_get_state_play_mode() -> None:
    rt = make_runtime("zoom")
    state = rt.get_state()
    # Play mode shows a subset of fields
    assert state["topic"] == ""
    assert state["duration"] == 60
    assert state["timezone"] == "UTC"
    assert state["join_url"] == ""


def test_get_state_edit_mode() -> None:
    rt = make_runtime("zoom", permission=Permission.edit)
    state = rt.get_state()
    assert "topic" in state
    assert "credentials_configured" in state
    assert state["credentials_configured"] is False


def test_credentials_save() -> None:
    rt = make_runtime("zoom", permission=Permission.edit)
    rt.on_action(
        "credentials.save",
        {
            "zoom_account_id": "acc123",
            "zoom_client_id": "cli456",
            "zoom_client_secret": "sec789",
        },
    )
    state = rt.get_state()
    assert state["credentials_configured"] is True
