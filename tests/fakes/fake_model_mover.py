import asyncio

from streamer_toolbox.connections.vtube_studio.vts_position import VtsPosition
from streamer_toolbox.core.interfaces.model_mover import ModelMover


class FakeModelMover(ModelMover):
    """A model that only remembers: `moves` = (position, seconds) per move, `timeline` = moves and waits in order
    ("move" / "sleep", ...). sleep() is the fake clock to hand to the player."""

    def __init__(self, start: VtsPosition) -> None:
        self.at = start
        self.moves: list[tuple[VtsPosition, float]] = []
        self.timeline: list[tuple[str, object]] = []

    async def position(self) -> VtsPosition:
        return self.at

    async def move(self, position: VtsPosition, seconds: float = 1.0) -> None:
        self.at = position
        self.moves.append((position, seconds))
        self.timeline.append(("move", seconds))

    async def sleep(self, seconds: float) -> None:
        self.timeline.append(("sleep", seconds))
        await asyncio.sleep(0)  # a real pause point: a loop forever can be cancelled
