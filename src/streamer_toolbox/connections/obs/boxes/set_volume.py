from streamer_toolbox.connections.obs.boxes.obs_source_box import ObsSourceBox, Call


class SetVolume(ObsSourceBox):
    name = "set_volume"
    label = "Set volume"
    help = "Sets an audio source's volume, 0 to 1"
    group = "Audio"

    def __init__(self, call: Call) -> None:
        super().__init__(call)
        self.options = {"source": self.audio_names}

    async def run(self, source: str, volume: float) -> None:
        await self._request("SetInputVolume", {"inputName": source, "inputVolumeMul": max(float(volume), 0.0)})
