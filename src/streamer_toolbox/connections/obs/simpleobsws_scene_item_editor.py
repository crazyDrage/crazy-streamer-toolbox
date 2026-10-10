import simpleobsws

from streamer_toolbox.core.layout.box import Box
from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError
from streamer_toolbox.core.interfaces.scene_item_editor import SceneItemEditor

# obs_alignment flags: LEFT=1, RIGHT=2, TOP=4, BOTTOM=8, centre=0
_ALIGN_TOP_LEFT = 5
_ALIGN_CENTRE = 0


class SimpleobswsSceneItemEditor(SceneItemEditor):
    """SceneItemEditor over obs-websocket v5, using an already connected simpleobsws client."""

    def __init__(self, client: simpleobsws.WebSocketClient) -> None:
        self._client = client

    async def set_bounds(self, scene_name: str, source_name: str, bounds: Box) -> None:
        item_id = await self._scene_item_id(scene_name, source_name)
        await self._call("SetSceneItemTransform", {
            "sceneName": scene_name,
            "sceneItemId": item_id,
            "sceneItemTransform": {
                "alignment": _ALIGN_TOP_LEFT,
                "positionX": bounds.x,
                "positionY": bounds.y,
                "boundsType": "OBS_BOUNDS_SCALE_INNER",
                "boundsAlignment": _ALIGN_CENTRE,
                "boundsWidth": bounds.width,
                "boundsHeight": bounds.height,
            },
        })

    async def _scene_item_id(self, scene_name: str, source_name: str) -> int:
        data = await self._call("GetSceneItemId", {"sceneName": scene_name, "sourceName": source_name})
        return data["sceneItemId"]

    async def _call(self, request_type: str, request_data: dict) -> dict:
        response = await self._client.call(simpleobsws.Request(request_type, request_data))
        if not response.ok():
            status = response.requestStatus
            raise ObsRequestError(request_type, status.code, status.comment)
        return response.responseData or {}
