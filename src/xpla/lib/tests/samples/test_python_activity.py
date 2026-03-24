"""Tests for the python sample activity."""

from xpla.lib.permission import Permission
from xpla.lib.tests.samples.conftest import make_runtime


def test_get_state_defaults() -> None:
    rt = make_runtime("python")
    state = rt.get_state()
    assert state["instructions"] == ""
    assert state["test_code"] == ""
    assert state["starter_code"] == ""
    assert state["user_code"] == ""


def test_config_save() -> None:
    rt = make_runtime("python", permission=Permission.edit)
    rt.on_action(
        "config.save",
        {
            "instructions": "Write a function",
            "test_code": "assert add(1,2)==3",
            "starter_code": "def add(a, b):\n    pass",
        },
    )
    state = rt.get_state()
    assert state["instructions"] == "Write a function"
    assert state["test_code"] == "assert add(1,2)==3"
    assert state["starter_code"] == "def add(a, b):\n    pass"


def test_config_save_emits_events() -> None:
    rt = make_runtime("python", permission=Permission.edit)
    rt.on_action(
        "config.save",
        {
            "instructions": "Do something",
            "test_code": "",
            "starter_code": "",
        },
    )
    events = rt.clear_pending_events()
    names = {e["name"] for e in events}
    assert "fields.change.instructions" in names


def test_user_code_per_user() -> None:
    rt = make_runtime("python", user_id="alice")
    rt.on_action("code.run", {"code": "print('hello')"})
    rt.clear_pending_events()

    # user_code is user,activity scoped — different users have different code
    rt_bob = make_runtime("python", user_id="bob")
    state = rt_bob.get_state()
    assert state["user_code"] == ""
