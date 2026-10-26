from typing import TYPE_CHECKING

from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vts_connection import VtsConnection


class StopModelAnimation(Box):
    name = "stop_animation"
    label = "Stop model animation"
    help = "Stops the model animation that's playing (also one that loops forever). Gives true if one was playing"
    group = "Model position"
    labels = {"back_to_start": "Back to the start", "back_seconds": "Seconds to go back"}
    hints = {"back_to_start": "Then go back to where the model was when that animation began"}

    def __init__(self, vts: "VtsConnection") -> None:
        self._vts = vts

    async def run(self, back_to_start: bool = False, back_seconds: float = 1.0) -> bool:
        return await self._vts.stop_animation(to_bool(back_to_start), float(back_seconds))
