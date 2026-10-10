import asyncio
import itertools
import math
from collections.abc import Awaitable, Callable

from streamer_toolbox.connections.vtube_studio.vts_animation import VtsAnimation
from streamer_toolbox.connections.vtube_studio.vts_position import VtsPosition
from streamer_toolbox.core.interfaces.model_mover import ModelMover

LONGEST_MOVE = 2.0  # seconds VTS takes for one move at most
FRAMES_PER_SECOND = 30
# VTS ends a move a little after its time: read right away, the next "where is the model" is off a bit, and a
# relative animation played again and again (Loop) creeps (seen on the real VTS: ~0.00005 per round, 0 with this)
SETTLE = 0.15


class VtsAnimationPlayer:
    """Plays a VtsAnimation on the model and returns when it's done.

    A step up to 2 seconds is one VTS move (VTS eases it in and out). A longer one is sent as frames (a jump every
    1/30 s, eased the same way), because VTS takes 2 seconds at most per move. `forever` plays it until the task
    is cancelled; `start` is where the model was when it began (to go back there after a stop)."""

    def __init__(self, mover: ModelMover, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep) -> None:
        self._mover = mover
        self._sleep = sleep
        self.start: VtsPosition | None = None

    async def play(self, animation: VtsAnimation, repeat: int = 1, back_to_start: bool = False,
                   back_seconds: float = 1.0, forever: bool = False) -> VtsPosition:
        """Plays it repeat times (at least once) or forever, then back to where the model started if asked.
        Returns where it started."""
        if forever and animation.steps and animation.seconds <= 0:
            raise ValueError("a looping animation needs some seconds or wait in its steps")
        start = here = self.start = await self._mover.position()
        for _ in itertools.count() if forever and animation.steps else range(max(1, repeat)):
            for step in animation.steps:
                here = await self._go(here, animation.target(step, start), step.seconds)
                if step.wait > 0:
                    await self._sleep(step.wait)
        if back_to_start and animation.steps:
            await self.go_back(back_seconds, here)
        if animation.steps:
            await self._sleep(SETTLE)
        return start

    async def go_back(self, seconds: float = 1.0, here: VtsPosition | None = None) -> None:
        """To where the model was when the animation began (after it ended or was stopped)."""
        if self.start is not None:
            await self._go(here or await self._mover.position(), self.start, seconds)

    async def _go(self, here: VtsPosition, there: VtsPosition, seconds: float) -> VtsPosition:
        there = there.turned_near(here.rotation)
        seconds = max(0.0, seconds)
        if seconds <= LONGEST_MOVE:
            await self._mover.move(there, seconds)
            await self._sleep(seconds)
            return there
        frames = math.ceil(seconds * FRAMES_PER_SECOND)
        for frame in range(1, frames + 1):
            part = (1 - math.cos(math.pi * frame / frames)) / 2  # slow, fast, slow, like a VTS move
            await self._mover.move(here.towards(there, part), 0)
            await self._sleep(seconds / frames)
        return there
