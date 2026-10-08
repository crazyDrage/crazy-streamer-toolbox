import unittest

from streamer_toolbox.connections.obs.keep_inside import keep_inside


class TestKeepInside(unittest.TestCase):
    def test_a_box_that_fits_stays(self) -> None:
        self.assertEqual(keep_inside(100, 100, 5, 640, 360, 1920, 1080), (100, 100))  # 5 = top left

    def test_a_tall_video_below_the_canvas_moves_up_just_enough(self) -> None:
        self.assertEqual(keep_inside(1600, 500, 5, 300, 900, 1920, 1080), (1600, 180))

    def test_alignment_point_is_kept_as_obs_has_it(self) -> None:
        # centre-aligned (0): the point is the box's middle; right edge sticks out by 100
        self.assertEqual(keep_inside(1870, 540, 0, 300, 300, 1920, 1080), (1770, 540))
        # bottom right (2 + 8): the point is the box's bottom right corner
        self.assertEqual(keep_inside(2000, 1200, 10, 400, 200, 1920, 1080), (1920, 1080))

    def test_bigger_than_the_canvas_goes_to_the_top_left(self) -> None:
        self.assertEqual(keep_inside(300, 300, 5, 2500, 1500, 1920, 1080), (0, 0))


if __name__ == "__main__":
    unittest.main()
