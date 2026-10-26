from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.points.boxes.point_box import PointBox, PLATFORMS, _viewer, _whole


class SetPoints(PointBox):
    name = "set"
    label = "Set points"
    help = "Sets a viewer's points to a number"
    group = "Points"
    options = {"platform": fixed_choices(PLATFORMS)}
    hints = {"viewer": "usually Start's user_login", "platform": "empty = twitch"}

    async def run(self, viewer: str, points: int = 0, platform: str = "twitch") -> int:
        return await self._bank().set(_viewer(viewer), max(0, _whole(points)), platform)
