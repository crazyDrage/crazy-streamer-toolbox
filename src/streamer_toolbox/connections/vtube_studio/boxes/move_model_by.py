from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vts_connection import VtsConnection


class MoveModelBy(Box):
    name = "move_model_by"
    label = "Move model by (from where it is)"
    help = "Moves the model from where it is now, e.g. x -0.2 = a bit to the left (the screen is -1 to 1 wide). " \
           "0 = keep that one"
    group = "Model position"
    offered = False  # Move model with "from where it is" does this now (his round 60, A); old flows keep it

    def __init__(self, vts: "VtsConnection") -> None:
        self._vts = vts

    async def run(self, x: float = 0.0, y: float = 0.0, rotation: float = 0.0, size: float = 0.0,
                  seconds: float = 1.0) -> None:
        return await self._vts.move_by(x, y, rotation, size, seconds)
