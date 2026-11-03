from typing import TYPE_CHECKING, Any

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vtube_studio.vts_look_actions import VtsLookActions


class PhysicsWind(Box):
    name = "physics"
    label = "Physics / wind"
    help = "Physics strength and / or wind (0 to 100) for some seconds; then back to your own settings"
    hints = {"strength": "0 to 100, empty = as it is", "wind": "0 to 100, empty = as it is",
             "seconds": "how long; the box waits that long"}
    group = "Look"

    def __init__(self, vts_look: "VtsLookActions") -> None:
        self._vts_look = vts_look

    async def run(self, strength: Any = "", wind: Any = "", seconds: float = 5.0) -> None:
        return await self._vts_look.physics(strength, wind, seconds)
