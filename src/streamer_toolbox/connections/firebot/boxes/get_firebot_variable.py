from typing import Any
from urllib.parse import quote

from streamer_toolbox.connections.firebot.boxes.firebot_box import FirebotBox, _named


class GetFirebotVariable(FirebotBox):
    name = "get_variable"
    label = "Get Firebot variable"
    help = "The value of a Firebot custom variable"
    group = "Variables"
    outputs = {"value": "text"}
    hints = {"name": "A variable Firebot doesn't have gives an empty value"}

    async def run(self, name: str) -> dict[str, Any]:
        # Firebot answers with the value itself (text, a number, an object, ...), and with nothing at all
        # for a variable it doesn't have (seen on the real program, 2026-10-11)
        answer = await self._send("GET", f"custom-variables/{quote(_named(name))}")
        return {"value": "" if answer is None else answer}
