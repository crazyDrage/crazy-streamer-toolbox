from typing import TYPE_CHECKING, Any

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_look_actions import VtsLookActions


class VtsStats(Box):
    name = "get_stats"
    label = "VTS stats"
    help = "VTube Studio's numbers: FPS, version, minutes running, plugins"
    live = True
    outputs = {"fps": "number", "version": "text", "minutes": "number",
               "plugins": "number"}
    group = "Model"

    def __init__(self, vts_look: "VtsLookActions") -> None:
        self._vts_look = vts_look

    async def run(self) -> dict[str, Any]:
        return await self._vts_look.stats()
