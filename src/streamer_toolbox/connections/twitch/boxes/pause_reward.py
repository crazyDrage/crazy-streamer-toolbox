from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.twitch_connection import TwitchConnection


class PauseReward(Box):
    name = "set_reward_paused"
    label = "Pause reward"
    help = "Pauses or unpauses a reward the toolbox made"
    group = "Channel points"

    def __init__(self, twitch: "TwitchConnection") -> None:
        self._twitch = twitch
        self.options = {"reward": self._twitch.reward_choices}

    async def run(self, reward: str, paused: bool = True) -> None:
        return await self._twitch.set_reward_paused(reward, paused)
