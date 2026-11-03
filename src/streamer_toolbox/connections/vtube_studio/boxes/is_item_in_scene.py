from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_item_actions import VtsItemActions


class IsItemInScene(Box):
    name = "item_in_scene"
    label = "Is item in scene"
    help = "Whether an item file is in the scene now (true / false, for an If)"
    group = "Items"

    def __init__(self, vts_item: "VtsItemActions") -> None:
        self._vts_item = vts_item
        self.options = {"file": self._vts_item.item_files}

    async def run(self, file: str) -> bool:
        return await self._vts_item.item_in_scene(file)
