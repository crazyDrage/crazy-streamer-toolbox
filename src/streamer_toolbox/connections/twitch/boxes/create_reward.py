from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.twitch_connection import TwitchConnection


class CreateReward(Box):
    name = "create_reward"
    label = "Create reward"
    help = "Makes a new channel point reward (the toolbox may then pause it)"
    group = "Channel points"

    def __init__(self, twitch: "TwitchConnection") -> None:
        self._twitch = twitch

    async def run(self, title: str, cost: int = 100, prompt: str = "", needs_text: bool = False) -> str:
        return await self._twitch.create_reward(title, cost, prompt, needs_text)
