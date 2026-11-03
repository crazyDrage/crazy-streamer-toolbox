from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_item_actions import VtsItemActions


class RemoveItems(Box):
    name = "remove_items"
    label = "Remove items"
    help = "Removes an item by instance id (from Load item), or all items the toolbox loaded when left empty"
    group = "Items"

    def __init__(self, vts_item: "VtsItemActions") -> None:
        self._vts_item = vts_item

    async def run(self, instance: str = "") -> int:
        return await self._vts_item.remove_items(instance)
