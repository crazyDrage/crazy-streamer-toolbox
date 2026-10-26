import json
from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_request_box import ObsRequestBox, Call
from streamer_toolbox.connections.obs.obs_protocol import ObsProtocol


class RawRequest(ObsRequestBox):
    name = "request"
    label = "Raw request"
    help = 'Sends OBS any request by name (see the obs-websocket protocol), data as JSON text like {"sceneName": ' \
           '"desktop"}; picking a request fills in its fields. The answer can be saved in a variable; after a test, ' \
           '"Dots from this result" gives the box a dot per key of the answer'
    group = "Advanced"
    flow_only = True

    def __init__(self, call: Call, protocol: ObsProtocol | None = None) -> None:
        super().__init__(call, protocol)
        self.options = {"request": self.request_names}
        self.fills = {"request": self._protocol.template}
        self.live_hints = {"data": self._protocol.hint}

    async def run(self, request: str, data: Any = "") -> dict[str, Any]:
        if isinstance(data, str):
            try:
                data = json.loads(data) if data.strip() else None
            except ValueError as e:
                raise ValueError(f"data is not JSON text: {e}") from None
        if data is not None and not isinstance(data, dict):
            raise ValueError(f"data must be an object like {{\"name\": value}}, not {data!r}")
        return await self._request(request, data)
