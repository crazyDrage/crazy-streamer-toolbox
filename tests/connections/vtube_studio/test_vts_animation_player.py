import asyncio
import unittest

from streamer_toolbox.connections.vtube_studio.vts_animation import VtsAnimation
from streamer_toolbox.connections.vtube_studio.vts_animation_player import (FRAMES_PER_SECOND, SETTLE,
                                                                         VtsAnimationPlayer)
from streamer_toolbox.connections.vtube_studio.vts_position import VtsPosition
from tests.fakes.fake_model_mover import FakeModelMover

START = VtsPosition(0.0, -0.5, 0.0, -50.0)


def _animation(relative: bool, *steps: tuple[float, float, float, float]) -> VtsAnimation:
    """steps as (x, y, seconds, wait)."""
    return VtsAnimation.from_dict({"relative": relative, "steps": [
        {"x": x, "y": y, "rotation": 0.0, "size": -50.0 if not relative else 0.0, "seconds": s, "wait": w}
        for x, y, s, w in steps]})


class TestVtsAnimationPlayer(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.model = FakeModelMover(START)
        self.player = VtsAnimationPlayer(self.model, self.model.sleep)

    async def test_each_step_is_a_move_then_its_time_then_its_wait(self) -> None:
        await self.player.play(_animation(False, (0.5, 0.0, 1.0, 0.0), (-0.5, 0.0, 0.5, 2.0)))
        self.assertEqual([p.x for p, _ in self.model.moves], [0.5, -0.5])
        self.assertEqual(self.model.timeline, [("move", 1.0), ("sleep", 1.0), ("move", 0.5), ("sleep", 0.5),
                                               ("sleep", 2.0), ("sleep", SETTLE)])

    async def test_relative_steps_start_where_the_model_is(self) -> None:
        await self.player.play(_animation(True, (0.2, 0.1, 0.5, 0.0)))
        position, _ = self.model.moves[0]
        self.assertAlmostEqual(position.x, 0.2)
        self.assertAlmostEqual(position.y, -0.4)
        self.assertEqual(position.size, -50.0)

    async def test_repeat_and_back_to_start(self) -> None:
        await self.player.play(_animation(False, (0.5, 0.0, 0.2, 0.0)), repeat=3, back_to_start=True,
                               back_seconds=1.5)
        self.assertEqual(len(self.model.moves), 4)
        self.assertEqual(self.model.moves[-1], (START, 1.5))

    async def test_a_long_step_is_sent_as_eased_frames(self) -> None:
        await self.player.play(_animation(False, (1.0, -0.5, 3.0, 0.0)))
        self.assertEqual(len(self.model.moves), 3 * FRAMES_PER_SECOND)
        self.assertTrue(all(seconds == 0 for _, seconds in self.model.moves))
        xs = [p.x for p, _ in self.model.moves]
        self.assertAlmostEqual(xs[-1], 1.0)
        self.assertLess(xs[1] - xs[0], xs[46] - xs[45])  # slow at the start, faster in the middle

    async def test_no_steps_does_nothing(self) -> None:
        await self.player.play(VtsAnimation(), back_to_start=True)
        self.assertEqual(self.model.moves, [])

    async def test_forever_loops_until_cancelled_then_can_go_back(self) -> None:
        task = asyncio.create_task(self.player.play(_animation(False, (0.5, 0.0, 0.2, 0.0), (-0.5, 0.0, 0.2, 0.0)),
                                                    forever=True))
        while len(self.model.moves) < 7:
            await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual([p.x for p, _ in self.model.moves[:4]], [0.5, -0.5, 0.5, -0.5])
        await self.player.go_back(0.5)
        self.assertEqual(self.model.moves[-1], (START, 0.5))

    async def test_forever_needs_some_time(self) -> None:
        with self.assertRaises(ValueError):
            await self.player.play(_animation(False, (0.5, 0.0, 0.0, 0.0)), forever=True)
