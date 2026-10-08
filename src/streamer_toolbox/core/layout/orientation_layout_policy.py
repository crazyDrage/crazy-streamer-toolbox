from streamer_toolbox.core.layout.box import Box
from streamer_toolbox.core.interfaces.layout_policy import LayoutPolicy
from streamer_toolbox.core.media.orientation import Orientation
from streamer_toolbox.core.media.video_size import VideoSize


class OrientationLayoutPolicy(LayoutPolicy):
    """Gives the source one set of bounds for landscape videos and another for portrait ones.

    Square videos use the landscape bounds unless square bounds are given.
    """

    def __init__(self, landscape_bounds: Box, portrait_bounds: Box, square_bounds: Box | None = None) -> None:
        self._bounds = {
            Orientation.LANDSCAPE: landscape_bounds,
            Orientation.PORTRAIT: portrait_bounds,
            Orientation.SQUARE: square_bounds or landscape_bounds,
        }

    def bounds_for(self, size: VideoSize) -> Box:
        return self._bounds[size.orientation]
