from streamer_toolbox.connections.obs.boxes.obs_scene_box import ObsSceneBox


class GetProfile(ObsSceneBox):
    name = "get_profile"
    label = "Get profile"
    help = "The name of the OBS profile in use (Profile menu in OBS)"
    group = "Profile / scene collection"
    live = True

    async def run(self) -> str:
        return (await self._requests("GetProfileList")).get("currentProfileName", "")
