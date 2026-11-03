from streamer_toolbox.connections.obs.boxes.obs_source_box import ObsSourceBox, Call
from streamer_toolbox.core.files.file_types import IMAGE_TYPES


class SetImageFile(ObsSourceBox):
    name = "set_image_file"
    label = "Set image file"
    help = "Puts a picture file into an Image source (like a meme image on a soundboard button). Doesn't show " \
           "it: use Show / hide source"
    group = "Media"
    files = {"path": IMAGE_TYPES}

    def __init__(self, call: Call) -> None:
        super().__init__(call)
        self.options = {"source": self.image_names}

    async def run(self, source: str, path: str) -> None:
        await self._request("SetInputSettings", {"inputName": source, "inputSettings": {"file": str(path)}})
