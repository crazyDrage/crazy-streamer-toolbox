from streamer_toolbox.connections.obs.boxes.obs_input_box import ObsInputBox, Call


class MoveSource(ObsInputBox):
    name = "move_source"
    label = "Move source"
    help = "Moves a source in a scene to x / y (pixels from the top left of the canvas); an empty one stays"
    group = "Sources"
    outputs = {"x": "number", "y": "number"}

    def __init__(self, call: Call) -> None:
        super().__init__(call)
        self.options = {"scene": self.scene_names, "source": self.source_names}

    async def run(self, scene: str, source: str, x: float | None = None,
                  y: float | None = None) -> dict[str, float]:
        item = (await self._request("GetSceneItemId", {"sceneName": scene, "sourceName": source}))["sceneItemId"]
        now = (await self._request("GetSceneItemTransform", {"sceneName": scene, "sceneItemId": item}))
        transform = now.get("sceneItemTransform", {})
        place = {"positionX": float(transform.get("positionX", 0)) if x in (None, "") else float(x),
                 "positionY": float(transform.get("positionY", 0)) if y in (None, "") else float(y)}
        await self._request("SetSceneItemTransform", {"sceneName": scene, "sceneItemId": item,
                                                      "sceneItemTransform": place})
        return {"x": place["positionX"], "y": place["positionY"]}
