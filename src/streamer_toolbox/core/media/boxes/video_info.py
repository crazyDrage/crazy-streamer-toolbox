from pathlib import Path
from typing import Any

from streamer_toolbox.core.files.file_types import VIDEO_TYPES
from streamer_toolbox.core.media.boxes.video_box import VideoBox


class VideoInfo(VideoBox):
    name = "info"
    label = "Video info"
    help = "Reads a video file (MP4 / MOV): width, height, seconds (how long it plays) and orientation, each an " \
           "orange dot"
    group = "Video"
    outputs = {"width": "number", "height": "number", "seconds": "number", "orientation": "text"}
    files = {"path": VIDEO_TYPES}

    async def run(self, path: str) -> dict[str, Any]:
        file = Path(str(path).strip().strip('"'))
        if not file.is_file():
            raise FileNotFoundError(f"no video file at {file}")
        size, seconds = self._probe.probe(file), self._probe.length(file)
        if size is None or seconds is None:
            raise ValueError(f"can't read the size or length of {file.name} (only MP4 / MOV files)")
        return {"width": size.width, "height": size.height, "seconds": round(seconds, 3),
                "orientation": size.orientation.name.lower()}
