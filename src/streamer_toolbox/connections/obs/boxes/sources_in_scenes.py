from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_scene_box import ObsSceneBox
from streamer_toolbox.connections.obs.obs_requests import ObsRequests


class SourcesInScenes(ObsSceneBox):
    """His round 82: "a list of (source, scene) pairs, where I can make every source visible / invisible with the
    result" (Show / hide sources takes it)."""

    name = "sources_in_scenes"
    label = "Sources in scenes"
    help = "Where a source is: a list of {scene, source, visible, item_id}, one per scene it is in (also inside a " \
           "group). Empty source = every source in every scene. Show / hide sources takes the list"
    group = "Scenes"
    hints = {"source": "e.g. so-event; empty = all of them"}

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"source": self._requests.source_names}

    async def run(self, source: str = "") -> list[dict[str, Any]]:
        wanted = str(source or "").strip()
        pairs: list[dict[str, Any]] = []
        for scene in await self._requests.scene_names():
            items = (await self._requests("GetSceneItemList", {"sceneName": scene}))["sceneItems"]
            pairs += self._pairs(scene, items, wanted)
            for group in (i["sourceName"] for i in items if i.get("isGroup")):
                inside = (await self._requests("GetGroupSceneItemList", {"sceneName": group}))["sceneItems"]
                pairs += self._pairs(group, inside, wanted)
        return pairs

    @staticmethod
    def _pairs(scene: str, items: list[dict[str, Any]], wanted: str) -> list[dict[str, Any]]:
        ordered = sorted(items, key=lambda i: i.get("sceneItemIndex", 0), reverse=True)  # OBS: 0 = bottom
        return [{"scene": scene, "source": i["sourceName"], "visible": bool(i.get("sceneItemEnabled")),
                 "item_id": i["sceneItemId"]} for i in ordered if not wanted or i["sourceName"] == wanted]
