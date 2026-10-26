from pathlib import Path, PureWindowsPath
from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_output_box import ObsOutputBox, IMAGE_FORMATS
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.files.file_types import IMAGE_TYPES


class Screenshot(ObsOutputBox):
    name = "screenshot"
    label = "Screenshot"
    help = "Saves a picture of a source or scene as it is now (png, jpg, bmp or webp, by the file's ending); " \
           "gives the file"
    group = "Sources"
    hints = {"width": "empty = its own size; the height follows"}
    files = {"file": IMAGE_TYPES}

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"source": self._source_and_scene_names}

    async def run(self, source: str, file: str, width: int | None = None) -> str:
        path = Path(str(file)).expanduser()
        image_format = IMAGE_FORMATS.get(path.suffix.casefold())
        if image_format is None:
            raise ValueError(f"the file should end in {', '.join(IMAGE_FORMATS)}, not {path.name!r}")
        if not (path.is_absolute() or PureWindowsPath(path).is_absolute()):  # OBS may run on another system
            raise ValueError(f"OBS needs the full path (like C:\\clips\\shot.png), not {str(file)!r}")
        data: dict[str, Any] = {"sourceName": source, "imageFormat": image_format, "imageFilePath": str(path)}
        if width not in (None, ""):
            data["imageWidth"] = int(float(width))
        await self._requests("SaveSourceScreenshot", data)
        return str(path)
