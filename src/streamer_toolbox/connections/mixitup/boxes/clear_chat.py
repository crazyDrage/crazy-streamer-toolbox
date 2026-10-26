from streamer_toolbox.connections.mixitup.boxes.mixitup_box import MixitupBox


class ClearChat(MixitupBox):
    name = "clear_chat"
    label = "Clear chat"
    help = "Clears the chat on every platform"
    group = "Chat"

    async def run(self) -> None:
        await self._send("POST", "chat/clear")
