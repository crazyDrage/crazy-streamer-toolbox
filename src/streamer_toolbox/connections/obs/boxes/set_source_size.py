from streamer_toolbox.connections.obs.boxes.obs_source_box import ObsSourceBox, Call, _bool


class SetSourceSize(ObsSourceBox):
    name = "set_source_size"
    label = "Set source size"
    help = "Sizes a source in a scene to width × height (times scale, e.g. 0.5 for half), keeping where it is " \
           "and its shape. Wire in the width and height of Video info"
    group = "Sources"
    labels = {"keep_inside": "Keep inside the canvas"}
    hints = {"keep_inside": "on: if the new size sticks out (a tall video), it moves just enough to "
                            "fit"}
    outputs = {"width": "number", "height": "number"}

    def __init__(self, call: Call) -> None:
        super().__init__(call)
        self.options = {"scene": self.scene_names, "source": self.source_names}

    async def run(self, scene: str, source: str, width: float, height: float,
                  scale: float = 1.0, keep_inside: bool = False) -> dict[str, float]:
        """Bounds of width × height (scaled), content fitted inside keeping its shape; the position stays, unless
        keep_inside and the new size would stick out of the canvas: then it moves just enough to fit."""
        size = {"width": round(float(width) * float(scale), 2), "height": round(float(height) * float(scale), 2)}
        if size["width"] <= 0 or size["height"] <= 0:
            raise ValueError(f"a size must be above 0, got {size['width']} × {size['height']}")
        item = await self._request("GetSceneItemId", {"sceneName": scene, "sourceName": source})
        transform = {"boundsType": "OBS_BOUNDS_SCALE_INNER", "boundsAlignment": 0,
                     "boundsWidth": size["width"], "boundsHeight": size["height"]}
        if _bool(keep_inside):
            transform.update(await self._inside(scene, item["sceneItemId"], size["width"], size["height"]))
        await self._request("SetSceneItemTransform", {
            "sceneName": scene, "sceneItemId": item["sceneItemId"], "sceneItemTransform": transform})
        return size
