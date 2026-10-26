from typing import TYPE_CHECKING, Any

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.obs.obs_media_playback import ObsMediaPlayback


class MediaStatus(Box):
    name = "get_media_status"
    label = "Media status"
    help = "Where a Media Source is: state (playing, paused, ended, ...), seconds long, seconds played"
    group = "Media"
    outputs = {"state": "text", "seconds": "number", "position": "number"}

    def __init__(self, obs_media_playback: "ObsMediaPlayback") -> None:
        self._obs_media_playback = obs_media_playback
        self.options = {"source": self._obs_media_playback._requests.media_names}

    async def run(self, source: str) -> dict[str, Any]:
        return await self._obs_media_playback.media_status(source)
