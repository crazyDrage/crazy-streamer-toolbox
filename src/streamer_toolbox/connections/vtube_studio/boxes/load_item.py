from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_item_actions import VtsItemActions


class LoadItem(Box):
    name = "load_item"
    label = "Load item"
    help = "Puts an item (a file from VTS's Items folder) into the scene; x/y from -1 to 1 like the model. " \
           "Returns its instance id"
    group = "Items"

    def __init__(self, vts_item: "VtsItemActions") -> None:
        self._vts_item = vts_item
        self.options = {"file": self._vts_item.item_files}

    async def run(self, file: str, x: float = 0.0, y: float = 0.0, size: float = 0.3, rotation: float = 0.0,
                  order: int = 10, seconds: float = 0.5) -> str:
        return await self._vts_item.load_item(file, x, y, size, rotation, order, seconds)
