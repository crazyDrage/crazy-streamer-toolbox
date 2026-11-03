from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_look_actions import VtsLookActions


class HoldParameter(Box):
    name = "hold_parameter"
    label = "Hold parameter"
    help = "Holds a tracking parameter (e.g. MouthOpen, FaceAngleX) at a value for some seconds, over what the " \
           "tracking says"
    hints = {"seconds": "how long; the box waits that long",
             "weight": "0 to 1: how much of the value is used (1 = all)"}
    group = "Parameters"

    def __init__(self, vts_look: "VtsLookActions") -> None:
        self._vts_look = vts_look
        self.options = {"parameter": self._vts_look.parameter_names}

    async def run(self, parameter: str, value: float, seconds: float = 2.0, weight: float = 1.0) -> None:
        return await self._vts_look.hold_parameter(parameter, value, seconds, weight)
