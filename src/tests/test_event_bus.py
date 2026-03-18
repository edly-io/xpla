"""Tests for EventBus context/permission matching and event routing."""

import asyncio
from unittest.mock import AsyncMock

from xpla.lib.event_bus import (
    EventBus,
    _has_permission,
    _matches_context,
    Subscriber,
)
from xpla.lib.permission import Permission


def _make_subscriber(
    user_id: str = "alice",
    permission: Permission = Permission.play,
    course_id: str = "course1",
    activity_id: str = "activity1",
) -> Subscriber:
    ws = AsyncMock()
    return Subscriber(
        websocket=ws,
        user_id=user_id,
        permission=permission,
        course_id=course_id,
        activity_id=activity_id,
    )


class TestMatchesContext:
    """Tests for context matching logic."""

    def test_empty_context_matches_all(self) -> None:
        sub = _make_subscriber()
        assert _matches_context(sub, {})

    def test_matching_activity_id(self) -> None:
        sub = _make_subscriber(activity_id="act1")
        assert _matches_context(sub, {"activity_id": "act1"})

    def test_non_matching_activity_id(self) -> None:
        sub = _make_subscriber(activity_id="act1")
        assert not _matches_context(sub, {"activity_id": "act2"})

    def test_matching_course_id(self) -> None:
        sub = _make_subscriber(course_id="c1")
        assert _matches_context(sub, {"course_id": "c1"})

    def test_non_matching_course_id(self) -> None:
        sub = _make_subscriber(course_id="c1")
        assert not _matches_context(sub, {"course_id": "c2"})

    def test_matching_user_id(self) -> None:
        sub = _make_subscriber(user_id="alice")
        assert _matches_context(sub, {"user_id": "alice"})

    def test_non_matching_user_id(self) -> None:
        sub = _make_subscriber(user_id="alice")
        assert not _matches_context(sub, {"user_id": "bob"})

    def test_multiple_dimensions_all_match(self) -> None:
        sub = _make_subscriber(activity_id="a1", course_id="c1", user_id="alice")
        assert _matches_context(
            sub, {"activity_id": "a1", "course_id": "c1", "user_id": "alice"}
        )

    def test_multiple_dimensions_partial_mismatch(self) -> None:
        sub = _make_subscriber(activity_id="a1", course_id="c1", user_id="alice")
        assert not _matches_context(sub, {"activity_id": "a1", "user_id": "bob"})


class TestHasPermission:
    """Tests for permission level checking."""

    def test_view_receives_view_events(self) -> None:
        sub = _make_subscriber(permission=Permission.view)
        assert _has_permission(sub, "view")

    def test_view_does_not_receive_play_events(self) -> None:
        sub = _make_subscriber(permission=Permission.view)
        assert not _has_permission(sub, "play")

    def test_play_receives_play_events(self) -> None:
        sub = _make_subscriber(permission=Permission.play)
        assert _has_permission(sub, "play")

    def test_play_receives_view_events(self) -> None:
        sub = _make_subscriber(permission=Permission.play)
        assert _has_permission(sub, "view")

    def test_play_does_not_receive_edit_events(self) -> None:
        sub = _make_subscriber(permission=Permission.play)
        assert not _has_permission(sub, "edit")

    def test_edit_receives_all_events(self) -> None:
        sub = _make_subscriber(permission=Permission.edit)
        assert _has_permission(sub, "view")
        assert _has_permission(sub, "play")
        assert _has_permission(sub, "edit")


class TestEventBus:
    """Tests for EventBus subscribe/unsubscribe/publish."""

    def test_subscribe_and_unsubscribe(self) -> None:
        bus = EventBus()
        sub = bus.subscribe("chat", AsyncMock(), "alice", Permission.play, "c1", "a1")
        assert len(bus._subscribers["chat"]) == 1  # pylint: disable=protected-access
        bus.unsubscribe("chat", sub)
        assert len(bus._subscribers["chat"]) == 0  # pylint: disable=protected-access

    def test_unsubscribe_nonexistent_is_noop(self) -> None:
        bus = EventBus()
        sub = _make_subscriber()
        bus.unsubscribe("chat", sub)  # should not raise

    def test_publish_sends_to_matching_subscribers(self) -> None:
        bus = EventBus()
        ws_alice = AsyncMock()
        ws_bob = AsyncMock()
        bus.subscribe("chat", ws_alice, "alice", Permission.play, "c1", "a1")
        bus.subscribe("chat", ws_bob, "bob", Permission.play, "c1", "a1")

        asyncio.run(
            bus.publish(
                "chat",
                [
                    {
                        "name": "chat.new",
                        "value": '"hello"',
                        "context": {"activity_id": "a1"},
                        "permission": "play",
                    }
                ],
            )
        )

        ws_alice.send_json.assert_called_once_with(
            {"name": "chat.new", "value": '"hello"'}
        )
        ws_bob.send_json.assert_called_once_with(
            {"name": "chat.new", "value": '"hello"'}
        )

    def test_publish_filters_by_context(self) -> None:
        bus = EventBus()
        ws_alice = AsyncMock()
        ws_bob = AsyncMock()
        bus.subscribe("chat", ws_alice, "alice", Permission.play, "c1", "a1")
        bus.subscribe("chat", ws_bob, "bob", Permission.play, "c1", "a1")

        asyncio.run(
            bus.publish(
                "chat",
                [
                    {
                        "name": "result",
                        "value": '"ok"',
                        "context": {"activity_id": "a1", "user_id": "alice"},
                        "permission": "play",
                    }
                ],
            )
        )

        ws_alice.send_json.assert_called_once()
        ws_bob.send_json.assert_not_called()

    def test_publish_filters_by_permission(self) -> None:
        bus = EventBus()
        ws_viewer = AsyncMock()
        ws_editor = AsyncMock()
        bus.subscribe("quiz", ws_viewer, "alice", Permission.view, "c1", "a1")
        bus.subscribe("quiz", ws_editor, "bob", Permission.edit, "c1", "a1")

        asyncio.run(
            bus.publish(
                "quiz",
                [
                    {
                        "name": "config.saved",
                        "value": "{}",
                        "context": {"activity_id": "a1"},
                        "permission": "edit",
                    }
                ],
            )
        )

        ws_viewer.send_json.assert_not_called()
        ws_editor.send_json.assert_called_once()

    def test_publish_to_nonexistent_type_is_noop(self) -> None:
        asyncio.run(
            EventBus().publish(
                "nonexistent",
                [
                    {
                        "name": "test",
                        "value": '""',
                        "context": {},
                        "permission": "play",
                    }
                ],
            )
        )
        # Should not raise
