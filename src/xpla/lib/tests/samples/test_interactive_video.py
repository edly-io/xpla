"""Tests for the interactive-video sample activity."""

import json

from xpla.lib.permission import Permission
from xpla.lib.tests.samples.conftest import make_runtime

INTERACTIONS = [
    {
        "time": 10.0,
        "question": "What color is the sky?",
        "answers": ["Red", "Blue", "Green"],
        "correct_answers": [1],
    }
]


def test_get_state_defaults() -> None:
    rt = make_runtime("interactive-video")
    state = rt.get_state()
    assert state["video_id"] == ""
    assert state["interactions"] == []


def test_config_save() -> None:
    rt = make_runtime("interactive-video", permission=Permission.edit)
    rt.on_action(
        "config.save",
        {"video_id": "abc123", "interactions": INTERACTIONS},
    )
    state = rt.get_state()
    assert state["video_id"] == "abc123"
    interactions: list[dict[str, object]] = state["interactions"]  # type: ignore[assignment]
    assert len(interactions) == 1


def test_answer_submit_correct() -> None:
    rt = make_runtime("interactive-video", permission=Permission.edit)
    rt.on_action(
        "config.save",
        {"video_id": "v1", "interactions": INTERACTIONS},
    )
    rt.clear_pending_events()

    rt.permission = Permission.play
    rt.on_action("answer.submit", {"index": 0, "selected": [1]})
    events = rt.clear_pending_events()
    result_events = [e for e in events if e["name"] == "answer.result"]
    assert len(result_events) == 1
    result = json.loads(result_events[0]["value"])
    assert result["correct"] is True


def test_answer_submit_incorrect() -> None:
    rt = make_runtime("interactive-video", permission=Permission.edit)
    rt.on_action(
        "config.save",
        {"video_id": "v1", "interactions": INTERACTIONS},
    )
    rt.clear_pending_events()

    rt.permission = Permission.play
    rt.on_action("answer.submit", {"index": 0, "selected": [0]})
    events = rt.clear_pending_events()
    result_events = [e for e in events if e["name"] == "answer.result"]
    assert len(result_events) == 1
    result = json.loads(result_events[0]["value"])
    assert result["correct"] is False
