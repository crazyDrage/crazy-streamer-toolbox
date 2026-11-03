from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.interfaces.video_probe import VideoProbe


class VideoBox(Box):
    """What the video boxes share (not a box itself: it has no run).

    Video boxes that read the file itself, no OBS needed: Video info (size and length)."""

    def __init__(self, probe: VideoProbe) -> None:
        self._probe = probe
