import uuid
from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_placement_box import ObsPlacementBox, MARKER_COLOR, MARKER_SIZE
from streamer_toolbox.connections.obs.obs_placement import ObsPlacement
from streamer_toolbox.connections.obs.obs_requests import ObsRequests


class PutPlaceMarker(ObsPlacementBox):
    name = "put_place_marker"
    label = "Put place marker"
    help = "Shows a coloured marker in a scene to drag and size in OBS (at a place, if you give one). Take place " \
           "marker reads where it ended up"
    group = "Advanced"
    outputs = {"source": "text", "scene": "text"}
    flow_only = True

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"scene": self._requests.scene_names}

    async def run(self, scene: str, place: Any = "") -> dict[str, Any]:
        """A see-through colour source on top of the scene, at `place` (its spot and size) or top left."""
        at = ObsPlacement.from_value(place) if place not in (None, "") else None
        width, height = (at.width, at.height) if at and at.width > 0 and at.height > 0 else MARKER_SIZE
        name = f"toolbox place marker {uuid.uuid4().hex[:6]}"
        made = await self._requests("CreateInput", {
            "sceneName": scene, "inputName": name, "inputKind": "color_source_v3", "sceneItemEnabled": True,
            "inputSettings": {"color": MARKER_COLOR, "width": round(width), "height": round(height)}})
        if at:
            try:  # only the spot: without bounds he sizes it by dragging its corners
                await self._requests("SetSceneItemTransform", {
                    "sceneName": scene, "sceneItemId": made["sceneItemId"],
                    "sceneItemTransform": {"positionX": at.x, "positionY": at.y, "rotation": at.rotation,
                                           "alignment": at.alignment}})
            except BaseException:
                await self._requests("RemoveInput", {"inputName": name})
                raise
        return {"source": name, "scene": scene}
