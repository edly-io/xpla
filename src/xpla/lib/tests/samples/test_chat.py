"""Tests for the chat sample activity."""

import json
from typing import Any

from xpla.lib.tests.samples.conftest import make_runtime


def test_get_state_defaults() -> None:
    rt = make_runtime("chat")
    state = rt.get_state()
    assert state["messages"] == []


def test_post_message() -> None:
    rt = make_runtime("chat")
    rt.on_action("chat.post", {"text": "Hello!"})
    state = rt.get_state()
    messages: list[Any] = state["messages"]  # type: ignore[assignment]
    assert len(messages) == 1
    assert messages[0]["value"]["text"] == "Hello!"


def test_post_emits_event() -> None:
    rt = make_runtime("chat")
    rt.on_action("chat.post", {"text": "Hi"})
    events = rt.clear_pending_events()
    chat_events = [e for e in events if e["name"] == "chat.new"]
    assert len(chat_events) == 1
    value = json.loads(chat_events[0]["value"])
    assert value["text"] == "Hi"


def test_multiple_messages() -> None:
    rt = make_runtime("chat")
    rt.on_action("chat.post", {"text": "First"})
    rt.on_action("chat.post", {"text": "Second"})
    state = rt.get_state()
    messages: list[Any] = state["messages"]  # type: ignore[assignment]
    assert len(messages) == 2


def test_messages_shared_across_users() -> None:
    rt = make_runtime("chat", user_id="alice")
    rt.on_action("chat.post", {"text": "Hello from Alice"})

    rt.user_id = "bob"
    state = rt.get_state()
    messages: list[Any] = state["messages"]  # type: ignore[assignment]
    assert len(messages) == 1
