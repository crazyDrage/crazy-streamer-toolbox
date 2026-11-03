from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.obs.obs_media_playback import ObsMediaPlayback


class PlaceLikeSource(Box):
    name = "place_like"
    label = "Place like source"
    help = "Gives a source the spot and size another source has in the scene (e.g. a new video where sound_alert " \
           "is)"
    group = "Sources"
    labels = {"like": "Like source"}

    def __init__(self, obs_media_playback: "ObsMediaPlayback") -> None:
        self._obs_media_playback = obs_media_playback
        self.options = {"scene": self._obs_media_playback._requests.scene_names, "source": self._obs_media_playback._requests.source_names,
                        "like": self._obs_media_playback._requests.source_names}

    async def run(self, scene: str, source: str, like: str) -> None:
        return await self._obs_media_playback.place_like(scene, source, like)
