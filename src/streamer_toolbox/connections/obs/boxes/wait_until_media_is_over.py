from typing import TYPE_CHECKING, Any

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.obs.obs_media_playback import ObsMediaPlayback


class WaitUntilMediaIsOver(Box):
    name = "wait_media_end"
    label = "Wait until media is over"
    help = "Waits until a Media Source's video (or sound) is over; gives how long it was. Show the source first: " \
           "a hidden one doesn't start"
    group = "Media"
    outputs = {"seconds": "number"}

    def __init__(self, obs_media_playback: "ObsMediaPlayback") -> None:
        self._obs_media_playback = obs_media_playback
        self.options = {"source": self._obs_media_playback._requests.media_names}

    async def run(self, source: str) -> dict[str, Any]:
        return await self._obs_media_playback.wait_media_end(source)
