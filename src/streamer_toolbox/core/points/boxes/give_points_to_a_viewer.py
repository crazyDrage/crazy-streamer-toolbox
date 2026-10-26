from typing import Any

from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.points.boxes.point_box import PointBox, PLATFORMS, _viewer, _whole


class GivePointsToAViewer(PointBox):
    name = "give"
    label = "Give points to a viewer"
    help = "One viewer gives points to another (fails if they don't have that many)"
    group = "Points"
    options = {"platform": fixed_choices(PLATFORMS)}

    async def run(self, giver: str, receiver: str, amount: int = 1, platform: str = "twitch") -> dict[str, Any]:
        amount = _whole(amount)
        if amount <= 0:
            raise ValueError("the amount to give must be above 0")
        bank = self._bank()
        if not await bank.spend(_viewer(giver), amount, platform):
            raise ValueError(f"{giver} doesn't have {amount} points")
        return {"giver": await bank.get(_viewer(giver), platform),
                "receiver": await bank.add(_viewer(receiver), amount, platform)}
