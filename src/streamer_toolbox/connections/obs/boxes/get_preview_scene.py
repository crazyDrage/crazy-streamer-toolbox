from streamer_toolbox.connections.obs.boxes.obs_scene_box import ObsSceneBox
from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError

STUDIO_MODE_OFF = 506


class GetPreviewScene(ObsSceneBox):
    name = "get_preview_scene"
    label = "Get preview scene"
    help = "The scene in studio mode's preview. Empty while studio mode is off"
    group = "Studio mode"
    live = True

    async def run(self) -> str:
        try:
            return (await self._requests("GetCurrentPreviewScene")).get("currentPreviewSceneName", "")
        except ObsRequestError as e:
            if e.code == STUDIO_MODE_OFF:
                return ""
            raise
