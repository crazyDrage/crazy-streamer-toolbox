from dataclasses import dataclass

from streamer_toolbox.core.media.orientation import Orientation


@dataclass(frozen=True)
class VideoSize:
    """Display size of a video, after any rotation flag has been applied."""

    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"video size must be positive, got {self.width}x{self.height}")

    @property
    def orientation(self) -> Orientation:
        if self.width > self.height:
            return Orientation.LANDSCAPE
        if self.height > self.width:
            return Orientation.PORTRAIT
        return Orientation.SQUARE
