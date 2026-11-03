from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_look_actions import VtsLookActions


class IsFaceFound(Box):
    name = "face_found"
    label = "Is face found"
    help = "Whether the tracker sees your face now (true / false)"
    live = True
    group = "Model"

    def __init__(self, vts_look: "VtsLookActions") -> None:
        self._vts_look = vts_look

    async def run(self) -> bool:
        return await self._vts_look.face_found()
