from streamer_toolbox.connections.vnyan.boxes.vnyan_box import VnyanBox


class SendMessageToVNyan(VnyanBox):
    name = "send"
    label = "Send message to VNyan"
    help = 'Sends a message to VNyan: its "WebSocket" node with the same Command Text runs'
    hints = {"message": "The node's Command Text, exactly as written in VNyan",
             "value": "Optional: the node gets it as its Value (a number) and in its Message"}

    async def run(self, message: str, value: str = "") -> None:
        message, value = str(message).strip(), str(value).strip()
        if not message:
            raise ValueError("Which message? It is the Command Text of a WebSocket node in VNyan")
        await self._send_text(f"{message} {value}" if value else message)
