from collections.abc import Callable
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.interfaces.point_bank import PointBank

PLATFORMS = {"twitch": "Twitch", "youtube": "YouTube", "rumble": "Rumble"}


class PointActions:
    """The Points boxes: the toolbox's own currency per viewer, for flows (a command that costs points, a reward
    that gives some, a leaderboard). The viewer is usually Start's user_login, the platform Start's platform.
    `bank` gives where the points live right now (the toolbox's store or Mix It Up's currency): he can switch
    on the Points page without touching a flow."""

    def __init__(self, bank: Callable[[], PointBank]) -> None:
        self._bank = bank

    def add_to(self, actions: ActionRegistry) -> None:
        async def platforms() -> dict[str, str]:
            return PLATFORMS

        box = {"group": "Points", "options": {"platform": platforms},
               "hints": {"viewer": "usually Start's user_login", "platform": "empty = twitch"}}
        actions.add("points.get", self.get, "How many points a viewer has", "Get points", live=True, **box)
        actions.add("points.add", self.add, "Gives a viewer points (a minus number takes them, never below 0); "
                    "gives back the new number", "Add points", **box)
        actions.add("points.set", self.set, "Sets a viewer's points to a number", "Set points", **box)
        actions.add("points.spend", self.spend, "Takes the amount if the viewer has that much. Gives ok (true / "
                    "false) and points (what is left): put an If on ok for a command that costs points",
                    "Spend points", **box)
        actions.add("points.give", self.give, "One viewer gives points to another (fails if they don't have that "
                    "many)", "Give points to a viewer", group="Points", options={"platform": platforms})
        actions.add("points.top", self.top, "The viewers with the most points, as a list of {user, platform, "
                    "points}", "Top points", group="Points", live=True)

    async def get(self, viewer: str, platform: str = "twitch") -> int:
        return await self._bank().get(_viewer(viewer), platform)

    async def add(self, viewer: str, amount: int = 1, platform: str = "twitch") -> int:
        return await self._bank().add(_viewer(viewer), _whole(amount), platform)

    async def set(self, viewer: str, points: int = 0, platform: str = "twitch") -> int:
        return await self._bank().set(_viewer(viewer), max(0, _whole(points)), platform)

    async def spend(self, viewer: str, amount: int = 1, platform: str = "twitch") -> dict[str, Any]:
        ok = await self._bank().spend(_viewer(viewer), _whole(amount), platform)
        return {"ok": ok, "points": await self._bank().get(_viewer(viewer), platform)}

    async def give(self, giver: str, receiver: str, amount: int = 1, platform: str = "twitch") -> dict[str, Any]:
        amount = _whole(amount)
        if amount <= 0:
            raise ValueError("the amount to give must be above 0")
        bank = self._bank()
        if not await bank.spend(_viewer(giver), amount, platform):
            raise ValueError(f"{giver} doesn't have {amount} points")
        return {"giver": await bank.get(_viewer(giver), platform),
                "receiver": await bank.add(_viewer(receiver), amount, platform)}

    async def top(self, count: int = 10) -> list[dict[str, Any]]:
        return await self._bank().top(_whole(count))


def _viewer(viewer: str) -> str:
    name = str(viewer).strip().lstrip("@")
    if not name:
        raise ValueError("a viewer's name is needed (wire Start's user_login)")
    return name


def _whole(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        raise ValueError(f"a whole number is needed, not {value!r}") from None
