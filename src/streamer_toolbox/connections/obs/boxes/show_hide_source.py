from streamer_toolbox.connections.obs.boxes.obs_source_box import ObsSourceBox, Call, _bool


class ShowHideSource(ObsSourceBox):
    name = "set_source_visible"
    label = "Show / hide source"
    help = "Shows or hides a source in a scene"
    group = "Sources"

    def __init__(self, call: Call) -> None:
        super().__init__(call)
        self.options = {"scene": self.scene_names, "source": self.source_names}

    async def run(self, scene: str, source: str, visible: bool = True) -> None:
        item = await self._request("GetSceneItemId", {"sceneName": scene, "sourceName": source})
        await self._request("SetSceneItemEnabled", {"sceneName": scene, "sceneItemId": item["sceneItemId"],
                                                    "sceneItemEnabled": _bool(visible)})
