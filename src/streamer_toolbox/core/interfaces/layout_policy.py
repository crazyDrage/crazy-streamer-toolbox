from abc import ABC, abstractmethod

from streamer_toolbox.core.layout.box import Box
from streamer_toolbox.core.media.video_size import VideoSize


class LayoutPolicy(ABC):
    """Decides the bounds of an existing OBS source for a video of a given size.

    The same source is reused for every video; only its transform (position and bounds) changes.
    """

    @abstractmethod
    def bounds_for(self, size: VideoSize) -> Box:
        """The bounding box the source should get so the video fits."""
