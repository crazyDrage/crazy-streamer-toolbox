from typing import Any
from urllib.parse import quote

from streamer_toolbox.connections.firebot.boxes.firebot_box import FirebotBox, Send, _find, _number


class SetFirebotCounter(FirebotBox):
    name = "set_counter"
    label = "Set Firebot counter"
    help = "Sets a Firebot counter, or adds to it"
    group = "Counters"
    outputs = {"value": "number"}
    hints = {"add": "Yes: the value is added (a minus takes away). No: the counter becomes it"}

    def __init__(self, send: Send) -> None:
        super().__init__(send)
        self.options = {"counter": self.counter_names}

    async def run(self, counter: str, value: float = 1, add: bool = False) -> dict[str, Any]:
        counter_id = _find(await self._by_name("counters"), counter, "counter")
        answer = await self._send("POST", f"counters/{quote(counter_id)}",
                                  json={"value": _number(value), "override": not add})
        return {"value": answer.get("newValue", 0) if isinstance(answer, dict) else 0}
