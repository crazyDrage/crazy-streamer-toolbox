from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.points.boxes.point_box import PointBox, PLATFORMS, _viewer, _whole


class AddPoints(PointBox):
    name = "add"
    label = "Add points"
    help = "Gives a viewer points (a minus number takes them, never below 0); gives back the new number"
    group = "Points"
    options = {"platform": fixed_choices(PLATFORMS)}
    hints = {"viewer": "usually Start's user_login", "platform": "empty = twitch"}

    async def run(self, viewer: str, amount: int = 1, platform: str = "twitch") -> int:
        return await self._bank().add(_viewer(viewer), _whole(amount), platform)
