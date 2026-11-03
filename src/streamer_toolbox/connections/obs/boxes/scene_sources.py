from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_scene_box import ObsSceneBox
from streamer_toolbox.connections.obs.obs_requests import ObsRequests


class SceneSources(ObsSceneBox):
    name = "get_scene_sources"
    label = "Scene sources"
    help = "What is in a scene, top first: a list of {source, visible, kind}"
    group = "Scenes"

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"scene": self._requests.scene_names}

    async def run(self, scene: str) -> list[dict[str, Any]]:
        items = (await self._requests("GetSceneItemList", {"sceneName": scene}))["sceneItems"]
        ordered = sorted(items, key=lambda i: i.get("sceneItemIndex", 0), reverse=True)  # OBS: 0 = bottom
        return [{"source": i["sourceName"], "visible": bool(i.get("sceneItemEnabled")),
                 "kind": i.get("inputKind") or ("group" if i.get("isGroup") else "scene")}
                for i in ordered]
