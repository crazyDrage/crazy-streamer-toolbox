from typing import TYPE_CHECKING, Any

from streamer_toolbox.connections.vtube_studio.boxes.vts_item_shared import (EXACT_SPOT, PIN_HINTS, PIN_LABELS,
                                                                             PIN_SHOWN, _angle_from, _pin_spots,
                                                                             _pin_to)
from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_item_actions import VtsItemActions


class AddItemPinnedToModel(Box):
    name = "add_pinned_item"
    label = "Add item pinned to model"
    help = "Puts an item (a file from VTS's Items folder) onto the model in one step: loads it and pins its " \
           "middle on the exact spot (or on a model part). Gives its instance id, for Remove items / Unpin item"
    group = "Items"
    capture = "vts.record_pin_spot:saved_spot"
    outputs = {"instance": "text", "pinned": "yes/no"}
    shown = PIN_SHOWN
    labels = {**PIN_LABELS, "seconds": "Fade in (s)"}
    hints = {**PIN_HINTS, "size": "0 to 1, like Load item", "angle": "degrees",
             "order": "higher = in front of other items"}

    def __init__(self, vts_item: "VtsItemActions") -> None:
        self._vts_item = vts_item
        self.options = {"file": self._vts_item.item_files, "pin_to": _pin_to,
                        "art_mesh": self._vts_item.art_mesh_names,
                        "spot": _pin_spots, "angle_from": _angle_from}

    async def run(self, file: str, pin_to: str = EXACT_SPOT, saved_spot: dict[str, Any] | None = None,
                  art_mesh: str = "", spot: str = "center", size: float = 0.3, angle: float = 0.0,
                  angle_from: str = "model", order: int = 10, seconds: float = 0.5) -> dict[str, Any]:
        return await self._vts_item.add_pinned_item(file, pin_to, saved_spot, art_mesh, spot, size, angle, angle_from, order, seconds)
