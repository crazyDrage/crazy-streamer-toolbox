from streamer_toolbox.connections.warudo.boxes.warudo_box import WarudoBox


class SendRawMessageToWarudo(WarudoBox):
    name = "raw"
    label = "Send raw message to Warudo"
    help = 'Sends a text to Warudo as it is: every blueprint that starts with an "On WebSocket Raw Message" node ' \
           "runs and gets the text"
    hints = {"message": "Any text; the node gives it out as it is"}

    async def run(self, message: str) -> None:
        if str(message) == "":
            raise ValueError("Which message? Any text; the On WebSocket Raw Message node gives it out")
        await self._send_text(str(message))
