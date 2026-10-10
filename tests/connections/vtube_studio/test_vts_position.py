import unittest

from streamer_toolbox.connections.vtube_studio.vts_position import VtsPosition


class TestVtsPosition(unittest.TestCase):
    def test_minus_then_plus_gives_the_spot_back(self) -> None:
        a, b = VtsPosition(0.5, -0.2, 30.0, -40.0), VtsPosition(0.1, 0.3, 10.0, -50.0)
        change = a.minus(b)
        self.assertEqual(change, VtsPosition(0.4, -0.5, 20.0, 10.0))
        back = b.plus(change)
        for got, want in zip(back.to_dict().values(), a.to_dict().values()):
            self.assertAlmostEqual(got, want)

    def test_rotation_changes_go_the_short_way(self) -> None:
        self.assertEqual(VtsPosition(0, 0, 10, 0).minus(VtsPosition(0, 0, 350, 0)).rotation, 20)
        self.assertEqual(VtsPosition(0, 0, 350, 0).minus(VtsPosition(0, 0, 10, 0)).rotation, -20)
        self.assertEqual(VtsPosition(0, 0, 350, 0).plus(VtsPosition(0, 0, 20, 0)).rotation, 10)

    def test_turned_near_picks_the_close_way_of_writing_an_angle(self) -> None:
        self.assertEqual(VtsPosition(0, 0, 10, 0).turned_near(-20).rotation, 10)
        self.assertEqual(VtsPosition(0, 0, -10, 0).turned_near(350).rotation, 350)
        self.assertEqual(VtsPosition(0, 0, 90, 0).turned_near(0).rotation, 90)

    def test_towards(self) -> None:
        half = VtsPosition(0, 0, 0, -50).towards(VtsPosition(1, -1, 90, 50), 0.5)
        self.assertEqual(half, VtsPosition(0.5, -0.5, 45, 0))
        self.assertEqual(VtsPosition(0, 0, 350, 0).towards(VtsPosition(0, 0, 10, 0), 0.5).rotation, 0)
