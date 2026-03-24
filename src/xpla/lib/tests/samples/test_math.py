"""Tests for the math sample activity."""

import json

from xpla.lib.tests.samples.conftest import make_runtime


def test_get_state_defaults() -> None:
    rt = make_runtime("math")
    state = rt.get_state()
    assert state["correct_answers"] == 0
    assert state["wrong_answers"] == 0


def test_correct_answer() -> None:
    rt = make_runtime("math")
    rt.on_action("answer.submit", {"question": "2+2", "answer": "4"})
    events = rt.clear_pending_events()
    result_events = [e for e in events if e["name"] == "answer.result"]
    assert len(result_events) == 1
    result = json.loads(result_events[0]["value"])
    assert result["correct"] is True


def test_wrong_answer() -> None:
    rt = make_runtime("math")
    rt.on_action("answer.submit", {"question": "2+2", "answer": "5"})
    events = rt.clear_pending_events()
    result_events = [e for e in events if e["name"] == "answer.result"]
    assert len(result_events) == 1
    result = json.loads(result_events[0]["value"])
    assert result["correct"] is False


def test_score_increments() -> None:
    rt = make_runtime("math")
    rt.on_action("answer.submit", {"question": "2+2", "answer": "4"})
    rt.on_action("answer.submit", {"question": "3+3", "answer": "6"})
    rt.on_action("answer.submit", {"question": "1+1", "answer": "3"})

    state = rt.get_state()
    assert state["correct_answers"] == 2
    assert state["wrong_answers"] == 1


def test_scores_are_per_user() -> None:
    rt = make_runtime("math", user_id="alice")
    rt.on_action("answer.submit", {"question": "2+2", "answer": "4"})

    rt.user_id = "bob"
    state = rt.get_state()
    assert state["correct_answers"] == 0

    rt.user_id = "alice"
    state = rt.get_state()
    assert state["correct_answers"] == 1
