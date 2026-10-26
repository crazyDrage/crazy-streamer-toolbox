from typing import Any

from streamer_toolbox.connections.obs.obs_placement import ObsPlacement
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.interfaces.box import Box


MARKER_COLOR = 0xB3FF5E6C
MARKER_SIZE = (640.0, 360.0)


class ObsPlacementBox(Box):
    """What the obs placement boxes share (not a box itself: it has no run).

    OBS boxes for a place in a scene (ObsPlacement): read a source's place, put a source at a place. The
    place of the Place source box is set up in its own window: a coloured marker appears in OBS, he drags and
    sizes it there, and the window takes over where it ended up (put_marker / take_marker, also boxes so the
    window and plugins use the same way in)."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    async def apply(self, scene: str, item: int, place: ObsPlacement) -> None:
        await self._requests("SetSceneItemTransform", {"sceneName": scene, "sceneItemId": item,
                                                       "sceneItemTransform": place.to_transform()})

    async def get_place(self, scene: str, source: str) -> dict[str, Any]:
        item = await self._requests.scene_item_id(scene, source)
        now = await self._requests("GetSceneItemTransform", {"sceneName": scene, "sceneItemId": item})
        return ObsPlacement.from_transform(now["sceneItemTransform"], scene).to_dict()
