from streamer_toolbox.connections.obs.boxes.obs_source_box import ObsSourceBox, Call
from streamer_toolbox.core.files.file_types import MEDIA_TYPES


class SetMediaFile(ObsSourceBox):
    name = "set_media_file"
    label = "Set media file"
    help = "Puts a video (or sound) file into a Media Source. Doesn't show it: use Show / hide source, then " \
           "Media control → restart"
    group = "Media"
    files = {"path": MEDIA_TYPES}

    def __init__(self, call: Call) -> None:
        super().__init__(call)
        self.options = {"source": self.media_names}

    async def run(self, source: str, path: str) -> None:
        await self._request("SetInputSettings", {"inputName": source, "inputSettings": {
            "local_file": str(path), "is_local_file": True}})
