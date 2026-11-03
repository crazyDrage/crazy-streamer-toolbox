from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_look_actions import VtsLookActions


class GetParameter(Box):
    name = "get_parameter"
    label = "Get parameter"
    help = "A tracking parameter's value now (and its range)"
    outputs = {"value": "number", "min": "number", "max": "number"}
    group = "Parameters"

    def __init__(self, vts_look: "VtsLookActions") -> None:
        self._vts_look = vts_look
        self.options = {"parameter": self._vts_look.parameter_names}

    async def run(self, parameter: str) -> dict[str, float]:
        return await self._vts_look.get_parameter(parameter)
