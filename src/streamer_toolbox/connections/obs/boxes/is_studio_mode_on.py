from streamer_toolbox.connections.obs.boxes.obs_scene_box import ObsSceneBox


class IsStudioModeOn(ObsSceneBox):
    name = "get_studio_mode"
    label = "Is studio mode on"
    help = "Whether OBS's studio mode (preview next to program) is on (true / false)"
    group = "Studio mode"
    live = True

    async def run(self) -> bool:
        return bool((await self._requests("GetStudioModeEnabled")).get("studioModeEnabled"))
