from typing import TYPE_CHECKING, Any

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vts_connection import VtsConnection


class MoveModelToSavedPosition(Box):
    name = "move_to_position"
    label = "Move model to saved position"
    help = "Moves the loaded model to one of its saved positions (old way; variables replace it)"
    group = "Model position"
    capture = "vts.save_position"

    def __init__(self, vts: "VtsConnection") -> None:
        self._vts = vts
        self.options = {"position": self._vts.position_names}

    async def run(self, position: str, seconds: float = 1.0) -> dict[str, Any]:
        return await self._vts.move_to_position(position, seconds)
