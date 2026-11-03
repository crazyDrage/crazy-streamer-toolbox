from typing import TYPE_CHECKING

from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vts_connection import VtsConnection


class MoveModelNumbers(Box):
    name = "move_model"
    label = "Move model"
    help = "Moves the model to exact values (an empty one stays as it is, e.g. only x = only sideways), or with " \
           "\"from where it is\" on by that much from where it is now (x -0.2 = a bit to the left; empty = 0)"
    group = "Model position"
    hints = {"from_where_it_is": "On: the numbers are added to where the model is now"}

    def __init__(self, vts: "VtsConnection") -> None:
        self._vts = vts

    async def run(self, x: float | None = None, y: float | None = None, rotation: float | None = None,
                  size: float | None = None, seconds: float = 1.0, from_where_it_is: bool = False) -> None:
        """One box for both ways (his round 60, A); Move model by stays for flows that have it."""
        if to_bool(from_where_it_is):
            return await self._vts.move_by(x or 0.0, y or 0.0, rotation or 0.0, size or 0.0, seconds)
        return await self._vts.move_some(x, y, rotation, size, seconds)
