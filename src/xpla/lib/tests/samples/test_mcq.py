"""Tests for the mcq sample activity."""

import json

from xpla.lib.permission import Permission
from xpla.lib.tests.samples.conftest import make_runtime


def test_get_state_defaults() -> None:
    rt = make_runtime("mcq")
    state = rt.get_state()
    assert state["question"] == ""
    assert state["answers"] == []


def test_config_save() -> None:
    rt = make_runtime("mcq", permission=Permission.edit)
    rt.on_action(
        "config.save",
        {
            "question": "What is 2+2?",
            "answers": ["3", "4", "5"],
            "correct_answers": [1],
        },
    )
    state = rt.get_state()
    assert state["question"] == "What is 2+2?"
    assert state["answers"] == ["3", "4", "5"]


def test_answer_submit_correct() -> None:
    rt = make_runtime("mcq", permission=Permission.edit)
    rt.on_action(
        "config.save",
        {
            "question": "What is 2+2?",
            "answers": ["3", "4", "5"],
            "correct_answers": [1],
        },
    )
    rt.clear_pending_events()

    rt.permission = Permission.play
    rt.on_action("answer.submit", [1])
    events = rt.clear_pending_events()
    result_events = [e for e in events if e["name"] == "answer.result"]
    assert len(result_events) == 1
    result = json.loads(result_events[0]["value"])
    assert result["correct"] is True


def test_answer_submit_incorrect() -> None:
    rt = make_runtime("mcq", permission=Permission.edit)
    rt.on_action(
        "config.save",
        {
            "question": "What is 2+2?",
            "answers": ["3", "4", "5"],
            "correct_answers": [1],
        },
    )
    rt.clear_pending_events()

    rt.permission = Permission.play
    rt.on_action("answer.submit", [0])
    events = rt.clear_pending_events()
    result_events = [e for e in events if e["name"] == "answer.result"]
    assert len(result_events) == 1
    result = json.loads(result_events[0]["value"])
    assert result["correct"] is False


def test_play_state_hides_correct_answers() -> None:
    rt = make_runtime("mcq", permission=Permission.edit)
    rt.on_action(
        "config.save",
        {
            "question": "Q?",
            "answers": ["A", "B"],
            "correct_answers": [0],
        },
    )

    rt.permission = Permission.play
    state = rt.get_state()
    # In play mode, correct_answers should be hidden
    assert "correct_answers" not in state
