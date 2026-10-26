from streamer_toolbox.connections.obs.boxes.obs_audio_box import ObsAudioBox
from streamer_toolbox.connections.obs.obs_requests import ObsRequests


class IsMuted(ObsAudioBox):
    name = "get_mute"
    label = "Is muted"
    help = "Whether a source is muted (true / false)"
    group = "Audio"

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"source": self._requests.input_names}

    async def run(self, source: str) -> bool:
        return (await self._requests("GetInputMute", {"inputName": source}))["inputMuted"]
