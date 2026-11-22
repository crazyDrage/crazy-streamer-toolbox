import json
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.interfaces.box import Box

SendText = Callable[[str], Awaitable[None]]
NOT_AN_OBJECT = 'The values must be an object like {"color": "red"}'


class VnyanBox(Box):
    """What the vnyan boxes that send share (not a box itself: it has no run).

    VNyan's boxes. VNyan has no list of things to do from outside: what happens is built in its own node
    graph and given a name there, and the toolbox sends that name (like a SAMMI button).

    - Send message → the graph's "WebSocket Command" node whose Command Text is the message. A whole number
      after a space is the node's Value.
    - Send data → every WebSocket Command node with an empty Command Text; the values are its Data (11-22)."""

    def __init__(self, send_text: SendText) -> None:
        self._send_text = send_text


def _payload(values: Any) -> dict[str, str]:
    """An object's values, every one as text (VNyan gives every Data value out as text)."""
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
