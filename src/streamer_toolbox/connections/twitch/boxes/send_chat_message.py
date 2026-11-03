from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.twitch_connection import TwitchConnection


class SendChatMessage(Box):
    name = "send_chat"
    label = "Send chat message"
    help = "Writes in your chat as you"
    group = "Chat"

    def __init__(self, twitch: "TwitchConnection") -> None:
        self._twitch = twitch

    async def run(self, message: str) -> None:
        return await self._twitch.send_chat(message)
