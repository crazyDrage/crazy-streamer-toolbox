from streamer_toolbox.connections.obs.boxes.obs_source_box import ObsSourceBox, Call


class IsSourceShown(ObsSourceBox):
    name = "get_source_visible"
    label = "Is source shown"
    help = "Whether a source in a scene is shown (true / false), its eye in OBS"
    group = "Sources"

    def __init__(self, call: Call) -> None:
        super().__init__(call)
        self.options = {"scene": self.scene_names, "source": self.source_names}

    async def run(self, scene: str, source: str) -> bool:
        item = await self._request("GetSceneItemId", {"sceneName": scene, "sourceName": source})
        answer = await self._request("GetSceneItemEnabled", {"sceneName": scene, "sceneItemId": item["sceneItemId"]})
        return bool(answer.get("sceneItemEnabled"))
