from streamer_toolbox.connections.vnyan.boxes.send_data_to_vnyan import SendDataToVNyan
from streamer_toolbox.connections.vnyan.boxes.send_message_to_vnyan import SendMessageToVNyan
from streamer_toolbox.connections.vnyan.boxes.vnyan_box import SendText
from streamer_toolbox.connections.vnyan.boxes.vnyan_data_block import VNyanDataBlock
from streamer_toolbox.connections.vnyan.boxes.vnyan_text_block import VNyanTextBlock
from streamer_toolbox.connections.vnyan.vnyan_copy_texts import VNyanCopyTexts
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class VNyanActions:
    """VNyan's boxes. VNyan has no list of things to do from outside: what happens is built in its own node
    graph and given a name there, and the toolbox sends that name (like a SAMMI button).

    - Send message → the graph's "WebSocket Command" node whose Command Text is the message. A whole number
      after a space is the node's Value.
    - Send data → every WebSocket Command node with an empty Command Text; the values are its Data (11-22).
    Each has a "Copy VNyan block" button (the hidden text_block / data_block): the nodes to paste into VNyan.
    (Send API message went 11-22, his "outdated now": Send data does what it did, over the same websocket.)

    One Box class per box, in boxes/."""

    def __init__(self, send_text: SendText) -> None:
        self._send_text = send_text

    def add_to(self, actions: ActionRegistry) -> None:
        texts = VNyanCopyTexts()
        for box in (SendMessageToVNyan(self._send_text), SendDataToVNyan(self._send_text),
                    VNyanTextBlock(texts), VNyanDataBlock(texts)):
            actions.add_box(box, "vnyan")
