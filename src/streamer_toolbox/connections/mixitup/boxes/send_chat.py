from streamer_toolbox.connections.mixitup.boxes.mixitup_box import MixitupBox, _platforms
from streamer_toolbox.core.data.box_value import to_bool


class SendChat(MixitupBox):
    name = "send_chat"
    label = "Send chat"
    help = "Sends a chat message through Mix It Up"
    group = "Chat"
    options = {"platform": _platforms}
    labels = {"as_streamer": "As you (not the bot)"}

    async def run(self, message: str, platform: str = "All", as_streamer: bool = False) -> None:
        await self._send("POST", "chat/message", json={"Message": str(message), "Platform": platform or "All",
                                                       "SendAsStreamer": to_bool(as_streamer)})
