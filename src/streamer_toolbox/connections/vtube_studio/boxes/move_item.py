from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_item_actions import VtsItemActions


class MoveItem(Box):
    name = "move_item"
    label = "Move item"
    help = "Moves a loaded item (instance id from Load item) over some seconds; size / rotation -1000 keep them"
    group = "Items"

    def __init__(self, vts_item: "VtsItemActions") -> None:
        self._vts_item = vts_item

    async def run(self, instance: str, x: float, y: float, size: float = -1000, rotation: float = -1000,
                  seconds: float = 1.0) -> None:
        return await self._vts_item.move_item(instance, x, y, size, rotation, seconds)
