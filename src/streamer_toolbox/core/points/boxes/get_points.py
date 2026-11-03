from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.points.boxes.point_box import PointBox, PLATFORMS, _viewer


class GetPoints(PointBox):
    name = "get"
    label = "Get points"
    help = "How many points a viewer has"
    live = True
    group = "Points"
    options = {"platform": fixed_choices(PLATFORMS)}
    hints = {"viewer": "usually Start's user_login", "platform": "empty = twitch"}

    async def run(self, viewer: str, platform: str = "twitch") -> int:
        return await self._bank().get(_viewer(viewer), platform)
