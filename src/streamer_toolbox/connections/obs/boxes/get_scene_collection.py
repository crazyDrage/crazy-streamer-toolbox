from streamer_toolbox.connections.obs.boxes.obs_scene_box import ObsSceneBox


class GetSceneCollection(ObsSceneBox):
    name = "get_scene_collection"
    label = "Get scene collection"
    help = "The name of the OBS scene collection in use (Scene Collection menu in OBS)"
    group = "Profile / scene collection"
    live = True

    async def run(self) -> str:
        return (await self._requests("GetSceneCollectionList")).get("currentSceneCollectionName", "")
