"""Learning Activity Server package."""

from server.app import create_app
from server import capabilities

__all__ = ["create_app", "capabilities"]
