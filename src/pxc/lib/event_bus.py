"""In-memory pub/sub for broadcasting events via WebSockets."""

from dataclasses import dataclass
import logging

from starlette.websockets import WebSocket, WebSocketDisconnect

from pxc.lib.runtime import PendingEvent, HostContext
from pxc.lib.permission import Permission

logger = logging.getLogger(__name__)

# Permission hierarchy for comparison
_PERMISSION_RANK: dict[str, int] = {
    "view": 0,
    "play": 1,
    "edit": 2,
}


@dataclass
class Subscriber:
    websocket: WebSocket
    user_id: str
    permission: Permission
    course_id: str
    activity_id: str


class EventBus:
    """Manages WebSocket subscribers and broadcasts events with context/permission filtering."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Subscriber]] = {}

    def subscribe(
        self,
        activity_type: str,
        websocket: WebSocket,
        user_id: str,
        permission: Permission,
        course_id: str,
        activity_id: str,
    ) -> Subscriber:
        subscriber = Subscriber(
            websocket=websocket,
            user_id=user_id,
            permission=permission,
            course_id=course_id,
            activity_id=activity_id,
        )
        self._subscribers.setdefault(activity_type, []).append(subscriber)
        return subscriber

    def unsubscribe(self, activity_type: str, subscriber: Subscriber) -> None:
        subs = self._subscribers.get(activity_type, [])
        try:
            subs.remove(subscriber)
        except ValueError:
            pass

    async def publish(self, activity_type: str, events: list[PendingEvent]) -> None:
        subscribers = self._subscribers.get(activity_type, [])
        for event in events:
            event_context = event["context"]
            event_permission = event["permission"]
            for sub in subscribers:
                if not _matches_context(sub, event_context):
                    continue
                if not _has_permission(sub, event_permission):
                    continue
                try:
                    await sub.websocket.send_json(
                        {
                            "name": event["name"],
                            "value": event["value"],
                        }
                    )
                except WebSocketDisconnect:
                    logger.warning("Failed to send event to subscriber %s", sub.user_id)


def _matches_context(subscriber: Subscriber, event_context: HostContext) -> bool:
    """Check if a subscriber matches the event context.

    Each dimension present in the event context must match the subscriber's value.
    Missing dimensions mean "any" (broader broadcast).
    """
    for key, value in event_context.items():
        if key == "activity_id" and subscriber.activity_id != value:
            return False
        if key == "course_id" and subscriber.course_id != value:
            return False
        if key == "user_id" and subscriber.user_id != value:
            return False
    return True


def _has_permission(subscriber: Subscriber, required: str) -> bool:
    """Check if subscriber's permission level meets the minimum required."""
    sub_rank = _PERMISSION_RANK.get(subscriber.permission.value, 0)
    req_rank = _PERMISSION_RANK.get(required, 0)
    return sub_rank >= req_rank
