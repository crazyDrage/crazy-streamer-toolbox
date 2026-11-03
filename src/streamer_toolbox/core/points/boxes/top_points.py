from typing import Any

from streamer_toolbox.core.points.boxes.point_box import PointBox, _whole


class TopPoints(PointBox):
    name = "top"
    label = "Top points"
    help = "The viewers with the most points, as a list of {user, platform, points}"
    group = "Points"
    live = True

    async def run(self, count: int = 10) -> list[dict[str, Any]]:
        return await self._bank().top(_whole(count))
