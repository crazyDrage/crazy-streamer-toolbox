import unittest

from streamer_toolbox.core.layout.box import Box
from streamer_toolbox.core.media.video_size import VideoSize


class TestBoxFitInside(unittest.TestCase):
    def test_portrait_video_in_landscape_box_is_pillarboxed(self) -> None:
        fitted = Box(0, 0, 576, 324).fit_inside(VideoSize(1080, 1920))
        self.assertAlmostEqual(fitted.height, 324)
        self.assertAlmostEqual(fitted.width, 182.25)
        self.assertAlmostEqual(fitted.x, (576 - 182.25) / 2)
        self.assertAlmostEqual(fitted.y, 0)

    def test_matching_aspect_fills_box(self) -> None:
        box = Box(10, 20, 576, 324)
        self.assertEqual(box.fit_inside(VideoSize(1920, 1080)), box)


if __name__ == "__main__":
    unittest.main()
