import json
from typing import Any

from streamer_toolbox.connections.vnyan.boxes.vnyan_box import VnyanBox, _payload


class SendDataToVNyan(VnyanBox):
    name = "data"
    label = "Send data to VNyan"
    help = 'Sends values to VNyan: every "WebSocket Command" node with an EMPTY Command Text runs and gets them ' \
           "in its Data"
    hints = {"data": 'An object like {"command": "throw", "item": "tomato"} (e.g. from Build object). In VNyan a '
                     "Dictionary Values node reads each one by its name"}
    # his 11-22: the nodes to paste into VNyan, a Dictionary Values key for every value
    copies = "vnyan.data_block:Copy VNyan block"

    async def run(self, data: Any) -> None:
        values = _payload(data)
        if not values:
            raise ValueError('Which values? An object like {"command": "throw"}')
        await self._send_text(json.dumps(values, ensure_ascii=False))
