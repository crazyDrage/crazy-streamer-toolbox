from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_item_actions import VtsItemActions


class UnpinItem(Box):
    name = "unpin_item"
    label = "Unpin item"
    help = "Unpins an item from the model; it stays where it is"
    group = "Items"

    def __init__(self, vts_item: "VtsItemActions") -> None:
        self._vts_item = vts_item

    async def run(self, instance: str) -> bool:
        return await self._vts_item.unpin_item(instance)
