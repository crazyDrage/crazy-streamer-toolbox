from streamer_toolbox.connections.vnyan.boxes.send_api_message_to_vnyan import SendApiMessageToVNyan
from streamer_toolbox.connections.vnyan.boxes.send_message_to_vnyan import SendMessageToVNyan
from streamer_toolbox.connections.vnyan.boxes.vnyan_box import SendApi, SendText
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class VNyanActions:
    """VNyan's boxes. VNyan has no list of things to do from outside: what happens is built in its own node
    graph and given a name there, and the toolbox sends that name (like a SAMMI button).

    - Send message → the graph's "WebSocket" node whose Command Text is the message. What follows the message
      after a space is the node's Value.
    - Send API message → the graph's "API Message" node with that Action; the values go along as its payload
      (VNyan wants every payload value as text).

    One Box class per box, in boxes/."""

    def __init__(self, send_text: SendText, send_api: SendApi) -> None:
        self._send_text = send_text
        self._send_api = send_api

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (SendMessageToVNyan(self._send_text, self._send_api), SendApiMessageToVNyan(self._send_text,
                    self._send_api)):
            actions.add_box(box, "vnyan")
