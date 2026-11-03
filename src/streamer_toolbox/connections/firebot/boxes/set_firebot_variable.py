from typing import Any
from urllib.parse import quote

from streamer_toolbox.connections.firebot.boxes.firebot_box import FirebotBox, _named


class SetFirebotVariable(FirebotBox):
    name = "set_variable"
    label = "Set Firebot variable"
    help = "Sets a Firebot custom variable"
    group = "Variables"
    hints = {"seconds": "Optional: Firebot forgets it after this long (0 = never)"}

    async def run(self, name: str, value: Any = "", seconds: float = 0) -> None:
        await self._send("POST", f"custom-variables/{quote(_named(name))}",
                         json={"data": value, "ttl": max(int(float(seconds)), 0)})
