from streamer_toolbox.connections.obs.boxes.obs_request_box import Call
from streamer_toolbox.connections.obs.boxes.raw_request import RawRequest
from streamer_toolbox.connections.obs.obs_protocol import ObsProtocol
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class ObsRequestActions:
    """SAMMI's OBS raw request: any obs-websocket request by its name, for what has no box of its own yet.
    Flow only, so no API caller can send OBS any request it likes.

    One Box class per box, in boxes/."""

    def __init__(self, call: Call, protocol: ObsProtocol | None = None) -> None:
        self._call = call
        self._protocol = protocol or ObsProtocol()

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (RawRequest(self._call, self._protocol),):
            actions.add_box(box, "obs")
