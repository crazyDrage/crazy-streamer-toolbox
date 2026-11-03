from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_placement_box import ObsPlacementBox
from streamer_toolbox.connections.obs.obs_placement import ObsPlacement
from streamer_toolbox.connections.obs.obs_requests import ObsRequests


class PlaceSource(ObsPlacementBox):
    name = "place_source"
    label = "Place source"
    help = "Puts a source at a place in the scene: the spot and size you set up once with a marker in OBS (Set " \
           "up the place). The source is fitted into that box, keeping its shape"
    group = "Sources"
    editors = {"place": "obs_placement"}

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"scene": self._requests.scene_names, "source": self._requests.source_names}

    async def run(self, scene: str, source: str, place: Any) -> None:
        if place in (None, ""):
            raise ValueError("no place yet: Set up the place first (the button in this box)")
        await self.apply(scene, await self._requests.scene_item_id(scene, source), ObsPlacement.from_value(place))
