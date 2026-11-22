from streamer_toolbox.connections.vnyan.vnyan_copy_texts import VNyanCopyTexts
from streamer_toolbox.core.interfaces.box import Box


class VNyanTextBlock(Box):
    """Send message to VNyan's "Copy VNyan block" (his 11-22): a WebSocket Command node with this Command Text and
    Number to Text on its Value, to paste into VNyan. Not in the Add box window."""

    name = "text_block"
    label = "VNyan block for a message"
    help = "The VNyan nodes that run on this message, as a text to paste into a VNyan node graph"
    offered = False

    def __init__(self, texts: VNyanCopyTexts) -> None:
        self._texts = texts

    async def run(self, message: str) -> str:
        return self._texts.text_block(message)
