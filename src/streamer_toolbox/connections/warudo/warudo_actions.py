from collections.abc import Callable

from streamer_toolbox.connections.warudo.boxes.send_action_to_warudo import SendActionToWarudo
from streamer_toolbox.connections.warudo.boxes.send_raw_message_to_warudo import SendRawMessageToWarudo
from streamer_toolbox.connections.warudo.boxes.warudo_box import SendText
from streamer_toolbox.connections.warudo.boxes.warudo_input_address import WarudoInputAddress
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class WarudoActions:
    """Warudo's boxes. Warudo has two websocket nodes (his round 95): "On WebSocket Raw Message" gets any text
    as it is (raw box), "On WebSocket Action" gets a JSON message with an Action Name (send box).

    Warudo's own help text (Localizations/Warudo.Core.json): raw = "Send a raw string to ws://localhost:19190";
    action = "Send a JSON string like {0}", the {0} filled in by the program. Like VNyan, Warudo has no list of things to do from outside: a blueprint in Warudo starts
    with an "On WebSocket Action" node that has an Action Name (and a data type), and the toolbox sends that
    name with a value.

    The message is {"action": <name>, "data": <value>}. NOT CONFIRMED: Warudo's handbook names the port, a
    community tool's docs name the node, but neither shows the message; this shape is from memory. To check
    with the real program before trusting it.

    One Box class per box, in boxes/."""

    def __init__(self, send_text: SendText, address: Callable[[str], str] | None = None,
                 known: Callable[[], list[str]] = list) -> None:
        self._send_text = send_text
        self._address = address  # None: no incoming addresses (no inbox)
        self._known = known

    def add_to(self, actions: ActionRegistry) -> None:
        boxes = [SendActionToWarudo(self._send_text), SendRawMessageToWarudo(self._send_text)]
        if self._address is not None:
            boxes.append(WarudoInputAddress(self._address, self._known))
        for box in boxes:
            actions.add_box(box, "warudo")
