from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from streamer_toolbox.core.media.video_size import VideoSize


class VideoProbe(ABC):
    """Finds the display size and length of a video file without playing it."""

    @abstractmethod
    def probe(self, path: Path) -> Optional[VideoSize]:
        """Return the display size, or None when this probe can't read the file."""

    @abstractmethod
    def length(self, path: Path) -> Optional[float]:
        """Return how long the video plays, in seconds, or None when this probe can't read it."""
