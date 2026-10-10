from pathlib import Path
from typing import Optional

from streamer_toolbox.core.interfaces.video_probe import VideoProbe
from streamer_toolbox.core.media.video_size import VideoSize


class FakeVideoProbe(VideoProbe):
    """Returns sizes (and lengths, if given) from dicts keyed by file name."""

    def __init__(self, sizes: dict[str, VideoSize], lengths: dict[str, float] | None = None) -> None:
        self._sizes = sizes
        self._lengths = lengths or {}

    def probe(self, path: Path) -> Optional[VideoSize]:
        return self._sizes.get(path.name)

    def length(self, path: Path) -> Optional[float]:
        return self._lengths.get(path.name)
