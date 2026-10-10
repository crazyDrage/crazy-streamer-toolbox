import json
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry

SendText = Callable[[str], Awaitable[None]]  # one websocket text → Warudo


class WarudoActions:
    """Warudo's box. Like VNyan, Warudo has no list of things to do from outside: a blueprint in Warudo starts
    with an "On WebSocket Action" node that has an Action Name (and a data type), and the toolbox sends that
    name with a value.

    The message is {"action": <name>, "data": <value>}. NOT CONFIRMED: Warudo's handbook names the port, a
    community tool's docs name the node, but neither shows the message; this shape is from memory. To check
    with the real program before trusting it."""

    def __init__(self, send_text: SendText) -> None:
        self._send_text = send_text

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("warudo.send", self.send, 'Sends an action to Warudo: the blueprint that starts with an '
                    '"On WebSocket Action" node of the same Action Name runs', "Send action to Warudo",
                    hints={"action": "The node's Action Name, exactly as written in Warudo",
                           "data": "Optional: the value the node gives out (text or a number, as the node's "
                                   "type says)"})

    async def send(self, action: str, data: Any = "") -> None:
        action = str(action).strip()
        if not action:
            raise ValueError("Which action? It is the Action Name of an On WebSocket Action node in Warudo")
        message: dict[str, Any] = {"action": action}
        if data not in (None, ""):
            message["data"] = _value(data)
        await self._send_text(json.dumps(message, ensure_ascii=False))


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
