from typing import Any

from streamer_toolbox.connections.vnyan.boxes.vnyan_box import VnyanBox, _payload


class SendApiMessageToVNyan(VnyanBox):
    name = "api_message"
    label = "Send API message to VNyan"
    help = 'Sends an API message to VNyan: its "API Message" node with the same Action runs and gets the values'
    hints = {"action": "The node's Action, exactly as written in VNyan",
             "values": 'Optional: an object like {"color": "red"}; the node gets it as a '
                       'dictionary'}

    async def run(self, action: str, values: Any = None) -> None:
        action = str(action).strip()
        if not action:
            raise ValueError("Which action? It is the Action of an API Message node in VNyan")
        await self._send_api({"action": action, "payload": _payload(values)})
