from typing import TYPE_CHECKING, Any

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vts_connection import VtsConnection


class SaveModelPosition(Box):
    name = "save_position"
    label = "Save model position"
    help = "Saves where the loaded model is now under a name (old way; variables replace it)"
    group = "Model position"

    def __init__(self, vts: "VtsConnection") -> None:
        self._vts = vts
        self.options = {"position": self._vts.position_names}

    async def run(self, position: str) -> dict[str, Any]:
        return await self._vts.save_position(position)
