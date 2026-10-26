from streamer_toolbox.connections.obs.boxes.obs_source_box import ObsSourceBox, Call


class GetVolume(ObsSourceBox):
    name = "get_volume"
    label = "Get volume"
    help = "An audio source's volume, 0 to 1 (save it to put it back later)"
    group = "Audio"

    def __init__(self, call: Call) -> None:
        super().__init__(call)
        self.options = {"source": self.audio_names}

    async def run(self, source: str) -> float:
        return (await self._request("GetInputVolume", {"inputName": source}))["inputVolumeMul"]
