import json
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry

SendText = Callable[[str], Awaitable[None]]            # one websocket text → VNyan
SendApi = Callable[[dict[str, Any]], Awaitable[None]]  # one {"action", "payload"} → VNyan's web API
NOT_AN_OBJECT = 'The values must be an object like {"color": "red"}'


class VNyanActions:
    """VNyan's boxes. VNyan has no list of things to do from outside: what happens is built in its own node
    graph and given a name there, and the toolbox sends that name (like a SAMMI button).

    - Send message → the graph's "WebSocket" node whose Command Text is the message. What follows the message
      after a space is the node's Value.
    - Send API message → the graph's "API Message" node with that Action; the values go along as its payload
      (VNyan wants every payload value as text)."""

    def __init__(self, send_text: SendText, send_api: SendApi) -> None:
        self._send_text = send_text
        self._send_api = send_api

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("vnyan.send", self.send, 'Sends a message to VNyan: its "WebSocket" node with the same '
                    'Command Text runs', "Send message to VNyan",
                    hints={"message": "The node's Command Text, exactly as written in VNyan",
                           "value": "Optional: the node gets it as its Value (a number) and in its Message"})
        actions.add("vnyan.api_message", self.api_message, 'Sends an API message to VNyan: its "API Message" '
                    'node with the same Action runs and gets the values', "Send API message to VNyan",
                    hints={"action": "The node's Action, exactly as written in VNyan",
                           "values": 'Optional: an object like {"color": "red"}; the node gets it as a '
                                     'dictionary'})

    async def send(self, message: str, value: str = "") -> None:
        message, value = str(message).strip(), str(value).strip()
        if not message:
            raise ValueError("Which message? It is the Command Text of a WebSocket node in VNyan")
        await self._send_text(f"{message} {value}" if value else message)

    async def api_message(self, action: str, values: Any = None) -> None:
        action = str(action).strip()
        if not action:
            raise ValueError("Which action? It is the Action of an API Message node in VNyan")
        await self._send_api({"action": action, "payload": _payload(values)})


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
