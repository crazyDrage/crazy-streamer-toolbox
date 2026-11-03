from abc import ABC, abstractmethod
from typing import Any


class Listener(ABC):
    """Hears every event of the toolbox: a follow, a redeem, a chat message, a key, another plugin's trigger.

    `kind` is the event's name ("twitch.follow", "example.blinked"), `data` a dict with its fields
    (core/events/event_fields.py). Keep it quick, and never write what events carry (chat, names) into a log or
    a file."""

    @abstractmethod
    async def heard(self, kind: str, data: dict[str, Any]) -> None:
        """Called for every event."""
