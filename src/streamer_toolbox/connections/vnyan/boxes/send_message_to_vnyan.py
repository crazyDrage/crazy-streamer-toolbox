from streamer_toolbox.connections.vnyan.boxes.vnyan_box import VnyanBox


class SendMessageToVNyan(VnyanBox):
    name = "send"
    label = "Send message to VNyan"
    help = 'Sends a message to VNyan: its "WebSocket Command" node with the same Command Text runs'
    hints = {"message": "The node's Command Text, exactly as written in VNyan (spaces are fine)",
             "value": "Optional: a whole number, the node's Value (anything else gives 0 there; the node's "
                      "Message always has the whole line)"}
    copies = "vnyan.text_block:Copy VNyan block"  # his 11-22: the node to paste into VNyan, with this message

    async def run(self, message: str, value: str = "") -> None:
        message, value = str(message).strip(), str(value).strip()
        if not message:
            raise ValueError("Which message? It is the Command Text of a WebSocket Command node in VNyan")
        await self._send_text(f"{message} {value}" if value else message)
