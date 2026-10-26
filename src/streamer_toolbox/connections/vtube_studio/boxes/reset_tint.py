from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_look_actions import VtsLookActions


class ResetTint(Box):
    name = "reset_tint"
    label = "Reset tint"
    help = "Takes the tint away again (whole model or parts)"
    labels = {"parts": "Parts by word", "picked": "Picked parts"}
    hints = {"parts": "both parts fields empty = the whole model",
             "picked": "exact parts of the loaded model, ticked in the list (the button)"}
    group = "Look"

    def __init__(self, vts_look: "VtsLookActions") -> None:
        self._vts_look = vts_look
        self.many = {"picked": self._vts_look.part_names}
        self.lights = {"picked": self._vts_look.light_part}

    async def run(self, parts: str = "", picked: str = "") -> None:
        return await self._vts_look.reset_tint(parts, picked)
