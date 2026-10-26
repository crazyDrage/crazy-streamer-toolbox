from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.twitch_connection import TwitchConnection


class StreamMarker(Box):
    name = "create_marker"
    label = "Stream marker"
    help = "Puts a stream marker (only while live), e.g. to find a moment later for a clip"
    group = "Stream"

    def __init__(self, twitch: "TwitchConnection") -> None:
        self._twitch = twitch

    async def run(self, description: str = "") -> str:
        return await self._twitch.create_marker(description)
