from typing import Any

from streamer_toolbox.core.interfaces.point_bank import PointBank
from streamer_toolbox.core.points.point_store import PointStore


class LocalPointBank(PointBank):
    """The points in the toolbox's own store (config/points/points.json)."""

    def __init__(self, store: PointStore) -> None:
        self._store = store

    async def get(self, viewer: str, platform: str = "twitch") -> int:
        return self._store.get(viewer, platform)

    async def add(self, viewer: str, amount: int, platform: str = "twitch") -> int:
        return self._store.add(viewer, amount, platform)

    async def set(self, viewer: str, points: int, platform: str = "twitch") -> int:
        return self._store.set(viewer, points, platform)

    async def spend(self, viewer: str, amount: int, platform: str = "twitch") -> bool:
        return self._store.spend(viewer, amount, platform)

    async def top(self, count: int = 10) -> list[dict[str, Any]]:
        return self._store.top(count)
