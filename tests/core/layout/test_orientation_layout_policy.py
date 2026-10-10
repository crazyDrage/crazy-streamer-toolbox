import unittest

from streamer_toolbox.core.layout.box import Box
from streamer_toolbox.core.layout.orientation_layout_policy import OrientationLayoutPolicy
from streamer_toolbox.core.media.video_size import VideoSize

LANDSCAPE_BOUNDS = Box(x=1300, y=700, width=576, height=324)
PORTRAIT_BOUNDS = Box(x=1500, y=100, width=400, height=900)


class TestOrientationLayoutPolicy(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = OrientationLayoutPolicy(LANDSCAPE_BOUNDS, PORTRAIT_BOUNDS)

    def test_landscape_video_gets_landscape_bounds(self) -> None:
        self.assertEqual(self.policy.bounds_for(VideoSize(1920, 1080)), LANDSCAPE_BOUNDS)

    def test_portrait_video_gets_portrait_bounds(self) -> None:
        self.assertEqual(self.policy.bounds_for(VideoSize(1080, 1920)), PORTRAIT_BOUNDS)

    def test_square_defaults_to_landscape_bounds(self) -> None:
        self.assertEqual(self.policy.bounds_for(VideoSize(500, 500)), LANDSCAPE_BOUNDS)

    def test_square_bounds_override(self) -> None:
        square = Box(0, 0, 300, 300)
        policy = OrientationLayoutPolicy(LANDSCAPE_BOUNDS, PORTRAIT_BOUNDS, square_bounds=square)
        self.assertEqual(policy.bounds_for(VideoSize(500, 500)), square)


if __name__ == "__main__":
    unittest.main()
