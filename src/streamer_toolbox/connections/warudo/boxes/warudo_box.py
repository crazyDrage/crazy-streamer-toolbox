from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.interfaces.box import Box


SendText = Callable[[str], Awaitable[None]]


class WarudoBox(Box):
    """What the warudo boxes share (not a box itself: it has no run).

    Warudo's box. Like VNyan, Warudo has no list of things to do from outside: a blueprint in Warudo starts
    with an "On WebSocket Action" node that has an Action Name (and a data type), and the toolbox sends that
    name with a value.

    The message is {"action": <name>, "data": <value>}. NOT CONFIRMED: Warudo's handbook names the port, a
    community tool's docs name the node, but neither shows the message; this shape is from memory. To check
    with the real program before trusting it."""

    def __init__(self, send_text: SendText) -> None:
        self._send_text = send_text


def _value(data: Any) -> Any:
    """A typed "12" or "0.5" goes as a number (the node's type may be Integer or Float); the rest as it is."""
    if not isinstance(data, str):
        return data
    for number in (int, float):
        try:
            return number(data)
        except ValueError:
            pass
    return data
