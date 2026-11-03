from typing import TYPE_CHECKING, Any

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_item_actions import VtsItemActions


class RecordPinSpot(Box):
    name = "record_pin_spot"
    label = "Record pin spot"
    help = "Waits for you to click the model in VTube Studio (up to 'seconds') and gives back that exact spot, " \
           "for Pin item's saved_spot. Save it in a variable"
    group = "Items"
    outputs = {"art_mesh": "text", "model": "text"}

    def __init__(self, vts_item: "VtsItemActions") -> None:
        self._vts_item = vts_item

    async def run(self, seconds: float = 20.0) -> dict[str, Any]:
        return await self._vts_item.record_pin_spot(seconds)
