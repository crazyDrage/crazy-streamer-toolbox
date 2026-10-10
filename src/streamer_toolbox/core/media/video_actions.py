from pathlib import Path
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.files.file_types import VIDEO_TYPES
from streamer_toolbox.core.interfaces.video_probe import VideoProbe


class VideoActions:
    """Video boxes that read the file itself, no OBS needed: Video info (size and length)."""

    def __init__(self, probe: VideoProbe) -> None:
        self._probe = probe

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("video.info", self.info, "Reads a video file (MP4 / MOV): width, height, seconds (how long it "
                    "plays) and orientation, each an orange dot", "Video info", group="Video",
                    outputs={"width": "number", "height": "number", "seconds": "number", "orientation": "text"},
                    files={"path": VIDEO_TYPES})

    async def info(self, path: str) -> dict[str, Any]:
        file = Path(str(path).strip().strip('"'))
        if not file.is_file():
            raise FileNotFoundError(f"no video file at {file}")
        size, seconds = self._probe.probe(file), self._probe.length(file)
        if size is None or seconds is None:
            raise ValueError(f"can't read the size or length of {file.name} (only MP4 / MOV files)")
        return {"width": size.width, "height": size.height, "seconds": round(seconds, 3),
                "orientation": size.orientation.name.lower()}
