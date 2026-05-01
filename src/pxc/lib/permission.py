"""Runtime permission levels for activity access."""

from enum import Enum


class Permission(Enum):
    view = "view"
    play = "play"
    edit = "edit"
