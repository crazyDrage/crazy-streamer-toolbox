from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.twitch_connection import TwitchConnection


class RewardOnOff(Box):
    name = "set_reward_enabled"
    label = "Reward on / off"
    help = "Switches a reward the toolbox made on or off (off = viewers don't see it, e.g. for a collab)"
    group = "Channel points"

    def __init__(self, twitch: "TwitchConnection") -> None:
        self._twitch = twitch
        self.options = {"reward": self._twitch.reward_choices}

    async def run(self, reward: str, enabled: bool = True) -> None:
        return await self._twitch.set_reward_enabled(reward, enabled)
