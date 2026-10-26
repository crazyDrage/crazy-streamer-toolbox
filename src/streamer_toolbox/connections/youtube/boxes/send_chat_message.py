from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.youtube_connection import YouTubeConnection


class SendChatMessage(Box):
    name = "send_chat"
    label = "Send chat message"
    help = 'Writes in your YouTube live chat as you (only while live, and only with "May write in chat" switched ' \
           "on)"
    group = "Chat"

    def __init__(self, youtube: "YouTubeConnection") -> None:
        self._youtube = youtube

    async def run(self, message: str) -> None:
        return await self._youtube.send_chat(message)
