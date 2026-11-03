from pathlib import Path
from typing import Any

from streamer_toolbox.connections.obs.fit_media_by_orientation import FitMediaByOrientation
from streamer_toolbox.core.interfaces.box import Box


class FitVideo(Box):
    """One box per [obs.fit.<target>] in the settings: obs.fit_<target> resizes that target's source for a
    landscape or a portrait video. Its name and help come from the target, so they are set here, not above."""

    group = "Sources"

    def __init__(self, target: str, source: str, fitter: FitMediaByOrientation) -> None:
        self.name = f"fit_{target}"
        self.help = f"Resizes {source} for landscape or portrait video"
        self._fitter = fitter

    async def run(self, video_path: str) -> dict[str, Any]:
        bounds = await self._fitter.fit(Path(video_path))
        if bounds is None:
            return {"fitted": False, "reason": "video size unknown"}
        return {"fitted": True, "x": bounds.x, "y": bounds.y, "width": bounds.width, "height": bounds.height}
