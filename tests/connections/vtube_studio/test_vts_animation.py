import unittest

from streamer_toolbox.connections.vtube_studio.vts_animation import VtsAnimation
from streamer_toolbox.connections.vtube_studio.vts_position import VtsPosition

FIXED = {"relative": False, "steps": [
    {"x": 0.0, "y": -0.5, "rotation": 0.0, "size": -50.0, "seconds": 1.0, "wait": 0.0},
    {"x": 0.4, "y": -0.3, "rotation": 15.0, "size": -50.0, "seconds": 0.5, "wait": 2.0}]}


class TestVtsAnimation(unittest.TestCase):
    def test_reads_and_writes_what_the_box_keeps(self) -> None:
        animation = VtsAnimation.from_dict(FIXED)
        self.assertEqual(len(animation.steps), 2)
        self.assertEqual(animation.seconds, 3.5)
        self.assertEqual(animation.to_dict(), FIXED)

    def test_empty_is_no_steps(self) -> None:
        self.assertEqual(VtsAnimation.from_dict("").steps, ())
        self.assertEqual(VtsAnimation.from_dict(None).steps, ())

    def test_fixed_to_relative_from_step_one_and_back_from_somewhere_else(self) -> None:
        animation = VtsAnimation.from_dict(FIXED)
        relative = animation.as_relative(animation.steps[0].position)
        self.assertTrue(relative.relative)
        self.assertEqual(relative.steps[0].position, VtsPosition(0, 0, 0, 0))
        self.assertAlmostEqual(relative.steps[1].position.x, 0.4)
        self.assertAlmostEqual(relative.steps[1].position.y, 0.2)
        self.assertEqual(relative.steps[1].wait, 2.0)  # times stay
        moved = relative.as_fixed(VtsPosition(-0.6, 0.1, 0, -20))
        self.assertFalse(moved.relative)
        self.assertAlmostEqual(moved.steps[1].position.x, -0.2)
        self.assertAlmostEqual(moved.steps[1].position.y, 0.3)
        self.assertEqual(moved.steps[1].position.rotation, 15)
        self.assertEqual(moved.steps[1].position.size, -20)

    def test_relative_steps_play_from_the_start_spot(self) -> None:
        relative = VtsAnimation.from_dict({**FIXED, "relative": True})
        start = VtsPosition(0.1, 0.1, 0, 0)
        target = relative.target(relative.steps[1], start)
        self.assertAlmostEqual(target.x, 0.5)
        self.assertAlmostEqual(target.y, -0.2)
        fixed = VtsAnimation.from_dict(FIXED)
        self.assertEqual(fixed.target(fixed.steps[1], start), fixed.steps[1].position)

    def test_base_is_kept(self) -> None:
        data = {**FIXED, "relative": True, "base": {"x": 0.1, "y": 0.2, "rotation": 0.0, "size": 5.0}}
        self.assertEqual(VtsAnimation.from_dict(data).base, VtsPosition(0.1, 0.2, 0, 5))
        self.assertEqual(VtsAnimation.from_dict(data).to_dict(), data)
