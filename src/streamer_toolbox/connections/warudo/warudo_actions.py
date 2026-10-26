from streamer_toolbox.connections.warudo.boxes.send_action_to_warudo import SendActionToWarudo
from streamer_toolbox.connections.warudo.boxes.warudo_box import SendText
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class WarudoActions:
    """Warudo's box. Like VNyan, Warudo has no list of things to do from outside: a blueprint in Warudo starts
    with an "On WebSocket Action" node that has an Action Name (and a data type), and the toolbox sends that
    name with a value.

    The message is {"action": <name>, "data": <value>}. NOT CONFIRMED: Warudo's handbook names the port, a
    community tool's docs name the node, but neither shows the message; this shape is from memory. To check
    with the real program before trusting it.

    One Box class per box, in boxes/."""

    def __init__(self, send_text: SendText) -> None:
        self._send_text = send_text

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (SendActionToWarudo(self._send_text),):
            actions.add_box(box, "warudo")
