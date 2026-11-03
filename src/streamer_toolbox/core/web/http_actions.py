import httpx

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.web.boxes.web_request import WebRequest


class HttpActions:
    """Web requests (SAMMI's HTTP Request), e.g. a vibration board's REST API on the home network.
    The answer comes back as {status, ok, body}; a JSON body is already turned into a list / object.

    One Box class per box, in boxes/."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport  # tests answer without a network

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (WebRequest(self._transport),):
            actions.add_box(box, "web")
