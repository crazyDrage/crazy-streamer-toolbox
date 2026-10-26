from streamer_toolbox.connections.obs.boxes.obs_scene_box import ObsSceneBox


class SourceList(ObsSceneBox):
    name = "get_sources"
    label = "Source list"
    help = "The names of all sources (cameras, pictures, media, audio ...), A to Z. Scenes are not in it"
    group = "Sources"
    live = True

    async def run(self) -> list[str]:
        return await self._requests.input_names()
