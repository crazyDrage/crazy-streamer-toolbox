from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.interfaces.video_probe import VideoProbe
from streamer_toolbox.core.media.boxes.video_info import VideoInfo


class VideoActions:
    """Video boxes that read the file itself, no OBS needed: Video info (size and length).

    One Box class per box, in boxes/."""

    def __init__(self, probe: VideoProbe) -> None:
        self._probe = probe

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (VideoInfo(self._probe),):
            actions.add_box(box, "video")
