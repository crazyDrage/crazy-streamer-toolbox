from typing import TYPE_CHECKING, Any

from streamer_toolbox.connections.obs.boxes.obs_media_playback_shared import _monitoring
from streamer_toolbox.core.files.file_types import MEDIA_TYPES
from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.obs.obs_media_playback import ObsMediaPlayback


class PlayVideoOnce(Box):
    name = "play_video_once"
    label = "Play video once"
    help = "Plays a video (or sound) file, or one at an address (https://..., e.g. from Clip video address), in " \
           "a scene with its own new Media Source: sound settings like the Audio Mixer's, the place and size of " \
           "another source if you like, and the source is removed again when the video is over"
    group = "Media"
    labels = {"place_like": "Place like source", "wait": "Wait until it's over"}
    editors = {"place": "obs_placement"}
    hints = {"tracks": "audio tracks, e.g. 1, 2 (empty = OBS's default)",
             "volume": "0 to 1",
             "place_like": "takes this source's place and size in the scene (e.g. sound_alert); "
                           "empty = top left, own size. Or set up a place of its own below",
             "wait": "off: the flow goes on right away, the source still goes when it's over"}
    outputs = {"seconds": "number", "source": "text"}
    files = {"file": MEDIA_TYPES}

    def __init__(self, obs_media_playback: "ObsMediaPlayback") -> None:
        self._obs_media_playback = obs_media_playback
        self.options = {"scene": self._obs_media_playback._requests.scene_names, "monitoring": _monitoring,
                        "place_like": self._obs_media_playback._requests.source_names}

    async def run(self, scene: str, file: str, monitoring: str = "monitor and output", tracks: Any = "",
                  volume: float = 1.0, place_like: str = "", wait: bool = True,
                  place: Any = "") -> dict[str, Any]:
        return await self._obs_media_playback.play_once(scene, file, monitoring, tracks, volume, place_like, wait, place)
