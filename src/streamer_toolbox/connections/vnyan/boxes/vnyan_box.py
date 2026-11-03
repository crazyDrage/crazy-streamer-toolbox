import json
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.interfaces.box import Box

SendText = Callable[[str], Awaitable[None]]
SendApi = Callable[[dict[str, Any]], Awaitable[None]]
NOT_AN_OBJECT = 'The values must be an object like {"color": "red"}'


class VnyanBox(Box):
    """What the vnyan boxes share (not a box itself: it has no run).

    VNyan's boxes. VNyan has no list of things to do from outside: what happens is built in its own node
    graph and given a name there, and the toolbox sends that name (like a SAMMI button).

    - Send message → the graph's "WebSocket" node whose Command Text is the message. What follows the message
      after a space is the node's Value.
    - Send API message → the graph's "API Message" node with that Action; the values go along as its payload
      (VNyan wants every payload value as text)."""

    def __init__(self, send_text: SendText, send_api: SendApi) -> None:
        self._send_text = send_text
        self._send_api = send_api


def _payload(values: Any) -> dict[str, str]:
    if values in (None, ""):
        return {}
    if isinstance(values, str):
        try:
            values = json.loads(values)
        except ValueError:
            raise ValueError(NOT_AN_OBJECT) from None
    if not isinstance(values, dict):
        raise ValueError(NOT_AN_OBJECT)
    return {str(key): value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            for key, value in values.items()}
