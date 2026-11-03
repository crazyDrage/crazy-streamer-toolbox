from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vts_connection import VtsConnection


class GetLoadedModel(Box):
    name = "get_model"
    label = "Get loaded model"
    help = "The name of the loaded model"
    group = "Model"
    live = True

    def __init__(self, vts: "VtsConnection") -> None:
        self._vts = vts

    async def run(self) -> str:
        return (await self._vts.current_model())[0]
