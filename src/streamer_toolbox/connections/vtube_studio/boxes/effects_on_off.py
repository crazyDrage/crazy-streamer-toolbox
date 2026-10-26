from typing import TYPE_CHECKING

from streamer_toolbox.connections.vtube_studio.boxes.vts_look_shared import _states
from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_look_actions import VtsLookActions


class EffectsOnOff(Box):
    name = "effects_on"
    label = "Effects on / off"
    help = "Switches VTube Studio's visual effects on or off (what they are set to stays)"
    options = {"state": _states}
    group = "Visual effects"

    def __init__(self, vts_look: "VtsLookActions") -> None:
        self._vts_look = vts_look

    async def run(self, state: str = "on") -> bool:
        return await self._vts_look.effects_on(state)
