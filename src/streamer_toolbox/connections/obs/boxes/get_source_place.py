from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_placement_box import ObsPlacementBox
from streamer_toolbox.connections.obs.obs_requests import ObsRequests


class GetSourcePlace(ObsPlacementBox):
    name = "get_source_place"
    label = "Get source place"
    help = "Where a source sits in a scene: x, y, width, height (as shown), rotation. Wire it into Place source " \
           "to put another source there"
    group = "Sources"
    outputs = {"x": "number", "y": "number", "width": "number", "height": "number",
               "rotation": "number", "alignment": "number"}

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"scene": self._requests.scene_names, "source": self._requests.source_names}

    async def run(self, scene: str, source: str) -> dict[str, Any]:
        return await self.get_place(scene, source)
