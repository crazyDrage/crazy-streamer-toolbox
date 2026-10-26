from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_look_actions import VtsLookActions


class EffectsPreset(Box):
    name = "effects_preset"
    label = "Effects preset"
    help = "Loads a visual effects (VFX) preset you saved in VTube Studio, fading over 'fade' seconds"
    hints = {"fade": "0 to 2 seconds"}
    group = "Visual effects"

    def __init__(self, vts_look: "VtsLookActions") -> None:
        self._vts_look = vts_look
        self.options = {"preset": self._vts_look.preset_names}

    async def run(self, preset: str, fade: float = 1.0) -> None:
        return await self._vts_look.effects_preset(preset, fade)
