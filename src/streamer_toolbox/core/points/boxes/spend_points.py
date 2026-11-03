from typing import Any

from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.points.boxes.point_box import PointBox, PLATFORMS, _viewer, _whole


class SpendPoints(PointBox):
    name = "spend"
    label = "Spend points"
    help = "Takes the amount if the viewer has that much. Gives ok (true / false) and points (what is left): put " \
           "an If on ok for a command that costs points"
    group = "Points"
    options = {"platform": fixed_choices(PLATFORMS)}
    hints = {"viewer": "usually Start's user_login", "platform": "empty = twitch"}

    async def run(self, viewer: str, amount: int = 1, platform: str = "twitch") -> dict[str, Any]:
        ok = await self._bank().spend(_viewer(viewer), _whole(amount), platform)
        return {"ok": ok, "points": await self._bank().get(_viewer(viewer), platform)}
