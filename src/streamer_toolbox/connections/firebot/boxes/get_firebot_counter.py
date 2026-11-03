from typing import Any
from urllib.parse import quote

from streamer_toolbox.connections.firebot.boxes.firebot_box import FirebotBox, Send, _find


class GetFirebotCounter(FirebotBox):
    name = "get_counter"
    label = "Get Firebot counter"
    help = "The value of a Firebot counter"
    group = "Counters"
    outputs = {"value": "number"}

    def __init__(self, send: Send) -> None:
        super().__init__(send)
        self.options = {"counter": self.counter_names}

    async def run(self, counter: str) -> dict[str, Any]:
        counter_id = _find(await self._by_name("counters"), counter, "counter")
        answer = await self._send("GET", f"counters/{quote(counter_id)}")
        return {"value": answer.get("value", 0) if isinstance(answer, dict) else 0}
