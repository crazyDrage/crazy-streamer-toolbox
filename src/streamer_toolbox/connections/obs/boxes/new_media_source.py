from typing import TYPE_CHECKING, Any

from streamer_toolbox.core.files.file_types import MEDIA_TYPES
from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.obs.obs_media_playback import ObsMediaPlayback


class NewMediaSource(Box):
    name = "new_media_source"
    label = "New media source"
    help = "Play video once in parts, part 1: makes a new Media Source for a file in a scene, hidden. Then set " \
           "it up (Set audio monitoring, Set audio tracks, Set volume, Place like source), Show / hide source, " \
           "Wait until media is over, Remove source"
    group = "Media"
    hints = {"name": "empty = a new name each time (toolbox <file> <letters>)",
             "visible": "off: it starts playing when you show it"}
    outputs = {"source": "text", "scene": "text", "item_id": "number"}
    files = {"file": MEDIA_TYPES}

    def __init__(self, obs_media_playback: "ObsMediaPlayback") -> None:
        self._obs_media_playback = obs_media_playback
        self.options = {"scene": self._obs_media_playback._requests.scene_names}

    async def run(self, scene: str, file: str, name: str = "",
                  visible: bool = False) -> dict[str, Any]:
        return await self._obs_media_playback.new_media_source(scene, file, name, visible)
