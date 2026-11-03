from streamer_toolbox.connections.obs.boxes.obs_scene_box import ObsSceneBox


class SceneList(ObsSceneBox):
    name = "get_scenes"
    label = "Scene list"
    help = "The names of all scenes, in OBS's order (top first)"
    group = "Scenes"
    live = True

    async def run(self) -> list[str]:
        return await self._requests.scene_names()
