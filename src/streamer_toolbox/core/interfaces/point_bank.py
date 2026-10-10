from abc import ABC, abstractmethod
from typing import Any


class PointBank(ABC):
    """Where the viewers' points live: the toolbox's own store, or another program's currency (Mix It Up). The
    Points boxes and the points chat command talk to this, so a flow doesn't change when he switches."""

    @abstractmethod
    async def get(self, viewer: str, platform: str = "twitch") -> int:
        """How many points the viewer has (0 for one never seen)."""

    @abstractmethod
    async def add(self, viewer: str, amount: int, platform: str = "twitch") -> int:
        """Gives points (a minus number takes them); the viewer's points after it."""

    @abstractmethod
    async def set(self, viewer: str, points: int, platform: str = "twitch") -> int:
        """Sets the viewer's points; gives them back."""

    @abstractmethod
    async def spend(self, viewer: str, amount: int, platform: str = "twitch") -> bool:
        """Takes the amount if the viewer has that much; False (nothing taken) if not."""

    @abstractmethod
    async def top(self, count: int = 10) -> list[dict[str, Any]]:
        """The viewers with the most points: [{"user", "platform", "points"}], most first."""
