from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_look_actions import VtsLookActions


class RandomEffects(Box):
    name = "random_effects"
    label = "Random effects"
    help = "Random visual effects, for fun: chaos 0 = mild, 1 = complete chaos (0.4 to 0.5 looks good)"
    group = "Visual effects"

    def __init__(self, vts_look: "VtsLookActions") -> None:
        self._vts_look = vts_look

    async def run(self, chaos: float = 0.45) -> None:
        return await self._vts_look.random_effects(chaos)
