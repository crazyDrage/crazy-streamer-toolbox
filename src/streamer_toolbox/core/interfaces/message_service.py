from abc import ABC, abstractmethod


class MessageService(ABC):
    """Shows the streamer a message, like SAMMI's popup message."""

    @abstractmethod
    async def show(self, message: str, title: str = "") -> int:
        """Shows it on every open screen until closed; returns on how many (0: no GUI open)."""
