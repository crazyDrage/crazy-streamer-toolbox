from typing import TYPE_CHECKING, Any

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_look_actions import VtsLookActions


class SetEffectValue(Box):
    name = "set_effect"
    label = "Set effect value"
    help = "Sets one visual effect setting (e.g. Bloom_Strength 0.8; a *_Strength above 0 turns that effect on)"
    labels = {"only_this": "Others back to default"}
    hints = {"value": "a number, true / false, or a colour like FF0000FF, as the setting needs",
             "fade": "0 to 2 seconds", "only_this": "on: every other effect fades off"}
    group = "Visual effects"

    def __init__(self, vts_look: "VtsLookActions") -> None:
        self._vts_look = vts_look
        self.options = {"setting": self._vts_look.effect_settings}

    async def run(self, setting: str, value: Any, fade: float = 0.5, only_this: bool = False) -> None:
        return await self._vts_look.set_effect(setting, value, fade, only_this)
