from typing import TYPE_CHECKING, Any

from streamer_toolbox.connections.vtube_studio.boxes.vts_item_shared import (EXACT_SPOT, PIN_HINTS, PIN_LABELS,
                                                                             PIN_SHOWN, _angle_from, _pin_spots,
                                                                             _pin_to)
from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_item_actions import VtsItemActions


class PinItemToModel(Box):
    name = "pin_item"
    label = "Pin item to model"
    help = "Pins a loaded item onto the model: its middle goes on an exact spot (Save current: click the model " \
           "in VTS), or on a model part (its center or a random spot). Angle and size empty = it keeps the ones " \
           "it has"
    group = "Items"
    capture = "vts.record_pin_spot:saved_spot"
    shown = PIN_SHOWN
    labels = {**PIN_LABELS, "instance": "Item"}
    hints = {**PIN_HINTS, "instance": "The instance id Load item gives: wire it from that box "
                                      "(Wire from a box)",
             "angle": "degrees; empty = keep the item's angle",
             "size": "0 to 1; empty = keep the item's size"}

    def __init__(self, vts_item: "VtsItemActions") -> None:
        self._vts_item = vts_item
        self.options = {"pin_to": _pin_to, "art_mesh": self._vts_item.art_mesh_names, "spot": _pin_spots,
                        "angle_from": _angle_from}

    async def run(self, instance: str, pin_to: str = EXACT_SPOT, saved_spot: dict[str, Any] | None = None,
                  art_mesh: str = "", spot: str = "center", angle: Any = "", angle_from: str = "item",
                  size: Any = "") -> bool:
        return await self._vts_item.pin_item(instance, pin_to, saved_spot, art_mesh, spot, angle, angle_from, size)
