from streamer_toolbox.connections.obs.boxes.obs_audio_box import ObsAudioBox, TRACKS
from streamer_toolbox.connections.obs.obs_requests import ObsRequests


class GetAudioTracks(ObsAudioBox):
    name = "get_audio_tracks"
    label = "Get audio tracks"
    help = "The audio tracks a source goes to, as a list like [1, 2]"
    group = "Audio"

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"source": self._requests.input_names}

    async def run(self, source: str) -> list[int]:
        tracks = (await self._requests("GetInputAudioTracks", {"inputName": source}))["inputAudioTracks"]
        return [int(t) for t in TRACKS if tracks.get(t)]
