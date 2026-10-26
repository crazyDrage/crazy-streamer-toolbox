from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_placement_box import ObsPlacementBox
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.data.box_value import to_bool


class TakePlaceMarker(ObsPlacementBox):
    name = "take_place_marker"
    label = "Take place marker"
    help = "Reads where a place marker is now and removes it; keep off = only remove it"
    group = "Advanced"
    outputs = {"x": "number", "y": "number", "width": "number", "height": "number"}
    flow_only = True

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"scene": self._requests.scene_names}

    async def run(self, scene: str, source: str, keep: bool = True) -> dict[str, Any]:
        """keep: the marker's place (read before it's removed); not keep: {} (Cancel)."""
        try:
            return await self.get_place(scene, source) if to_bool(keep) else {}
        finally:
            await self._requests("RemoveInput", {"inputName": source})
