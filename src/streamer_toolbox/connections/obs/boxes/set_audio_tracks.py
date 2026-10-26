from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_audio_box import ObsAudioBox, TRACKS, track_numbers
from streamer_toolbox.connections.obs.obs_requests import ObsRequests


class SetAudioTracks(ObsAudioBox):
    name = "set_audio_tracks"
    label = "Set audio tracks"
    help = "Which audio tracks (1 to 6) a source goes to; the others are switched off"
    hints = {"tracks": "e.g. 1, 2 (or all, or none)"}
    group = "Audio"

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"source": self._requests.input_names}

    async def run(self, source: str, tracks: Any = "1") -> list[int]:
        on = track_numbers(tracks)
        await self._requests("SetInputAudioTracks", {"inputName": source,
                                                     "inputAudioTracks": {t: t in on for t in TRACKS}})
        return [int(t) for t in on]
