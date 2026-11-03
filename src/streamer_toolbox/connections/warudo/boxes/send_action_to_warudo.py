import json
from typing import Any

from streamer_toolbox.connections.warudo.boxes.warudo_box import WarudoBox, _value


class SendActionToWarudo(WarudoBox):
    name = "send"
    label = "Send action to Warudo"
    help = 'Sends an action to Warudo: the blueprint that starts with an "On WebSocket Action" node of the same ' \
           "Action Name runs"
    hints = {"action": "The node's Action Name, exactly as written in Warudo",
             "data": "Optional: the value the node gives out (text or a number, as the node's "
                     "type says)"}

    async def run(self, action: str, data: Any = "") -> None:
        action = str(action).strip()
        if not action:
            raise ValueError("Which action? It is the Action Name of an On WebSocket Action node in Warudo")
        message: dict[str, Any] = {"action": action}
        if data not in (None, ""):
            message["data"] = _value(data)
        await self._send_text(json.dumps(message, ensure_ascii=False))
