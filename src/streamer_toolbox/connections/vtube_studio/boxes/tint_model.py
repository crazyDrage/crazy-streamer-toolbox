from typing import TYPE_CHECKING

from streamer_toolbox.connections.vtube_studio.boxes.vts_look_shared import _color_names
from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_look_actions import VtsLookActions


class TintModel(Box):
    name = "tint"
    label = "Tint model"
    help = "Tints the model, or the parts whose name has one of the words (darker only: white = as it was)"
    options = {"color": _color_names}
    colors = ("color",)
    labels = {"parts": "Parts by word", "picked": "Picked parts"}
    hints = {"color": "a name (red, orange, ...), the colour picker, or hex like FF8800 / "
                      "#FF880080 (with alpha)",
             "parts": "words like hair, eye: any part whose name has one. Both parts fields "
                      "empty = the whole model",
             "picked": "exact parts of the loaded model, ticked in the list (the button)",
             "lighting": "1 = your colour wins over VTS's scene lighting, 0 = the lighting wins"}
    outputs = {"parts_tinted": "number"}
    group = "Look"

    def __init__(self, vts_look: "VtsLookActions") -> None:
        self._vts_look = vts_look
        self.many = {"picked": self._vts_look.part_names}
        self.lights = {"picked": self._vts_look.light_part}

    async def run(self, color: str = "red", parts: str = "", picked: str = "",
                  lighting: float = 1.0) -> dict[str, int]:
        return await self._vts_look.tint(color, parts, picked, lighting)
