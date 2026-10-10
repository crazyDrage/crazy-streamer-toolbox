from dataclasses import dataclass

from streamer_toolbox.core.media.video_size import VideoSize


@dataclass(frozen=True)
class Box:
    """A rectangle on the OBS canvas, in canvas pixels."""

    x: float
    y: float
    width: float
    height: float

    def fit_inside(self, size: VideoSize) -> "Box":
        """The largest rectangle with the video's aspect ratio that fits in this box, centred.

        This matches what OBS does for a scene item with bounds type OBS_BOUNDS_SCALE_INNER
        and centre bounds alignment.
        """
        scale = min(self.width / size.width, self.height / size.height)
        width = size.width * scale
        height = size.height * scale
        return Box(
            x=self.x + (self.width - width) / 2,
            y=self.y + (self.height - height) / 2,
            width=width,
            height=height,
        )
